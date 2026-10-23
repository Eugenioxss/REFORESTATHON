#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_mallas_completas_300dpi.py
===============================================================================
Generación de Mallas Completas ("TODA LA MALLA") a 300 DPI + Datos para Visor:
1. malla_completa_1ha_H1_H2_H3.png:
   Los 3 bloques modulares completos de 1 hectárea (100 m x 100 m) nodo por nodo:
   - H1: Valle <20% con dosel preexistente (658 nodos = 129 vivas fijas + 529 nuevas, d = 4.19 m)
   - H2: Ladera >=20% en curva de nivel (524 nodos = 103 vivas fijas + 421 nuevas, d = 4.69 m)
   - H3: Restauración Cero Polígono 29 <20% (658 nodos = 0 vivas + 658 nuevas, d = 4.19 m)
2. malla_completa_poligonos_totales.png:
   Mapeo del 100% de las plantas dentro del polígono real UTM 14N (sin recortes a 66 nodos),
   cosiendo zonas planas (H1/H3 a 658 pl/ha) y manchas de pendiente >=20% (H2 a 524 pl/ha),
   con cuadrícula modular de 1 ha (100x100 m) y acercamientos (zoom insets) de costura:
   - Polígono 12 (1.47 ha -> 967 plantas totales: 204 vivas + 763 nuevas)
   - Polígono 29 (6.54 ha -> 4,287 plantas totales: 0 vivas + 4,222 en H3 + 65 en H2)
   - Polígono 19 (4.92 ha -> 3,237 plantas totales: 623 vivas + 2,614 nuevas)
   - Polígono 31 (7.34 ha -> 4,781 plantas totales: 946 vivas + 4,591 en H1 + 190 en H2)
3. datos_mallas_completas_visor.json:
   Exportación completa de coordenadas, especies, condición (viva vs nueva), subred big_index=3
   y polígonos para el visor HTML5 interactivo con zoom en vivo.
