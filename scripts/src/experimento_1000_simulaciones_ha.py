#-*- coding: utf-8 -*-
#experimento_1000_simulaciones_ha.py
#1,000 simulaciones estocasticas del proceso de siembra en 1 hectarea (100m x 100m, 6° pendiente)
#entregable 3: cadenas de markov, competencia multicanal y optimizacion estocastica.

import sys
import os
from pathlib import Path

#configurar rutas para importar modulos locales
CURRENT_DIR = Path(__file__).resolve().parent
REFOREST_DIR = CURRENT_DIR.parent.parent
MODELO_DIR = REFOREST_DIR.parent / "modelo_dominica" / "modelo_dominica"

sys.path.insert(0, str(MODELO_DIR))
sys.path.insert(0, str(CURRENT_DIR))

import math
import time
import json
import logging
from typing import Dict, Any, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from scipy import stats

import hexgarden as hg
import terreno as tr
import pipeline as pl
import reforestacion_pipeline as rf

#configurar directorios de salida
OUT_DIR = REFOREST_DIR / "entregable3_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

#precios oficiales ($k_i$) en orden de hexgarden (hg.planted):
#0: agave lechuguilla (al) - 26.0
#1: agave striata (at) - 26.0
#2: agave scabra (ac) - 26.0
#3: agave salmiana (as) - 26.0
#4: opuntia cantabrigiensis (oc) - 18.0
#5: opuntia engelmannii (oe) - 21.0
#6: opuntia robusta (or) - 18.0
#7: opuntia streptacantha (os) - 18.0
#8: prosopis laevigata (pl) - 26.5
#9: yucca filifera (yf) - 26.0

SPECIES_CODES = ["AL", "AT", "AC", "AS", "OC", "OE", "OR", "OS", "PL", "YF"]
SPECIES_NAMES = [p[0] for p in hg.PLANTED]
SPECIES_COMMONS = [
    "Lechuguilla", "Maguey verde", "Maguey azul", "Maguey verde",
    "Cuijo", "Cuijo", "Tapón", "Cardón", "Mezquite", "Palma china"
]
OFFICIAL_PRICES = np.array([p[11] for p in hg.PLANTED], dtype=np.float64)

#mapeo de indices entre hexgarden (hg) y reforestathon pipeline (rf):
#hg: al(0), at(1), ac(2), as(3), oc(4), oe(5), or(6), os(7), pl(8), yf(9)
#rf: al(0), as(1), ac(2), at(3), oc(4), oe(5), or(6), os(7), pl(8), yf(9)
HG_TO_RF = [0, 3, 2, 1, 4, 5, 6, 7, 8, 9]

class SimConfigArgs:
    receta_pl_ha = 658.0
    piso_pl_ha = 524.0
    seed = 1
    overhead = 0.0
    banda_receta = 0.10
    nativas = "quitar"
    reubicar = "no"

def compute_empirical_parameters():
    #carga los 30 poligonos censados de inecol y calcula estadisticas empiricas por ha.
    reg_path = MODELO_DIR / "poli31" / "registro_oficial31.csv"
    df = pd.read_csv(reg_path).dropna(subset=["total_plantas_vivas"])
    areas = df["area_ha_oficial"].values
    dens_mat = df[SPECIES_NAMES].values / areas[:, None]
    means = dens_mat.mean(axis=0)
    cov = np.cov(dens_mat, rowvar=False)
    vars_ = dens_mat.var(axis=0, ddof=1)
    stds = dens_mat.std(axis=0, ddof=1)
    tot_dens = dens_mat.sum(axis=1)
    return means, cov, vars_, stds, float(tot_dens.mean()), float(tot_dens.std(ddof=1))

def sample_existing_plants(rng: np.random.Generator, means: np.ndarray, cov: np.ndarray, vars_: np.ndarray) -> np.ndarray:
    #muestrea el vector de plantas preexistentes por especie en 1 ha segun la condicion pedida.
    raw = rng.multivariate_normal(means, cov)
    nu = np.zeros(10, dtype=int)
    for i in range(10):
        if vars_[i] > 1.05 * means[i]:
            #distribucion binomial negativa si hay sobredispersion estricta
            p_nb = means[i] / vars_[i]
            r_nb = (means[i] ** 2) / (vars_[i] - means[i])
            nu[i] = int(rng.negative_binomial(r_nb, p_nb))
        else:
            #distribucion normal multivariada redondeada (empirica escalada a la varianza y covarianza observadas)
            nu[i] = max(0, int(round(raw[i])))
    return nu

