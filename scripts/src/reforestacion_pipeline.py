# -*- coding: utf-8 -*-
"""
Pipeline CONAFOR sincronizado con la estructura de REFORESTATHON:
- Lee datos reales desde: REFORESTATHON/data/semiraw/*.csv
- Guarda resultados en:   REFORESTATHON/scripts/outputs/
- Guarda bitácoras en:    REFORESTATHON/scripts/logs/
Optimizado para Windows: AMD Ryzen 7 6800H (16 hilos) + 32 GB RAM + RTX 3060 (6 GB VRAM)
"""

import os
import gc
import time
import math
import logging
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch

# ==============================================================================
# 1. CONFIGURACIÓN DE RUTAS SEGÚN TU ÁRBOL DE DIRECTORIOS EN VS CODE
# ==============================================================================
# Ubicación actual del script: REFORESTATHON/scripts/src/reforestacion_pipeline.py
SRC_DIR = Path(__file__).resolve().parent          # .../REFORESTATHON/scripts/src
SCRIPTS_DIR = SRC_DIR.parent                       # .../REFORESTATHON/scripts
ROOT_DIR = SCRIPTS_DIR.parent                      # .../REFORESTATHON
DATA_DIR = ROOT_DIR / "data" / "semiraw"           # .../REFORESTATHON/data/semiraw
OUT_DIR = SCRIPTS_DIR / "outputs"                  # .../REFORESTATHON/scripts/outputs
LOG_DIR = SCRIPTS_DIR / "logs"                     # .../REFORESTATHON/scripts/logs

OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "execution.log", mode="w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("REFORESTATHON")

PRESUPUESTO_POR_HA = 13200.0  # Presupuesto de referencia en datos_inecol.xlsx ($)


# ==============================================================================
# 2. CARGA DE DATOS DESDE data/semiraw/ (CON RESPALDO INTERNO)
# ==============================================================================

def load_semiraw_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, List[int]]:
    """
    Carga catalogo_especies_consolidado.csv, poligonos_plantas_wide.csv
    y orden_plantacion_100m.csv desde REFORESTATHON/data/semiraw/.
    """
    cat_path = DATA_DIR / "catalogo_especies_consolidado.csv"
    wide_path = DATA_DIR / "poligonos_plantas_wide.csv"
    row_path = DATA_DIR / "orden_plantacion_100m.csv"

    if not (cat_path.exists() and wide_path.exists() and row_path.exists()):
        raise FileNotFoundError(
            f"No se encontraron todos los CSVs en {DATA_DIR}. "
            f"Verifica la carpeta data/semiraw/."
        )

    df_cat = pd.read_csv(cat_path)
    df_wide = pd.read_csv(wide_path)
    df_row = pd.read_csv(row_path)

    # Normalizar catálogo de especies y agregar género taxonómico y rol funcional
    df_cat["especie"] = df_cat["especie"].str.strip()
    df_cat["id"] = np.arange(len(df_cat))
    df_cat["genero"] = df_cat["especie"].apply(lambda s: s.split()[0])

    def _assign_role(gen: str) -> str:
        if gen == "Prosopis":
            return "Nodriza"
        if gen == "Agave":
            return "Rosetofila"
        if gen == "Opuntia":
            return "Cactacea"
        return "Arborescente"

    df_cat["rol"] = df_cat["genero"].apply(_assign_role)

    # Mapear la fila muestra de 22 posiciones en 100m a los IDs (0..9)
    sp_to_id: Dict[str, int] = dict(zip(df_cat["especie"], df_cat["id"]))
    baseline_row_22: List[int] = [sp_to_id[str(sp).strip()] for sp in df_row["especie"]]

    logger.info(f"Datos cargados exitosamente desde: {DATA_DIR}")
    logger.info(
        f"Catálogo: {len(df_cat)} especies | Polígonos: {len(df_wide)} | "
        f"Fila 100m: {len(baseline_row_22)} posiciones."
    )
    return df_cat, df_wide, baseline_row_22


# ==============================================================================
# 3. MATRIZ DE COMPETENCIA c_ij EN [0,1] Y PONDERACIÓN DE SUPERVIVENCIA 2023
# ==============================================================================