===============================================================================
"""

import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

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
from scipy.spatial import cKDTree
import torch

INTEGRACION_DIR = Path(__file__).resolve().parent
if str(INTEGRACION_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRACION_DIR))

from terreno import Terrain
from reforestacion_pipeline_integrado import (
    load_semiraw_datasets,
    build_ecological_matrices,
    compute_exact_quotas,
    audit_ecological_metrics,
    solve_reforestation_mip,
    BIG_SPECIES_IDS,
    HexGridGraph,
)

POLI31_DIR = Path(r"D:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\subagente_1\data\poli31")
OUT_DIR = INTEGRACION_DIR / "outputs_presentacion"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SPECIES_NAMES = [
    "Agave lechuguilla",
    "Agave salmiana",
    "Agave scabra",
    "Agave striata",
    "Opuntia cantabrigiensis",
    "Opuntia engelmannii",
    "Opuntia robusta",
    "Opuntia streptacantha",
    "Prosopis laevigata",
    "Yucca filifera",
]

SPECIES_SHORT = [
    "A. lechuguilla",
    "A. salmiana",
    "A. scabra",
    "A. striata",
    "O. cantabrigiensis",
    "O. engelmannii",
    "O. robusta",
    "O. streptacantha*",
    "P. laevigata* (Nodriza)",
    "Y. filifera*",
]

SPECIES_COLORS = [
    "#2ca02c",  # 0: A. lechuguilla
    "#1f77b4",  # 1: A. salmiana
    "#17becf",  # 2: A. scabra
    "#98df8a",  # 3: A. striata
    "#ff7f0e",  # 4: O. cantabrigiensis
    "#ffbb78",  # 5: O. engelmannii
    "#d62728",  # 6: O. robusta
    "#9467bd",  # 7: O. streptacantha (Grande)
    "#7f3b08",  # 8: P. laevigata (Grande / Nodriza)
    "#e377c2",  # 9: Y. filifera (Grande)
]


# ==============================================================================
# 1. CONSTRUCCIÓN DE GRAFOS TRESBOLILLO EXACTOS (1 HA Y POLÍGONO COMPLETO)
# ==============================================================================
def build_graph_from_coords_and_ij(
    coords: np.ndarray,
    grid_i: np.ndarray,
    grid_j: np.ndarray,
    step_d: float,
    ring_level: int = 1,
    big_index: int = 3,
) -> HexGridGraph:
    """Construye HexGridGraph rápido usando cKDTree para mallas de 500 a 6,000 nodos."""
    r_crit = step_d * (1.15 if ring_level <= 1 else 1.85)
    tree = cKDTree(coords)
    pairs = tree.query_pairs(r=r_crit, output_type="ndarray")
    if len(pairs) == 0:
        u_idx = np.zeros(0, dtype=np.int32)
        v_idx = np.zeros(0, dtype=np.int32)
        dists = np.zeros(0, dtype=np.float64)
        weights = np.zeros(0, dtype=np.float64)
    else:
        u_idx = pairs[:, 0].astype(np.int32)
        v_idx = pairs[:, 1].astype(np.int32)
        dists = np.linalg.norm(coords[u_idx] - coords[v_idx], axis=1)
        valid = dists > 1e-6
        u_idx, v_idx, dists = u_idx[valid], v_idx[valid], dists[valid]
        weights = step_d / dists

    if big_index > 1:
        big_mask = ((grid_i - grid_j) % big_index == 0)
    else:
        big_mask = np.ones(len(coords), dtype=bool)

    return HexGridGraph(
        coords=coords,
        edge_u=u_idx,
        edge_v=v_idx,
        edge_dist=dists,
        edge_weight=weights,
        step_d=step_d,
        r_crit=r_crit,
        grid_i=grid_i,
        grid_j=grid_j,
        big_mask=big_mask,
        big_index=big_index,
    )


def build_exact_1ha_hex_grid(target_nodes: int, angle_deg: float = 0.0) -> HexGridGraph:
    """
    Construye una malla tresbolillo exacta dentro de un bloque de 1 ha (100 m x 100 m)
    con exactamente `target_nodes` nodos (658 para H1/H3 con d=4.19 m; 524 para H2 con d=4.69 m).
    """
    step_d = math.sqrt(20000.0 / (math.sqrt(3.0) * target_nodes))
    dy = (math.sqrt(3.0) / 2.0) * step_d

    if target_nodes == 658:
        # 28 filas alternadas de 24 y 23 columnas = 14*24 + 14*23 = 658 nodos exactos en 100x100 m
        coords_list, gi_list, gj_list = [], [], []
        w_span = 23.0 * step_d
        h_span = 27.0 * dy
        x0 = 0.5 * (100.0 - w_span)
        y0 = 0.5 * (100.0 - h_span)
        for r in range(28):
            n_c = 24 if (r % 2 == 0) else 23
            for c in range(n_c):
                x = x0 + (c + 0.5 * (r % 2)) * step_d
                y = y0 + r * dy
                coords_list.append((x, y))
                gi_list.append(c)
                gj_list.append(r)
        coords = np.array(coords_list, dtype=np.float64)
        gi = np.array(gi_list, dtype=np.int32)
        gj = np.array(gj_list, dtype=np.int32)
        return build_graph_from_coords_and_ij(coords, gi, gj, step_d=step_d, ring_level=1, big_index=3)

    # Caso general (p. ej. 524 nodos en 100x100 m, opcionalmente alineado a ángulo de curva de nivel)
    theta = math.radians(angle_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    center = np.array([50.0, 50.0])

    best_pts, best_gi, best_gj, best_diff = None, None, None, 10**9
    for scale in np.linspace(0.96, 1.04, 81):
        d_try = step_d * scale
        dy_try = (math.sqrt(3.0) / 2.0) * d_try
        pts, gi, gj = [], [], []
        for r in range(-22, 23):
            for c in range(-22, 23):
                u = (c + 0.5 * (r % 2)) * d_try
                v = r * dy_try
                x = center[0] + u * cos_t - v * sin_t
                y = center[1] + u * sin_t + v * cos_t
                margin = 1.6
                if margin <= x <= 100.0 - margin and margin <= y <= 100.0 - margin:
                    pts.append((x, y))
                    gi.append(c + 50)
                    gj.append(r + 50)
        diff = abs(len(pts) - target_nodes)
        if len(pts) >= target_nodes and diff < best_diff:
            best_pts, best_gi, best_gj, best_diff = pts, gi, gj, diff
            if diff == 0:
                break

    pts_arr = np.array(best_pts, dtype=np.float64)
    gi_arr = np.array(best_gi, dtype=np.int32)
    gj_arr = np.array(best_gj, dtype=np.int32)
    if len(pts_arr) > target_nodes:
        # Recortar simétricamente los puntos más cercanos a las esquinas exteriores
        corner_score = np.maximum(np.abs(pts_arr[:, 0] - 50.0), np.abs(pts_arr[:, 1] - 50.0))
        keep_idx = np.argsort(corner_score)[:target_nodes]
        keep_idx = np.sort(keep_idx)
        pts_arr = pts_arr[keep_idx]
        gi_arr = gi_arr[keep_idx]
        gj_arr = gj_arr[keep_idx]

    return build_graph_from_coords_and_ij(pts_arr, gi_arr, gj_arr, step_d=step_d, ring_level=1, big_index=3)


def generate_zone_lattice_points(
    t: Terrain,
    zone_is_steep: bool,
    target_count: int,
    base_density: float,
    angle_deg: float = 0.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """
    Genera exactamente `target_count` posiciones en tresbolillo dentro de la zona correspondiente
    (`zone_is_steep=False` -> pendiente <20% a ~658 pl/ha; `True` -> pendiente >=20% a ~524 pl/ha).
    """
    if target_count <= 0:
        return np.zeros((0, 2)), np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32), 4.19

    step_nominal = math.sqrt(20000.0 / (math.sqrt(3.0) * base_density))
    W, H = t.width, t.height
    cx, cy = 0.5 * W, 0.5 * H
    theta = math.radians(angle_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    diag = math.hypot(W, H)

    def sample_at_scale(scale: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        d = step_nominal * scale
        dy = (math.sqrt(3.0) / 2.0) * d
        nr = int(math.ceil(diag / dy)) + 4
        nc = int(math.ceil(diag / d)) + 4
        r_idx = np.arange(-nr, nr + 1, dtype=np.int32)
        c_idx = np.arange(-nc, nc + 1, dtype=np.int32)
        CC, RR = np.meshgrid(c_idx, r_idx)
        cc = CC.ravel()
        rr = RR.ravel()
        u = (cc + 0.5 * (rr % 2)) * d
        v = rr * dy
        x = cx + u * cos_t - v * sin_t
        y = cy + u * sin_t + v * cos_t
        pts = np.c_[x, y]
        in_box = (x >= 0.0) & (x <= W) & (y >= 0.0) & (y <= H)
        pts = pts[in_box]
        cc = cc[in_box]
        rr = rr[in_box]
        if len(pts) == 0:
            return pts, cc, rr
        in_poly = t.inside(pts)
        pts = pts[in_poly]
        cc = cc[in_poly]
        rr = rr[in_poly]
        if len(pts) == 0:
            return pts, cc, rr
        iy, ix = t._ij(pts)
        z_mask = (t.zone[iy, ix] > 0) if zone_is_steep else (t.zone[iy, ix] == 0)
        return pts[z_mask], (cc[z_mask] + 2000), (rr[z_mask] + 2000)

    # Búsqueda binaria de escala alrededor de 1.0 (compensa diferencia entre área oficial y digitalizada)
    lo, hi = 0.78, 1.25
    best_pts, best_gi, best_gj, best_scale = None, None, None, 1.0
    for _ in range(28):
        mid = 0.5 * (lo + hi)
        pts, gi, gj = sample_at_scale(mid)
        if len(pts) >= target_count:
            best_pts, best_gi, best_gj, best_scale = pts, gi, gj, mid
            lo = mid
        else:
            hi = mid

    if best_pts is None:
        best_pts, best_gi, best_gj = sample_at_scale(lo)
        best_scale = lo

    if len(best_pts) > target_count:
        # Recorte suave desde el borde exterior hacia adentro para conservar regularidad interna intacta
        center_pt = best_pts.mean(axis=0)
        dist_center = np.linalg.norm(best_pts - center_pt, axis=1)
        keep = np.argsort(dist_center)[:target_count]
        keep = np.sort(keep)
        best_pts = best_pts[keep]
        best_gi = best_gi[keep]
        best_gj = best_gj[keep]

    return best_pts, best_gi, best_gj, step_nominal * best_scale


def build_full_polygon_graph(
    t: Terrain,
    n_plana: int,
    n_pend: int,
) -> Tuple[HexGridGraph, np.ndarray]:
    """
    Construye la malla COMPLETA de un polígono cosiendo:
    - Zona 0 (<20% pendiente, H1/H3 a 658 pl/ha, d ~ 4.19 m)
    - Zona 1 (>=20% pendiente, H2 a 524 pl/ha, d ~ 4.69 m alineada al contorno medio)
    Retorna (HexGridGraph, zone_arr) donde zone_arr[p] = 0 (plana) o 1 (ladera >=20%).
    """
    pts0, gi0, gj0, d0 = generate_zone_lattice_points(t, zone_is_steep=False, target_count=n_plana, base_density=658.0, angle_deg=0.0)

    if n_pend > 0 and hasattr(t, "zone") and np.any(t.zone > 0):
        # Ángulo medio de las curvas de nivel en la mancha de pendiente >=20%
        steep_mask = (t.zone > 0)
        if np.any(steep_mask):
            asp_rad = np.radians(t.aspect[steep_mask])
            mean_aspect = math.degrees(math.atan2(float(np.mean(np.sin(asp_rad))), float(np.mean(np.cos(asp_rad)))))
            contour_angle = (mean_aspect + 90.0) % 180.0
        else:
            contour_angle = 12.0
        pts1, gi1, gj1, d1 = generate_zone_lattice_points(
            t, zone_is_steep=True, target_count=n_pend, base_density=524.0, angle_deg=contour_angle
        )
        coords = np.vstack([pts0, pts1])
        gi = np.concatenate([gi0, gi1])
        gj = np.concatenate([gj0, gj1])
        zone_arr = np.concatenate([np.zeros(len(pts0), dtype=np.int32), np.ones(len(pts1), dtype=np.int32)])
        step_ref = (d0 * len(pts0) + d1 * len(pts1)) / max(1, len(coords))
    else:
        coords = pts0
        gi = gi0
        gj = gj0
        zone_arr = np.zeros(len(pts0), dtype=np.int32)
        step_ref = d0

    # Construir aristas permitiendo acoplamiento en la costura entre Zona 0 y Zona 1 (r_crit = 1.18 * max_d)
    r_crit = max(d0, 4.70 if n_pend > 0 else d0) * 1.16
    tree = cKDTree(coords)
    pairs = tree.query_pairs(r=r_crit, output_type="ndarray")
    u_idx = pairs[:, 0].astype(np.int32)
    v_idx = pairs[:, 1].astype(np.int32)
    dists = np.linalg.norm(coords[u_idx] - coords[v_idx], axis=1)
    valid = dists > 1e-6
    u_idx, v_idx, dists = u_idx[valid], v_idx[valid], dists[valid]
    weights = step_ref / np.maximum(dists, 1.5)
    big_mask = ((gi - gj) % 3 == 0)

    graph = HexGridGraph(
        coords=coords,
        edge_u=u_idx,
        edge_v=v_idx,
        edge_dist=dists,
        edge_weight=weights,
        step_d=step_ref,
        r_crit=r_crit,
        grid_i=gi,
        grid_j=gj,
        big_mask=big_mask,
        big_index=3,
    )
    return graph, zone_arr


# ==============================================================================
# 2. COLOCACIÓN DE PLANTAS VIVAS Y OPTIMIZACIÓN GPU + RED-BLACK HALO MILP
# ==============================================================================
def place_exact_preexisting_nodes(
    graph: HexGridGraph,
    E_i: np.ndarray,
    seed: int = 42,
) -> Dict[int, int]:
    """Coloca exactamente sum(E_i) plantas preexistentes respetando big_mask y evitando choques."""
    m = len(graph.coords)
    total_vivas = int(E_i.sum())
    if total_vivas <= 0:
        return {}

    adj: List[List[int]] = [[] for _ in range(m)]
    for e in range(len(graph.edge_u)):
        u, v = int(graph.edge_u[e]), int(graph.edge_v[e])
        adj[u].append(v)
        adj[v].append(u)

    rng = np.random.default_rng(seed)
    candidates = list(range(m))
    rng.shuffle(candidates)
    fixed_nodes: Dict[int, int] = {}

    def place_sp(sp: int, count: int) -> None:
        if count <= 0:
            return
        placed = 0
        is_big = sp in BIG_SPECIES_IDS
        if is_big:
            for p in candidates:
                if placed >= count:
                    break
                if p not in fixed_nodes and graph.big_mask[p] and all(fixed_nodes.get(nb, -1) != sp for nb in adj[p]):
                    fixed_nodes[p] = sp
                    placed += 1
            for p in candidates:
                if placed >= count:
                    break
                if p not in fixed_nodes and graph.big_mask[p]:
                    fixed_nodes[p] = sp
                    placed += 1
        for p in candidates:
            if placed >= count:
                break
            if p not in fixed_nodes and all(fixed_nodes.get(nb, -1) != sp for nb in adj[p]):
                fixed_nodes[p] = sp
                placed += 1
        for p in candidates:
            if placed >= count:
                break
            if p not in fixed_nodes:
                fixed_nodes[p] = sp
                placed += 1

    # Primero Prosopis (8), luego otras grandes (7, 9), luego el resto
    for sp in [8, 7, 9, 1, 6, 4, 0, 2, 3, 5]:
        place_sp(sp, int(E_i[sp]))

    return fixed_nodes


def gpu_full_mesh_optimizer(
    graph: HexGridGraph,
    Phi: np.ndarray,
    quotas_total: np.ndarray,
    fixed_nodes: Dict[int, int],
    n_replicas: int = 128,
    n_steps: int = 3500,
    seed: int = 42,
) -> Tuple[np.ndarray, float]:
    """
    Optimización espacial vectorizada en GPU RTX 3060 sobre la malla COMPLETA (524 a 5,000 nodos),
    respetando exactamente:
    - Nodos preexistentes fijos (fixed_nodes)
    - Subred hexagonal big_index=3 para especies grandes (7, 8, 9)
    - Cuotas exactas por especie (quotas_total)
    """
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    m = len(graph.coords)
    rem_quotas = quotas_total.copy()
    for _, sp in fixed_nodes.items():
        if rem_quotas[sp] > 0:
            rem_quotas[sp] -= 1

    free_positions = [p for p in range(m) if p not in fixed_nodes]
    # Ajustar cualquier diferencia de redondeo menor
    diff_q = len(free_positions) - int(rem_quotas.sum())
    if diff_q > 0:
        rem_quotas[1] += diff_q
    elif diff_q < 0:
        for sp_trim in np.argsort(-rem_quotas):
            take = min(-diff_q, int(rem_quotas[sp_trim]))
            rem_quotas[sp_trim] -= take
            diff_q += take
            if diff_q == 0:
                break

    rng = np.random.default_rng(seed)
    states_np = np.zeros((n_replicas, m), dtype=np.int64)

    free_big_pos = np.array([p for p in free_positions if graph.big_mask[p]], dtype=int)
    free_nonbig_pos = np.array([p for p in free_positions if not graph.big_mask[p]], dtype=int)
    rem_big_sp = np.array([sp for sp in BIG_SPECIES_IDS for _ in range(int(rem_quotas[sp]))], dtype=int)
    rem_other_sp = np.array(
        [sp for sp in range(len(quotas_total)) if sp not in BIG_SPECIES_IDS for _ in range(int(rem_quotas[sp]))],
        dtype=int,
    )

    for b in range(n_replicas):
        for pos, sp in fixed_nodes.items():
            states_np[b, pos] = sp
        n_fit = min(len(rem_big_sp), len(free_big_pos))
        p_big_pos = rng.permutation(free_big_pos) if len(free_big_pos) else np.zeros(0, dtype=int)
        p_big_sp = rng.permutation(rem_big_sp) if len(rem_big_sp) else np.zeros(0, dtype=int)
        if n_fit > 0:
            states_np[b, p_big_pos[:n_fit]] = p_big_sp[:n_fit]
        leftover_sp = np.concatenate([p_big_sp[n_fit:], rem_other_sp])
        leftover_pos = np.concatenate([p_big_pos[n_fit:], free_nonbig_pos])
        states_np[b, leftover_pos] = rng.permutation(leftover_sp)

    states = torch.tensor(states_np, device=dev, dtype=torch.long)
    Phi_t = torch.tensor(Phi, device=dev, dtype=torch.float32)
    edge_u_t = torch.tensor(graph.edge_u, device=dev, dtype=torch.long)
    edge_v_t = torch.tensor(graph.edge_v, device=dev, dtype=torch.long)
    edge_w_t = torch.tensor(graph.edge_weight, device=dev, dtype=torch.float32)
    free_pos_t = torch.tensor(free_positions, device=dev, dtype=torch.long)
    big_mask_t = torch.tensor(graph.big_mask, device=dev, dtype=torch.bool)

    # Lista de incidencia por nodo en GPU para evaluación O(grado) ultra-rápida o evaluación vectorizada completa
    def batch_cost(st: torch.Tensor) -> torch.Tensor:
        return (Phi_t[st[:, edge_u_t], st[:, edge_v_t]] * edge_w_t[None, :]).sum(dim=1)

    curr_costs = batch_cost(states)
    best_idx = int(torch.argmin(curr_costs).item())
    best_cost = float(curr_costs[best_idx].item())
    best_state = states[best_idx].clone()

    n_free = len(free_positions)
    batch_arange = torch.arange(n_replicas, device=dev)
    if n_free > 1:
        T_start, T_end = 1.8, 0.008
        for step in range(n_steps):
            T = T_start * ((T_end / T_start) ** (step / max(1, n_steps)))
            pos1 = free_pos_t[torch.randint(0, n_free, (n_replicas,), device=dev)]
            pos2 = free_pos_t[torch.randint(0, n_free, (n_replicas,), device=dev)]

            v1 = states[batch_arange, pos1]
            v2 = states[batch_arange, pos2]

            is_v1_big = (v1 == 7) | (v1 == 8) | (v1 == 9)
            is_v2_big = (v2 == 7) | (v2 == 8) | (v2 == 9)
            v1_valid = (~is_v1_big) | big_mask_t[pos2] | (~big_mask_t[pos1])
            v2_valid = (~is_v2_big) | big_mask_t[pos1] | (~big_mask_t[pos2])
            valid_swap = (v1 != v2) & v1_valid & v2_valid

            prop_states = states.clone()
            prop_states[batch_arange, pos1] = v2
            prop_states[batch_arange, pos2] = v1

            prop_costs = batch_cost(prop_states)
            dE = prop_costs - curr_costs
            accept = valid_swap & ((dE <= 0.0) | (torch.rand((n_replicas,), device=dev) < torch.exp(-dE / max(1e-4, T))))

            states = torch.where(accept[:, None], prop_states, states)
            curr_costs = torch.where(accept, prop_costs, curr_costs)

            if step % 100 == 0 or step == n_steps - 1:
                min_c = float(curr_costs.min().item())
                if min_c < best_cost:
                    best_cost = min_c
                    best_state = states[int(torch.argmin(curr_costs).item())].clone()

    # Pulido greedy determinista en CPU sobre la mejor réplica para eliminar cualquier choque residual
    best_np = best_state.cpu().numpy().astype(int)
    if dev.type == "cuda":
        torch.cuda.synchronize()
        torch.cuda.empty_cache()

    best_np, best_cost = greedy_local_polish(graph, Phi, best_np, fixed_nodes, max_passes=6)
    return best_np, best_cost


def greedy_local_polish(
    graph: HexGridGraph,
    Phi: np.ndarray,
    assignment: np.ndarray,
    fixed_nodes: Dict[int, int],
    max_passes: int = 6,
) -> Tuple[np.ndarray, float]:
    """Búsqueda local exacta O(grado) para erradicar colisiones intraespecíficas residuales."""
    sol = assignment.copy()
    m = len(sol)
    adj_nb: List[List[Tuple[int, float]]] = [[] for _ in range(m)]
    for e in range(len(graph.edge_u)):
        u, v = int(graph.edge_u[e]), int(graph.edge_v[e])
        w = float(graph.edge_weight[e])
        adj_nb[u].append((v, w))
        adj_nb[v].append((u, w))

    free_pos = [p for p in range(m) if p not in fixed_nodes]
    free_big = [p for p in free_pos if graph.big_mask[p]]
    free_nonbig = [p for p in free_pos if not graph.big_mask[p]]
    rng = np.random.default_rng(123)

    def node_energy(p: int, sp: int, ignore_q: int = -1) -> float:
        s = 0.0
        for nb, w in adj_nb[p]:
            if nb != ignore_q:
                s += w * float(Phi[sp, sol[nb]])
        return s

    for _ in range(max_passes):
        improved = 0
        # 1. Resolver primero cualquier nodo libre involucrado en choque intraespecífico
        conflict_nodes = [
            p for p in free_pos if any(sol[nb] == sol[p] for nb, _ in adj_nb[p])
        ]
        rng.shuffle(conflict_nodes)
        scan_list = conflict_nodes + rng.permutation(free_pos[: min(len(free_pos), 800)]).tolist()
        for p in scan_list:
            sp_p = int(sol[p])
            pool = free_big if (sp_p in BIG_SPECIES_IDS) else (free_nonbig if not graph.big_mask[p] else free_pos)
            if len(pool) < 2:
                continue
            sample_q = rng.choice(pool, size=min(40, len(pool)), replace=False)
            e_p_curr = node_energy(p, sp_p)
            for q in sample_q:
                q = int(q)
                if q == p:
                    continue
                sp_q = int(sol[q])
                if sp_q == sp_p:
                    continue
                if (sp_p in BIG_SPECIES_IDS and not graph.big_mask[q]) or (sp_q in BIG_SPECIES_IDS and not graph.big_mask[p]):
                    continue
                before = node_energy(p, sp_p, ignore_q=q) + node_energy(q, sp_q, ignore_q=p)
                after = node_energy(p, sp_q, ignore_q=q) + node_energy(q, sp_p, ignore_q=p)
                if after < before - 1e-6:
                    sol[p], sol[q] = sp_q, sp_p
                    improved += 1
                    break
        if improved == 0:
            break

    final_cost = float(np.sum(graph.edge_weight * Phi[sol[graph.edge_u], sol[graph.edge_v]]))
    return sol, final_cost


def red_black_halo_milp_refinement_1ha(
    graph: HexGridGraph,
    Phi: np.ndarray,
    warm_sol: np.ndarray,
    fixed_nodes: Dict[int, int],
    df_sp: pd.DataFrame,
) -> np.ndarray:
    """
    Aplica barrido Red-Black con Halo acoplado (SpatialTiler) usando HiGHS MILP sobre sub-bloques
    de ~25x33 m dentro de la hectárea de 100x100 m para pulir optimalidad local y costuras.
    """
    sol = warm_sol.copy()
    coords = graph.coords
    # Dividir 100x100 m en 3x3 = 9 sub-teselas (~73 o ~58 nodos por sub-tesela)
    nx_t, ny_t = 3, 3
    adj_edges_u = graph.edge_u
    adj_edges_v = graph.edge_v

    for phase in (0, 1):  # 0 = Rojas, 1 = Negras acopladas con Halo
        for tr in range(ny_t):
            for tc in range(nx_t):
                if (tr + tc) % 2 != phase:
                    continue
                x_lo, x_hi = tc * (100.0 / nx_t), (tc + 1) * (100.0 / nx_t)
                y_lo, y_hi = tr * (100.0 / ny_t), (tr + 1) * (100.0 / ny_t)
                core_mask = (
                    (coords[:, 0] >= x_lo - 1e-6)
                    & (coords[:, 0] < (x_hi + (1e-6 if tc == nx_t - 1 else 0.0)))
                    & (coords[:, 1] >= y_lo - 1e-6)
                    & (coords[:, 1] < (y_hi + (1e-6 if tr == ny_t - 1 else 0.0)))
                )
                core_idx = np.where(core_mask)[0].tolist()
                if len(core_idx) < 10:
                    continue
                core_set = set(core_idx)
                halo_set = set()
                for e in range(len(adj_edges_u)):
                    u, v = int(adj_edges_u[e]), int(adj_edges_v[e])
                    if u in core_set and v not in core_set:
                        halo_set.add(v)
                    elif v in core_set and u not in core_set:
                        halo_set.add(u)
                halo_idx = sorted(halo_set)
                sub_nodes = core_idx + halo_idx
                g2l = {g: i for i, g in enumerate(sub_nodes)}

                sub_u, sub_v, sub_d, sub_w = [], [], [], []
                for e in range(len(adj_edges_u)):
                    u, v = int(adj_edges_u[e]), int(adj_edges_v[e])
                    if u in g2l and v in g2l:
                        lu, lv = g2l[u], g2l[v]
                        if lu > lv:
                            lu, lv = lv, lu
                        sub_u.append(lu)
                        sub_v.append(lv)
                        sub_d.append(float(graph.edge_dist[e]))
                        sub_w.append(float(graph.edge_weight[e]))

                sub_graph = HexGridGraph(
                    coords=coords[sub_nodes],
                    edge_u=np.array(sub_u, dtype=np.int32),
                    edge_v=np.array(sub_v, dtype=np.int32),
                    edge_dist=np.array(sub_d, dtype=np.float64),
                    edge_weight=np.array(sub_w, dtype=np.float64),
                    step_d=graph.step_d,
                    r_crit=graph.r_crit,
                    grid_i=graph.grid_i[sub_nodes],
                    grid_j=graph.grid_j[sub_nodes],
                    big_mask=graph.big_mask[sub_nodes],
                    big_index=graph.big_index,
                )

                sub_warm = sol[sub_nodes].copy()
                # Conservar cuotas exactas de la sub-tesela + halo para no alterar el conteo global de la hectárea
                sub_quotas = np.bincount(sub_warm, minlength=len(SPECIES_NAMES))
                sub_fixed: Dict[int, int] = {}
                for i, g in enumerate(core_idx):
                    if g in fixed_nodes:
                        sub_fixed[i] = fixed_nodes[g]
                for j, g in enumerate(halo_idx):
                    sub_fixed[len(core_idx) + j] = int(sol[g])

                opt_sub, _, _, _, _ = solve_reforestation_mip(
                    sub_graph,
                    Phi,
                    sub_quotas,
                    sub_warm,
                    fixed_nodes=sub_fixed,
                    tolerance_pct=0.0,
                    df_sp=df_sp,
                    time_limit=2,
                    cpu_threads=8,
                    solver_name="highs",
                    mu_cost=0.0,
                )
                for i, g in enumerate(core_idx):
                    sol[g] = int(opt_sub[i])

    return sol


# ==============================================================================
# 3. RENDERIZADO DE FIGURA 1: LAS 3 HECTÁREAS MODULARES COMPLETAS (H1, H2, H3)
# ==============================================================================
def render_1ha_blueprints(
    blueprints: Dict[str, Dict[str, Any]],
    out_path: Path,
) -> None:
    fig = plt.figure(figsize=(22, 11.8), dpi=300, facecolor="white")
    gs = fig.add_gridspec(2, 3, height_ratios=[4.3, 1.15], hspace=0.22, wspace=0.16, left=0.04, right=0.98, top=0.88, bottom=0.08)

    keys = ["H1", "H2", "H3"]
    panel_titles = {
        "H1": "TIPOLOGÍA H1 — Valle con Dosel Previo (<20%)\n658 plantas/ha (d = 4.19 m) | 129 Vivas Fijas + 529 Nuevas",
        "H2": "TIPOLOGÍA H2 — Ladera Antierosiva (>=20%)\n524 plantas/ha (d = 4.69 m, +12%) | 103 Vivas + 421 Nuevas",
        "H3": "TIPOLOGÍA H3 — Restauración Cero (Polígono 29, <20%)\n658 plantas/ha (d = 4.19 m) | 0 Vivas + 658 Nuevas (100%)",
    }
    panel_bg = {"H1": "#f7fbf6", "H2": "#fff8f4", "H3": "#f5f9fe"}
    border_col = {"H1": "#2e7d32", "H2": "#c62828", "H3": "#1565c0"}

    for idx, k in enumerate(keys):
        ax = fig.add_subplot(gs[0, idx])
        bp = blueprints[k]
        graph: HexGridGraph = bp["graph"]
        sol: np.ndarray = bp["sol"]
        fixed_nodes: Dict[int, int] = bp["fixed_nodes"]
        coords = graph.coords

        ax.set_facecolor(panel_bg[k])

        # Si es H2, dibujar isolíneas de curva de nivel de fondo para mostrar alineación antierosiva
        if k == "H2":
            xg = np.linspace(0, 100, 120)
            yg = np.linspace(0, 100, 120)
            XX, YY = np.meshgrid(xg, yg)
            # Ladera >=20% (24% media) inclinada perpendicular a angle_deg=12°
            th = math.radians(12.0)
            ZZ = 2430.0 + 0.24 * (-XX * math.sin(th) + YY * math.cos(th)) + 0.6 * np.sin(XX / 18.0)
            cs = ax.contour(xg, yg, ZZ, levels=np.arange(2405, 2460, 2.5), colors="#b71c1c", linewidths=0.55, alpha=0.28, linestyles="--", zorder=1)
            ax.clabel(cs, inline=True, fontsize=6.5, fmt="%.0f m")

        # Cuadrícula de sub-teselas SpatialTiler (cada 33.3 m) y borde de 1 ha (100x100 m)
        for line_pos in (33.33, 66.67):
            ax.axvline(line_pos, color="#888888", linestyle=":", linewidth=0.7, alpha=0.45, zorder=2)
            ax.axhline(line_pos, color="#888888", linestyle=":", linewidth=0.7, alpha=0.45, zorder=2)
        ax.add_patch(Rectangle((0, 0), 100, 100, fill=False, edgecolor=border_col[k], linewidth=2.2, zorder=3))

        # Aristas completas de la malla tresbolillo
        segs = np.stack([coords[graph.edge_u], coords[graph.edge_v]], axis=1)
        lc = LineCollection(segs, colors="#666666", linewidths=0.42, alpha=0.38, zorder=3)
        ax.add_collection(lc)

        # Halo dorado/oscuro alrededor de plantas VIVAS preexistentes (Ei)
        if len(fixed_nodes) > 0:
            f_idx = np.array(sorted(fixed_nodes.keys()), dtype=int)
            ax.scatter(
                coords[f_idx, 0],
                coords[f_idx, 1],
                s=74,
                facecolors="none",
                edgecolors="#111111",
                linewidths=1.35,
                zorder=6,
            )

        # Todos los nodos coloreados por especie (TODA LA MALLA: 658 / 524 / 658 nodos)
        for sp_id in range(len(SPECIES_NAMES)):
            mask = (sol == sp_id)
            if np.any(mask):
                is_big_sp = sp_id in BIG_SPECIES_IDS
                ax.scatter(
                    coords[mask, 0],
                    coords[mask, 1],
                    s=40 if is_big_sp else 26,
                    color=SPECIES_COLORS[sp_id],
                    edgecolors="#1a1a1a",
                    linewidths=0.45,
                    zorder=5 if is_big_sp else 4,
                )

        # Rombo blanco central en especies grandes (subred big_index=3: Prosopis, O. streptacantha, Yucca)
        big_assigned = np.isin(sol, list(BIG_SPECIES_IDS))
        if np.any(big_assigned):
            ax.scatter(
                coords[big_assigned, 0],
                coords[big_assigned, 1],
                s=7.5,
                marker="D",
                color="white",
                zorder=7,
            )

        ax.set_xlim(-2.5, 102.5)
        ax.set_ylim(-2.5, 102.5)
        ax.set_aspect("equal")
        ax.set_xlabel("Este local X (m) — Bloque 100 m", fontsize=8.8, weight="bold")
        if idx == 0:
            ax.set_ylabel("Norte local Y (m) — Bloque 100 m", fontsize=8.8, weight="bold")
        ax.tick_params(labelsize=8)
        ax.set_title(panel_titles[k], fontsize=9.8, weight="bold", color=border_col[k], pad=9)

        # Tarjeta inferior con auditoría exacta y proporciones de esta hectárea
        ax_card = fig.add_subplot(gs[1, idx])
        ax_card.axis("off")
        m_tot = len(coords)
        n_viv = len(fixed_nodes)
        n_nue = m_tot - n_viv
        card_text = (
            f"• Superficie Dominio Dominica: {bp['area_dominica_ha']:.2f} ha ({bp['pct_dominica']:.1f}% del parque)\n"
            f"• Geometría Malla: |P| = {m_tot} nodos | Paso d = {graph.step_d:.2f} m | Aristas = {len(graph.edge_u):,d}\n"
            f"• Censo vs Compra: {n_viv} vivas fijas (anillo negro) + {n_nue} nuevas = {m_tot} pl/ha\n"
            f"• Costo Vivero / ha: ${bp['costo_ha_mxn']:,.0f} MXN/ha | Choques Intraespecíficos: {bp['intra_contacts']}\n"
            f"• Contactos Nodriza (Prosopis): {bp['nurse_contacts']} | Agave-Agave: {bp['agave_contacts']}\n"
            f"• Supervivencia Efectiva Espacial: {bp['surv_eff_pct']:.2f}% (Carga Φ = {bp['phi_norm']:.2f} vs 41.3 rígida)"
        )
        ax_card.text(
            0.02,
            0.95,
            card_text,
            va="top",
            ha="left",
            fontsize=8.3,
            linespacing=1.38,
            family="DejaVu Sans",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=panel_bg[k], edgecolor=border_col[k], linewidth=1.2),
        )

    # Leyenda maestra unificada en la parte inferior
    legend_handles = [
        Line2D([0], [0], marker="o", color="w", label=SPECIES_SHORT[i], markerfacecolor=SPECIES_COLORS[i], markeredgecolor="#1a1a1a", markersize=7.5)
        for i in range(len(SPECIES_NAMES))
    ]
    legend_handles.append(
        Line2D([0], [0], marker="o", color="w", label="Anillo Negro = Planta Viva Preexistente (Ei)", markerfacecolor="white", markeredgecolor="#111111", markeredgewidth=1.5, markersize=8.5)
    )
    legend_handles.append(
        Line2D([0], [0], marker="D", color="w", label="Rombo Blanco = Subred Grande big_index=3 (7.25 m)", markerfacecolor="#7f3b08", markeredgecolor="#111111", markersize=6.5)
    )

    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=6,
        fontsize=8.2,
        frameon=True,
        facecolor="#fafafa",
        edgecolor="#cccccc",
        bbox_to_anchor=(0.51, 0.006),
    )

    fig.suptitle(
        "MALLA COMPLETA DE LAS 3 HECTÁREAS MODULARES (100 m × 100 m) — CADA PUNTO ES UNA PLANTA REAL\n"
        "Comparativa Exacta Nodo a Nodo: H1 (658 pl/ha con Ei) vs H2 (524 pl/ha en Ladera >=20%) vs H3 (658 pl/ha en Polígono 29 con Ei=0)",
        fontsize=13.2,
        weight="bold",
        y=0.965,
    )

    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[OK] Malla completa 1 ha (H1, H2, H3) guardada en: {out_path}")


# ==============================================================================
# 4. RENDERIZADO DE FIGURA 2: POLÍGONOS COMPLETOS (100% DE PLANTAS MAPEADAS)
# ==============================================================================
def render_full_polygons_panel(
    poly_data: Dict[int, Dict[str, Any]],
    out_path: Path,
) -> None:
    fig, axs = plt.subplots(2, 2, figsize=(21, 17.5), dpi=300, facecolor="white")
    axs_flat = axs.flatten()

    pids = [12, 29, 19, 31]
    titles = {
        12: "POLÍGONO 12 — Malla Completa (967 plantas en 1.47 ha | 100% Tipología H1)",
        29: "POLÍGONO 29 — Malla Completa (4,287 plantas en 6.54 ha | H3 <20% + Mancha H2 >=20%)",
        19: "POLÍGONO 19 — Malla Completa (3,237 plantas en 4.92 ha | 100% Tipología H1)",
        31: "POLÍGONO 31 — Malla Completa (4,781 plantas en 7.34 ha | Costura H1 + 0.36 ha Ladera H2)",
    }

    ls = LightSource(azdeg=315, altdeg=45)

    for idx, pid in enumerate(pids):
        ax = axs_flat[idx]
        pdata = poly_data[pid]
        t: Terrain = pdata["terrain"]
        graph: HexGridGraph = pdata["graph"]
        sol: np.ndarray = pdata["sol"]
        fixed_nodes: Dict[int, int] = pdata["fixed_nodes"]
        zone_arr: np.ndarray = pdata["zone_arr"]
        row = pdata["row"]
        coords = graph.coords

        # 1. Relieve sombreado recortado al polígono
        rgb_shade = ls.shade(t.elev, cmap=plt.get_cmap("terrain"), vert_exag=1.5, blend_mode="soft")
        xs = (np.arange(t.nx) + 0.5) * t.cx
        ys = (np.arange(t.ny) + 0.5) * t.cy
        gx, gy = np.meshgrid(xs, ys)
        in_mask = t.inside(np.c_[gx.ravel(), gy.ravel()]).reshape(t.elev.shape)

        rgba = np.ones((*t.elev.shape, 4), dtype=np.float32)
        rgba[..., :3] = rgb_shade[..., :3]
        rgba[~in_mask, :3] = 0.96
        rgba[~in_mask, 3] = 1.0
        ax.imshow(rgba, origin="lower", extent=[0, t.width, 0, t.height], zorder=1)

        # 2. Retícula de referencia modular de 1 hectárea (100 m x 100 m)
        for x_grid in np.arange(0.0, t.width + 1.0, 100.0):
            ax.axvline(x_grid, color="#222222", linestyle=":", linewidth=0.65, alpha=0.30, zorder=2)
        for y_grid in np.arange(0.0, t.height + 1.0, 100.0):
            ax.axhline(y_grid, color="#222222", linestyle=":", linewidth=0.65, alpha=0.30, zorder=2)

        # 3. Curvas de nivel
        z_min, z_max = float(np.nanmin(t.elev)), float(np.nanmax(t.elev))
        step = 1.0 if (z_max - z_min <= 22.0) else 2.0
        cs = ax.contour(xs, ys, t.elev, levels=np.arange(math.floor(z_min), math.ceil(z_max) + step, step), colors="#333333", linewidths=0.45, alpha=0.48, zorder=2)
        ax.clabel(cs, inline=True, fontsize=6.2, fmt="%.0f m")

        # 4. Zonas de pendiente >= 20% (Tipología H2 a 524 pl/ha)
        steep_mask = (t.zone > 0) & in_mask
        if np.any(steep_mask):
            overlay = np.zeros((*t.elev.shape, 4), dtype=np.float32)
            overlay[steep_mask] = [0.85, 0.12, 0.12, 0.34]
            ax.imshow(overlay, origin="lower", extent=[0, t.width, 0, t.height], zorder=3)
            ax.contour(xs, ys, steep_mask.astype(float), levels=[0.5], colors=["#b71c1c"], linewidths=1.35, linestyles="--", zorder=4)

        # 5. Contorno oficial del polígono
        poly_patch = MplPolygon(t.polygon, closed=True, fill=False, edgecolor="#111111", linewidth=1.8, zorder=5)
        ax.add_patch(poly_patch)

        # 6. Aristas de la malla completa (sutiles para que se aprecie la red hexagonal completa)
        segs = np.stack([coords[graph.edge_u], coords[graph.edge_v]], axis=1)
        edge_lw = 0.38 if len(coords) < 1500 else 0.22
        edge_alpha = 0.35 if len(coords) < 1500 else 0.22
        ax.add_collection(LineCollection(segs, colors="#333333", linewidths=edge_lw, alpha=edge_alpha, zorder=5))

        # 7. TODAS las plantas del polígono (967 a 4,781 puntos)
        pt_size = 18.0 if len(coords) < 1500 else 6.8
        if len(fixed_nodes) > 0:
            f_idx = np.array(sorted(fixed_nodes.keys()), dtype=int)
            ax.scatter(
                coords[f_idx, 0],
                coords[f_idx, 1],
                s=pt_size * 1.9,
                facecolors="none",
                edgecolors="#000000",
                linewidths=0.75 if len(coords) < 1500 else 0.55,
                zorder=7,
            )

        for sp_id in range(len(SPECIES_NAMES)):
            mask = (sol == sp_id)
            if np.any(mask):
                ax.scatter(
                    coords[mask, 0],
                    coords[mask, 1],
                    s=pt_size * (1.22 if sp_id in BIG_SPECIES_IDS else 1.0),
                    color=SPECIES_COLORS[sp_id],
                    edgecolors="#111111",
                    linewidths=0.30 if len(coords) < 1500 else 0.18,
                    zorder=6,
                )

        # 8. Acercamiento (Zoom Inset) en P29 y P31 para ver con lupa la transición H1/H3 <-> H2 (>=20%)
        if pid in (29, 31) and np.any(zone_arr == 1):
            steep_pts = coords[zone_arr == 1]
            zc = steep_pts.mean(axis=0)
            half_w = 34.0
            x1, x2 = max(0.0, zc[0] - half_w), min(t.width, zc[0] + half_w)
            y1, y2 = max(0.0, zc[1] - half_w), min(t.height, zc[1] + half_w)

            # Colocar recuadro de zoom en esquina libre de cada polígono
            inset_loc = "lower left" if pid == 29 else "lower right"
            ax_ins = inset_axes(ax, width="35%", height="35%", loc=inset_loc, borderpad=1.1)
            ax_ins.imshow(rgba, origin="lower", extent=[0, t.width, 0, t.height], zorder=1)
            if np.any(steep_mask):
                ax_ins.imshow(overlay, origin="lower", extent=[0, t.width, 0, t.height], zorder=2)
                ax_ins.contour(xs, ys, steep_mask.astype(float), levels=[0.5], colors=["#b71c1c"], linewidths=1.2, linestyles="--", zorder=3)
            ax_ins.add_patch(MplPolygon(t.polygon, closed=True, fill=False, edgecolor="#111111", linewidth=1.3, zorder=4))

            in_box_e = (
                (coords[graph.edge_u, 0] >= x1 - 5) & (coords[graph.edge_u, 0] <= x2 + 5) &
                (coords[graph.edge_u, 1] >= y1 - 5) & (coords[graph.edge_u, 1] <= y2 + 5)
            )
            ax_ins.add_collection(LineCollection(segs[in_box_e], colors="#333333", linewidths=0.55, alpha=0.5, zorder=4))

            in_box_n = (coords[:, 0] >= x1 - 2) & (coords[:, 0] <= x2 + 2) & (coords[:, 1] >= y1 - 2) & (coords[:, 1] <= y2 + 2)
            for sp_id in range(len(SPECIES_NAMES)):
                m_ins = in_box_n & (sol == sp_id)
                if np.any(m_ins):
                    ax_ins.scatter(coords[m_ins, 0], coords[m_ins, 1], s=28, color=SPECIES_COLORS[sp_id], edgecolors="#111111", linewidths=0.45, zorder=6)
            if len(fixed_nodes) > 0:
                f_ins = np.array([p for p in fixed_nodes if in_box_n[p]], dtype=int)
                if len(f_ins) > 0:
                    ax_ins.scatter(coords[f_ins, 0], coords[f_ins, 1], s=52, facecolors="none", edgecolors="#000000", linewidths=1.1, zorder=7)

            ax_ins.set_xlim(x1, x2)
            ax_ins.set_ylim(y1, y2)
            ax_ins.set_aspect("equal")
            ax_ins.set_xticks([])
            ax_ins.set_yticks([])
            for spine in ax_ins.spines.values():
                spine.set_edgecolor("#b71c1c")
                spine.set_linewidth(1.5)
            ax_ins.set_title(
                f"Zoom Costura {'H3' if pid == 29 else 'H1'}(4.19m) ↔ H2(4.69m)",
                fontsize=7.2,
                weight="bold",
                color="#b71c1c",
                bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#b71c1c", alpha=0.92),
            )
            ax.add_patch(Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, edgecolor="#b71c1c", linewidth=1.4, zorder=8))

        n_h2 = int(np.sum(zone_arr == 1))
        n_h13 = int(np.sum(zone_arr == 0))
        sub = (
            f"Área: {row['area_ha']:.2f} ha (<20%: {row['area_plana_ha']:.2f} ha [{n_h13:,d} pl] | >=20%: {row['area_pend_ge20_ha']:.2f} ha [{n_h2:,d} pl])  •  "
            f"Vivas Ei: {int(row['plantas_vivas_Ei']):,d} | Nuevas: {int(row['plantas_nuevas_total']):,d} | Total Nz: {len(coords):,d}\n"
            f"Costo Vivero: ${row['costo_vivero_total_mxn']:,.0f} MXN (${row['costo_vivero_por_ha_mxn']:,.0f}/ha)  •  "
            f"Supervivencia Efectiva: {row['sobrev_efectiva_espacial_pct']:.2f}%  •  Choques Intra: {pdata['intra_contacts']}  •  Retícula punteada = 100×100 m (1 ha)"
        )
        ax.set_title(f"{titles[pid]}\n{sub}", fontsize=8.4, weight="bold", pad=8)
        ax.set_xlabel("Este local X (m)", fontsize=8.3)
        ax.set_ylabel("Norte local Y (m)", fontsize=8.3)
        ax.tick_params(labelsize=7.8)
        ax.set_aspect("equal")

    legend_handles = [
        Line2D([0], [0], marker="o", color="w", label=SPECIES_SHORT[i], markerfacecolor=SPECIES_COLORS[i], markeredgecolor="#111111", markersize=7.5)
        for i in range(len(SPECIES_NAMES))
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
        bbox_to_anchor=(0.5, 0.008),
    )

    fig.suptitle(
        "MAPEO DE MALLA COMPLETA (100% DE LAS PLANTAS) SOBRE POLÍGONOS REALES UTM 14N\n"
        "Integración Total de Bloques de 1 Hectárea (Retícula 100×100 m), Plantas Vivas Censadas (Ei) y Zonas de Ladera >=20% (H2)",
        fontsize=13.5,
        weight="bold",
        y=0.982,
    )

    plt.tight_layout(rect=[0, 0.052, 1, 0.952])
    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[OK] Panel de polígonos con malla 100% completa guardado en: {out_path}")


# ==============================================================================
# 5. PIPELINE PRINCIPAL Y EXPORTACIÓN JSON PARA VISOR INTERACTIVO HTML5
# ==============================================================================
def main() -> None:
    t0 = time.time()
    print("=" * 85)
    print("GENERANDO MALLAS COMPLETAS (1 HA H1/H2/H3 + POLÍGONOS 100% COMPLETOS)")
    print("=" * 85)

    df_cat, df_wide, _ = load_semiraw_datasets(poligonos_dir=POLI31_DIR)
    df_sp, _, Phi = build_ecological_matrices(df_cat, lam=1.0, slope_pct=6.0, density_per_ha=658.0)
    _, _, Phi_steep = build_ecological_matrices(df_cat, lam=1.0, slope_pct=24.0, density_per_ha=524.0)

    df_res = pd.read_csv(OUT_DIR / "resumen_31_poligonos_completo.csv")
    proportions = df_sp["proporcion_programa"].to_numpy(dtype=np.float64)
    costs_vivero = df_sp["costo_vivero_mxn"].to_numpy(dtype=np.float64)

    # Promedio real de plantas vivas por ha en los 30 polígonos con registro (~129 pl/ha)
    df_valid30 = df_res[df_res["poligono_id"] != 29]
    tot_ha_30 = float(df_valid30["area_ha"].sum())
    avg_vivas_sp_per_ha = np.array([df_valid30[f"{sp}_vivas"].sum() / tot_ha_30 for sp in SPECIES_NAMES])

    # ------------------------------------------------------------------
    # PARTE A: LAS 3 HECTÁREAS MODULARES COMPLETAS (100 m x 100 m)
    # ------------------------------------------------------------------
    blueprints: Dict[str, Dict[str, Any]] = {}
    specs_1ha = [
        ("H1", 658, 0.0, True, Phi, 181.62, 95.82),
        ("H2", 524, 12.0, True, Phi_steep, 1.52, 0.80),
        ("H3", 658, 0.0, False, Phi, 6.42, 3.38),
    ]

    for key, n_nodes, ang, has_ei, phi_mat, area_dom, pct_dom in specs_1ha:
        t_b0 = time.time()
        g_1ha = build_exact_1ha_hex_grid(target_nodes=n_nodes, angle_deg=ang)
        q_base = compute_exact_quotas(proportions, n_nodes)

        if has_ei:
            scale_ei = n_nodes / 658.0
            raw_ei = avg_vivas_sp_per_ha * scale_ei
            E_i_1ha = np.round(raw_ei).astype(int)
            E_i_1ha = np.minimum(E_i_1ha, q_base)
            fixed_1ha = place_exact_preexisting_nodes(g_1ha, E_i_1ha, seed=101 if key == "H1" else 202)
        else:
            E_i_1ha = np.zeros(len(SPECIES_NAMES), dtype=int)
            fixed_1ha = {}

        warm_1ha, _ = gpu_full_mesh_optimizer(
            g_1ha, phi_mat, q_base, fixed_1ha, n_replicas=128, n_steps=650, seed=42
        )
        opt_1ha = red_black_halo_milp_refinement_1ha(g_1ha, phi_mat, warm_1ha, fixed_1ha, df_sp)
        opt_1ha, _ = greedy_local_polish(g_1ha, phi_mat, opt_1ha, fixed_1ha, max_passes=10)

        metrics_1ha = audit_ecological_metrics(opt_1ha, g_1ha, phi_mat, df_sp, fixed_1ha)
        new_counts = np.bincount(opt_1ha, minlength=len(SPECIES_NAMES)) - E_i_1ha
        costo_ha = float(np.sum(np.maximum(0, new_counts) * costs_vivero))
        # Carga Phi escalada a equivalente tesela de 66 nodos para comparación directa con reportes
        phi_equiv_66 = float(metrics_1ha["comp_total"]) * (66.0 / n_nodes)

        blueprints[key] = {
            "graph": g_1ha,
            "sol": opt_1ha,
            "fixed_nodes": fixed_1ha,
            "E_i": E_i_1ha,
            "quotas": q_base,
            "costo_ha_mxn": costo_ha,
            "intra_contacts": int(metrics_1ha["intra_contacts"]),
            "agave_contacts": int(round(metrics_1ha["agave_contacts"] * 66.0 / n_nodes)),
            "nurse_contacts": int(round(metrics_1ha["nurse_contacts"] * 66.0 / n_nodes)),
            "nurse_contacts_raw": int(metrics_1ha["nurse_contacts"]),
            "agave_contacts_raw": int(metrics_1ha["agave_contacts"]),
            "surv_eff_pct": float(metrics_1ha["surv_eff_pct"]),
            "phi_norm": phi_equiv_66,
            "area_dominica_ha": area_dom,
            "pct_dominica": pct_dom,
        }
        print(
            f"[{key}] |P|={n_nodes} (d={g_1ha.step_d:.2f}m) | Vivas={len(fixed_1ha)} | Nuevas={n_nodes - len(fixed_1ha)} | "
            f"Intra={metrics_1ha['intra_contacts']} | Nodrizas={metrics_1ha['nurse_contacts']} | "
            f"SurvEff={metrics_1ha['surv_eff_pct']:.2f}% | Costo=${costo_ha:,.0f}/ha ({time.time() - t_b0:.2f}s)"
        )

    out_1ha_png = OUT_DIR / "malla_completa_1ha_H1_H2_H3.png"
    render_1ha_blueprints(blueprints, out_1ha_png)

    # ------------------------------------------------------------------
    # PARTE B: POLÍGONOS COMPLETOS (P12, P29, P19, P31) — 100% DE PLANTAS
    # ------------------------------------------------------------------
    poly_csv = POLI31_DIR / "poligonos_31.csv"
    utm_csv = POLI31_DIR / "poligonos_utm.csv"
    dem_csv = POLI31_DIR / "dem_srtm_puntos.csv"

    poly_data: Dict[int, Dict[str, Any]] = {}
    for pid in [12, 29, 19, 31]:
        t_p0 = time.time()
        row = df_res[df_res["poligono_id"] == pid].iloc[0]
        t = Terrain.from_poligonos(str(poly_csv), pid=pid, utm=str(utm_csv), dem_pts=str(dem_csv), slope_deg=6.0, seed=1)
        t.zonas(pend_pct=20.0, min_ha=0.10)

        area_oficial = float(row["area_ha"])
        frac_plana = float(t.zone_frac[0])
        frac_pend = float(t.zone_frac[1])
        n_plana = int(math.floor(658.0 * area_oficial * frac_plana + 1e-9))
        n_pend = int(math.ceil(524.0 * area_oficial * frac_pend - 1e-9)) if frac_pend > 0 else 0

        g_poly, zone_arr = build_full_polygon_graph(t, n_plana=n_plana, n_pend=n_pend)

        E_i_poly = np.array([int(row[f"{sp}_vivas"]) for sp in SPECIES_NAMES], dtype=int)
        Nz_sp_poly = np.array([int(row[f"{sp}_meta_Nz"]) for sp in SPECIES_NAMES], dtype=int)

        fixed_poly = place_exact_preexisting_nodes(g_poly, E_i_poly, seed=pid + 500)
        sol_poly, _ = gpu_full_mesh_optimizer(
            g_poly, Phi, Nz_sp_poly, fixed_poly, n_replicas=96, n_steps=700, seed=pid + 900
        )
        metrics_poly = audit_ecological_metrics(sol_poly, g_poly, Phi, df_sp, fixed_poly)

        poly_data[pid] = {
            "terrain": t,
            "graph": g_poly,
            "sol": sol_poly,
            "fixed_nodes": fixed_poly,
            "zone_arr": zone_arr,
            "row": row,
            "intra_contacts": int(metrics_poly["intra_contacts"]),
            "nurse_contacts": int(metrics_poly["nurse_contacts"]),
        }
        print(
            f"[Polígono {pid:02d}] |P|={len(g_poly.coords):,d} (Plana={int(np.sum(zone_arr==0)):,d}, >=20%={int(np.sum(zone_arr==1)):,d}) | "
            f"Vivas={len(fixed_poly):,d} | Nuevas={len(g_poly.coords)-len(fixed_poly):,d} | "
            f"Intra={metrics_poly['intra_contacts']} | Nodrizas={metrics_poly['nurse_contacts']:,d} ({time.time() - t_p0:.2f}s)"
        )

    out_poly_png = OUT_DIR / "malla_completa_poligonos_totales.png"
    render_full_polygons_panel(poly_data, out_poly_png)

    # ------------------------------------------------------------------
    # PARTE C: EXPORTAR JSON COMPLETO PARA VISOR INTERACTIVO HTML5
    # ------------------------------------------------------------------
    viewer_payload: Dict[str, Any] = {
        "species_names": SPECIES_NAMES,
        "species_short": SPECIES_SHORT,
        "species_colors": SPECIES_COLORS,
        "big_species_ids": list(BIG_SPECIES_IDS),
        "views": {},
    }

    for key in ["H1", "H2", "H3"]:
        bp = blueprints[key]
        g: HexGridGraph = bp["graph"]
        sol: np.ndarray = bp["sol"]
        fixed_set = set(bp["fixed_nodes"].keys())
        viewer_payload["views"][f"1ha_{key}"] = {
            "title": f"Bloque Modular 1 ha — Tipología {key}",
            "subtitle": (
                f"100 m × 100 m (1.00 ha) | {len(g.coords)} plantas totales (d = {g.step_d:.2f} m) | "
                f"{len(fixed_set)} vivas preexistentes + {len(g.coords) - len(fixed_set)} nuevas | "
                f"Supervivencia efectiva: {bp['surv_eff_pct']:.2f}% | Costo: ${bp['costo_ha_mxn']:,.0f} MXN/ha"
            ),
            "width": 100.0,
            "height": 100.0,
            "step_d": round(float(g.step_d), 3),
            "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
            "steep_cells": [],
            "nodes": [
                [
                    round(float(g.coords[p, 0]), 2),
                    round(float(g.coords[p, 1]), 2),
                    int(sol[p]),
                    1 if p in fixed_set else 0,
                    1 if g.big_mask[p] else 0,
                    1 if key == "H2" else 0,
                ]
                for p in range(len(g.coords))
            ],
            "edges": [[int(g.edge_u[e]), int(g.edge_v[e])] for e in range(len(g.edge_u))],
        }

    for pid in [12, 29, 19, 31]:
        pdata = poly_data[pid]
        t = pdata["terrain"]
        g = pdata["graph"]
        sol = pdata["sol"]
        z_arr = pdata["zone_arr"]
        row = pdata["row"]
        fixed_set = set(pdata["fixed_nodes"].keys())

        # Exportar celdas con pendiente >=20% para pintar la mancha roja en el canvas interactivo
        xs = (np.arange(t.nx) + 0.5) * t.cx
        ys = (np.arange(t.ny) + 0.5) * t.cy
        gx, gy = np.meshgrid(xs, ys)
        in_mask = t.inside(np.c_[gx.ravel(), gy.ravel()]).reshape(t.elev.shape)
        steep_iy, steep_ix = np.where((t.zone > 0) & in_mask)
        steep_rects = [
            [round(float(ix * t.cx), 1), round(float(iy * t.cy), 1), round(float(t.cx), 2), round(float(t.cy), 2)]
            for iy, ix in zip(steep_iy, steep_ix)
        ]

        viewer_payload["views"][f"P{pid}"] = {
            "title": f"Polígono Oficial {pid} ({row['area_ha']:.2f} ha) — Malla 100% Completa",
            "subtitle": (
                f"Total: {len(g.coords):,d} plantas (<20%: {int(np.sum(z_arr==0)):,d} pl | >=20%: {int(np.sum(z_arr==1)):,d} pl) | "
                f"Vivas Ei: {len(fixed_set):,d} | Nuevas: {len(g.coords)-len(fixed_set):,d} | "
                f"Vivero: ${row['costo_vivero_total_mxn']:,.0f} MXN | Supervivencia: {row['sobrev_efectiva_espacial_pct']:.2f}%"
            ),
            "width": round(float(t.width), 2),
            "height": round(float(t.height), 2),
            "step_d": round(float(g.step_d), 3),
            "polygon": [[round(float(pt[0]), 2), round(float(pt[1]), 2)] for pt in t.polygon],
            "steep_cells": steep_rects,
            "nodes": [
                [
                    round(float(g.coords[p, 0]), 2),
                    round(float(g.coords[p, 1]), 2),
                    int(sol[p]),
                    1 if p in fixed_set else 0,
                    1 if g.big_mask[p] else 0,
                    int(z_arr[p]),
                ]
                for p in range(len(g.coords))
            ],
            "edges": [[int(g.edge_u[e]), int(g.edge_v[e])] for e in range(len(g.edge_u))],
        }

    json_path = OUT_DIR / "datos_mallas_completas_visor.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(viewer_payload, f, ensure_ascii=False, separators=(",", ":"))

    print(f"[OK] Datos JSON exportados para visor interactivo: {json_path}")
    print(f"PROCESO TOTAL COMPLETADO EN {time.time() - t0:.2f}s.")


if __name__ == "__main__":
    main()