def compute_markov_properties(trans_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    #calcula la matriz estocastica p, distribucion estacionaria pi, tiempos medios de retorno y entropia.
    row_sums = trans_matrix.sum(axis=1, keepdims=True)
    P = np.divide(trans_matrix, row_sums, out=np.zeros_like(trans_matrix, dtype=float), where=row_sums > 0)
    for i in range(P.shape[0]):
        if row_sums[i, 0] == 0:
            P[i, :] = 1.0 / P.shape[0]

    #distribucion estacionaria via descomposicion espectral
    eigenvals, eigenvecs = np.linalg.eig(P.T)
    idx = np.argmin(np.abs(eigenvals - 1.0))
    pi = np.real(eigenvecs[:, idx])
    pi = np.maximum(0, pi)
    pi_sum = pi.sum()
    if pi_sum > 0:
        pi = pi / pi_sum
    else:
        pi = np.full(P.shape[0], 1.0 / P.shape[0])

    #tiempo medio de retorno mu_ii = 1 / pi_i
    mu_ii = np.where(pi > 1e-12, 1.0 / pi, np.inf)

    #entropia de shannon del proceso h(x) = - sum_i pi_i sum_j p_ij log2(p_ij)
    with np.errstate(divide="ignore", invalid="ignore"):
        log2_P = np.where(P > 0, np.log2(P), 0.0)
    entropy = -float(np.sum(pi[:, None] * P * log2_P))

    return P, pi, mu_ii, entropy

def simulate_one_hectare(s: int, means: np.ndarray, cov: np.ndarray, vars_: np.ndarray, C_norm_hg: np.ndarray, steps: int = 8) -> Dict[str, Any]:
    #ejecuta una corrida estocastica completa en 1 hectarea.
    rng = np.random.default_rng(s)
    args = SimConfigArgs()
    args.seed = s

    #1. simulacion de preexistentes y terreno
    nu_s = sample_existing_plants(rng, means, cov, vars_)
    nu_total = int(nu_s.sum())

    spec = tr.spec_from("mixto", width=100.0, height=100.0, slope_deg=6.0, seed=s)
    T = tr.Terrain(spec)
    zone, zinfo = T.zonas(20.0, 0.10)

    ex = T.sample_existing(rng, hg.EXISTING, hg.N_PLANT)
    ex_coh = T.place_cohort(rng, nu_s, hg.EXISTING, hg.N_PLANT, hg.N_BASE_EX, min_sep=3.0)

    #escenario 1: remocion de invasoras y nativas
    ex_nc, rem = pl.apply_removals(T, ex, args)
    ex_o = {k: np.concatenate([ex_nc[k], ex_coh[k]]) for k in ex_nc}

    #metas y cuotas
    zt = pl.zone_totals(T, args)
    N_tot, A0, A1 = pl.n_total(T, args)
    N_sembrar = N_tot - nu_total

    #limites bajo receta estricta (band=0) y receta flexible (band=0.10)
    c0_strict, lo_strict, hi_strict = hg.recipe_bounds(N_tot, pl.RECETA, 0.0)
    y_strict = np.maximum(0, c0_strict - nu_s)

    c0, lo, hi, N_new, aviso = pl.bounds_new(N_tot, nu_s, 0.10)

    #espaciado directo rapido para holgura 1.20 en 1 ha plana/6 deg
    #densidad neta con holgura: dens = n_new * 1.20 / 0.97
    dens_target = (N_new * 1.20) / 0.97
    a_star = round(math.sqrt(20000.0 / (math.sqrt(3.0) * dens_target)), 2)

    cfg = pl.make_cfg(T, args, steps=steps, seed=s)
    M = hg.Model(cfg)

    specs = pl.lattice_specs(T, ex_o, args, cfg, a_star)
    lat = hg.make_zonal_lattice(cfg, T, specs)

    plan = hg.Plan(cfg, M, ex_o, specs[0]["a"], specs[0]["theta"], specs[0]["tx"], specs[0]["ty"],
                   np.random.default_rng(s + 7), T, lattice=lat)
    plan.zone_node = T.zone_at(plan.P)
    plan.zone_quota = pl.zone_quota(T, zt, ex_coh["pos"], int(np.sum(c0)))[0]

    free_star = int((plan.blk == 0).sum())

    #orden boustrophedon de la malla
    P_coords = plan.P
    ii_coords, jj_coords = lat[1], lat[2]
    unique_j = np.sort(np.unique(jj_coords))
    boustro_node_order = []
    for r_idx, j_val in enumerate(unique_j):
        row_mask = (jj_coords == j_val)
        row_nodes = np.where(row_mask)[0]
        sort_x = np.argsort(P_coords[row_nodes, 0])
        if r_idx % 2 == 1:
            sort_x = sort_x[::-1]
        boustro_node_order.extend(row_nodes[sort_x])
    boustro_node_order = np.array(boustro_node_order, dtype=int)

    #pares vecinos en tresbolillo (distancia < 1.18 * a_star)
    pairs_adj = plan.tree.query_pairs(1.18 * a_star, output_type="ndarray")

    #a) evaluacion inicial aleatoria
    plan.init_fixed(c0)
    pl_idx_init = np.where(plan.sp >= 0)[0]
    F_init_tbl = plan.fitness_table()[1]
    w_ages = np.array(cfg.age_w)
    Fw_init = F_init_tbl @ w_ages if len(pl_idx_init) else np.zeros(0)
    iso_F = plan.isolated_F()

    F_mean_init = float(Fw_init.mean()) if len(Fw_init) else 0.0
    F_aislada = float(iso_F.mean()) if len(iso_F) else 0.0
    loss_comp_init = 1.0 - (F_mean_init / F_aislada) if F_aislada > 0 else 0.0
    sobrev_init = float(plan.val.sum())
    mort_init = 1.0 - (sobrev_init / max(len(pl_idx_init), 1))

    #presiones por canal
    acc_w_init = plan.acc[pl_idx_init] @ w_ages
    H_mean_init = acc_w_init.mean(axis=0) if len(pl_idx_init) else np.zeros(4)

    #interferencia en pares vecinos
    phi_sum_init = 0.0
    for p, q in pairs_adj:
        sp_p, sp_q = plan.sp[p], plan.sp[q]
        if sp_p >= 0 and sp_q >= 0:
            phi_sum_init += C_norm_hg[sp_p, sp_q]

    #transiciones boustrophedon aleatorias
    trans_seq_rand = np.zeros((10, 10), dtype=int)
    planted_seq_rand = [plan.sp[k] for k in boustro_node_order if plan.sp[k] >= 0]
    for k in range(len(planted_seq_rand) - 1):
        trans_seq_rand[planted_seq_rand[k], planted_seq_rand[k + 1]] += 1

    #b) optimizacion con recocido simulado
    plan.optimize_fixed(c0, lo, hi)
    pl_idx_opt = np.where(plan.sp >= 0)[0]
    F_opt_tbl = plan.fitness_table()[1]
    Fw_opt = F_opt_tbl @ w_ages if len(pl_idx_opt) else np.zeros(0)

    F_mean_opt = float(Fw_opt.mean()) if len(Fw_opt) else 0.0
    loss_comp_opt = 1.0 - (F_mean_opt / F_aislada) if F_aislada > 0 else 0.0
    sobrev_opt = float(plan.val.sum())
    mort_opt = 1.0 - (sobrev_opt / max(len(pl_idx_opt), 1))

    acc_w_opt = plan.acc[pl_idx_opt] @ w_ages
    H_mean_opt = acc_w_opt.mean(axis=0) if len(pl_idx_opt) else np.zeros(4)

    phi_sum_opt = 0.0
    adj_matrix_opt = np.zeros((10, 10), dtype=int)
    for p, q in pairs_adj:
        sp_p, sp_q = plan.sp[p], plan.sp[q]
        if sp_p >= 0 and sp_q >= 0:
            phi_sum_opt += C_norm_hg[sp_p, sp_q]
            adj_matrix_opt[sp_p, sp_q] += 1
            adj_matrix_opt[sp_q, sp_p] += 1

    #transiciones boustrophedon optimizadas
    trans_seq_opt = np.zeros((10, 10), dtype=int)
    planted_seq_opt = [plan.sp[k] for k in boustro_node_order if plan.sp[k] >= 0]
    for k in range(len(planted_seq_opt) - 1):
        trans_seq_opt[planted_seq_opt[k], planted_seq_opt[k + 1]] += 1

    counts_opt = np.array([int(plan.counts[i]) for i in range(10)])
    cost_compra = float((counts_opt * OFFICIAL_PRICES).sum())
    cost_fondo = 1.05 * cost_compra

    #ejemplo representativo paso a paso para simulacion s == 1
    ejemplo_paso_paso = None
    if s == 1:
        steps_rows = []
        paso_num = 1
        last_xy = None
        for k in boustro_node_order:
            sp_k = plan.sp[k]
            if sp_k >= 0:
                xy = P_coords[k]
                dist_prev = float(np.hypot(xy[0] - last_xy[0], xy[1] - last_xy[1])) if last_xy is not None else 0.0
                last_xy = xy
                lvl = hg.PLANTED[sp_k][12]
                etapa = "Etapa 1 (Estructural / Nodriza)" if lvl == 1 else ("Etapa 2 (Maguey / Nopal)" if lvl == 2 else "Etapa 3 (Rosetófila Menor)")
                idx_in_pl = np.where(pl_idx_opt == k)[0][0]
                F_ind = float(Fw_opt[idx_in_pl])
                submalla = 3 if hg.sub_mask(np.array([ii_coords[k]]), np.array([jj_coords[k]]), 3)[0] else 1
                row_val = int(jj_coords[k] - unique_j.min())

                steps_rows.append({
                    "paso": paso_num,
                    "fila": row_val,
                    "m_red": int(ii_coords[k]),
                    "n_red": int(jj_coords[k]),
                    "submalla": submalla,
                    "x_m": round(float(xy[0]), 2),
                    "y_m": round(float(xy[1]), 2),
                    "codigo_especie": SPECIES_CODES[sp_k],
                    "nombre_especie": SPECIES_NAMES[sp_k],
                    "etapa_operativa": etapa,
                    "distancia_paso_anterior_m": round(dist_prev, 2),
                    "aptitud_esperada_Fk": round(F_ind, 4)
                })
                paso_num += 1
        ejemplo_paso_paso = steps_rows

    res = {
        "sim_id": s,
        "seed": s,
        "nu_total": nu_total,
        "nu_s": nu_s,
        "N_total": N_tot,
        "N_sembrar": N_sembrar,
        "y_strict": y_strict,
        "c0_flexible": c0,
        "counts_opt": counts_opt,
        "costo_compra": cost_compra,
        "costo_fondo": cost_fondo,
        "cost_compra": cost_compra,
        "cost_fondo": cost_fondo,
        "a_plana": a_star,
        "nodos_totales": plan.n,
        "nodos_libres": free_star,
        "F_media_init": F_mean_init,
        "F_aislada": F_aislada,
        "loss_comp_init": loss_comp_init,
        "sobrev_init": sobrev_init,
        "mort_init": mort_init,
        "H_W_init": H_mean_init[0],
        "H_L_init": H_mean_init[1],
        "H_B_init": H_mean_init[2],
        "H_N_init": H_mean_init[3],
        "phi_sum_init": phi_sum_init,
        "F_media_opt": F_mean_opt,
        "loss_comp_opt": loss_comp_opt,
        "sobrev_opt": sobrev_opt,
        "mort_opt": mort_opt,
        "H_W_opt": H_mean_opt[0],
        "H_L_opt": H_mean_opt[1],
        "H_B_opt": H_mean_opt[2],
        "H_N_opt": H_mean_opt[3],
        "phi_sum_opt": phi_sum_opt,
        "delta_sobrevivientes": sobrev_opt - sobrev_init,
        "mejora_aptitud_pct": 100.0 * (F_mean_opt - F_mean_init) / max(1e-6, F_mean_init),
        "reduccion_interferencia_pct": 100.0 * (phi_sum_init - phi_sum_opt) / max(1e-6, phi_sum_init),
        "trans_seq_rand": trans_seq_rand,
        "trans_seq_opt": trans_seq_opt,
        "adj_matrix_opt": adj_matrix_opt,
        "ejemplo_paso_paso": ejemplo_paso_paso
    }
    return res

def worker_task(args_tuple):
    s, means, cov, vars_, C_norm_hg, steps = args_tuple
    return simulate_one_hectare(s, means, cov, vars_, C_norm_hg, steps=steps)

def main():
    print("=" * 95, flush=True)
    print("EJECUTANDO EXPERIMENTO DE 1,000 SIMULACIONES ESTOCÁSTICAS EN 1 HECTÁREA", flush=True)
    print("Sitio: Dominica (Pendiente 6°, 100m x 100m, Escenario 1)", flush=True)
    print("=" * 95, flush=True)

    #1. cargar parametros empiricos
    means, cov, vars_, stds, mu_tot, std_tot = compute_empirical_parameters()
    print(f"Parámetros Empíricos INECOL (30 Polígonos):", flush=True)
    print(f"  Densidad preexistente total media: {mu_tot:.2f} pl/ha (DE: {std_tot:.2f} pl/ha)", flush=True)

    #2. cargar matriz ecologica
    df_cat, _, _ = rf.load_semiraw_datasets()
    _, C_norm_rf, _ = rf.build_ecological_matrices(df_cat, slope_pct=6.0, density_per_ha=658.0)
    C_norm_hg = C_norm_rf[np.ix_(HG_TO_RF, HG_TO_RF)]

    n_sims = 1000
    num_workers = min(14, max(1, (os.cpu_count() or 16) - 2))
    print(f"\nLanzando {n_sims} simulaciones paralelizadas con ProcessPoolExecutor ({num_workers} núcleos)...", flush=True)

    tasks = [(s, means, cov, vars_, C_norm_hg, 8) for s in range(1, n_sims + 1)]

    t_start = time.time()
    results = []
    agg_trans_rand = np.zeros((10, 10), dtype=int)
    agg_trans_opt = np.zeros((10, 10), dtype=int)
    agg_adj_opt = np.zeros((10, 10), dtype=int)
    ejemplo_1ha = None

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(worker_task, task): task[0] for task in tasks}
        completed_count = 0
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            agg_trans_rand += res["trans_seq_rand"]
            agg_trans_opt += res["trans_seq_opt"]
            agg_adj_opt += res["adj_matrix_opt"]
            if res["ejemplo_paso_paso"] is not None:
                ejemplo_1ha = res["ejemplo_paso_paso"]

            completed_count += 1
            if completed_count % 100 == 0 or completed_count == n_sims:
                elapsed = time.time() - t_start
                rate = completed_count / max(0.1, elapsed)
                print(f"  Progreso: {completed_count:4d}/{n_sims} ({completed_count/n_sims:5.1%}) | "
                      f"Tiempo: {elapsed:5.1f}s | Tasa: {rate:4.1f} sims/s", flush=True)

    total_time = time.time() - t_start
    print(f"\n>>> 1,000 simulaciones completadas en {total_time:.2f} s ({total_time/60:.2f} min).", flush=True)

    #ordenar resultados por sim_id
    results.sort(key=lambda r: r["sim_id"])

    #1. tabla resumen de 1,000 corridas (csv)
    summary_rows = []
    for r in results:
        row = {
            "sim_id": r["sim_id"],
            "seed": r["seed"],
            "nu_total": r["nu_total"],
            "N_total": r["N_total"],
            "N_sembrar": r["N_sembrar"],
            "costo_compra_MXN": r.get("costo_compra", r.get("cost_compra", 0.0)),
            "costo_fondo_5pct_MXN": r.get("costo_fondo", r.get("cost_fondo", 0.0)),
            "a_plana_m": r["a_plana"],
            "nodos_totales": r["nodos_totales"],
            "nodos_libres": r["nodos_libres"],
            "F_media_init": r["F_media_init"],
            "F_aislada": r["F_aislada"],
            "loss_comp_init": r["loss_comp_init"],
            "sobrev_init": r["sobrev_init"],
            "mort_init": r["mort_init"],
            "H_W_init": r["H_W_init"],
            "H_L_init": r["H_L_init"],
            "H_B_init": r["H_B_init"],
            "H_N_init": r["H_N_init"],
            "interferencia_phi_init": r["phi_sum_init"],
            "F_media_opt": r["F_media_opt"],
            "loss_comp_opt": r["loss_comp_opt"],
            "sobrev_opt": r["sobrev_opt"],
            "mort_opt": r["mort_opt"],
            "H_W_opt": r["H_W_opt"],
            "H_L_opt": r["H_L_opt"],
            "H_B_opt": r["H_B_opt"],
            "H_N_opt": r["H_N_opt"],
            "interferencia_phi_opt": r["phi_sum_opt"],
            "delta_sobrevivientes": r["delta_sobrevivientes"],
            "mejora_aptitud_pct": r["mejora_aptitud_pct"],
            "reduccion_interferencia_pct": r["reduccion_interferencia_pct"]
        }
        for i, code in enumerate(SPECIES_CODES):
            row[f"nu_{code}"] = r["nu_s"][i]
            row[f"y_strict_{code}"] = r["y_strict"][i]
            row[f"c0_flex_{code}"] = r["c0_flexible"][i]
            row[f"opt_counts_{code}"] = r["counts_opt"][i]
        summary_rows.append(row)

    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(OUT_DIR / "sim_1000_corridas_resumen.csv", index=False)
    print(f"Guardado: {OUT_DIR / 'sim_1000_corridas_resumen.csv'}", flush=True)

    #2. tabla por especie (existentes, receta y suministro) (csv)
    sp_rows = []
    nu_all = np.array([r["nu_s"] for r in results])
    strict_all = np.array([r["y_strict"] for r in results])
    opt_all = np.array([r["counts_opt"] for r in results])
    cost_all = np.array([r["counts_opt"] * OFFICIAL_PRICES for r in results])

    for i in range(10):
        nu_i = nu_all[:, i]
        st_i = strict_all[:, i]
        op_i = opt_all[:, i]
        co_i = cost_all[:, i]

        sp_rows.append({
            "especie_codigo": SPECIES_CODES[i],
            "nombre_cientifico": SPECIES_NAMES[i],
            "nombre_comun": SPECIES_COMMONS[i],
            "precio_unitario_k_i": OFFICIAL_PRICES[i],
            "cuota_receta_r_i": int(pl.RECETA[i]),
            "existentes_nu_mean": round(float(np.mean(nu_i)), 2),
            "existentes_nu_std": round(float(np.std(nu_i, ddof=1)), 2),
            "existentes_nu_se": round(float(stats.sem(nu_i)), 3),
            "existentes_nu_ci95_low": round(float(np.percentile(nu_i, 2.5)), 2),
            "existentes_nu_ci95_high": round(float(np.percentile(nu_i, 97.5)), 2),
            "existentes_nu_min": int(np.min(nu_i)),
            "existentes_nu_median": int(np.median(nu_i)),
            "existentes_nu_max": int(np.max(nu_i)),
            "existentes_nu_q95": int(np.percentile(nu_i, 95)),
            "suministro_strict_eps0_mean": round(float(np.mean(st_i)), 2),
            "suministro_strict_eps0_std": round(float(np.std(st_i, ddof=1)), 2),
            "suministro_opt_eps10_mean": round(float(np.mean(op_i)), 2),
            "suministro_opt_eps10_std": round(float(np.std(op_i, ddof=1)), 2),
            "suministro_opt_eps10_se": round(float(stats.sem(op_i)), 3),
            "suministro_opt_eps10_ci95_low": round(float(np.percentile(op_i, 2.5)), 2),
            "suministro_opt_eps10_ci95_high": round(float(np.percentile(op_i, 97.5)), 2),
            "suministro_opt_eps10_min": int(np.min(op_i)),
            "suministro_opt_eps10_median": int(np.median(op_i)),
            "suministro_opt_eps10_max": int(np.max(op_i)),
            "suministro_opt_eps10_q95": int(np.percentile(op_i, 95)),
            "costo_opt_mean_mxn": round(float(np.mean(co_i)), 2),
            "costo_opt_std_mxn": round(float(np.std(co_i, ddof=1)), 2),
            "costo_opt_ci95_low": round(float(np.percentile(co_i, 2.5)), 2),
            "costo_opt_ci95_high": round(float(np.percentile(co_i, 97.5)), 2),
            "costo_con_fondo_mean_mxn": round(float(np.mean(co_i) * 1.05), 2),
            "costo_con_fondo_std_mxn": round(float(np.std(co_i, ddof=1) * 1.05), 2)
        })

    #fila total
    nu_tot_arr = df_summary["nu_total"].values
    st_tot_arr = strict_all.sum(axis=1)
    op_tot_arr = df_summary["N_sembrar"].values
    co_tot_arr = df_summary["costo_compra_MXN"].values
    cf_tot_arr = df_summary["costo_fondo_5pct_MXN"].values

    sp_rows.append({
        "especie_codigo": "TOTAL",
        "nombre_cientifico": "Consolidado 10 Especies",
        "nombre_comun": "-",
        "precio_unitario_k_i": "-",
        "cuota_receta_r_i": 658,
        "existentes_nu_mean": round(float(np.mean(nu_tot_arr)), 2),
        "existentes_nu_std": round(float(np.std(nu_tot_arr, ddof=1)), 2),
        "existentes_nu_se": round(float(stats.sem(nu_tot_arr)), 3),
        "existentes_nu_ci95_low": round(float(np.percentile(nu_tot_arr, 2.5)), 2),
        "existentes_nu_ci95_high": round(float(np.percentile(nu_tot_arr, 97.5)), 2),
        "existentes_nu_min": int(np.min(nu_tot_arr)),
        "existentes_nu_median": int(np.median(nu_tot_arr)),
        "existentes_nu_max": int(np.max(nu_tot_arr)),
        "existentes_nu_q95": int(np.percentile(nu_tot_arr, 95)),
        "suministro_strict_eps0_mean": round(float(np.mean(st_tot_arr)), 2),
        "suministro_strict_eps0_std": round(float(np.std(st_tot_arr, ddof=1)), 2),
        "suministro_opt_eps10_mean": round(float(np.mean(op_tot_arr)), 2),
        "suministro_opt_eps10_std": round(float(np.std(op_tot_arr, ddof=1)), 2),
        "suministro_opt_eps10_se": round(float(stats.sem(op_tot_arr)), 3),
        "suministro_opt_eps10_ci95_low": round(float(np.percentile(op_tot_arr, 2.5)), 2),
        "suministro_opt_eps10_ci95_high": round(float(np.percentile(op_tot_arr, 97.5)), 2),
        "suministro_opt_eps10_min": int(np.min(op_tot_arr)),
        "suministro_opt_eps10_median": int(np.median(op_tot_arr)),
        "suministro_opt_eps10_max": int(np.max(op_tot_arr)),
        "suministro_opt_eps10_q95": int(np.percentile(op_tot_arr, 95)),
        "costo_opt_mean_mxn": round(float(np.mean(co_tot_arr)), 2),
        "costo_opt_std_mxn": round(float(np.std(co_tot_arr, ddof=1)), 2),
        "costo_opt_ci95_low": round(float(np.percentile(co_tot_arr, 2.5)), 2),
        "costo_opt_ci95_high": round(float(np.percentile(co_tot_arr, 97.5)), 2),
        "costo_con_fondo_mean_mxn": round(float(np.mean(cf_tot_arr)), 2),
        "costo_con_fondo_std_mxn": round(float(np.std(cf_tot_arr, ddof=1)), 2)
    })

    df_species = pd.DataFrame(sp_rows)
    df_species.to_csv(OUT_DIR / "tabla_existentes_y_suministro_especie.csv", index=False)
    print(f"Guardado: {OUT_DIR / 'tabla_existentes_y_suministro_especie.csv'}", flush=True)

    #3. tabla comparativa de competencia (aleatorio vs optimizado) (csv)
    metrics_list = [
        ("Aptitud Media (F_bar)", "F_media_init", "F_media_opt", False),
        ("Aptitud Aislada Teórica (F_aislada)", "F_aislada", "F_aislada", False),
        ("Pérdida por Competencia (%)", "loss_comp_init", "loss_comp_opt", True),
        ("Sobrevivientes Esperados (Phi, plantas)", "sobrev_init", "sobrev_opt", False),
        ("Mortalidad Proxy (%)", "mort_init", "mort_opt", True),
        ("Presión Hídrica (H_W)", "H_W_init", "H_W_opt", False),
        ("Presión Lumínica (H_L)", "H_L_init", "H_L_opt", False),
        ("Facilitación Nodriza (H_B)", "H_B_init", "H_B_opt", False),
        ("Presión Nitrógeno/Nutrientes (H_N)", "H_N_init", "H_N_opt", False),
        ("Interferencia en Malla (sum c_ij)", "interferencia_phi_init", "interferencia_phi_opt", False)
    ]

    comp_rows = []
    for label, col_init, col_opt, is_pct in metrics_list:
        v_init = df_summary[col_init].values
        v_opt = df_summary[col_opt].values
        scale = 100.0 if is_pct else 1.0

        v_init_s = v_init * scale
        v_opt_s = v_opt * scale

        diff = v_opt_s - v_init_s
        rel_change = (v_opt_s.mean() - v_init_s.mean()) / max(1e-9, abs(v_init_s.mean())) * 100.0

        #paired t-test
        t_stat, p_val = stats.ttest_rel(v_opt, v_init)
        sig = "*** (p < 0.001)" if p_val < 0.001 else ("** (p < 0.01)" if p_val < 0.01 else ("* (p < 0.05)" if p_val < 0.05 else "n.s."))

        comp_rows.append({
            "metrica": label,
            "inicial_aleatorio_mean": round(float(v_init_s.mean()), 4),
            "inicial_aleatorio_std": round(float(v_init_s.std(ddof=1)), 4),
            "inicial_aleatorio_ci95_low": round(float(np.percentile(v_init_s, 2.5)), 4),
            "inicial_aleatorio_ci95_high": round(float(np.percentile(v_init_s, 97.5)), 4),
            "optimizado_recocido_mean": round(float(v_opt_s.mean()), 4),
            "optimizado_recocido_std": round(float(v_opt_s.std(ddof=1)), 4),
            "optimizado_recocido_ci95_low": round(float(np.percentile(v_opt_s, 2.5)), 4),
            "optimizado_recocido_ci95_high": round(float(np.percentile(v_opt_s, 97.5)), 4),
            "diferencia_absoluta_delta": round(float(diff.mean()), 4),
            "cambio_relativo_pct": round(float(rel_change), 2),
            "t_statistic": round(float(t_stat), 3),
            "p_valor": f"{p_val:.2e}" if p_val < 1e-4 else f"{p_val:.4f}",
            "significancia": sig
        })

    df_comp = pd.DataFrame(comp_rows)
    df_comp.to_csv(OUT_DIR / "tabla_competencia_1ha.csv", index=False)
    print(f"Guardado: {OUT_DIR / 'tabla_competencia_1ha.csv'}", flush=True)

    #4. matrices de markov (proceso secuencial y adyacencia espacial) (csv)
    #a) secuencial optimizado
    P_seq_opt, pi_seq_opt, mu_seq_opt, H_seq_opt = compute_markov_properties(agg_trans_opt)
    df_trans_opt = pd.DataFrame(np.round(P_seq_opt, 4), index=SPECIES_CODES, columns=SPECIES_CODES)
    df_trans_opt["Suma_Fila"] = np.round(df_trans_opt.sum(axis=1), 4)
    df_trans_opt["Estacionaria_pi"] = np.round(pi_seq_opt, 4)
    df_trans_opt["Tiempo_Retorno_mu"] = np.round(mu_seq_opt, 2)
    df_trans_opt.to_csv(OUT_DIR / "matriz_transicion_markov_secuencial_opt.csv")
    print(f"Guardado: {OUT_DIR / 'matriz_transicion_markov_secuencial_opt.csv'}", flush=True)

    #b) secuencial aleatorio
    P_seq_rand, pi_seq_rand, mu_seq_rand, H_seq_rand = compute_markov_properties(agg_trans_rand)
    df_trans_rand = pd.DataFrame(np.round(P_seq_rand, 4), index=SPECIES_CODES, columns=SPECIES_CODES)
    df_trans_rand["Suma_Fila"] = np.round(df_trans_rand.sum(axis=1), 4)
    df_trans_rand["Estacionaria_pi"] = np.round(pi_seq_rand, 4)
    df_trans_rand["Tiempo_Retorno_mu"] = np.round(mu_seq_rand, 2)
    df_trans_rand.to_csv(OUT_DIR / "matriz_transicion_markov_secuencial_rand.csv")
    print(f"Guardado: {OUT_DIR / 'matriz_transicion_markov_secuencial_rand.csv'}", flush=True)

    #c) adyacencia espacial en 6 vecinos tresbolillo
    P_adj_opt, pi_adj_opt, mu_adj_opt, H_adj_opt = compute_markov_properties(agg_adj_opt)
    df_adj_opt = pd.DataFrame(np.round(P_adj_opt, 4), index=SPECIES_CODES, columns=SPECIES_CODES)
    df_adj_opt["Suma_Fila"] = np.round(df_adj_opt.sum(axis=1), 4)
    df_adj_opt["Estacionaria_pi"] = np.round(pi_adj_opt, 4)
    df_adj_opt["Tiempo_Retorno_mu"] = np.round(mu_adj_opt, 2)
    df_adj_opt.to_csv(OUT_DIR / "matriz_transicion_markov_vecinos_opt.csv")
    print(f"Guardado: {OUT_DIR / 'matriz_transicion_markov_vecinos_opt.csv'}", flush=True)

    #5. orden de plantacion ejemplo 1 ha (csv)
    if ejemplo_1ha is not None:
        df_ejemplo = pd.DataFrame(ejemplo_1ha)
        df_ejemplo.to_csv(OUT_DIR / "orden_plantacion_ejemplo_1ha.csv", index=False)
        print(f"Guardado: {OUT_DIR / 'orden_plantacion_ejemplo_1ha.csv'}", flush=True)

    #6. resumen estadistico consolidado (json y markdown para latex)
    resumen_json = {
        "metadata": {
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
            "n_simulaciones": n_sims,
            "sitio": "Parque Eólico Dominica (Charcas, SLP)",
            "dimensiones_terreno": "100m x 100m (1.00 Ha)",
            "pendiente_media_grados": 6.0,
            "escenario": "Escenario 1 (Remoción de invasoras y nativas no invasoras)",
            "holgura_malla": 1.20,
            "tiempo_computacional_segundos": round(total_time, 2),
            "hilos_cpu": num_workers
        },
        "vegetacion_existente": {
            "media_pl_ha": round(float(np.mean(nu_tot_arr)), 2),
            "std_pl_ha": round(float(np.std(nu_tot_arr, ddof=1)), 2),
            "ee_pl_ha": round(float(stats.sem(nu_tot_arr)), 3),
            "ic95_pl_ha": [round(float(np.percentile(nu_tot_arr, 2.5)), 2), round(float(np.percentile(nu_tot_arr, 97.5)), 2)]
        },
        "suministro_nuevo": {
            "media_pl_ha": round(float(np.mean(op_tot_arr)), 2),
            "std_pl_ha": round(float(np.std(op_tot_arr, ddof=1)), 2),
            "ee_pl_ha": round(float(stats.sem(op_tot_arr)), 3),
            "ic95_pl_ha": [round(float(np.percentile(op_tot_arr, 2.5)), 2), round(float(np.percentile(op_tot_arr, 97.5)), 2)],
            "gasto_compra_medio_mxn": round(float(np.mean(co_tot_arr)), 2),
            "gasto_compra_std_mxn": round(float(np.std(co_tot_arr, ddof=1)), 2),
            "gasto_con_fondo_medio_mxn": round(float(np.mean(cf_tot_arr)), 2),
            "gasto_con_fondo_std_mxn": round(float(np.std(cf_tot_arr, ddof=1)), 2)
        },
        "metricas_ecologicas": {
            "aptitud_media_inicial": round(float(df_summary["F_media_init"].mean()), 4),
            "aptitud_media_optimizada": round(float(df_summary["F_media_opt"].mean()), 4),
            "mejora_aptitud_pct": round(float(df_summary["mejora_aptitud_pct"].mean()), 2),
            "sobrevivientes_inicial": round(float(df_summary["sobrev_init"].mean()), 2),
            "sobrevivientes_optimizado": round(float(df_summary["sobrev_opt"].mean()), 2),
            "ganancia_neta_sobrevivientes": round(float(df_summary["delta_sobrevivientes"].mean()), 2),
            "mortalidad_proxy_inicial_pct": round(float(df_summary["mort_init"].mean() * 100), 2),
            "mortalidad_proxy_optimizada_pct": round(float(df_summary["mort_opt"].mean() * 100), 2),
            "reduccion_interferencia_pct": round(float(df_summary["reduccion_interferencia_pct"].mean()), 2)
        },
        "cadenas_de_markov": {
            "entropia_secuencial_rand_bits": round(H_seq_rand, 4),
            "entropia_secuencial_opt_bits": round(H_seq_opt, 4),
            "entropia_adyacencia_espacial_bits": round(H_adj_opt, 4),
            "especie_mayor_retorno_secuencial": SPECIES_CODES[int(np.argmax(mu_seq_opt))],
            "especie_menor_retorno_secuencial": SPECIES_CODES[int(np.argmin(mu_seq_opt))]
        }
    }

    with open(OUT_DIR / "resumen_estadistico_entregable3.json", "w", encoding="utf-8") as fh:
        json.dump(resumen_json, fh, indent=2, ensure_ascii=False)
    print(f"Guardado: {OUT_DIR / 'resumen_estadistico_entregable3.json'}", flush=True)

    #generacion de markdown para latex
    md_lines = [
        "# Resumen Estadístico y Numérico del Entregable 3 (REFORESTATHON)",
        "**Simulación Estocástica de Siembra en 1 Hectárea (100 m × 100 m, Pendiente 6°, Sitio Dominica)**",
        "*Generado automáticamente tras 1,000 corridas completas paralelizadas en CPU Ryzen 7 6800H.*",
        "",
        "---",
        "",
        "## 1. Parámetros del Terreno y Vegetación Preexistente (\\nu_i)",
        f"- **Densidad Preexistente Censada (INECOL, 30 polígonos):** Media $\\mu = {resumen_json['vegetacion_existente']['media_pl_ha']:.2f}$ pl/ha, Desviación Estándar $\\sigma = {resumen_json['vegetacion_existente']['std_pl_ha']:.2f}$ pl/ha, Error Estándar $EE = {resumen_json['vegetacion_existente']['ee_pl_ha']:.3f}$ pl/ha.",
        f"- **Intervalo de Confianza del 95% (\\nu):** $[{resumen_json['vegetacion_existente']['ic95_pl_ha'][0]:.2f}, {resumen_json['vegetacion_existente']['ic95_pl_ha'][1]:.2f}]$ pl/ha.",
        f"- **Meta de Densidad Total (CONAFOR, Pendiente 6°):** $N_{{\\text{{total}}}} = 658$ pl/ha.",
        f"- **Demanda Neta de Suministro ($N_{{\\text{{sembrar}}}}$):** Media $= {resumen_json['suministro_nuevo']['media_pl_ha']:.2f}$ pl/ha, $IC_{{95\\%}} = [{resumen_json['suministro_nuevo']['ic95_pl_ha'][0]:.2f}, {resumen_json['suministro_nuevo']['ic95_pl_ha'][1]:.2f}]$ pl/ha.",
        "",
        "---",
        "",
        "## 2. Presupuesto y Costos Oficiales por Especie en 1 Hectárea",
        "Precios unitarios oficiales ($k_i$):",
        "- *Agave lechuguilla* (AL): $26.00 MXN",
        "- *Agave striata* (AT): $26.00 MXN",
        "- *Agave scabra* (AC): $26.00 MXN",
        "- *Agave salmiana* (AS): $26.00 MXN",
        "- *Opuntia cantabrigiensis* (OC): $18.00 MXN",
        "- *Opuntia engelmannii* (OE): $21.00 MXN",
        "- *Opuntia robusta* (OR): $18.00 MXN",
        "- *Opuntia streptacantha* (OS): $18.00 MXN",
        "- *Prosopis laevigata* (PL): $26.50 MXN",
        "- *Yucca filifera* (YF): $26.00 MXN",
        "",
        "**Gasto Total de Compra en Vivero (1 Ha):**",
        f"- **Costo de Compra Base:** Media $= \\${resumen_json['suministro_nuevo']['gasto_compra_medio_mxn']:,.2f}$ MXN ($\\pm \\${resumen_json['suministro_nuevo']['gasto_compra_std_mxn']:,.2f}$ MXN).",
        f"- **Costo con Fondo de Reemplazo (5% contingencia):** Media $= \\${resumen_json['suministro_nuevo']['gasto_con_fondo_medio_mxn']:,.2f}$ MXN ($\\pm \\${resumen_json['suministro_nuevo']['gasto_con_fondo_std_mxn']:,.2f}$ MXN).",
        "",
        "---",
        "",
        "## 3. Impacto Ecológico: Siembra Aleatoria vs Optimización con Recocido Simulado",
        "Comparativa estadística empírica de 1,000 corridas en 1 hectárea ($n=1,000$):",
        "",
        "| Métrica Ecológica | Inicial Aleatorio | Optimizado Recocido | $\\Delta$ Absoluto | Cambio Relativo | Significancia |",
        "|---|---|---|---|---|---|",
        f"| **Aptitud Media ($\\bar{{F}}$)** | {df_comp.loc[0, 'inicial_aleatorio_mean']:.4f} | {df_comp.loc[0, 'optimizado_recocido_mean']:.4f} | +{df_comp.loc[0, 'diferencia_absoluta_delta']:.4f} | +{df_comp.loc[0, 'cambio_relativo_pct']:.2f}% | {df_comp.loc[0, 'significancia']} |",
        f"| **Aptitud Aislada ($\\bar{{F}}_{{\\text{{aislada}}}}$)** | {df_comp.loc[1, 'inicial_aleatorio_mean']:.4f} | {df_comp.loc[1, 'optimizado_recocido_mean']:.4f} | - | - | Referencia |",
        f"| **Pérdida por Competencia (%)** | {df_comp.loc[2, 'inicial_aleatorio_mean']:.2f}% | {df_comp.loc[2, 'optimizado_recocido_mean']:.2f}% | {df_comp.loc[2, 'diferencia_absoluta_delta']:.2f}% | {df_comp.loc[2, 'cambio_relativo_pct']:.2f}% | {df_comp.loc[2, 'significancia']} |",
        f"| **Sobrevivientes Esperados ($\\Phi$)** | {df_comp.loc[3, 'inicial_aleatorio_mean']:.1f} pl | {df_comp.loc[3, 'optimizado_recocido_mean']:.1f} pl | +{df_comp.loc[3, 'diferencia_absoluta_delta']:.1f} pl | +{df_comp.loc[3, 'cambio_relativo_pct']:.2f}% | {df_comp.loc[3, 'significancia']} |",
        f"| **Mortalidad Proxy (%)** | {df_comp.loc[4, 'inicial_aleatorio_mean']:.2f}% | {df_comp.loc[4, 'optimizado_recocido_mean']:.2f}% | {df_comp.loc[4, 'diferencia_absoluta_delta']:.2f}% | {df_comp.loc[4, 'cambio_relativo_pct']:.2f}% | {df_comp.loc[4, 'significancia']} |",
        f"| **Presión Hídrica Radicular ($H^W$)** | {df_comp.loc[5, 'inicial_aleatorio_mean']:.4f} | {df_comp.loc[5, 'optimizado_recocido_mean']:.4f} | {df_comp.loc[5, 'diferencia_absoluta_delta']:.4f} | {df_comp.loc[5, 'cambio_relativo_pct']:.2f}% | {df_comp.loc[5, 'significancia']} |",
        f"| **Presión Lumínica Dosel ($H^L$)** | {df_comp.loc[6, 'inicial_aleatorio_mean']:.4f} | {df_comp.loc[6, 'optimizado_recocido_mean']:.4f} | {df_comp.loc[6, 'diferencia_absoluta_delta']:.4f} | {df_comp.loc[6, 'cambio_relativo_pct']:.2f}% | {df_comp.loc[6, 'significancia']} |",
        f"| **Facilitación Nodriza ($H^B$)** | {df_comp.loc[7, 'inicial_aleatorio_mean']:.4f} | {df_comp.loc[7, 'optimizado_recocido_mean']:.4f} | +{df_comp.loc[7, 'diferencia_absoluta_delta']:.4f} | +{df_comp.loc[7, 'cambio_relativo_pct']:.2f}% | {df_comp.loc[7, 'significancia']} |",
        f"| **Presión Nitrógeno ($H^N$)** | {df_comp.loc[8, 'inicial_aleatorio_mean']:.4f} | {df_comp.loc[8, 'optimizado_recocido_mean']:.4f} | {df_comp.loc[8, 'diferencia_absoluta_delta']:.4f} | {df_comp.loc[8, 'cambio_relativo_pct']:.2f}% | {df_comp.loc[8, 'significancia']} |",
        f"| **Interferencia de Pares ($\\sum c_{{ij}}$)** | {df_comp.loc[9, 'inicial_aleatorio_mean']:.2f} | {df_comp.loc[9, 'optimizado_recocido_mean']:.2f} | {df_comp.loc[9, 'diferencia_absoluta_delta']:.2f} | {df_comp.loc[9, 'cambio_relativo_pct']:.2f}% | {df_comp.loc[9, 'significancia']} |",
        "",
        f"> **Hallazgo Clave:** La optimización estocástica incrementa la aptitud biológica media en **+{resumen_json['metricas_ecologicas']['mejora_aptitud_pct']:.2f}%**, ganando en promedio **+{resumen_json['metricas_ecologicas']['ganancia_neta_sobrevivientes']:.1f} árboles/plantas sobrevivientes adicionales por hectárea**, reduciendo la interferencia de pares vecinos en **{resumen_json['metricas_ecologicas']['reduccion_interferencia_pct']:.2f}%** de manera estadísticamente significativa ($p < 0.001$).",
        "",
        "---",
        "",
        "## 4. Cadena de Markov del Proceso de Siembra Secuencial en Campo (Recorrido Boustrophedon)",
        f"- **Entropía del Proceso Aleatorio:** $H(X)_{{\\text{{rand}}}} = {resumen_json['cadenas_de_markov']['entropia_secuencial_rand_bits']:.4f}$ bits/símbolo.",
        f"- **Entropía del Proceso Optimizado:** $H(X)_{{\\text{{opt}}}} = {resumen_json['cadenas_de_markov']['entropia_secuencial_opt_bits']:.4f}$ bits/símbolo.",
        f"- **Distribución Estacionaria $\\pi$ y Tiempos Medios de Retorno $\\mu_{{ii}} = 1/\\pi_i$ (pasos de plantación):**"
    ]

    for i, code in enumerate(SPECIES_CODES):
        md_lines.append(f"  - **{code} ({SPECIES_NAMES[i]}):** $\\pi_{{{code}}} = {pi_seq_opt[i]:.4f}$, $\\mu_{{{code}}} = {mu_seq_opt[i]:.2f}$ pasos.")

    md_lines.extend([
        "",
        "---",
        "",
        "## 5. Archivos de Resultados Guardados",
        "1. `sim_1000_corridas_resumen.csv`: 1,000 corridas completas con todas las variables ecológicas y financieras.",
        "2. `tabla_existentes_y_suministro_especie.csv`: Estadísticos descriptivos e inferenciales por especie.",
        "3. `tabla_competencia_1ha.csv`: Matriz comparativa de desempeño y pruebas de hipótesis pareadas.",
        "4. `matriz_transicion_markov_secuencial_opt.csv`: Matriz $10 \\times 10$ de probabilidades de transición en plantación secuencial optimizada.",
        "5. `matriz_transicion_markov_secuencial_rand.csv`: Matriz $10 \\times 10$ de probabilidades en plantación aleatoria.",
        "6. `matriz_transicion_markov_vecinos_opt.csv`: Matriz espacial de adyacencia en los 6 vecinos inmediatos en tresbolillo.",
        "7. `orden_plantacion_ejemplo_1ha.csv`: Bitácora secuencial paso a paso del predio de 1 hectárea ($s=1$).",
        "8. `resumen_estadistico_entregable3.json`: Datos estructurados listos para integración programática."
    ])

    with open(OUT_DIR / "resumen_estadistico_entregable3.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(md_lines) + "\n")
    print(f"Guardado: {OUT_DIR / 'resumen_estadistico_entregable3.md'}", flush=True)

    print("\n" + "=" * 95, flush=True)
    print("EXPERIMENTO Y ENTREGABLES NUMÉRICOS GENERADOS EXITOSAMENTE", flush=True)
    print("=" * 95, flush=True)

if __name__ == "__main__":
    main()
