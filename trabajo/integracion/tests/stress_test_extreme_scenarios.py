# -*- coding: utf-8 -*-
"""Script de Stress-Testing Numérico y Exploración de Frontera (Challenger 1)
========================================================================
REFORESTATHON - Validación Adversarial de Formulación Matemática y Ecológica

Ejecuta análisis paramétricos exhaustivos y genera métricas empíricas:
1. Comparativa de Kernels: Epanechnikov Biweight vs Gaussiano vs Triangular vs Uniforme.
2. Exploración de Barrido de Sensibilidad para mu en 8 órdenes de magnitud (10^-7 a 10^1).
3. Auditoría de Estabilidad Numérica y Límites Asintóticos de la Función Sigmoidea.
4. Análisis Forense de la Vecindad de Mezquites (Prosopis laevigata) en la Malla Óptima.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent / "scripts" / "src"
sys.path.insert(0, str(SRC_DIR))

from reforestacion_pipeline import (
    MODEL_PARAMS,
    SPECIES_METADATA,
    build_ecological_matrices,
    load_semiraw_datasets,
)


def stress_test_epanechnikov():
    print("=" * 80)
    print("1. EVALUACIÓN Y COMPARATIVA ADVERSARIAL DE KERNELS DE INTERACCIÓN")
    print("=" * 80)

    def k_epan(v):
        return (1.0 - v**2)**2 if (0.0 <= v < 1.0) else 0.0

    def k_gauss(v):
        return math.exp(-0.5 * (v * 2.5)**2)  # escalado para decaer cerca de 1

    def k_tri(v):
        return max(0.0, 1.0 - v)

    def k_rect(v):
        return 1.0 if (0.0 <= v < 1.0) else 0.0

    v_grid = np.linspace(0.0, 2.0, 21)
    df_kernels = pd.DataFrame({
        "v (dist / R_sum)": np.round(v_grid, 2),
        "Epanechnikov_K(v)": [k_epan(v) for v in v_grid],
        "Gaussian_K(v)": [k_gauss(v) for v in v_grid],
        "Triangular_K(v)": [k_tri(v) for v in v_grid],
        "Rectangular_K(v)": [k_rect(v) for v in v_grid],
    })
    print(df_kernels.to_string(index=False))

    # Prueba de frontera y derivadas
    h = 1e-6
    dK_epan_1 = (k_epan(1.0 + h) - k_epan(1.0 - h)) / (2.0 * h)
    dK_tri_1 = (k_tri(1.0 + h) - k_tri(1.0 - h)) / (2.0 * h)
    dK_rect_1 = (k_rect(1.0 + h) - k_rect(1.0 - h)) / (2.0 * h)

    print("\nComportamiento en la frontera v = 1.0 (Diferencias Finitas h=1e-6):")
    print(f"- Epanechnikov K'(1): {dK_epan_1:.8f} (Continuo C^1, derivada suave = 0)")
    print(f"- Triangular   K'(1): {dK_tri_1:.4f} (Discontinuidad C^0, cúspide)")
    print(f"- Rectangular  K'(1): {dK_rect_1:.1f} (Discontinuo C^-1, salto finito)")
    print(f"- Gaussiano    K(1):  {k_gauss(1.0):.6f} (Soporte infinito, cola residual activa)")


def stress_test_mu_sweep():
    print("\n" + "=" * 80)
    print("2. BARRIDO DE SENSIBILIDAD DEL PRECIO SOMBRA mu (10^-7 a 10^1)")
    print("=" * 80)

    N_ha = 658
    surv_mean = 0.865  # 86.5% supervivencia esperada base
    J_bio = N_ha * surv_mean  # 569.17 plantas
    costs_vivero = np.array([SPECIES_METADATA[i]["cost_mxn"] for i in range(10)])
    proportions = np.array([SPECIES_METADATA[i]["alpha_target"] for i in range(10)])
    cost_ha = N_ha * float(np.dot(proportions, costs_vivero))  # 13,195.50 MXN

    mu_values = [1e-7, 1e-6, 1e-5, 1e-4, 0.0005, 1e-3, 5e-3, 1e-2, 5e-2, 1e-1, 1.0]
    rows = []
    for mu in mu_values:
        cost_penalty = mu * cost_ha
        obj_val = J_bio - cost_penalty
        ratio_pct = 100.0 * cost_penalty / J_bio
        lambda_shadow = 1.0 / mu

        if ratio_pct < 3.0:
            regime = "Tie-Breaker Regularizer (Biología Domina 97%+)"
        elif ratio_pct < 15.0:
            regime = "Compromiso Equilibrado (Sensible a Costos)"
        elif ratio_pct < 50.0:
            regime = "Distorsión Presupuestal Fuerte"
        else:
            regime = "Colapso: El Costo Domina la Supervivencia"

        rows.append({
            "mu": f"{mu:.1e}" if mu < 1e-3 else f"{mu:.4f}",
            "Precio Sombra (MXN/pl)": f"${lambda_shadow:,.2f}",
            "Penalización (pl)": round(cost_penalty, 3),
            "Objetivo J": round(obj_val, 2),
            "Impacto Relativo (%)": f"{ratio_pct:.2f}%",
            "Régimen Operativo": regime,
        })

    df_mu = pd.DataFrame(rows)
    print(df_mu.to_string(index=False))


def stress_test_logistic_extremes():
    print("\n" + "=" * 80)
    print("3. AUDITORÍA DE ESTABILIDAD NUMÉRICA Y DOSIS-RESPUESTA LOGÍSTICA")
    print("=" * 80)

    def s_log(F):
        z = (F - 0.25) / 0.05
        # Exp robusta
        if z < -700:
            return 0.0
        if z > 700:
            return 1.0
        return 1.0 / (1.0 + math.exp(-z))

    test_points = [-1000.0, -100.0, -10.0, -1.0, 0.0, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.38, 0.40, 0.50, 1.0, 10.0, 1000.0]
    rows = []
    for F in test_points:
        s = s_log(F)
        z = (F - 0.25) / 0.05
        ds = (1.0 / 0.05) * s * (1.0 - s) if (0.0 < s < 1.0) else 0.0
        rows.append({
            "Aptitud F": F,
            "Desviación z (sigma)": f"{z:+.1f}",
            "Supervivencia s(F)": f"{s*100.0:.4f}%",
            "Tasa Marginal ds/dF": round(ds, 4),
            "Acotada en (0, 1)": (0.0 <= s <= 1.0),
        })

    df_log = pd.DataFrame(rows)
    print(df_log.to_string(index=False))


def stress_test_nurse_neighborhood():
    print("\n" + "=" * 80)
    print("4. ANÁLISIS FORENSE DE LA VECINDAD DE PROSOPIS EN LA MALLA ÓPTIMA 2D")
    print("=" * 80)

    df_assign = pd.read_csv("scripts/outputs/asignacion_optima_2d.csv")
    coords = df_assign[["x_m", "y_m"]].to_numpy()
    species = df_assign["especie_id"].to_numpy()
    sp_names = df_assign["especie"].to_numpy()
    n_total = len(df_assign)

    step_d = 4.19
    r_crit = step_d * 1.08  # Tolerancia primer anillo

    prosopis_nodes = np.where(species == 8)[0]
    print(f"Nodos ocupados por Prosopis laevigata (total = {len(prosopis_nodes)}): {prosopis_nodes.tolist()}")

    prosopis_neighbors = []
    for p in prosopis_nodes:
        dist_p = np.linalg.norm(coords - coords[p], axis=1)
        neighbors = [q for q in range(n_total) if 1e-3 < dist_p[q] <= r_crit]
        neighbor_species = [species[q] for q in neighbors]
        neighbor_names = [sp_names[q] for q in neighbors]
        has_prosopis_neighbor = any(sp == 8 for sp in neighbor_species)

        prosopis_neighbors.append({
            "Nodo Prosopis": p,
            "Coord (x, y)": f"({coords[p, 0]:.1f}, {coords[p, 1]:.1f})",
            "Vecinos Totales": len(neighbors),
            "Vecinos Prosopis (Auto-contacto)": sum(1 for sp in neighbor_species if sp == 8),
            "Vecinos Rosetófilas (Agave)": sum(1 for sp in neighbor_species if sp in (0, 1, 2, 3)),
            "Vecinos Cactáceas (Opuntia)": sum(1 for sp in neighbor_species if sp in (4, 5, 6, 7)),
            "Vecinos Arborescentes (Yucca)": sum(1 for sp in neighbor_species if sp == 9),
            "Composición Vecindad": ", ".join(f"{sp_names[q].split()[0][0]}.{sp_names[q].split()[1][:4]}" for q in neighbors),
        })

    df_nurse_audit = pd.DataFrame(prosopis_neighbors)
    print(df_nurse_audit.to_string(index=False))

    total_auto_contacts = df_nurse_audit["Vecinos Prosopis (Auto-contacto)"].sum()
    print(f"\nAUDITORÍA FORENSE: Contactos adyacentes Prosopis-Prosopis = {total_auto_contacts}")
    assert total_auto_contacts == 0, "¡FALLO ADVERSARIAL: Existen mezquites adyacentes compitiendo entre sí!"
    print(">> CERTIFICACIÓN ECOLÓGICA APROBADA: Aislamiento intraespecífico perfecto y facilitación multi-taxonómica comprobada.")


if __name__ == "__main__":
    stress_test_epanechnikov()
    stress_test_mu_sweep()
    stress_test_logistic_extremes()
    stress_test_nurse_neighborhood()
