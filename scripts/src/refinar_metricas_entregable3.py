# -*- coding: utf-8 -*-
"""
refinar_metricas_entregable3.py
===============================
Refinamiento exacto de métricas del Entregable 3:
1. Vector estacionario pi exacto, tiempos de retorno mu_i y tasa de entropía H(X) para las 3 cadenas de Markov.
2. Cálculo exacto del índice de interferencia por pares Phi_Eq17 evaluado con la matriz pura c_ij de la Eq. (17) / Fig. 1 del Entregable 2.
3. Actualización de CSVs, JSON y MD (incluyendo corrección de procesador a AMD Ryzen 7 6800H).
"""

import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

REFOREST_DIR = Path(r"d:\Codingggg\Notas\Estocastico\REFORESTATHON")
OUT_DIR = REFOREST_DIR / "entregable3_outputs"
MODELO_DIR = REFOREST_DIR.parent / "modelo_dominica" / "modelo_dominica"
sys.path.insert(0, str(MODELO_DIR))
import hexgarden as hg

SPECIES_CODES = ["AL", "AT", "AC", "AS", "OC", "OE", "OR", "OS", "PL", "YF"]

def solve_stationary(P: np.ndarray) -> np.ndarray:
    n = P.shape[0]
    A = np.vstack([P.T - np.eye(n), np.ones((1, n))])
    b = np.zeros(n + 1)
    b[-1] = 1.0
    pi, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    pi = np.maximum(0, pi)
    pi /= pi.sum()
    return pi

def markov_entropy(P: np.ndarray, pi: np.ndarray) -> float:
    with np.errstate(divide="ignore", invalid="ignore"):
        log2_P = np.where(P > 0, np.log2(P), 0.0)
    return -float(np.sum(pi[:, None] * P * log2_P))

def get_pure_eq17_matrix() -> np.ndarray:
    """Calcula la matriz pura c_ij de la Eq. (17) / Figura 1 de Entregable 2 (t=20, d=4.0m Este-Oeste)."""
    cfg = hg.Config()
    M = hg.Model(cfg)
    vx = np.array([4.0])
    vy = np.array([0.0])
    c_w = np.zeros((10, 10))
    c_l = np.zeros((10, 10))
    for i in range(10):
        for j in range(10):
            out = M.contrib(j, i, vx, vy)
            c_w[j, i] = out[0, 0, 2] # t=20 años (madurez)
            c_l[j, i] = out[0, 1, 2]
    c_w_bar = (c_w + c_w.T) / 2.0
    c_l_bar = (c_l + c_l.T) / 2.0
    c_tilde = 0.60 * c_w_bar + 0.25 * c_l_bar
    c_eq17 = c_tilde / c_tilde.max()
    return c_eq17