def build_ecological_matrices(
    df_cat: pd.DataFrame,
    lam: float = 1.0
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """
    Construye la matriz de competencia base c_ij en escala [0, 1] y la pondera
    simétricamente usando el inverso de la tasa de supervivencia de 2023.
    """
    df = df_cat.copy()
    df["s_2023"] = df["supervivencia_2023_pct"] / 100.0
    df["inv_s2023"] = 1.0 / df["s_2023"]

    inv_min = float(df["inv_s2023"].min())
    inv_max = float(df["inv_s2023"].max())
    # Reescalamiento Min-Max del inverso de supervivencia hacia [1, 1 + lam]
    df["w_vuln"] = 1.0 + lam * (df["inv_s2023"] - inv_min) / (inv_max - inv_min)

    n = len(df)
    C_base = np.zeros((n, n), dtype=np.float64)

    for i in range(n):
        for j in range(n):
            if i == j:
                # Competencia intraespecífica máxima (mismo estrato radicular y lumínico)
                C_base[i, j] = 1.00
            elif df.loc[i, "genero"] == df.loc[j, "genero"]:
                # Competencia intragenérica (mismo género)
                C_base[i, j] = 0.80 if df.loc[i, "genero"] == "Agave" else 0.75
            elif df.loc[i, "genero"] == "Prosopis" or df.loc[j, "genero"] == "Prosopis":
                # Efecto nodriza del mezquite (Prosopis laevigata) con otras especies
                C_base[i, j] = 0.05
            else:
                # Competencia intergenérica moderada
                C_base[i, j] = 0.35

    w = df["w_vuln"].to_numpy(dtype=np.float64)
    # Matriz efectiva simétrica: Phi_ij = c_ij * (w_i + w_j) / 2
    Phi = C_base * (w[:, None] + w[None, :]) / 2.0
    return df, C_base, Phi


# ==============================================================================
# 4. SIMULACIÓN MONTE CARLO EN RTX 3060 PARA CANTIDAD A ADQUIRIR
# ==============================================================================

def run_monte_carlo_rtx3060(
    df_species: pd.DataFrame,
    df_wide: pd.DataFrame,
    target_area_ha: float = 1.0,
    n_sims: int = 1_000_000
) -> pd.DataFrame:
    """
    Ajusta distribuciones discretas (Binomial Negativa / Poisson) a las densidades
    por hectárea observadas en los 30 polígonos y simula N escenarios en GPU.
    """
    t0 = time.perf_counter()
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if dev.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True

    sp_names = df_species["especie"].tolist()
    poly_ha = df_wide["dimension_ha"].to_numpy(dtype=np.float64)          # (30,)
    established = df_wide[sp_names].to_numpy(dtype=np.float64).T          # (10, 30)

    # Densidad empírica (plantas existentes por hectárea) en los 30 polígonos
    densities_per_ha = established / poly_ha[None, :]
    mean_dens = densities_per_ha.mean(axis=1)
    var_dens = densities_per_ha.var(axis=1, ddof=1)

    results = []
    torch.manual_seed(42)

    for i, row in df_species.iterrows():
        idx = int(row["id"])
        r_i = int(round(float(row["plantas_por_ha"]) * target_area_ha))
        mu = float(mean_dens[idx]) * target_area_ha
        sigma2 = float(var_dens[idx]) * (target_area_ha ** 2)

        if sigma2 > mu * 1.05:
            p_nb = mu / sigma2
            r_nb = (mu ** 2) / (sigma2 - mu)
            dist_name = f"NegBin(r={r_nb:.1f}, p={p_nb:.2f})"
            rate = torch.distributions.Gamma(
                concentration=torch.tensor(r_nb, device=dev, dtype=torch.float32),
                rate=torch.tensor(p_nb / (1.0 - p_nb), device=dev, dtype=torch.float32)
            ).sample(torch.Size([n_sims]))
            E_samples = torch.poisson(rate)
        else:
            dist_name = f"Poisson(λ={mu:.1f})"
            E_samples = torch.poisson(torch.full((n_sims,), float(mu), device=dev, dtype=torch.float32))

        F_samples = torch.clamp(float(r_i) - E_samples, min=0.0)
        f_mean = float(F_samples.mean().item())
        f_std = float(F_samples.std().item())
        se = f_std / math.sqrt(n_sims)
        q50 = float(torch.quantile(F_samples, 0.50).item())
        q95 = float(torch.quantile(F_samples, 0.95).item())
        prob_shortage = float((F_samples > round(f_mean)).float().mean().item())

        results.append({
            "especie": row["especie"],
            "nombre_comun": row["nombre_comun"],
            "requerimiento_ri": r_i,
            "existencia_media_Ei": round(mu, 2),
            "distribucion_ajustada": dist_name,
            "compra_esperada_E_Fi": round(f_mean, 2),
            "IC95_inf": round(f_mean - 1.96 * se, 2),
            "IC95_sup": round(f_mean + 1.96 * se, 2),
            "pedido_mediana_Q50": int(round(q50)),
            "pedido_seguro_Q95": int(round(q95)),
            "prob_faltante_en_media_%": round(prob_shortage * 100.0, 1)
        })

    if dev.type == "cuda":
        torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) * 1000.0
    logger.info(f"Monte Carlo en {dev} ({n_sims:,} escenarios x 10 especies) completado en {dt:.2f} ms.")

    df_mc = pd.DataFrame(results)
    costo_unitario = PRESUPUESTO_POR_HA / 658.0
    df_mc["costo_esp_MXN"] = np.round(df_mc["compra_esperada_E_Fi"] * costo_unitario, 2)
    df_mc.to_csv(OUT_DIR / "monte_carlo_compras.csv", index=False)
    return df_mc


