"""Verification of Gap Calculation and Objective Consistency in Gurobi and HiGHS.
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath('.'))

from scripts.src.reforestacion_pipeline import (
    load_semiraw_datasets,
    build_ecological_matrices,
    build_tres_bolillos_graph,
    compute_exact_quotas,
    gpu_parallel_annealing_warmstart,
    evaluate_assignment_cost,
    SPECIES_METADATA,
    get_target_density
)
import gurobipy as gp
from gurobipy import GRB
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import dok_matrix

df_cat, df_wide, _ = load_semiraw_datasets()
df_cat["alpha_target"] = [SPECIES_METADATA[i]["alpha_target"] for i in range(len(df_cat))]
density_val, density_ref_ha = get_target_density(6.0)
df_sp, C_norm, Phi = build_ecological_matrices(df_cat, lam=1.0, slope_pct=6.0, density_per_ha=density_ref_ha)

rows, cols = 6, 11
m = rows * cols
graph = build_tres_bolillos_graph(rows, cols, density_per_ha=density_ref_ha, ring_level=1)
proportions = df_sp["proporcion_programa"].to_numpy(dtype=np.float64)
quotas = compute_exact_quotas(proportions, m)
k_i = df_sp["costo_vivero_mxn"].to_numpy(dtype=np.float64)
mu_cost = 0.0005

warm_sol, warm_cost = gpu_parallel_annealing_warmstart(graph, Phi, quotas, n_replicas=256, n_steps=2000)

print(f"--- GAP CALCULATION AUDIT ---")
print(f"Spatial cost of warm sol: {evaluate_assignment_cost(warm_sol, graph, Phi, cost_mxn=None):.6f}")
print(f"Total cost with budget mu*k_i: {evaluate_assignment_cost(warm_sol, graph, Phi, cost_mxn=k_i, mu_cost=mu_cost):.6f}")
print(f"Budget term (mu * sum(k_i)): {mu_cost * sum(k_i[warm_sol[p]] for p in range(m)):.6f}")
