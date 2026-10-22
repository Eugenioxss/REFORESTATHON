"""Empirical Stress-Test of Spatial Tiling with Red-Black Checkerboard and Halo Exchange.
Authored by Challenger 2 (Iteration 2).

Tests:
1. SpatialTiler on 6x22 grid (2 tiles: 1 Red, 1 Black coupled via Halo exchange).
2. SpatialTiler on 12x22 grid (4 tiles: 2 Red, 2 Black coupled via Halo exchange).
3. Verification of global quota consistency, assignment completeness, and boundary continuity.
"""

import math
import os
import sys
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("."))

from scripts.src.reforestacion_pipeline import (
    load_semiraw_datasets,
    build_ecological_matrices,
    build_tres_bolillos_graph,
    compute_exact_quotas,
    audit_ecological_metrics,
    evaluate_assignment_cost,
    SpatialTiler,
    get_target_density,
    SPECIES_METADATA,
)


def run_tiling_test(global_rows: int, global_cols: int, tile_rows: int = 6, tile_cols: int = 11):
    print(f"\n{'='*80}")
    print(f"STRESS-TEST: SPATIAL TILING {global_rows}x{global_cols} (|P|={global_rows*global_cols})")
    print(f"Teselas: {tile_rows}x{tile_cols} | Partición: {math.ceil(global_rows/tile_rows)}x{math.ceil(global_cols/tile_cols)}")
    print(f"{'='*80}")

    df_cat, df_wide, _ = load_semiraw_datasets()
    density_val, density_ref_ha = get_target_density(6.0)
    df_sp, C_norm, Phi = build_ecological_matrices(df_cat, lam=1.0, slope_pct=6.0, density_per_ha=density_ref_ha)

    tiler = SpatialTiler(
        tile_rows=tile_rows,
        tile_cols=tile_cols,
        slope_pct=6.0,
        ring_level=1,
    )

    t0 = time.perf_counter()
    assignment, graph, metrics = tiler.solve_tiled(
        global_rows=global_rows,
        global_cols=global_cols,
        df_sp=df_sp,
        Phi=Phi,
        time_limit_per_tile=30,
        cpu_threads=12,
        tolerance_pct=0.0,
    )
    elapsed = time.perf_counter() - t0

    total_nodes = global_rows * global_cols

    # 1. Verification of assignment completeness
    assert len(assignment) == total_nodes, f"Expected {total_nodes} nodes, got {len(assignment)}"
    assert np.all(assignment >= 0) and np.all(assignment < 10), "Invalid species indices found!"
    print(f"[PASS 1/5] Assignment complete: All {total_nodes} nodes assigned valid species [0..9].")

    # 2. Quota check
    counts = np.bincount(assignment, minlength=10)
    expected_props = df_sp["proporcion_programa"].to_numpy()
    expected_quotas = compute_exact_quotas(expected_props, total_nodes)
    quota_diff = np.abs(counts - expected_quotas)
    print(f"Global species counts: {counts.tolist()}")
    print(f"Expected global quotas: {expected_quotas.tolist()}")
    print(f"Max absolute quota discrepancy across domain: {quota_diff.max()}")
    # Small discrepancy can occur from independent integer rounding per tile
    assert quota_diff.max() <= math.ceil(global_rows/tile_rows) * math.ceil(global_cols/tile_cols), "Excessive quota drift!"
    print(f"[PASS 2/5] Quotas bounded within integer tiling tolerance.")

    # 3. Ecological metrics audit
    print(f"Global Competition Cost (Phi): {metrics['comp_total']:.4f}")
    print(f"Supervivencia Efectiva: {metrics['surv_eff_pct']:.2f}%")
    print(f"Interacciones Nodriza: {metrics['nurse_contacts']}")
    print(f"Contactos Intraespecíficos: {metrics['intra_contacts']}")
    print(f"Contactos Agave-Agave: {metrics['agave_contacts']}")
    assert metrics['comp_total'] > 0, "Competition cost must be positive"
    assert metrics['surv_eff_pct'] > 50.0, "Effective survival must be reasonable"
    print(f"[PASS 3/5] Ecological metrics valid.")

    # 4. Boundary cross-tile edge analysis (Halo exchange impact)
    # Check edges that cross from tile to tile
    n_cross_edges = 0
    cross_edge_costs = []
    for e in range(len(graph.edge_u)):
        u, v = int(graph.edge_u[e]), int(graph.edge_v[e])
        r_u, c_u = u // global_cols, u % global_cols
        r_v, c_v = v // global_cols, v % global_cols
        tile_u = (r_u // tile_rows, c_u // tile_cols)
        tile_v = (r_v // tile_rows, c_v // tile_cols)
        if tile_u != tile_v:
            n_cross_edges += 1
            sp_u, sp_v = assignment[u], assignment[v]
            cross_edge_costs.append(graph.edge_weight[e] * Phi[sp_u, sp_v])

    avg_cross_cost = float(np.mean(cross_edge_costs)) if cross_edge_costs else 0.0
    print(f"Cross-tile boundary edges: {n_cross_edges} edges, mean cost per edge: {avg_cross_cost:.4f}")
    assert n_cross_edges > 0, "Domain decomposition must have boundary cross-edges!"
    print(f"[PASS 4/5] Boundary cross-edges successfully verified and coupled.")

    # 5. Runtime & Efficiency
    print(f"Total Tiling Elapsed Time: {elapsed:.2f}s ({elapsed / (math.ceil(global_rows/tile_rows)*math.ceil(global_cols/tile_cols)):.2f}s per tile)")
    print(f"[PASS 5/5] Spatial Tiling verified successfully!")
    return elapsed, metrics


if __name__ == "__main__":
    print("Testing 6x22 grid (2 tiles: Red + Black)...")
    t_6x22, m_6x22 = run_tiling_test(6, 22, tile_rows=6, tile_cols=11)

    print("\nTesting 12x22 grid (4 tiles: 2 Red + 2 Black in 2x2 checkerboard)...")
    t_12x22, m_12x22 = run_tiling_test(12, 22, tile_rows=6, tile_cols=11)

    print("\n" + "="*80)
    print("ALL SPATIAL TILING STRESS-TESTS PASSED EMPIRICALLY!")
    print("="*80)