# ==============================================================================
# 5. MALLA 2D EN TRES BOLILLOS Y GRAFO ESPARSO DE VECINDAD N(p)
# ==============================================================================

@dataclass
class HexGridGraph:
    coords: np.ndarray
    edge_u: np.ndarray
    edge_v: np.ndarray
    edge_dist: np.ndarray
    edge_weight: np.ndarray
    step_d: float
    r_crit: float


def build_tres_bolillos_graph(
    n_rows: int,
    n_cols: int,
    density_per_ha: float = 658.0,
    ring_level: int = 1
) -> HexGridGraph:
    """
    Construye la malla bidimensional en tres bolillos y el conjunto de aristas
    de vecindad N(p) podando pares cuya distancia supere el radio crítico R_crit.
    """
    step_d = math.sqrt(20000.0 / (density_per_ha * math.sqrt(3.0)))
    r_crit = step_d * 1.08 if ring_level == 1 else step_d * 1.80

    coords_list = []
    for r in range(n_rows):
        for c in range(n_cols):
            u = (c + 0.5 * (r % 2)) * step_d
            v = r * (math.sqrt(3.0) / 2.0) * step_d
            coords_list.append((u, v))
    coords = np.array(coords_list, dtype=np.float64)

    m = len(coords)
    diff = coords[:, None, :] - coords[None, :, :]
    dist_mat = np.linalg.norm(diff, axis=-1)

    u_idx, v_idx = np.where((np.triu(dist_mat, k=1) > 1e-6) & (np.triu(dist_mat, k=1) <= r_crit))
    dists = dist_mat[u_idx, v_idx]
    weights = step_d / dists

    total_possible = m * (m - 1) // 2
    sparsity_saving = 100.0 * (1.0 - len(u_idx) / max(1, total_possible))
    logger.info(
        f"Malla 2D Tres Bolillos {n_rows}x{n_cols} (|P|={m}, d={step_d:.2f}m, R_crit={r_crit:.2f}m): "
        f"{len(u_idx)} aristas activas de {total_possible} pares ({sparsity_saving:.1f}% poda)."
    )
    return HexGridGraph(coords, u_idx, v_idx, dists, weights, step_d, r_crit)


def compute_exact_quotas(proportions: np.ndarray, total_positions: int) -> np.ndarray:
    """Calcula cuotas enteras r_i cuya suma coincide exactamente con |P|."""
    raw = proportions * total_positions
    quotas = np.floor(raw).astype(int)
    rem = int(total_positions - quotas.sum())
    if rem > 0:
        top_idx = np.argsort(raw - quotas)[::-1][:rem]
        quotas[top_idx] += 1
    return quotas


def evaluate_assignment_cost(assignment: np.ndarray, graph: HexGridGraph, Phi: np.ndarray) -> float:
    return float(np.sum(graph.edge_weight * Phi[assignment[graph.edge_u], assignment[graph.edge_v]]))


