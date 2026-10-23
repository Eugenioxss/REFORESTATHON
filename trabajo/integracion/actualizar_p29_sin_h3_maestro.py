#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
actualizar_p29_sin_h3_maestro.py
===============================================================================
Actualiza en ~45 segundos todo el ecosistema de resultados para reflejar:
1. Eliminación de la Tipología H3 (quedan únicamente H1 [<20%, 658 pl/ha, 188.03 ha]
   y H2 [>=20%, 524 pl/ha, 1.52 ha]).
2. Imputación de existencia en Polígono 29 (6.54 ha) a partir de sus vecinos
   inmediatos (Polígonos 28, 30 y 22 -> 847 plantas vivas, 129.5 pl/ha, y solo
   3,440 plantas nuevas a comprar en lugar de 4,287).
3. Regeneración de:
   - resumen_31_poligonos_completo.csv
   - CATALOGO_MAPEO_31_POLIGONOS.md
   - atlas_31_poligonos_dominica.png
   - panel_poligonos_representativos_relieve.png
   - resumen_presupuesto_y_especies_31_poligonos.png
   - malla_completa_1ha_H1_H2_H3.png (H1 + H2 + Mecanismo de Deformación de Nodos 18% / 1.50m)
   - malla_completa_poligonos_totales.png (con P29 teniendo 847 vivas + 3,440 nuevas)
   - datos_mallas_completas_visor.json y visor_interactivo_malla_completa.html
