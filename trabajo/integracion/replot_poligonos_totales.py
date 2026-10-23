#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-renderiza malla_completa_poligonos_totales.png en ~3s leyendo datos_mallas_completas_visor.json
para garantizar cero modo matemático accidental ($...$) y cero traslapes entre columnas o sobre el polígono."""

import json
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LightSource
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon as MplPolygon, Rectangle
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import numpy as np
import pandas as pd

INTEGRACION_DIR = Path(__file__).resolve().parent
if str(INTEGRACION_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRACION_DIR))

from terreno import Terrain

POLI31_DIR = Path(r"D:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\subagente_1\data\poli31")
OUT_DIR = INTEGRACION_DIR / "outputs_presentacion"

BIG_SPECIES_IDS = {7, 8, 9}


def main() -> None:
    with open(OUT_DIR / "datos_mallas_completas_visor.json", "r", encoding="utf-8") as f:
        payload = json.load(f)

    species_short = payload["species_short"]
    species_colors = payload["species_colors"]
    df_res = pd.read_csv(OUT_DIR / "resumen_31_poligonos_completo.csv")

    poly_csv = POLI31_DIR / "poligonos_31.csv"
    utm_csv = POLI31_DIR / "poligonos_utm.csv"
    dem_csv = POLI31_DIR / "dem_srtm_puntos.csv"

    fig = plt.figure(figsize=(21, 18.2), dpi=300, facecolor="white")
    gs = fig.add_gridspec(2, 2, hspace=0.22, wspace=0.16, left=0.04, right=0.98, top=0.905, bottom=0.065)

    pids = [12, 29, 19, 31]
    titles = {
        12: "POLÍGONO 12 — Malla Completa (967 plantas en 1.47 ha | 100% H1)",
        29: "POLÍGONO 29 — Malla Completa (4,287 pl en 6.54 ha | 847 Vivas Vecinos 28/30/22 | Costura H1 + H2)",
        19: "POLÍGONO 19 — Malla Completa (3,237 plantas en 4.92 ha | 100% H1)",
        31: "POLÍGONO 31 — Malla Completa (4,781 plantas en 7.34 ha | Costura H1 + H2)",
    }

    ls = LightSource(azdeg=315, altdeg=45)

    for idx, pid in enumerate(pids):
        ax = fig.add_subplot(gs[idx // 2, idx % 2])
        vdata = payload["views"][f"P{pid}"]
        row = df_res[df_res["poligono_id"] == pid].iloc[0]

        t = Terrain.from_poligonos(str(poly_csv), pid=pid, utm=str(utm_csv), dem_pts=str(dem_csv), slope_deg=6.0, seed=1)
        t.zonas(pend_pct=20.0, min_ha=0.10)

        nodes = np.array(vdata["nodes"], dtype=np.float64)
        coords = nodes[:, :2]
        sol = nodes[:, 2].astype(int)
        is_fixed = nodes[:, 3].astype(int) == 1
        zone_arr = nodes[:, 5].astype(int)
        edges = np.array(vdata["edges"], dtype=np.int32)

        # 1. Relieve sombreado recortado al polígono
        rgb_shade = ls.shade(t.elev, cmap=plt.get_cmap("terrain"), vert_exag=1.5, blend_mode="soft")
        xs = (np.arange(t.nx) + 0.5) * t.cx
        ys = (np.arange(t.ny) + 0.5) * t.cy
        gx, gy = np.meshgrid(xs, ys)
        in_mask = t.inside(np.c_[gx.ravel(), gy.ravel()]).reshape(t.elev.shape)

        rgba = np.ones((*t.elev.shape, 4), dtype=np.float32)
        rgba[..., :3] = rgb_shade[..., :3]
        rgba[~in_mask, :3] = 0.965
        rgba[~in_mask, 3] = 1.0
        ax.imshow(rgba, origin="lower", extent=[0, t.width, 0, t.height], zorder=1)

        # 2. Retícula modular de 1 hectárea (100 m x 100 m)
        for x_grid in np.arange(0.0, t.width + 1.0, 100.0):
            ax.axvline(x_grid, color="#222222", linestyle=":", linewidth=0.7, alpha=0.32, zorder=2)
        for y_grid in np.arange(0.0, t.height + 1.0, 100.0):
            ax.axhline(y_grid, color="#222222", linestyle=":", linewidth=0.7, alpha=0.32, zorder=2)

        # 3. Curvas de nivel
        z_min, z_max = float(np.nanmin(t.elev)), float(np.nanmax(t.elev))
        step = 1.0 if (z_max - z_min <= 22.0) else 2.0
        cs = ax.contour(
            xs, ys, t.elev,
            levels=np.arange(math.floor(z_min), math.ceil(z_max) + step, step),
            colors="#333333", linewidths=0.45, alpha=0.45, zorder=2
        )
        ax.clabel(cs, inline=True, fontsize=6.2, fmt="%.0f m")

        # 4. Zonas de pendiente >= 20% (Tipología H2 a 524 pl/ha)
        steep_mask = (t.zone > 0) & in_mask
        overlay = None
        if np.any(steep_mask):
            overlay = np.zeros((*t.elev.shape, 4), dtype=np.float32)
            overlay[steep_mask] = [0.85, 0.12, 0.12, 0.35]
            ax.imshow(overlay, origin="lower", extent=[0, t.width, 0, t.height], zorder=3)
            ax.contour(xs, ys, steep_mask.astype(float), levels=[0.5], colors=["#b71c1c"], linewidths=1.4, linestyles="--", zorder=4)

        # 5. Perímetro oficial del polígono
        ax.add_patch(MplPolygon(t.polygon, closed=True, fill=False, edgecolor="#111111", linewidth=1.8, zorder=5))

        # 6. Aristas de la malla completa
        segs = np.stack([coords[edges[:, 0]], coords[edges[:, 1]]], axis=1)
        edge_lw = 0.40 if len(coords) < 1500 else 0.22
        edge_alpha = 0.36 if len(coords) < 1500 else 0.22
        ax.add_collection(LineCollection(segs, colors="#333333", linewidths=edge_lw, alpha=edge_alpha, zorder=5))

        # 7. Todas las plantas del polígono
        pt_size = 18.5 if len(coords) < 1500 else 6.8
        if np.any(is_fixed):
            ax.scatter(
                coords[is_fixed, 0], coords[is_fixed, 1],
                s=pt_size * 1.9, facecolors="none", edgecolors="#000000",
                linewidths=0.75 if len(coords) < 1500 else 0.55, zorder=7
            )

        for sp_id in range(len(species_colors)):
            mask = (sol == sp_id)
            if np.any(mask):
                ax.scatter(
                    coords[mask, 0], coords[mask, 1],
                    s=pt_size * (1.22 if sp_id in BIG_SPECIES_IDS else 1.0),
                    color=species_colors[sp_id], edgecolors="#111111",
                    linewidths=0.30 if len(coords) < 1500 else 0.18, zorder=6
                )

        # 8. Acercamiento (Zoom Inset) de la costura H1/H3 (4.19 m) <-> H2 (4.69 m)
        if pid in (29, 31) and np.any(zone_arr == 1):
            steep_pts = coords[zone_arr == 1]
            zc = steep_pts.mean(axis=0)
            half_w = 34.0
            x1, x2 = max(0.0, zc[0] - half_w), min(t.width, zc[0] + half_w)
            y1, y2 = max(0.0, zc[1] - half_w), min(t.height, zc[1] + half_w)

            # En P31 la esquina superior izquierda está completamente fuera del polígono (cero obstrucción!)
            inset_loc = "lower left" if pid == 29 else "upper left"
            ax_ins = inset_axes(ax, width="36%", height="36%", loc=inset_loc, borderpad=1.25)
            ax_ins.imshow(rgba, origin="lower", extent=[0, t.width, 0, t.height], zorder=1)
            if overlay is not None:
                ax_ins.imshow(overlay, origin="lower", extent=[0, t.width, 0, t.height], zorder=2)
                ax_ins.contour(xs, ys, steep_mask.astype(float), levels=[0.5], colors=["#b71c1c"], linewidths=1.25, linestyles="--", zorder=3)
            ax_ins.add_patch(MplPolygon(t.polygon, closed=True, fill=False, edgecolor="#111111", linewidth=1.3, zorder=4))

            in_box_e = (
                (coords[edges[:, 0], 0] >= x1 - 5) & (coords[edges[:, 0], 0] <= x2 + 5) &
                (coords[edges[:, 0], 1] >= y1 - 5) & (coords[edges[:, 0], 1] <= y2 + 5)
            )
            ax_ins.add_collection(LineCollection(segs[in_box_e], colors="#333333", linewidths=0.55, alpha=0.52, zorder=4))

            in_box_n = (coords[:, 0] >= x1 - 2) & (coords[:, 0] <= x2 + 2) & (coords[:, 1] >= y1 - 2) & (coords[:, 1] <= y2 + 2)
            for sp_id in range(len(species_colors)):
                m_ins = in_box_n & (sol == sp_id)
                if np.any(m_ins):
                    ax_ins.scatter(coords[m_ins, 0], coords[m_ins, 1], s=29, color=species_colors[sp_id], edgecolors="#111111", linewidths=0.45, zorder=6)
            m_fix_ins = in_box_n & is_fixed
            if np.any(m_fix_ins):
                ax_ins.scatter(coords[m_fix_ins, 0], coords[m_fix_ins, 1], s=54, facecolors="none", edgecolors="#000000", linewidths=1.1, zorder=7)

            ax_ins.set_xlim(x1, x2)
            ax_ins.set_ylim(y1, y2)
            ax_ins.set_aspect("equal")
            ax_ins.set_xticks([])
            ax_ins.set_yticks([])
            for spine in ax_ins.spines.values():
                spine.set_edgecolor("#b71c1c")
                spine.set_linewidth(1.6)
            ax_ins.set_title(
                "Lupa Costura H1(4.19m) ↔ H2(4.69m)",
                fontsize=7.3, weight="bold", color="#b71c1c", pad=3,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#b71c1c", alpha=0.95),
            )
            ax.add_patch(Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, edgecolor="#b71c1c", linewidth=1.6, zorder=8))

        n_h2 = int(np.sum(zone_arr == 1))
        n_h13 = int(np.sum(zone_arr == 0))
        costo_tot_str = f"MXN {row['costo_vivero_total_mxn']:,.0f}"
        costo_ha_str = f"MXN {row['costo_vivero_por_ha_mxn']:,.0f}/ha"
        sub = (
            f"Área: {row['area_ha']:.2f} ha (<20%: {row['area_plana_ha']:.2f} ha [{n_h13:,d} pl] | >=20%: {row['area_pend_ge20_ha']:.2f} ha [{n_h2:,d} pl])\n"
            f"Vivas Ei: {int(row['plantas_vivas_Ei']):,d} | Nuevas: {int(row['plantas_nuevas_total']):,d} | Total Nz: {len(coords):,d} | "
            f"Vivero: {costo_tot_str} ({costo_ha_str}) | Sobrev: {row['sobrev_efectiva_espacial_pct']:.2f}%"
        )
        ax.set_title(f"{titles[pid]}\n{sub}", fontsize=8.4, weight="bold", pad=8)
        ax.set_xlabel("Este local X (m) — Retícula punteada cada 100 m (1 ha)", fontsize=8.2)
        ax.set_ylabel("Norte local Y (m)", fontsize=8.2)
        ax.tick_params(labelsize=7.8)
        ax.set_aspect("equal")

    legend_handles = [
        Line2D([0], [0], marker="o", color="w", label=species_short[i], markerfacecolor=species_colors[i], markeredgecolor="#111111", markersize=7.5)
        for i in range(len(species_colors))
    ]
    legend_handles.append(
        Line2D([0], [0], marker="o", color="w", label="Anillo Negro = Planta Viva Preexistente (Ei)", markerfacecolor="white", markeredgecolor="#000000", markeredgewidth=1.4, markersize=8.0)
    )
    legend_handles.append(
        Line2D([0], [0], color="#b71c1c", linestyle="--", linewidth=1.5, label="Zona Roja >=20% Pendiente (Tipología H2: 524 pl/ha, d=4.69 m)")
    )

    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=6,
        fontsize=8.3,
        frameon=True,
        facecolor="#fafafa",
        edgecolor="#cccccc",
        bbox_to_anchor=(0.51, 0.008),
    )

    fig.suptitle(
        "MAPEO DE MALLA COMPLETA (100% DE LAS PLANTAS) SOBRE POLÍGONOS REALES UTM 14N\n"
        "Integración Total de Bloques de 1 Hectárea (Retícula 100×100 m), Plantas Vivas Censadas (Ei) y Zonas de Ladera >=20% (H2)",
        fontsize=13.5,
        weight="bold",
        y=0.972,
    )

    out_path = OUT_DIR / "malla_completa_poligonos_totales.png"
    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[OK] Re-renderizado limpio en: {out_path}")


if __name__ == "__main__":
    main()