# ==============================================================================
# 6. WARM-START EN RTX 3060 + RELEVO TÉRMICO HACIA EL RYZEN 7 6800H
# ==============================================================================

def gpu_parallel_annealing_warmstart(
    graph: HexGridGraph,
    Phi: np.ndarray,
    quotas: np.ndarray,
    fixed_nodes: Optional[Dict[int, int]] = None,
    n_replicas: int = 1024,
    n_steps: int = 8000
) -> Tuple[np.ndarray, float]:
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    m = len(graph.coords)
    fixed_nodes = fixed_nodes or {}

    rem_quotas = quotas.copy()
    for pos, sp in fixed_nodes.items():
        if rem_quotas[sp] > 0:
            rem_quotas[sp] -= 1

    free_positions = [p for p in range(m) if p not in fixed_nodes]
    free_pool = np.repeat(np.arange(len(quotas)), rem_quotas)
    if len(free_pool) < len(free_positions):
        free_pool = np.concatenate([free_pool, np.zeros(len(free_positions) - len(free_pool), dtype=int)])
    free_pool = free_pool[:len(free_positions)]

    states_np = np.zeros((n_replicas, m), dtype=np.int64)
    rng = np.random.default_rng(42)
    for b in range(n_replicas):
        for pos, sp in fixed_nodes.items():
            states_np[b, pos] = sp
        states_np[b, free_positions] = rng.permutation(free_pool)

    states = torch.tensor(states_np, device=dev, dtype=torch.long)
    Phi_t = torch.tensor(Phi, device=dev, dtype=torch.float32)
    edge_u_t = torch.tensor(graph.edge_u, device=dev, dtype=torch.long)
    edge_v_t = torch.tensor(graph.edge_v, device=dev, dtype=torch.long)
    edge_w_t = torch.tensor(graph.edge_weight, device=dev, dtype=torch.float32)
    free_pos_t = torch.tensor(free_positions, device=dev, dtype=torch.long)

    def batch_cost(st: torch.Tensor) -> torch.Tensor:
        return (Phi_t[st[:, edge_u_t], st[:, edge_v_t]] * edge_w_t[None, :]).sum(dim=1)

    curr_costs = batch_cost(states)
    best_idx = int(torch.argmin(curr_costs).item())
    best_cost = float(curr_costs[best_idx].item())
    best_state = states[best_idx].clone()

    t0 = time.perf_counter()
    temps = torch.linspace(1.5, 0.005, n_steps, device=dev)
    n_free = len(free_positions)
    batch_indices = torch.arange(n_replicas, device=dev)

    for step in range(n_steps):
        T = temps[step]
        idx1 = free_pos_t[torch.randint(0, n_free, (n_replicas,), device=dev)]
        idx2 = free_pos_t[torch.randint(0, n_free, (n_replicas,), device=dev)]

        val1 = states[batch_indices, idx1]
        val2 = states[batch_indices, idx2]
        states[batch_indices, idx1] = val2
        states[batch_indices, idx2] = val1

        new_costs = batch_cost(states)
        delta = new_costs - curr_costs
        accept = (delta < 0) | (torch.rand(n_replicas, device=dev) < torch.exp(-delta / T))
        reject = ~accept

        states[batch_indices[reject], idx1[reject]] = val1[reject]
        states[batch_indices[reject], idx2[reject]] = val2[reject]
        curr_costs = torch.where(accept, new_costs, curr_costs)

        min_c, min_i = torch.min(curr_costs, dim=0)
        if float(min_c.item()) < best_cost:
            best_cost = float(min_c.item())
            best_state = states[int(min_i.item())].clone()

    best_np = best_state.cpu().numpy()
    dt = time.perf_counter() - t0
    logger.info(
        f"Warm-Start RTX 3060 ({n_replicas} réplicas x {n_steps} pasos) "
        f"en {dt:.2f}s -> Costo = {best_cost:.4f}"
    )

    # Liberar VRAM para ceder todo el margen térmico al Ryzen 7 6800H
    del states, Phi_t, edge_u_t, edge_v_t, edge_w_t, free_pos_t, curr_costs, best_state
    gc.collect()
    if dev.type == "cuda":
        torch.cuda.empty_cache()

    return best_np, best_cost