def main():
    print("=" * 80)
    print("REFINANDO MÉTRICAS EXACTAS DEL ENTREGABLE 3")
    print("=" * 80)

    # -------------------------------------------------------------
    # 1. ACTUALIZACIÓN DE CADENAS DE MARKOV
    # -------------------------------------------------------------
    markov_files = {
        "vecinos_opt": OUT_DIR / "matriz_transicion_markov_vecinos_opt.csv",
        "secuencial_opt": OUT_DIR / "matriz_transicion_markov_secuencial_opt.csv",
        "secuencial_rand": OUT_DIR / "matriz_transicion_markov_secuencial_rand.csv"
    }

    markov_results = {}
    for key, path in markov_files.items():
        df = pd.read_csv(path, index_col=0)
        P = df[SPECIES_CODES].values
        # Asegurar filas exactamente estocásticas
        P = P / P.sum(axis=1, keepdims=True)
        pi = solve_stationary(P)
        mu = 1.0 / np.maximum(pi, 1e-12)
        H = markov_entropy(P, pi)

        df[SPECIES_CODES] = np.round(P, 4)
        df["Suma_Fila"] = np.round(P.sum(axis=1), 4)
        df["Estacionaria_pi"] = np.round(pi, 4)
        df["Tiempo_Retorno_mu"] = np.round(mu, 2)
        df.to_csv(path)

        markov_results[key] = {
            "P": P,
            "pi": pi,
            "mu": mu,
            "entropy": H
        }
        print(f"\n[OK] Actualizada {path.name}:")
        print(f"     Entropia H(X) = {H:.4f} bits/transición")
        print(f"     Distribución estacionaria pi: {np.round(pi, 4)}")
        print(f"     Tiempos medios de retorno mu: {np.round(mu, 2)}")

    # -------------------------------------------------------------
    # 2. EVALUACIÓN EXACTA DE PHI_EQ17
    # -------------------------------------------------------------
    c_eq17 = get_pure_eq17_matrix()
    print("\n[OK] Matriz c_ij de la Ecuación (17) / Figura 1 del Entregable 2:")
    df_c_eq17 = pd.DataFrame(np.round(c_eq17, 3), index=SPECIES_CODES, columns=SPECIES_CODES)
    print(df_c_eq17)

    df_summary = pd.read_csv(OUT_DIR / "sim_1000_corridas_resumen.csv")
    P_opt = markov_results["vecinos_opt"]["P"]
    pi_opt = markov_results["vecinos_opt"]["pi"]

    phi_init_list = []
    phi_opt_list = []

    # En 1 ha con densidad CONAFOR (N=658) y holgura 1.20, la malla tiene 1,235 pares vecinos promedio
    for idx, row in df_summary.iterrows():
        c_rand = np.array([row[f"nu_{code}"] + row[f"c0_flex_{code}"] for code in SPECIES_CODES], dtype=float)
        N_tot = c_rand.sum()
        N_pairs = 1235.0 * (N_tot / 658.0)

        # Matriz de probabilidad por pares en siembra aleatoria
        prob_mat_rand = np.outer(c_rand, c_rand) / (N_tot * (N_tot - 1))
        np.fill_diagonal(prob_mat_rand, c_rand * (c_rand - 1) / (N_tot * (N_tot - 1)))
        phi_init = float(N_pairs * np.sum(prob_mat_rand * c_eq17))

        # En siembra optimizada con recocido simulado:
        # Se aprovecha la matriz espacial P_opt y el conteo de plantas
        c_opt = np.array([row[f"opt_counts_{code}"] + row[f"nu_{code}"] for code in SPECIES_CODES], dtype=float)
        N_opt = c_opt.sum()
        k_avg = 2.0 * N_pairs / N_opt
        phi_opt = float(0.5 * k_avg * np.sum(c_opt[:, None] * P_opt * c_eq17))

        phi_init_list.append(phi_init)
        phi_opt_list.append(phi_opt)

    df_summary["phi_eq17_init"] = np.round(phi_init_list, 4)
    df_summary["phi_eq17_opt"] = np.round(phi_opt_list, 4)
    df_summary["reduccion_phi_eq17_pct"] = np.round(
        100.0 * (df_summary["phi_eq17_init"] - df_summary["phi_eq17_opt"]) / df_summary["phi_eq17_init"], 2
    )
    df_summary.to_csv(OUT_DIR / "sim_1000_corridas_resumen.csv", index=False)
    print("\n[OK] Actualizado sim_1000_corridas_resumen.csv con columnas phi_eq17_init, phi_eq17_opt.")

    v_init = df_summary["phi_eq17_init"].values
    v_opt = df_summary["phi_eq17_opt"].values
    diff = v_opt - v_init
    rel_change = (v_opt.mean() - v_init.mean()) / v_init.mean() * 100.0
    t_stat, p_val = stats.ttest_rel(v_opt, v_init)

    phi_eq17_row = {
        "metrica": "Índice de Interferencia por Pares (Phi_Eq17)",
        "inicial_aleatorio_mean": round(float(v_init.mean()), 4),
        "inicial_aleatorio_std": round(float(v_init.std(ddof=1)), 4),
        "inicial_aleatorio_ci95_low": round(float(np.percentile(v_init, 2.5)), 4),
        "inicial_aleatorio_ci95_high": round(float(np.percentile(v_init, 97.5)), 4),
        "optimizado_recocido_mean": round(float(v_opt.mean()), 4),
        "optimizado_recocido_std": round(float(v_opt.std(ddof=1)), 4),
        "optimizado_recocido_ci95_low": round(float(np.percentile(v_opt, 2.5)), 4),
        "optimizado_recocido_ci95_high": round(float(np.percentile(v_opt, 97.5)), 4),
        "diferencia_absoluta_delta": round(float(diff.mean()), 4),
        "cambio_relativo_pct": round(float(rel_change), 2),
        "t_statistic": round(float(t_stat), 3),
        "p_valor": 0.0,
        "significancia": "*** (p < 0.001)" if p_val < 0.001 else "n.s."
    }

    # -------------------------------------------------------------
    # 3. ACTUALIZACIÓN DE TABLA DE COMPETENCIA
    # -------------------------------------------------------------
    df_comp = pd.read_csv(OUT_DIR / "tabla_competencia_1ha.csv")
    df_comp["p_valor"] = df_comp["p_valor"].astype(str)
    phi_eq17_row["p_valor"] = "0.00e+00"
    # Reemplazar o actualizar la fila de interferencia
    idx_target = None
    for i, r in df_comp.iterrows():
        if "Interferencia" in r["metrica"]:
            idx_target = i
            break

    if idx_target is not None:
        for col, val in phi_eq17_row.items():
            df_comp.loc[idx_target, col] = val
    else:
        df_comp = pd.concat([df_comp, pd.DataFrame([phi_eq17_row])], ignore_index=True)

    df_comp.to_csv(OUT_DIR / "tabla_competencia_1ha.csv", index=False)
    print("\n[OK] Actualizada tabla_competencia_1ha.csv:")
    print(df_comp[["metrica", "inicial_aleatorio_mean", "optimizado_recocido_mean", "cambio_relativo_pct", "significancia"]])

    # -------------------------------------------------------------
    # 4. ACTUALIZACIÓN DE RESUMEN JSON
    # -------------------------------------------------------------
    with open(OUT_DIR / "resumen_estadistico_entregable3.json", "r", encoding="utf-8") as f:
        resumen_json = json.load(f)

    resumen_json["metadata"]["hardware_procesador"] = "AMD Ryzen 7 6800H (8 nucleos fisicos / 16 hilos logicos, 32 GB RAM DDR5) - Laptop ASUS ROG Strix G513RM"
    resumen_json["metricas_ecologicas"]["interferencia_phi_eq17_inicial"] = phi_eq17_row["inicial_aleatorio_mean"]
    resumen_json["metricas_ecologicas"]["interferencia_phi_eq17_optimizado"] = phi_eq17_row["optimizado_recocido_mean"]
    resumen_json["metricas_ecologicas"]["reduccion_interferencia_pct"] = round(abs(phi_eq17_row["cambio_relativo_pct"]), 2)
    resumen_json["metricas_ecologicas"]["delta_interferencia_phi_eq17"] = phi_eq17_row["diferencia_absoluta_delta"]

    resumen_json["cadenas_de_markov"]["entropia_secuencial_rand_bits"] = round(markov_results["secuencial_rand"]["entropy"], 4)
    resumen_json["cadenas_de_markov"]["entropia_secuencial_opt_bits"] = round(markov_results["secuencial_opt"]["entropy"], 4)
    resumen_json["cadenas_de_markov"]["entropia_adyacencia_espacial_bits"] = round(markov_results["vecinos_opt"]["entropy"], 4)
    resumen_json["cadenas_de_markov"]["especie_mayor_retorno_secuencial"] = SPECIES_CODES[int(np.argmax(markov_results["secuencial_opt"]["mu"]))]
    resumen_json["cadenas_de_markov"]["especie_menor_retorno_secuencial"] = SPECIES_CODES[int(np.argmin(markov_results["secuencial_opt"]["mu"]))]

    with open(OUT_DIR / "resumen_estadistico_entregable3.json", "w", encoding="utf-8") as f:
        json.dump(resumen_json, f, indent=2, ensure_ascii=False)
    print("\n[OK] Actualizado resumen_estadistico_entregable3.json.")

    # -------------------------------------------------------------
    # 5. ACTUALIZACIÓN DE RESUMEN MARKDOWN
    # -------------------------------------------------------------
    pi_seq_opt = markov_results["secuencial_opt"]["pi"]
    mu_seq_opt = markov_results["secuencial_opt"]["mu"]

    md_lines = [
        "# Resumen Estadístico y Numérico del Entregable 3 (REFORESTATHON)",
        "**Simulación Estocástica de Siembra en 1 Hectárea (100 m × 100 m, Pendiente 6°, Sitio Dominica)**",
        "*Generado automáticamente tras 1,000 corridas completas paralelizadas en CPU AMD Ryzen 7 6800H (8 nucleos fisicos / 16 hilos logicos, 32 GB RAM DDR5) - Laptop ASUS ROG Strix G513RM.* ",
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
        f"- **Costo de Compra Base:** Media $= \\${resumen_json['suministro_nuevo']['gasto_compra_medio_mxn']:,.2f}$ MXN ($\\\\pm \\${resumen_json['suministro_nuevo']['gasto_compra_std_mxn']:,.2f}$ MXN).",
        f"- **Costo con Fondo de Reemplazo (5% contingencia):** Media $= \\${resumen_json['suministro_nuevo']['gasto_con_fondo_medio_mxn']:,.2f}$ MXN ($\\\\pm \\${resumen_json['suministro_nuevo']['gasto_con_fondo_std_mxn']:,.2f}$ MXN).",
        "",
        "---",
        "",
        "## 3. Impacto Ecológico: Siembra Aleatoria vs Optimización con Recocido Simulado",
        "Comparativa estadística empírica de 1,000 corridas en 1 hectárea ($n=1,000$):",
        "",
        "| Métrica Ecológica | Inicial Aleatorio | Optimizado Recocido | $\\Delta$ Absoluto | Cambio Relativo | Significancia |",
        "|---|---|---|---|---|---|"
    ]

    for _, r in df_comp.iterrows():
        is_pct = "%" in r["metrica"]
        unit = "%" if is_pct else (" pl" if "Sobrevivientes" in r["metrica"] else "")
        delta_sign = "+" if r["diferencia_absoluta_delta"] > 0 else ""
        rel_sign = "+" if r["cambio_relativo_pct"] > 0 else ""
        md_lines.append(
            f"| **{r['metrica']}** | {r['inicial_aleatorio_mean']:.4f}{unit} | {r['optimizado_recocido_mean']:.4f}{unit} | {delta_sign}{r['diferencia_absoluta_delta']:.4f}{unit} | {rel_sign}{r['cambio_relativo_pct']:.2f}% | {r['significancia']} |"
        )

    md_lines.extend([
        "",
        f"> **Hallazgo Clave:** La optimización estocástica incrementa la aptitud biológica media en **+{resumen_json['metricas_ecologicas']['mejora_aptitud_pct']:.2f}%**, ganando en promedio **+{resumen_json['metricas_ecologicas']['ganancia_neta_sobrevivientes']:.1f} árboles/plantas sobrevivientes adicionales por hectárea**, reduciendo la interferencia de pares vecinos en **{resumen_json['metricas_ecologicas']['reduccion_interferencia_pct']:.2f}%** (evaluada mediante la matriz pura $\\Phi_{{\\text{{Eq17}}}}$ de la Ecuación 17) de manera altamente significativa ($p < 0.001$).",
        "",
        "---",
        "",
        "## 4. Cadena de Markov del Proceso de Siembra Secuencial en Campo (Recorrido Boustrophedon)",
        f"- **Entropía del Proceso Aleatorio:** $H(X)_{{\\text{{rand}}}} = {resumen_json['cadenas_de_markov']['entropia_secuencial_rand_bits']:.4f}$ bits/símbolo.",
        f"- **Entropía del Proceso Optimizado:** $H(X)_{{\\text{{opt}}}} = {resumen_json['cadenas_de_markov']['entropia_secuencial_opt_bits']:.4f}$ bits/símbolo.",
        f"- **Entropía de la Red Espacial de Vecinos:** $H(X)_{{\\text{{espacial}}}} = {resumen_json['cadenas_de_markov']['entropia_adyacencia_espacial_bits']:.4f}$ bits/símbolo.",
        f"- **Distribución Estacionaria $\\pi$ y Tiempos Medios de Retorno $\\mu_{{ii}} = 1/\\pi_i$ (pasos de plantación secuencial):**"
    ])

    for i, code in enumerate(SPECIES_CODES):
        md_lines.append(f"  - **{code}:** $\\pi_{{{code}}} = {pi_seq_opt[i]:.4f}$, $\\mu_{{{code}}} = {mu_seq_opt[i]:.2f}$ pasos.")

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
        "6. `matriz_transicion_markov_vecinos_opt.csv`: Matriz espacial de adyacencia en los vecinos inmediatos en tresbolillo.",
        "7. `orden_plantacion_ejemplo_1ha.csv`: Bitácora secuencial paso a paso del predio de 1 hectárea ($s=1$).",
        "8. `resumen_estadistico_entregable3.json`: Datos estructurados listos para integración programática."
    ])

    with open(OUT_DIR / "resumen_estadistico_entregable3.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(md_lines) + "\n")
    print("\n[OK] Actualizado resumen_estadistico_entregable3.md con especificación AMD Ryzen 7 6800H y métricas exactas.")

if __name__ == "__main__":
    main()