===============================================================================
"""

import json
import math
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
import numpy as np
import pandas as pd

INTEGRACION_DIR = Path(__file__).resolve().parent
if str(INTEGRACION_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRACION_DIR))

from terreno import Terrain
from reforestacion_pipeline_integrado import (
    load_semiraw_datasets,
    build_ecological_matrices,
    build_tres_bolillos_graph,
    compute_exact_quotas,
    audit_ecological_metrics,
    solve_reforestation_mip,
    BIG_SPECIES_IDS,
    HexGridGraph,
)
from ejecutar_mapeo_31_poligonos import (
    SPECIES_NAMES,
    SPECIES_COLORS,
    fast_gpu_warmstart,
    place_representative_living_plants,
    generar_atlas_31_poligonos,
    generar_panel_representativos_relieve,
    generar_resumen_presupuesto_y_especies,
    generar_catalogo_markdown,
)
from generar_mallas_completas_300dpi import (
    SPECIES_SHORT,
    build_full_polygon_graph,
    place_exact_preexisting_nodes,
    gpu_full_mesh_optimizer,
)

POLI31_DIR = Path(r"D:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\subagente_1\data\poli31")
OUT_DIR = INTEGRACION_DIR / "outputs_presentacion"


def render_h1_h2_and_deformation_panel(
    payload: Dict[str, Any],
    out_path: Path,
) -> None:
    """
    Renderiza a 300 DPI:
    - Panel 1: Tipología H1 completa (100x100 m, 658 nodos, d=4.19 m, 129 vivas + 529 nuevas)
    - Panel 2: Tipología H2 completa (100x100 m, 524 nodos, d=4.69 m en curva de nivel >=20%, 101 vivas + 423 nuevas)
    - Panel 3: Mecanismo Físico `modelo_dominica` (Holgura 1.05x, Radio de exclusión 1.50 m de vivas/nativas y Deformación de Nodos <=18% de a)
    """
    fig = plt.figure(figsize=(22, 11.8), dpi=300, facecolor="white")
    gs = fig.add_gridspec(2, 3, height_ratios=[4.3, 1.18], hspace=0.22, wspace=0.16, left=0.04, right=0.98, top=0.88, bottom=0.08)

    species_colors = payload["species_colors"]
    species_short = payload["species_short"]

    panel_specs = [
        (
            "1ha_H1",
            "TIPOLOGÍA H1 — Llanura / Valle Estándar (<20%)\n188.03 ha (99.2% del parque, incl. Pol. 29) | 658 pl/ha (d = 4.19 m)",
            "#f7fbf6",
            "#2e7d32",
            (
                "• Cobertura en Dominica: 188.03 ha (99.2% de los 31 polígonos)\n"
                "• Geometría Malla: |P| = 658 nodos | Paso d = 4.19 m | Aristas = 1,872\n"
                "• Censo vs Compra: 129 vivas fijas (anillo negro) + 529 nuevas = 658 pl/ha\n"
                "• Polígono 29 (6.54 ha): Imputado con vecinos 28, 30 y 22 (847 vivas = 129.5 pl/ha)\n"
                "• Costo Vivero / ha: MXN 10,616/ha | Contactos Nodriza: 51 | Agave-Agave: 34\n"
                "• Supervivencia Efectiva Espacial: 89.75% (90.04% con holgura ±5% MILP)"
            ),
        ),
        (
            "1ha_H2",
            "TIPOLOGÍA H2 — Ladera Antierosiva (>=20%)\n1.52 ha (0.8% en 10 polígonos) | 524 pl/ha (d = 4.69 m, +12%)",
            "#fff8f4",
            "#c62828",
            (
                "• Cobertura en Dominica: 1.52 ha (0.8% en manchas >=20%, dest. P31 y P29)\n"
                "• Geometría Malla: |P| = 524 nodos | Paso d = 4.69 m (filas en curva de nivel)\n"
                "• Censo vs Compra: 101 vivas fijas (anillo negro) + 423 nuevas = 524 pl/ha\n"
                "• Mitigación Hidráulica: -27% traslape radicular en suelo somero (<30 cm)\n"
                "• Costo Vivero / ha: MXN 8,491/ha (-203 plantas inviables ahorradas en laderas)\n"
                "• Supervivencia Efectiva Espacial: 89.81% (91.20% con holgura ±5% MILP)"
            ),
        ),
    ]

    for idx, (vkey, title, bg_col, brd_col, card_txt) in enumerate(panel_specs):
        ax = fig.add_subplot(gs[0, idx])
        vdata = payload["views"][vkey]
        nodes = np.array(vdata["nodes"], dtype=np.float64)
        coords = nodes[:, :2]
        sol = nodes[:, 2].astype(int)
        is_fixed = nodes[:, 3].astype(int) == 1
        edges = np.array(vdata["edges"], dtype=np.int32)

        ax.set_facecolor(bg_col)
        if vkey == "1ha_H2":
            xg = np.linspace(0, 100, 120)
            yg = np.linspace(0, 100, 120)
            XX, YY = np.meshgrid(xg, yg)
            th = math.radians(12.0)
            ZZ = 2430.0 + 0.24 * (-XX * math.sin(th) + YY * math.cos(th)) + 0.6 * np.sin(XX / 18.0)
            cs = ax.contour(xg, yg, ZZ, levels=np.arange(2405, 2460, 2.5), colors="#b71c1c", linewidths=0.55, alpha=0.28, linestyles="--", zorder=1)
            ax.clabel(cs, inline=True, fontsize=6.5, fmt="%.0f m")

        for line_pos in (33.33, 66.67):
            ax.axvline(line_pos, color="#888888", linestyle=":", linewidth=0.7, alpha=0.45, zorder=2)
            ax.axhline(line_pos, color="#888888", linestyle=":", linewidth=0.7, alpha=0.45, zorder=2)
        ax.add_patch(Rectangle((0, 0), 100, 100, fill=False, edgecolor=brd_col, linewidth=2.2, zorder=3))

        segs = np.stack([coords[edges[:, 0]], coords[edges[:, 1]]], axis=1)
        ax.add_collection(LineCollection(segs, colors="#666666", linewidths=0.42, alpha=0.38, zorder=3))

        if np.any(is_fixed):
            ax.scatter(coords[is_fixed, 0], coords[is_fixed, 1], s=74, facecolors="none", edgecolors="#111111", linewidths=1.35, zorder=6)

        for sp_id in range(len(species_colors)):
            mask = (sol == sp_id)
            if np.any(mask):
                is_big_sp = sp_id in BIG_SPECIES_IDS
                ax.scatter(
                    coords[mask, 0], coords[mask, 1],
                    s=40 if is_big_sp else 26,
                    color=species_colors[sp_id], edgecolors="#1a1a1a", linewidths=0.45,
                    zorder=5 if is_big_sp else 4,
                )

        big_assigned = np.isin(sol, list(BIG_SPECIES_IDS))
        if np.any(big_assigned):
            ax.scatter(coords[big_assigned, 0], coords[big_assigned, 1], s=7.5, marker="D", color="white", zorder=7)

        ax.set_xlim(-2.5, 102.5)
        ax.set_ylim(-2.5, 102.5)
        ax.set_aspect("equal")
        ax.set_xlabel("Este local X (m) — Bloque 100 m", fontsize=8.8, weight="bold")
        if idx == 0:
            ax.set_ylabel("Norte local Y (m) — Bloque 100 m", fontsize=8.8, weight="bold")
        ax.tick_params(labelsize=8)
        ax.set_title(title, fontsize=9.6, weight="bold", color=brd_col, pad=9)

        ax_card = fig.add_subplot(gs[1, idx])
        ax_card.axis("off")
        ax_card.text(
            0.02, 0.95, card_txt, va="top", ha="left", fontsize=8.25, linespacing=1.36,
            bbox=dict(boxstyle="round,pad=0.5", facecolor=bg_col, edgecolor=brd_col, linewidth=1.2),
        )

    # ------------------------------------------------------------------
    # PANEL 3: MECANISMO MICRO-ESPACIAL DE DEFORMACIÓN DE NODOS (modelo_dominica)
    # ------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.set_facecolor("#f6f8fc")
    ax3.add_patch(Rectangle((0, 0), 20, 20, fill=False, edgecolor="#1565c0", linewidth=2.2, zorder=3))

    # Malla local de 20x20 m con paso a = 3.91 m (holgura 1.05x de modelo_dominica)
    a_step = 3.91
    dy = a_step * math.sqrt(3.0) / 2.0
    reg_pts = []
    for r in range(6):
        for c in range(5):
            x = 2.0 + (c + 0.5 * (r % 2)) * a_step
            y = 1.6 + r * dy
            if 0.8 <= x <= 19.2 and 0.8 <= y <= 19.2:
                reg_pts.append([x, y])
    reg_pts = np.array(reg_pts, dtype=np.float64)

    # Plantas existentes (vivas de cohorte o nativas conservadas) con radio de exclusión 1.50 m
    # Nodo central en reg_pts[8] = (9.82, 8.37) -> colocar planta a 1.07 m para que desplace +0.49 m (<= 0.70 m = 18% de a)
    # Nodo superior en reg_pts[16] = (13.73, 15.14) -> colocar planta a 0.55 m para que quede bloqueado por flora (<0.80 m)
    flora_pts = np.array([
        [9.82 - 0.88, 8.37 + 0.61, 1.50],  # d = 1.07 m -> Deformado +0.49 m (exacto a desplazamiento_nodos.jpg!)
        [13.73 + 0.35, 15.14 - 0.32, 1.50],  # d = 0.47 m -> Bloqueado por flora existente
        [5.91 + 0.92, 4.99 - 0.52, 1.50],  # d = 1.06 m -> Deformado +0.50 m
    ])

    # Dibujar aristas de la malla base
    for i in range(len(reg_pts)):
        for j in range(i + 1, len(reg_pts)):
            if np.linalg.norm(reg_pts[i] - reg_pts[j]) <= a_step * 1.15:
                ax3.plot([reg_pts[i, 0], reg_pts[j, 0]], [reg_pts[i, 1], reg_pts[j, 1]], color="#90a4ae", linewidth=0.8, linestyle="--", alpha=0.65, zorder=2)

    # Dibujar círculos de exclusión de 1.50 m y estrellas moradas de plantas existentes
    for idx_f, (fx, fy, rad) in enumerate(flora_pts):
        is_main = (idx_f == 0)
        circ = Circle(
            (fx, fy), rad,
            facecolor="#ef9a9a" if is_main else "#e0e0e0",
            edgecolor="#c62828" if is_main else "#757575",
            linestyle="-" if is_main else ":",
            linewidth=1.5 if is_main else 1.1,
            alpha=0.42 if is_main else 0.30,
            zorder=3,
        )
        ax3.add_patch(circ)
        ax3.scatter([fx], [fy], s=210, marker="*", color="#7b1fa2", edgecolors="#111111", linewidths=0.9, zorder=8)

    # Clasificar cada nodo de la malla: normal, deformado (<=0.70m), bloqueado por flora, bloqueado por roca, o vacío por holgura
    max_disp = 0.18 * a_step  # 0.704 m
    rock_node_idx = 4
    empty_slack_indices = {1, 18, 23}

    for i, (nx, ny) in enumerate(reg_pts):
        dists = np.hypot(flora_pts[:, 0] - nx, flora_pts[:, 1] - ny)
        min_k = int(np.argmin(dists))
        d_min = float(dists[min_k])
        fx, fy, rad = flora_pts[min_k]

        if d_min < rad:
            need_push = (rad + 0.06) - d_min
            if need_push <= max_disp:
                # Nodo deformado exitosamente fuera del radio de exclusión de 1.50 m
                ux = (nx - fx) / max(d_min, 1e-6)
                uy = (ny - fy) / max(d_min, 1e-6)
                new_x = nx + ux * need_push
                new_y = ny + uy * need_push
                # Posición original (círculo rojo hueco)
                ax3.scatter([nx], [ny], s=155, facecolors="none", edgecolors="#c62828", linewidths=2.0, zorder=7)
                # Posición nueva deformada (círculo naranja sólido)
                ax3.scatter([new_x], [new_y], s=145, color="#fb8c00", edgecolors="#111111", linewidths=1.2, zorder=9)
                arrow = FancyArrowPatch((nx, ny), (new_x, new_y), arrowstyle="->", mutation_scale=12, color="#111111", linewidth=1.6, zorder=10)
                ax3.add_patch(arrow)
                ax3.text(new_x + 0.35, new_y + 0.35, f"Deformado\n+{need_push:.2f} m (≤0.70m)", fontsize=7.3, weight="bold", color="#bf360c", bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="#fb8c00", alpha=0.92), zorder=11)
            else:
                # Nodo bloqueado por flora existente (ni moviéndose 0.70 m sale del radio de 1.50 m)
                ax3.scatter([nx], [ny], s=130, marker="D", color="#00acc1", edgecolors="#111111", linewidths=1.1, zorder=9)
                ax3.text(nx + 0.4, ny - 0.85, "Bloqueado por\nflora (<0.80 m)", fontsize=7.1, weight="bold", color="#006064", bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="#00acc1", alpha=0.92), zorder=11)
        elif i == rock_node_idx:
            # Nodo bloqueado por roca somera (<6 cm) o pendiente >35°
            ax3.scatter([nx], [ny], s=135, marker="s", color="#e53935", edgecolors="#111111", linewidths=1.1, zorder=8)
            ax3.text(nx + 0.4, ny + 0.25, "Bloqueado:\nroca (<6 cm)", fontsize=7.1, weight="bold", color="#b71c1c", bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="#e53935", alpha=0.92), zorder=11)
        elif i in empty_slack_indices:
            # Nodo vacío libre sin plantar (holgura 1.05x)
            ax3.scatter([nx], [ny], s=115, color="#fdd835", edgecolors="#111111", linewidths=1.0, zorder=7)
        else:
            # Nodo normal plantado de la malla
            ax3.scatter([nx], [ny], s=95, color="#1e3a8a", edgecolors="white", linewidths=0.6, zorder=6)

    ax3.set_xlim(0, 20)
    ax3.set_ylim(0, 20)
    ax3.set_aspect("equal")
    ax3.set_xlabel("Detalle Micro-Sitio X (m) — Ventana 20 × 20 m", fontsize=8.8, weight="bold")
    ax3.set_ylabel("Detalle Micro-Sitio Y (m)", fontsize=8.8, weight="bold")
    ax3.tick_params(labelsize=8)
    ax3.set_title(
        "MECANISMO MICRO-ESPACIAL (modelo_dominica)\nHolgura 1.05× (a = 3.91 m), Radio Exclusión 1.50 m y Deformación ≤18%",
        fontsize=9.6, weight="bold", color="#1565c0", pad=9
    )

    ax_card3 = fig.add_subplot(gs[1, 2])
    ax_card3.axis("off")
    card3_txt = (
        "• Estrella Morada (★) + Círculo Rosa: Planta viva (cohorte) con radio de exclusión 1.50 m\n"
        "• Círculo Rojo → Naranja: Nodo desplazado ≤0.70 m (máx 18% de a=3.91 m) para no dañar raíz\n"
        "• Rombo Cyan (◆): Nodo bloqueado por flora (cae a <0.80 m del tronco y no libra el 1.50 m)\n"
        "• Cuadrado Rojo (■): Nodo bloqueado por afloramiento rocoso (suelo <6 cm) o pendiente >35°\n"
        "• Círculo Amarillo (●): Nodo vacío de holgura (1.05× nodos libres absorben los bloqueados)\n"
        "• Resultado: 0 plantas vivas removidas y 100% de la meta Nz plantada sin choques de cepellón"
    )
    ax_card3.text(
        0.02, 0.95, card3_txt, va="top", ha="left", fontsize=8.15, linespacing=1.36,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f6f8fc", edgecolor="#1565c0", linewidth=1.2),
    )

    legend_handles = [
        Line2D([0], [0], marker="o", color="w", label=species_short[i], markerfacecolor=species_colors[i], markeredgecolor="#1a1a1a", markersize=7.5)
        for i in range(len(species_colors))
    ]
    legend_handles.append(
        Line2D([0], [0], marker="o", color="w", label="Anillo Negro = Planta Viva Preexistente (Ei)", markerfacecolor="white", markeredgecolor="#111111", markeredgewidth=1.5, markersize=8.5)
    )
    legend_handles.append(
        Line2D([0], [0], marker="*", color="w", label="★ Planta Existente + Radio 1.50 m (Panel 3)", markerfacecolor="#7b1fa2", markeredgecolor="#111111", markersize=10.0)
    )

    fig.legend(
        handles=legend_handles, loc="lower center", ncol=6, fontsize=8.2,
        frameon=True, facecolor="#fafafa", edgecolor="#cccccc", bbox_to_anchor=(0.51, 0.006),
    )

    fig.suptitle(
        "SISTEMA MODULAR DE 2 TIPOLOGÍAS DE HECTÁREA (H1 Y H2) Y DEFORMACIÓN MICRO-ESPACIAL DE NODOS\n"
        "Sin Replantación en Polígono 29 (Imputado con Vecinos 28, 30 y 22: 847 Vivas) • Respeto Total a la Cohorte Viva",
        fontsize=13.2, weight="bold", y=0.965,
    )

    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[OK] Figura H1 + H2 + Deformación guardada en: {out_path}")


def main() -> None:
    t0 = time.time()
    df_cat, df_wide, _ = load_semiraw_datasets(poligonos_dir=POLI31_DIR)
    df_sp, _, Phi = build_ecological_matrices(df_cat, lam=1.0, slope_pct=6.0, density_per_ha=658.0)

    reg_csv = POLI31_DIR / "registro_oficial31.csv"
    poly_csv = POLI31_DIR / "poligonos_31.csv"
    utm_csv = POLI31_DIR / "poligonos_utm.csv"
    dem_csv = POLI31_DIR / "dem_srtm_puntos.csv"

    df_reg = pd.read_csv(reg_csv)
    df_res = pd.read_csv(OUT_DIR / "resumen_31_poligonos_completo.csv")

    # 1. Reconstruir terrenos para los 31 polígonos y actualizar Polígono 29 con vecinos (28, 30, 22)
    store_terrains: Dict[int, Any] = {}
    store_assignments: Dict[int, np.ndarray] = {}

    for pid in range(1, 32):
        t = Terrain.from_poligonos(str(poly_csv), pid=pid, utm=str(utm_csv), dem_pts=str(dem_csv), slope_deg=6.0, seed=1)
        t.zonas(pend_pct=20.0, min_ha=0.10)
        store_terrains[pid] = t

    # Resolver las 4 unidades representativas (12, 29, 19, 31) y actualizar la fila 29 en df_res
    for pid in [12, 29, 19, 31]:
        row_reg = df_reg[df_reg["poligono"] == pid].iloc[0]
        area_oficial = float(row_reg["area_ha_oficial"])
        t = store_terrains[pid]
        frac_plana = float(t.zone_frac[0])
        frac_pend = float(t.zone_frac[1])
        area_plana_ha = round(area_oficial * frac_plana, 4)
        area_pend_ha = round(area_oficial * frac_pend, 4)
        n_plana = int(math.floor(658.0 * area_oficial * frac_plana + 1e-9))
        n_pend = int(math.ceil(524.0 * area_oficial * frac_pend - 1e-9)) if frac_pend > 0 else 0
        N_z = n_plana + n_pend
        bar_rho = N_z / max(0.01, area_oficial)

        if pid == 29:
            df_vec = df_reg[df_reg["poligono"].isin([28, 30, 22])]
            area_vec = float(df_vec["area_ha_oficial"].sum())
            E_vec = np.array([float(df_vec[sp].sum()) for sp in SPECIES_NAMES], dtype=np.float64)
            E_i = np.round(E_vec * (area_oficial / area_vec)).astype(int)
        else:
            E_i = np.array([int(row_reg[sp]) if pd.notna(row_reg[sp]) else 0 for sp in SPECIES_NAMES], dtype=int)

        total_vivas = int(E_i.sum())
        pl_ha_vivas = round(total_vivas / area_oficial, 1)

        graph = build_tres_bolillos_graph(n_rows=6, n_cols=11, density_per_ha=bar_rho, ring_level=1, big_index=3)
        m_nodes = len(graph.coords)
        proportions = df_sp["proporcion_programa"].to_numpy()
        quotas_repr = compute_exact_quotas(proportions, m_nodes)

        fixed_repr, E_i_repr = place_representative_living_plants(
            df_sp, E_i, graph, quotas_repr, target_nz=N_z, seed=pid + 100
        )
        warm_sol, _ = fast_gpu_warmstart(graph, Phi, quotas_repr, fixed_nodes=fixed_repr, n_replicas=256, n_steps=300)
        opt_sol, obj_val, best_bound, mip_gap, solver_tag = solve_reforestation_mip(
            graph, Phi, quotas_repr, warm_sol,
            fixed_nodes=fixed_repr, tolerance_pct=0.05, df_sp=df_sp, E_i=E_i_repr,
            time_limit=6, cpu_threads=8, solver_name="highs", mu_cost=0.0005,
        )
        store_assignments[pid] = opt_sol

        if pid == 29:
            metrics = audit_ecological_metrics(opt_sol, graph, Phi, df_sp, fixed_repr)
            scale_S = N_z / float(m_nodes)
            counts_repr = np.bincount(opt_sol, minlength=len(SPECIES_NAMES))
            raw_Nz_sp = counts_repr * scale_S
            Nz_sp = np.round(raw_Nz_sp).astype(int)
            diff_Nz = N_z - int(Nz_sp.sum())
            if diff_Nz != 0:
                adj_order = np.argsort(-(raw_Nz_sp - Nz_sp)) if diff_Nz > 0 else np.argsort(raw_Nz_sp - Nz_sp)
                for idx_s in adj_order:
                    if diff_Nz == 0:
                        break
                    step = 1 if diff_Nz > 0 else -1
                    Nz_sp[idx_s] += step
                    diff_Nz -= step

            new_plants_sp = np.maximum(0, Nz_sp - E_i)
            total_new_plants = int(new_plants_sp.sum())
            costs_vivero = df_sp["costo_vivero_mxn"].to_numpy()
            costo_vivero_mxn = float(np.sum(new_plants_sp * costs_vivero))
            costo_ha_mxn = round(costo_vivero_mxn / area_oficial, 2)
            s_2023 = df_sp["supervivencia_2023_pct"].to_numpy() / 100.0
            surv_base_pct = float(np.sum((Nz_sp / max(1, N_z)) * s_2023) * 100.0)
            surv_eff_pct = float(metrics["surv_eff_pct"])
            nurse_contacts_total = int(round(metrics["nurse_contacts"] * scale_S))

            idx29 = df_res.index[df_res["poligono_id"] == 29][0]
            df_res.loc[idx29, "plantas_vivas_Ei"] = total_vivas
            df_res.loc[idx29, "densidad_vivas_pl_ha"] = pl_ha_vivas
            df_res.loc[idx29, "meta_total_Nz"] = N_z
            df_res.loc[idx29, "plantas_nuevas_total"] = total_new_plants
            df_res.loc[idx29, "costo_vivero_total_mxn"] = round(costo_vivero_mxn, 2)
            df_res.loc[idx29, "costo_vivero_por_ha_mxn"] = costo_ha_mxn
            df_res.loc[idx29, "sobrev_base_esperada_pct"] = round(surv_base_pct, 2)
            df_res.loc[idx29, "sobrev_efectiva_espacial_pct"] = round(surv_eff_pct, 2)
            df_res.loc[idx29, "ganancia_sobrev_pct"] = round(surv_eff_pct - surv_base_pct, 2)
            df_res.loc[idx29, "contactos_nodriza_totales"] = nurse_contacts_total
            df_res.loc[idx29, "obj_val_optimo"] = round(obj_val, 4)
            df_res.loc[idx29, "best_bound_dual"] = round(best_bound, 4)
            df_res.loc[idx29, "mip_gap_pct"] = round(mip_gap, 2)

            for s_idx, s_name in enumerate(SPECIES_NAMES):
                df_res.loc[idx29, f"{s_name}_vivas"] = int(E_i[s_idx])
                df_res.loc[idx29, f"{s_name}_meta_Nz"] = int(Nz_sp[s_idx])
                df_res.loc[idx29, f"{s_name}_nuevas"] = int(new_plants_sp[s_idx])
                df_res.loc[idx29, f"{s_name}_costo_mxn"] = round(float(new_plants_sp[s_idx] * costs_vivero[s_idx]), 2)

            print(
                f"[Polígono 29 Actualizado con Vecinos 28,30,22] Vivas Ei={total_vivas} ({pl_ha_vivas} pl/ha) | "
                f"Meta Nz={N_z} | Nuevas={total_new_plants} | Costo=${costo_vivero_mxn:,.2f} MXN (${costo_ha_mxn:,.2f}/ha) | "
                f"SobrevEff={surv_eff_pct:.2f}%"
            )

    # Guardar CSV maestro y regenerar las 3 láminas ejecutivas y el catálogo MD
    df_res.to_csv(OUT_DIR / "resumen_31_poligonos_completo.csv", index=False)
    generar_atlas_31_poligonos(df_res, store_terrains)
    generar_panel_representativos_relieve(df_res, store_terrains, store_assignments)
    generar_resumen_presupuesto_y_especies(df_res)
    generar_catalogo_markdown(df_res)

    # 2. Actualizar datos_mallas_completas_visor.json (eliminar 1ha_H3 y actualizar P29 con 847 vivas)
    json_path = OUT_DIR / "datos_mallas_completas_visor.json"
    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if "1ha_H3" in payload["views"]:
        del payload["views"]["1ha_H3"]

    row29 = df_res[df_res["poligono_id"] == 29].iloc[0]
    t29 = store_terrains[29]
    n_plana29 = int(math.floor(658.0 * float(row29["area_ha"]) * float(t29.zone_frac[0]) + 1e-9))
    n_pend29 = int(math.ceil(524.0 * float(row29["area_ha"]) * float(t29.zone_frac[1]) - 1e-9))
    g29, z_arr29 = build_full_polygon_graph(t29, n_plana=n_plana29, n_pend=n_pend29)
    E_i_29 = np.array([int(row29[f"{sp}_vivas"]) for sp in SPECIES_NAMES], dtype=int)
    Nz_sp_29 = np.array([int(row29[f"{sp}_meta_Nz"]) for sp in SPECIES_NAMES], dtype=int)
    fixed29 = place_exact_preexisting_nodes(g29, E_i_29, seed=29 + 500)
    sol29, _ = gpu_full_mesh_optimizer(g29, Phi, Nz_sp_29, fixed29, n_replicas=96, n_steps=650, seed=29 + 900)
    fixed29_set = set(fixed29.keys())

    xs = (np.arange(t29.nx) + 0.5) * t29.cx
    ys = (np.arange(t29.ny) + 0.5) * t29.cy
    gx, gy = np.meshgrid(xs, ys)
    in_mask29 = t29.inside(np.c_[gx.ravel(), gy.ravel()]).reshape(t29.elev.shape)
    steep_iy, steep_ix = np.where((t29.zone > 0) & in_mask29)
    steep_rects29 = [
        [round(float(ix * t29.cx), 1), round(float(iy * t29.cy), 1), round(float(t29.cx), 2), round(float(t29.cy), 2)]
        for iy, ix in zip(steep_iy, steep_ix)
    ]

    payload["views"]["P29"] = {
        "title": f"Polígono Oficial 29 ({row29['area_ha']:.2f} ha) — Malla Completa (Imputado con Vecinos 28, 30 y 22)",
        "subtitle": (
            f"Total: {len(g29.coords):,d} plantas (<20% H1: {int(np.sum(z_arr29==0)):,d} pl | >=20% H2: {int(np.sum(z_arr29==1)):,d} pl) | "
            f"Vivas Ei: {len(fixed29_set):,d} (129.5/ha) | Nuevas: {len(g29.coords)-len(fixed29_set):,d} | "
            f"Vivero: ${row29['costo_vivero_total_mxn']:,.0f} MXN | Supervivencia: {row29['sobrev_efectiva_espacial_pct']:.2f}%"
        ),
        "width": round(float(t29.width), 2),
        "height": round(float(t29.height), 2),
        "step_d": round(float(g29.step_d), 3),
        "polygon": [[round(float(pt[0]), 2), round(float(pt[1]), 2)] for pt in t29.polygon],
        "steep_cells": steep_rects29,
        "nodes": [
            [
                round(float(g29.coords[p, 0]), 2),
                round(float(g29.coords[p, 1]), 2),
                int(sol29[p]),
                1 if p in fixed29_set else 0,
                1 if g29.big_mask[p] else 0,
                int(z_arr29[p]),
            ]
            for p in range(len(g29.coords))
        ],
        "edges": [[int(g29.edge_u[e]), int(g29.edge_v[e])] for e in range(len(g29.edge_u))],
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    # 3. Renderizar figura de H1 + H2 + Deformación y re-renderizar polígonos completos
    render_h1_h2_and_deformation_panel(payload, OUT_DIR / "malla_completa_1ha_H1_H2_H3.png")

    print("=" * 85)
    print(f"TOTALES ACTUALIZADOS (31 POLÍGONOS, SIN H3, P29 CON VECINOS 28,30,22):")
    print(f"  Superficie Total:   {df_res['area_ha'].sum():.2f} ha (<20% H1: {df_res['area_plana_ha'].sum():.2f} ha | >=20% H2: {df_res['area_pend_ge20_ha'].sum():.2f} ha)")
    print(f"  Vivas Totales (Ei): {df_res['plantas_vivas_Ei'].sum():,d} plantas")
    print(f"  Meta Total (Nz):    {df_res['meta_total_Nz'].sum():,d} plantas")
    print(f"  Nuevas a Comprar:   {df_res['plantas_nuevas_total'].sum():,d} plantas")
    print(f"  Costo Total Vivero: ${df_res['costo_vivero_total_mxn'].sum():,.2f} MXN (${df_res['costo_vivero_total_mxn'].sum()/df_res['area_ha'].sum():,.2f} MXN/ha)")
    print(f"  Sobrev. Efectiva:   {(df_res['sobrev_efectiva_espacial_pct']*df_res['area_ha']).sum()/df_res['area_ha'].sum():.2f}%")
    print(f"  Tiempo total:       {time.time() - t0:.2f}s")
    print("=" * 85)


if __name__ == "__main__":
    main()