# ==============================================================================
# 7. SOLVER EXACTO EN RYZEN 7 6800H (LINEALIZACIÓN AGREGADA RLT)
# ==============================================================================

def solve_exact_ryzen6800h(
    graph: HexGridGraph,
    Phi: np.ndarray,
    quotas: np.ndarray,
    warm_assignment: np.ndarray,
    fixed_nodes: Optional[Dict[int, int]] = None,
    tolerance_pct: float = 0.0,
    time_limit: int = 120,
    cpu_threads: int = 14
) -> Tuple[np.ndarray, float, float, str]:
    """
    Resuelve el modelo exacto mediante Linealización Agregada de Glover/RLT:
    z_e >= sum_j Phi_ij * x_jq - M_i * (1 - x_ip) para todo i in I.
    Intenta usar Gurobi primero y hace fallback transparente a HiGHS multihilo.
    """
    m = len(graph.coords)
    n_sp = len(quotas)
    n_edges = len(graph.edge_u)
    fixed_nodes = fixed_nodes or {}
    M_i = Phi.max(axis=1)

    # 1. Intentar con Gurobi (si cuenta con licencia académica activa)
    try:
        import gurobipy as gp  # type: ignore
        from gurobipy import GRB  # type: ignore

        env = gp.Env(empty=True)
        env.setParam("OutputFlag", 1)
        env.start()
        model = gp.Model("CONAFOR_Ryzen6800H", env=env)
        model.setParam("TimeLimit", time_limit)
        model.setParam("Threads", cpu_threads)
        model.setParam("SoftMemLimit", 24.0)

        x = model.addVars(n_sp, m, vtype=GRB.BINARY, name="x")
        z = model.addVars(n_edges, lb=0.0, vtype=GRB.CONTINUOUS, name="z")

        for p in range(m):
            for i in range(n_sp):
                x[i, p].Start = 1.0 if warm_assignment[p] == i else 0.0

        for p in range(m):
            model.addConstr(gp.quicksum(x[i, p] for i in range(n_sp)) == 1, name=f"one_sp_{p}")

        for p, sp_fixed in fixed_nodes.items():
            model.addConstr(x[sp_fixed, p] == 1, name=f"fixed_{p}")

        for i in range(n_sp):
            lb = int(math.floor(quotas[i] * (1.0 - tolerance_pct)))
            ub = int(math.ceil(quotas[i] * (1.0 + tolerance_pct)))
            if tolerance_pct == 0.0:
                model.addConstr(gp.quicksum(x[i, p] for p in range(m)) == int(quotas[i]), name=f"quota_{i}")
            else:
                model.addConstr(gp.quicksum(x[i, p] for p in range(m)) >= lb, name=f"quota_lb_{i}")
                model.addConstr(gp.quicksum(x[i, p] for p in range(m)) <= ub, name=f"quota_ub_{i}")

        for e in range(n_edges):
            p, q = int(graph.edge_u[e]), int(graph.edge_v[e])
            for i in range(n_sp):
                model.addConstr(
                    z[e] >= gp.quicksum(float(Phi[i, j]) * x[j, q] for j in range(n_sp))
                    - float(M_i[i]) * (1 - x[i, p])
                )

        model.setObjective(
            gp.quicksum(float(graph.edge_weight[e]) * z[e] for e in range(n_edges)),
            GRB.MINIMIZE
        )
        model.write(str(OUT_DIR / "modelo_conafor.lp"))
        model.optimize()

        sol = np.zeros(m, dtype=int)
        for p in range(m):
            for i in range(n_sp):
                if x[i, p].X > 0.5:
                    sol[p] = i
        return sol, float(model.ObjVal), float(model.MIPGap * 100.0), f"Gurobi ({cpu_threads} hilos)"

    except Exception as e:
        logger.warning(f"Pasando a Solver Exacto HiGHS en Ryzen 6800H (Detalle Gurobi: {e})")

    # 2. Fallback Exacto Open-Source con PuLP + HiGHS multihilo
    import pulp  # type: ignore

    prob = pulp.LpProblem("CONAFOR_TresBolillos_RLT", pulp.LpMinimize)
    x = pulp.LpVariable.dicts("x", (range(n_sp), range(m)), cat="Binary")
    z = pulp.LpVariable.dicts("z", range(n_edges), lowBound=0.0, cat="Continuous")

    for p in range(m):
        for i in range(n_sp):
            x[i][p].setInitialValue(1 if warm_assignment[p] == i else 0)
    for e in range(n_edges):
        p, q = int(graph.edge_u[e]), int(graph.edge_v[e])
        z[e].setInitialValue(float(Phi[warm_assignment[p], warm_assignment[q]]))

    prob += pulp.lpSum(float(graph.edge_weight[e]) * z[e] for e in range(n_edges))

    for p in range(m):
        prob += pulp.lpSum(x[i][p] for i in range(n_sp)) == 1, f"one_sp_{p}"

    for p, sp_fixed in fixed_nodes.items():
        prob += x[sp_fixed][p] == 1, f"fixed_{p}"

    for i in range(n_sp):
        lb = int(math.floor(quotas[i] * (1.0 - tolerance_pct)))
        ub = int(math.ceil(quotas[i] * (1.0 + tolerance_pct)))
        if tolerance_pct == 0.0:
            prob += pulp.lpSum(x[i][p] for p in range(m)) == int(quotas[i]), f"quota_{i}"
        else:
            prob += pulp.lpSum(x[i][p] for p in range(m)) >= lb, f"quota_lb_{i}"
            prob += pulp.lpSum(x[i][p] for p in range(m)) <= ub, f"quota_ub_{i}"

    for e in range(n_edges):
        p, q = int(graph.edge_u[e]), int(graph.edge_v[e])
        for i in range(n_sp):
            prob += (
                z[e] >= pulp.lpSum(float(Phi[i, j]) * x[j][q] for j in range(n_sp))
                - float(M_i[i]) * (1 - x[i][p])
            )

    prob.writeLP(str(OUT_DIR / "modelo_conafor.lp"))

    try:
        solver = pulp.HiGHS(msg=True, timeLimit=time_limit, threads=cpu_threads, warmStart=True)
        prob.solve(solver)
        solver_name = f"HiGHS ({cpu_threads} hilos)"
    except Exception:
        solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=time_limit, threads=cpu_threads, warmStart=True)
        prob.solve(solver)
        solver_name = f"CBC ({cpu_threads} hilos)"

    sol = warm_assignment.copy()
    if pulp.value(prob.objective) is not None:
        for p in range(m):
            for i in range(n_sp):
                val = pulp.value(x[i][p])
                if val is not None and val > 0.5:
                    sol[p] = i

    final_cost = evaluate_assignment_cost(sol, graph, Phi)
    return sol, final_cost, 0.0, solver_name


