"""Empirical Adversarial Stress Test Harness for REFORESTATHON MIP Solver & Scalability.
Authored by Challenger 2 (Solver & Scalability Adversarial Challenger).
"""
import sys
import os
import time
import math
import traceback
import numpy as np
import pandas as pd

# Add repo root to path
sys.path.insert(0, os.path.abspath('.'))

from scripts.src.reforestacion_pipeline import (
    load_semiraw_datasets,
    build_ecological_matrices,
    build_tres_bolillos_graph,
    compute_exact_quotas,
    gpu_parallel_annealing_warmstart,
    solve_reforestation_mip,
    SpatialTiler,
    audit_ecological_metrics,
    evaluate_assignment_cost,
    SPECIES_METADATA,
    MODEL_PARAMS,
    get_target_density
)

def run_solver_benchmarks():
    print("=" * 80)
    print("CHALLENGER 2: EMPIRICAL SOLVER STRESS HARNESS")
    print("=" * 80)

    # 1. Dataset loading check
    df_cat, df_wide, baseline_row_22 = load_semiraw_datasets()
    print(f"[OK] Datasets loaded. Cat: {len(df_cat)} sp, Wide: {len(df_wide)} polys.")

    # Check alpha_target in df_cat
    if "alpha_target" not in df_cat.columns:
        print("[DEFECT DETECTED] 'alpha_target' is missing in df_cat from load_semiraw_datasets().")
        # In our harness we patch df_cat for testing solver downstream
        df_cat["alpha_target"] = [SPECIES_METADATA[i]["alpha_target"] for i in range(len(df_cat))]
    else:
        print("[OK] 'alpha_target' present in df_cat.")

    density_val, density_ref_ha = get_target_density(6.0)
    df_sp, C_norm, Phi = build_ecological_matrices(df_cat, lam=1.0, slope_pct=6.0, density_per_ha=density_ref_ha)
    print(f"[OK] Ecological matrices built. Phi shape: {Phi.shape}, min: {Phi.min():.4f}, max: {Phi.max():.4f}")

    # =========================================================================
    # TEST 1: Default 6x11 grid with Auto / Gurobi
    # =========================================================================
    print("\n--- TEST 1: Default 6x11 Grid (66 nodes) with solver='auto' ---")
    rows, cols = 6, 11
    m_nodes = rows * cols
    graph_6x11 = build_tres_bolillos_graph(rows, cols, density_per_ha=density_ref_ha, ring_level=1)
    proportions = df_sp["proporcion_programa"].to_numpy(dtype=np.float64)
    quotas_6x11 = compute_exact_quotas(proportions, m_nodes)
    print(f"Quotas sum: {quotas_6x11.sum()}/{m_nodes}. Quotas: {quotas_6x11}")

    warm_6x11, warm_cost = gpu_parallel_annealing_warmstart(
        graph_6x11, Phi, quotas_6x11, n_replicas=512, n_steps=3000
    )
    print(f"Warm-start GPU cost: {warm_cost:.4f}")

    t0 = time.perf_counter()
    sol_auto, cost_auto, bound_auto, gap_auto, tag_auto = solve_reforestation_mip(
        graph=graph_6x11,
        Phi=Phi,
        quotas=quotas_6x11,
        warm_assignment=warm_6x11,
        tolerance_pct=0.0,
        df_sp=df_sp,
        time_limit=30,
        cpu_threads=8,
        solver_name="auto",
        mu_cost=0.0005,
    )
    t_auto = time.perf_counter() - t0
    print(f"Result solver='auto' ({tag_auto}):")
    print(f"  Time: {t_auto:.2f}s | ObjVal: {cost_auto:.4f} | BestBound: {bound_auto:.4f} | MIPGap: {gap_auto:.2f}%")

    # Sanity checks
    assert len(sol_auto) == m_nodes, f"Expected {m_nodes} assigned nodes, got {len(sol_auto)}"
    actual_counts_auto = np.bincount(sol_auto, minlength=10)
    print(f"  Assigned distribution: {actual_counts_auto.tolist()}")
    assert np.array_equal(actual_counts_auto, quotas_6x11), f"Quota mismatch: {actual_counts_auto} vs {quotas_6x11}"
    print("  [PASS] Quota constraints satisfied exactly.")

    # =========================================================================
    # TEST 2: Default 6x11 grid with solver='highs' explicitly
    # =========================================================================
    print("\n--- TEST 2: Default 6x11 Grid (66 nodes) with solver='highs' explicitly ---")
    t0 = time.perf_counter()
    sol_highs, cost_highs, bound_highs, gap_highs, tag_highs = solve_reforestation_mip(
        graph=graph_6x11,
        Phi=Phi,
        quotas=quotas_6x11,
        warm_assignment=warm_6x11,
        tolerance_pct=0.0,
        df_sp=df_sp,
        time_limit=30,
        cpu_threads=8,
        solver_name="highs",
        mu_cost=0.0005,
    )
    t_highs = time.perf_counter() - t0
    print(f"Result solver='highs' ({tag_highs}):")
    print(f"  Time: {t_highs:.2f}s | ObjVal: {cost_highs:.4f} | BestBound: {bound_highs:.4f} | MIPGap: {gap_highs:.2f}%")

    assert len(sol_highs) == m_nodes
    actual_counts_highs = np.bincount(sol_highs, minlength=10)
    print(f"  Assigned distribution: {actual_counts_highs.tolist()}")
    assert np.array_equal(actual_counts_highs, quotas_6x11), f"HiGHS quota mismatch: {actual_counts_highs} vs {quotas_6x11}"
    print("  [PASS] HiGHS solve succeeds and satisfies quotas.")

    # Check whether HiGHS returns authentic bounds and gap
    print(f"  HiGHS BestBound: {bound_highs}")
    print(f"  HiGHS MIPGap: {gap_highs}%")
    if gap_highs == 0.0:
        print("  [NOTE] HiGHS MIPGap reported 0.0% — check if proven optimal or hardcoded.")
    else:
        print(f"  [OK] Non-trivial dynamic MIPGap: {gap_highs:.2f}%")

    # =========================================================================
    # TEST 3: HiGHS with Slack / Tolerance (0.05 and 0.10)
    # =========================================================================
    print("\n--- TEST 3: HiGHS Solver with Tolerance/Slack (5% and 10%) ---")
    for tol in [0.05, 0.10]:
        t0 = time.perf_counter()
        sol_tol, cost_tol, bound_tol, gap_tol, tag_tol = solve_reforestation_mip(
            graph=graph_6x11,
            Phi=Phi,
            quotas=quotas_6x11,
            warm_assignment=warm_6x11,
            tolerance_pct=tol,
            df_sp=df_sp,
            time_limit=30,
            cpu_threads=8,
            solver_name="highs",
            mu_cost=0.0005,
        )
        t_tol = time.perf_counter() - t0
        print(f"HiGHS Tol {int(tol*100)}%: Time={t_tol:.2f}s | ObjVal={cost_tol:.4f} | Bound={bound_tol:.4f} | Gap={gap_tol:.2f}% | Tag={tag_tol}")

    # =========================================================================
    # TEST 4: Spatial Tiling Scalability (12x22 grid = 264 nodes, 4 tiles)
    # =========================================================================
    print("\n--- TEST 4: Spatial Tiling Domain Decomposition (12x22 = 264 nodes) ---")
    tiler = SpatialTiler(tile_rows=6, tile_cols=11, slope_pct=6.0, ring_level=1)
    t0 = time.perf_counter()
    tiled_assign, tiled_graph, tiled_metrics = tiler.solve_tiled(
        global_rows=12,
        global_cols=22,
        df_sp=df_sp,
        Phi=Phi,
        time_limit_per_tile=15,
        cpu_threads=8,
    )
    t_tile = time.perf_counter() - t0
    print(f"Tiling 12x22 completed in {t_tile:.2f}s:")
    print(f"  Total assigned: {len(tiled_assign)} / 264")
    print(f"  Surv Eff: {tiled_metrics['surv_eff_pct']:.2f}% | Nurse Contacts: {tiled_metrics['nurse_contacts']}")
    print(f"  Counts per species: {tiled_metrics['counts'].tolist()}")
    assert len(tiled_assign) == 12 * 22, f"Expected 264 nodes, got {len(tiled_assign)}"
    assert not (tiled_assign == 0).all(), "Tiling produced all zeros!"
    # Check that all species are represented
    assert len(np.unique(tiled_assign)) == 10, f"Expected 10 unique species, found {len(np.unique(tiled_assign))}"
    print("  [PASS] Spatial tiling 12x22 completed successfully.")

    # =========================================================================
    # TEST 5: Spatial Tiler Stress Test with Non-Multiple Dimensions (e.g. 10x15)
    # =========================================================================
    print("\n--- TEST 5: Spatial Tiler Non-Multiple Boundary Dimensions (10x15 = 150 nodes) ---")
    try:
        t0 = time.perf_counter()
        tiled_assign_nm, tiled_graph_nm, tiled_metrics_nm = tiler.solve_tiled(
            global_rows=10,
            global_cols=15,
            df_sp=df_sp,
            Phi=Phi,
            time_limit_per_tile=10,
            cpu_threads=8,
        )
        t_nm = time.perf_counter() - t0
        print(f"Tiling 10x15 completed in {t_nm:.2f}s:")
        print(f"  Total assigned: {len(tiled_assign_nm)} / 150")
        print(f"  Counts per species: {tiled_metrics_nm['counts'].tolist()}")
        print("  [PASS] Non-multiple grid dimensions handled cleanly.")
    except Exception as e:
        print(f"  [DEFECT/EXCEPTION in non-multiple tiling]: {e}")
        traceback.print_exc()

    # =========================================================================
    # TEST 6: HiGHS Dual Bound & Objective Formulation Audit
    # =========================================================================
    print("\n--- TEST 6: Objective & MIPGap Formula Analysis ---")
    # Let's inspect scipy.optimize.milp behavior on graph_6x11
    # Check if res_highs.mip_dual_bound corresponds to c^T x
    # Compare with spatial_cost vs linear_obj + edge_obj
    k_i = df_sp["costo_vivero_mxn"].to_numpy(dtype=np.float64)
    mu_cost = 0.0005
    n_sp = 10
    total_budget_cost = sum(k_i[sol_highs[p]] for p in range(m_nodes))
    mu_budget = mu_cost * total_budget_cost
    print(f"HiGHS sol financial cost: {total_budget_cost:.2f} MXN | mu*cost: {mu_budget:.4f}")
    print(f"Spatial cost alone: {evaluate_assignment_cost(sol_highs, graph_6x11, Phi):.4f}")
    print(f"HiGHS reported BestBound: {bound_highs:.4f}")
    print(f"Gap = 100 * max(0, cost - bound) / cost = 100 * ({cost_highs:.4f} - {bound_highs:.4f}) / {cost_highs:.4f} = {gap_highs:.2f}%")

if __name__ == "__main__":
    run_solver_benchmarks()
