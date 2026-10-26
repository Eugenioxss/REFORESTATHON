"""E2E Pipeline Simulation with In-Memory Monkeypatch to find any secondary bugs.
Authored by Challenger 2.
"""
import sys
import os
import argparse
from unittest.mock import patch
import pandas as pd

sys.path.insert(0, os.path.abspath('.'))

import scripts.src.reforestacion_pipeline as pipeline

# Monkeypatch load_semiraw_datasets to inject alpha_target
orig_load = pipeline.load_semiraw_datasets

def patched_load():
    df_cat, df_wide, baseline = orig_load()
    df_cat["alpha_target"] = [pipeline.SPECIES_METADATA[i]["alpha_target"] for i in range(len(df_cat))]
    return df_cat, df_wide, baseline

pipeline.load_semiraw_datasets = patched_load

print("--- RUNNING E2E PIPELINE SIMULATION (6x11, solver=auto) ---")
test_args = [
    "reforestacion_pipeline.py",
    "--rows", "6",
    "--cols", "11",
    "--time-limit", "15",
    "--threads", "8",
    "--solver", "auto"
]

with patch.object(sys, 'argv', test_args):
    try:
        pipeline.main()
        print("\n[SUCCESS] Pipeline completed through main() with in-memory alpha_target patch.")
    except Exception as e:
        print(f"\n[SECONDARY CRASH DETECTED]: {e}")
        import traceback
        traceback.print_exc()