# ==============================================================================
# 8. EXPORTACIÓN DE VISUALIZACIONES CIENTÍFICAS EN scripts/outputs/
# ==============================================================================

def export_visualizations(
    df_species: pd.DataFrame,
    Phi: np.ndarray,
    graph: HexGridGraph,
    assignment: np.ndarray,
    fixed_nodes: Dict[int, int]
) -> None:
    fig, ax = plt.subplots(figsize=(9, 7.5), dpi=200)
    im = ax.imshow(Phi, cmap="YlOrRd")
    names = [f"{r['especie']} (w={r['w_vuln']:.2f})" for _, r in df_species.iterrows()]
    ax.set_xticks(range(len(names)))
    ax.set_yticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8.5)
    ax.set_yticklabels(names, fontsize=8.5)
    for i in range(len(names)):
        for j in range(len(names)):
            ax.text(
                j, i, f"{Phi[i, j]:.2f}", ha="center", va="center",
                color="white" if Phi[i, j] > 0.85 else "black", fontsize=7.5
            )
    plt.colorbar(im, ax=ax, label="Penalización Efectiva $\\Phi_{ij} = c_{ij}(w_i+w_j)/2$")
    ax.set_title("Matriz de Competencia Ponderada por Inverso de Supervivencia 2023", fontsize=11, pad=12)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "matriz_competencia_phi.png")
    plt.close()

    fig, ax = plt.subplots(figsize=(11, 7.5), dpi=200)
    for e in range(len(graph.edge_u)):
        u, v = int(graph.edge_u[e]), int(graph.edge_v[e])
        ax.plot(
            [graph.coords[u, 0], graph.coords[v, 0]],
            [graph.coords[u, 1], graph.coords[v, 1]],
            color="#cccccc", linewidth=0.8, zorder=1
        )

    cmap = plt.get_cmap("tab10")
    for _, row in df_species.iterrows():
        sp_id = int(row["id"])
        mask = (assignment == sp_id)
        if np.any(mask):
            ax.scatter(
                graph.coords[mask, 0], graph.coords[mask, 1],
                s=160, color=cmap(sp_id), edgecolors="black", linewidths=0.8,
                label=f"{row['especie']} (n={mask.sum()})", zorder=3
            )

    if fixed_nodes:
        f_idx = list(fixed_nodes.keys())
        ax.scatter(
            graph.coords[f_idx, 0], graph.coords[f_idx, 1],
            s=280, facecolors="none", edgecolors="red", linewidths=2.2,
            label="Planta Preexistente (Fija)", zorder=4
        )

    ax.set_aspect("equal")
    ax.set_xlabel("Distancia Longitudinal X (m)")
    ax.set_ylabel("Distancia Transversal Y (m)")
    ax.set_title("Distribución Óptima en Malla 2D Tres Bolillos con Grafo de Vecindad $N(p)$", fontsize=11)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8.5, frameon=True)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "mapa_tres_bolillos_optimo.png")
    plt.close()


