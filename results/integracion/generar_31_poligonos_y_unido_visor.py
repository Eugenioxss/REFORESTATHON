#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_31_poligonos_y_unido_visor.py
===============================================================================
Genera las mallas completas de LOS 31 POLÍGONOS OFICIALES (P01 a P31, 124,514 plantas
totales = 24,416 vivas Ei + 100,098 nuevas) + las 2 tipologías modulares de 1 ha
(1ha_H1 y 1ha_H2), con coordenadas reales UTM 14N para ensamblar la vista unificada
del parque ("PARQUE_UNIDO") y las 31 vistas individuales en el visor HTML5 interactivo.
===============================================================================
"""

import csv
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Dict

import numpy as np
import pandas as pd

INTEGRACION_DIR = Path(__file__).resolve().parent
if str(INTEGRACION_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRACION_DIR))

from terreno import Terrain
from reforestacion_pipeline_integrado import (
    load_semiraw_datasets,
    build_ecological_matrices,
    BIG_SPECIES_IDS,
)
from generar_mallas_completas_300dpi import (
    SPECIES_NAMES,
    SPECIES_SHORT,
    SPECIES_COLORS,
    build_full_polygon_graph,
    place_exact_preexisting_nodes,
    gpu_full_mesh_optimizer,
)

POLI31_DIR = Path(r"D:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\subagente_1\data\poli31")
OUT_DIR = INTEGRACION_DIR / "outputs_presentacion"


def load_utm_origins(utm_csv: Path) -> Dict[int, tuple]:
    origins: Dict[int, list] = {}
    with open(utm_csv, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            pid = int(r["poligono"])
            origins.setdefault(pid, []).append((float(r["E_utm14N"]), float(r["N_utm14N"])))
    out = {}
    for pid, pts in origins.items():
        e_min = min(p[0] for p in pts)
        n_min = min(p[1] for p in pts)
        out[pid] = (round(e_min, 2), round(n_min, 2))
    return out


def main() -> None:
    t0 = time.time()
    df_cat, _, _ = load_semiraw_datasets(poligonos_dir=POLI31_DIR)
    _, _, Phi = build_ecological_matrices(df_cat, lam=1.0, slope_pct=6.0, density_per_ha=658.0)

    poly_csv = POLI31_DIR / "poligonos_31.csv"
    utm_csv = POLI31_DIR / "poligonos_utm.csv"
    dem_csv = POLI31_DIR / "dem_srtm_puntos.csv"
    df_res = pd.read_csv(OUT_DIR / "resumen_31_poligonos_completo.csv")
    utm_origins = load_utm_origins(utm_csv)

    # Cargar json actual para preservar 1ha_H1 y 1ha_H2 exactos
    json_path = OUT_DIR / "datos_mallas_completas_visor.json"
    with open(json_path, "r", encoding="utf-8") as f:
        existing_payload = json.load(f)

    views: Dict[str, Any] = {}
    if "1ha_H1" in existing_payload.get("views", {}):
        views["1ha_H1"] = existing_payload["views"]["1ha_H1"]
    if "1ha_H2" in existing_payload.get("views", {}):
        views["1ha_H2"] = existing_payload["views"]["1ha_H2"]

    total_nodes_all = 0
    total_ei_all = 0
    total_edges_all = 0

    # Calcular caja envolvente global UTM de los 31 polígonos
    all_utm_e = []
    all_utm_n = []
    with open(utm_csv, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            all_utm_e.append(float(r["E_utm14N"]))
            all_utm_n.append(float(r["N_utm14N"]))
    global_e_min = round(min(all_utm_e), 2)
    global_n_min = round(min(all_utm_n), 2)
    global_e_max = round(max(all_utm_e), 2)
    global_n_max = round(max(all_utm_n), 2)

    print(f"Generando mallas completas para los 31 polígonos (UTM E:[{global_e_min}, {global_e_max}], N:[{global_n_min}, {global_n_max}])...")

    for pid in range(1, 32):
        tp = time.time()
        row = df_res[df_res["poligono_id"] == pid].iloc[0]
        area_ha = float(row["area_ha"])
        t = Terrain.from_poligonos(str(poly_csv), pid=pid, utm=str(utm_csv), dem_pts=str(dem_csv), slope_deg=6.0, seed=1)
        t.zonas(pend_pct=20.0, min_ha=0.10)

        frac_plana = float(t.zone_frac[0])
        frac_pend = float(t.zone_frac[1])
        n_plana = int(math.floor(658.0 * area_ha * frac_plana + 1e-9))
        n_pend = int(math.ceil(524.0 * area_ha * frac_pend - 1e-9)) if frac_pend > 0 else 0
        graph, z_arr = build_full_polygon_graph(t, n_plana=n_plana, n_pend=n_pend)

        E_i = np.array([int(row[f"{sp}_vivas"]) for sp in SPECIES_NAMES], dtype=int)
        Nz_sp = np.array([int(row[f"{sp}_meta_Nz"]) for sp in SPECIES_NAMES], dtype=int)

        fixed_map = place_exact_preexisting_nodes(graph, E_i, seed=pid + 500)
        # Optimización rápida en GPU para cada polígono completo
        sol, _ = gpu_full_mesh_optimizer(
            graph, Phi, Nz_sp, fixed_map, n_replicas=48, n_steps=320, seed=pid + 900
        )
        fixed_set = set(fixed_map.keys())

        # Celdas de pendiente >= 20%
        xs = (np.arange(t.nx) + 0.5) * t.cx
        ys = (np.arange(t.ny) + 0.5) * t.cy
        gx, gy = np.meshgrid(xs, ys)
        in_mask = t.inside(np.c_[gx.ravel(), gy.ravel()]).reshape(t.elev.shape)
        steep_iy, steep_ix = np.where((t.zone > 0) & in_mask)
        steep_rects = [
            [round(float(ix * t.cx), 1), round(float(iy * t.cy), 1), round(float(t.cx), 2), round(float(t.cy), 2)]
            for iy, ix in zip(steep_iy, steep_ix)
        ]

        e0, n0 = utm_origins[pid]
        vkey = f"P{pid:02d}"
        n_nodes = len(graph.coords)
        n_ei = len(fixed_set)
        n_new = n_nodes - n_ei
        total_nodes_all += n_nodes
        total_ei_all += n_ei
        total_edges_all += len(graph.edge_u)

        extra_tag = " (Imputado Vecinos 28, 30 y 22)" if pid == 29 else ""
        views[vkey] = {
            "pid": pid,
            "title": f"Polígono Oficial {pid:02d} ({area_ha:.2f} ha){extra_tag} — Malla Completa",
            "subtitle": (
                f"Total: {n_nodes:,d} pl (<20% H1: {int(np.sum(z_arr==0)):,d} | >=20% H2: {int(np.sum(z_arr==1)):,d}) | "
                f"Vivas Ei: {n_ei:,d} ({n_ei/area_ha:.1f}/ha) | Nuevas: {n_new:,d} | "
                f"Vivero: ${float(row['costo_vivero_total_mxn']):,.0f} MXN | Sobrev.: {float(row['sobrev_efectiva_espacial_pct']):.2f}%"
            ),
            "area_ha": round(area_ha, 2),
            "costo_mxn": round(float(row["costo_vivero_total_mxn"]), 2),
            "sobrev_pct": round(float(row["sobrev_efectiva_espacial_pct"]), 2),
            "width": round(float(t.width), 2),
            "height": round(float(t.height), 2),
            "utm_e0": e0,
            "utm_n0": n0,
            "step_d": round(float(graph.step_d), 3),
            "polygon": [[round(float(pt[0]), 1), round(float(pt[1]), 1)] for pt in t.polygon],
            "steep_cells": steep_rects,
            "nodes": [
                [
                    round(float(graph.coords[p, 0]), 1),
                    round(float(graph.coords[p, 1]), 1),
                    int(sol[p]),
                    1 if p in fixed_set else 0,
                    1 if graph.big_mask[p] else 0,
                    int(z_arr[p]),
                ]
                for p in range(n_nodes)
            ],
            "edges": [[int(graph.edge_u[e]), int(graph.edge_v[e])] for e in range(len(graph.edge_u))],
        }
        print(
            f"  [P{pid:02d}] {area_ha:5.2f} ha | Nz={n_nodes:5,d} (Ei={n_ei:4,d}, Nuevas={n_new:4,d}) | "
            f"Aristas={len(graph.edge_u):6,d} | {time.time() - tp:.2f}s"
        )

    payload_out = {
        "species_names": SPECIES_NAMES,
        "species_short": SPECIES_SHORT,
        "species_colors": SPECIES_COLORS,
        "big_species_ids": sorted(list(BIG_SPECIES_IDS)),
        "park_meta": {
            "utm_e_min": global_e_min,
            "utm_n_min": global_n_min,
            "utm_e_max": global_e_max,
            "utm_n_max": global_n_max,
            "width": round(global_e_max - global_e_min, 2),
            "height": round(global_n_max - global_n_min, 2),
            "total_area_ha": round(float(df_res["area_ha"].sum()), 2),
            "total_nodes_Nz": total_nodes_all,
            "total_vivas_Ei": total_ei_all,
            "total_nuevas": total_nodes_all - total_ei_all,
            "total_edges": total_edges_all,
            "total_costo_mxn": round(float(df_res["costo_vivero_total_mxn"].sum()), 2),
            "mean_sobrev_pct": round(float((df_res["sobrev_efectiva_espacial_pct"] * df_res["area_ha"]).sum() / df_res["area_ha"].sum()), 2),
        },
        "views": views,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload_out, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = json_path.stat().st_size / (1024 * 1024)
    print("=" * 80)
    print(f"[OK] JSON con los 31 polígonos + H1/H2 guardado en: {json_path} ({size_mb:.2f} MB)")
    print(f"     Plantas totales: {total_nodes_all:,d} | Vivas Ei: {total_ei_all:,d} | Nuevas: {total_nodes_all - total_ei_all:,d}")
    print(f"     Aristas totales: {total_edges_all:,d} | Tiempo: {time.time() - t0:.2f}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