# ==============================================================================
# 9. EJECUCIÓN PRINCIPAL
# ==============================================================================

def main() -> None:
    default_threads = max(1, (os.cpu_count() or 16) - 2)  # 14 hilos en Ryzen 7 6800H

    parser = argparse.ArgumentParser(description="Pipeline REFORESTATHON (Ryzen 6800H + RTX 3060)")
    parser.add_argument("--rows", type=int, default=6, help="Filas de la malla 2D en tres bolillos")
    parser.add_argument("--cols", type=int, default=11, help="Columnas de la malla 2D en tres bolillos")
    parser.add_argument("--ring", type=int, default=1, choices=[1, 2], help="Anillo de vecindad N(p)")
    parser.add_argument("--time-limit", type=int, default=90, help="Tiempo límite del solver exacto (s)")
    parser.add_argument("--threads", type=int, default=default_threads, help="Hilos de CPU para el solver")
    parser.add_argument("--poligono-id", type=int, default=0, help="ID del polígono (1..30) o 0 para usar --polygon-ha")
    parser.add_argument("--polygon-ha", type=float, default=1.0, help="Hectáreas si --poligono-id es 0")
    args = parser.parse_args()

    logger.info("=== INICIANDO PIPELINE REFORESTATHON (RYZEN 7 6800H + RTX 3060) ===")
    if torch.cuda.is_available():
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        logger.info(f"GPU Activa: {torch.cuda.get_device_name(0)} ({vram_gb:.1f} GB VRAM, CUDA {torch.version.cuda})")
    logger.info(f"Hilos de CPU asignados al Solver Exacto: {args.threads} de {os.cpu_count()}.")

    # 1. Cargar CSVs reales desde data/semiraw/
    df_cat, df_wide, baseline_row_22 = load_semiraw_datasets()

    # Determinar área objetivo según --poligono-id o --polygon-ha
    if 1 <= args.poligono_id <= len(df_wide):
        poly_row = df_wide[df_wide["poligono_id"] == args.poligono_id].iloc[0]
        target_ha = float(poly_row["dimension_ha"])
        logger.info(f"Simulando {poly_row['poligono']} (ID={args.poligono_id}, Área={target_ha:.2f} Ha)")
    else:
        target_ha = args.polygon_ha
        logger.info(f"Simulando área estándar de {target_ha:.2f} Ha")

    # 2. Construir matrices ecológicas y pesos de vulnerabilidad 2023
    df_sp, C_base, Phi = build_ecological_matrices(df_cat, lam=1.0)
    logger.info(
        "\nCatálogo Consolidado y Pesos de Prioridad (Inverso Supervivencia 2023):\n"
        + df_sp[["especie", "nombre_comun", "plantas_por_ha", "supervivencia_2023_pct", "inv_s2023", "w_vuln"]].to_string(index=False)
    )

    # 3. Simulación Monte Carlo en RTX 3060
    df_mc = run_monte_carlo_rtx3060(df_sp, df_wide, target_area_ha=target_ha, n_sims=1_000_000)
    logger.info(
        f"\nResultados Monte Carlo de Compra ({target_ha:.2f} Ha):\n"
        + df_mc[["especie", "requerimiento_ri", "existencia_media_Ei", "compra_esperada_E_Fi", "pedido_seguro_Q95", "costo_esp_MXN"]].to_string(index=False)
    )

    # 4. Benchmark sobre orden_plantacion_100m.csv (22 posiciones)
    graph_1d = build_tres_bolillos_graph(n_rows=1, n_cols=len(baseline_row_22), density_per_ha=658.0, ring_level=1)
    base_arr = np.array(baseline_row_22, dtype=int)
    base_cost_1d = evaluate_assignment_cost(base_arr, graph_1d, Phi)
    quotas_22 = np.bincount(base_arr, minlength=len(df_sp))
    warm_1d, _ = gpu_parallel_annealing_warmstart(graph_1d, Phi, quotas_22, n_replicas=512, n_steps=3000)
    opt_1d, opt_cost_1d, _, _ = solve_exact_ryzen6800h(
        graph_1d, Phi, quotas_22, warm_1d, time_limit=20, cpu_threads=args.threads
    )
    logger.info(
        f"\n[Benchmark orden_plantacion_100m.csv] Costo Original = {base_cost_1d:.4f} | "
        f"Costo Óptimo = {opt_cost_1d:.4f} (Reducción = {100.0*(base_cost_1d - opt_cost_1d)/base_cost_1d:.2f}%)"
    )

    # 5. Optimización en Malla 2D Tres Bolillos
    graph_2d = build_tres_bolillos_graph(n_rows=args.rows, n_cols=args.cols, density_per_ha=658.0, ring_level=args.ring)
    m_nodes = args.rows * args.cols
    proportions = df_sp["proporcion_programa"].to_numpy(dtype=np.float64)
    quotas_2d = compute_exact_quotas(proportions, m_nodes)
    fixed_nodes_2d = {0: 1, m_nodes // 2: 8, m_nodes - 1: 6}

    rng = np.random.default_rng(123)
    init_cost_2d = evaluate_assignment_cost(
        rng.permutation(np.repeat(np.arange(len(df_sp)), quotas_2d)), graph_2d, Phi
    )

    warm_2d, warm_cost_2d = gpu_parallel_annealing_warmstart(
        graph_2d, Phi, quotas_2d, fixed_nodes=fixed_nodes_2d, n_replicas=1024, n_steps=8000
    )
    opt_2d, exact_cost_2d, _, solver_used = solve_exact_ryzen6800h(
        graph_2d, Phi, quotas_2d, warm_2d, fixed_nodes=fixed_nodes_2d,
        time_limit=args.time_limit, cpu_threads=args.threads
    )

    logger.info(
        f"\n[Malla 2D Tres Bolillos {args.rows}x{args.cols}] Aleatorio = {init_cost_2d:.4f} | "
        f"Warm-Start RTX 3060 = {warm_cost_2d:.4f} | Exacto ({solver_used}) = {exact_cost_2d:.4f} "
        f"(Mejora Total: {100.0*(init_cost_2d - exact_cost_2d)/init_cost_2d:.2f}%)"
    )

    df_out = pd.DataFrame({
        "posicion_p": np.arange(m_nodes),
        "x_m": np.round(graph_2d.coords[:, 0], 2),
        "y_m": np.round(graph_2d.coords[:, 1], 2),
        "especie_id": opt_2d,
        "especie": [df_sp.loc[i, "especie"] for i in opt_2d],
        "nombre_comun": [df_sp.loc[i, "nombre_comun"] for i in opt_2d],
        "es_preexistente": [p in fixed_nodes_2d for p in range(m_nodes)]
    })
    df_out.to_csv(OUT_DIR / "asignacion_optima_2d.csv", index=False)
    export_visualizations(df_sp, Phi, graph_2d, opt_2d, fixed_nodes_2d)
    logger.info(f"=== FINALIZADO. Archivos exportados en: {OUT_DIR} ===")


if __name__ == "__main__":
    main()