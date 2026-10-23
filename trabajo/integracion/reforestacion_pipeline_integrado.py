# -*- coding: utf-8 -*-
"""Pipeline CONAFOR Robusto y Optimización Estocástica (REFORESTATHON)
====================================================================
Implementa los requerimientos matemáticos, ecológicos y computacionales de R2 y R3:
1. Densidad objetivo dependiente de pendiente topográfica:
   N_z = floor(658 * A_z) para pendiente < 20% vs ceil(524 * A_z) para pendiente >= 20% (Norma CONAFOR).
2. Núcleo ecológico multicomponente:
   - Competencia hídrica radicular c^W con kernel biweight de Epanechnikov K(v) = (1 - v^2)^2 (Berger et al., 2008).
   - Competencia lumínica c^L por sombreo asimétrico foliar.
   - Facilitación por especie nodriza c^B (Prosopis laevigata / amortiguación microclimática).
   - Matriz compuesta normalizada c_ij sintetizada según jerarquía ecofisiológica (Ecs. 2, 3, 17).
3. Calibración empírica y parámetros ecofisiológicos de 10 especies nativas desde data/semiraw/.
4. Costos de adquisición en vivero diferenciados k_i in [14.50, 36.00] MXN con precio sombra mu = 0.0005.
5. Arquitectura de solver dual transparente:
   - Gurobi Optimizer (RLT-1 + cortes de cliques triangulares K_3).
   - Fallback automático e irrestricto a HiGHS (Branch-and-Cut) vía highspy y scipy.optimize.milp.
   - Cálculo dinámico del MIPGap auténtico a partir de cotas duales: (ObjVal - ObjBound) / abs(ObjVal).
6. Descomposición de dominio espacial (tiling en tablero de ajedrez / Red-Black sweeps) para escalamiento multi-hectárea.
7. Exportación de métricas auténticas, bitácoras completas y asignaciones espaciales en scripts/outputs/ y scripts/logs/.

Optimizado para: Windows 11, AMD Ryzen 7 6800H (16 hilos) + 32 GB RAM + NVIDIA RTX 3060 (6 GB VRAM).
"""

import argparse
from dataclasses import dataclass
import gc
import logging
import math
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import csc_matrix, dok_matrix
import torch

# ==============================================================================
# 1. CONFIGURACIÓN DE RUTAS, DIRECTORIOS Y LOGGING DUAL
# ==============================================================================
_FILE_DIR = Path(__file__).resolve().parent
if (_FILE_DIR / "data").exists():
    ROOT_DIR = _FILE_DIR
    SCRIPTS_DIR = _FILE_DIR / "scripts"
    SRC_DIR = SCRIPTS_DIR / "src"
else:
    SRC_DIR = _FILE_DIR                          # .../REFORESTATHON/scripts/src
    SCRIPTS_DIR = SRC_DIR.parent                  # .../REFORESTATHON/scripts
    ROOT_DIR = SCRIPTS_DIR.parent                 # .../REFORESTATHON
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
DATA_DIR = ROOT_DIR / "data" / "semiraw"          # .../REFORESTATHON/data/semiraw
POLI31_DIR = ROOT_DIR / "data" / "poli31"          # .../REFORESTATHON/data/poli31
OUT_DIR = SCRIPTS_DIR / "outputs"                 # .../REFORESTATHON/scripts/outputs
LOG_DIR = SCRIPTS_DIR / "logs"                    # .../REFORESTATHON/scripts/logs

OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configuración del Logger Principal
logger = logging.getLogger("REFORESTATHON")
logger.setLevel(logging.INFO)
logger.handlers.clear()

file_handler = logging.FileHandler(LOG_DIR / "execution.log", mode="w", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s"))
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s"))
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Handler específico para bitácora del solver (transparencia matemática forense)
solver_log_path = LOG_DIR / "solver_execution.log"
solver_logger = logging.getLogger("REFORESTATHON_SOLVER")
solver_logger.setLevel(logging.INFO)
solver_logger.handlers.clear()  # Previene acumulación duplicada de handlers
solver_file_handler = logging.FileHandler(solver_log_path, mode="w", encoding="utf-8")
solver_file_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
solver_logger.addHandler(solver_file_handler)

# Cabecera inicial de auditoría en la bitácora del solver
solver_logger.info("=" * 90)
solver_logger.info("BITÁCORA FORENSE DE EJECUCIÓN DEL SOLVER MATEMÁTICO (REFORESTATHON)")
solver_logger.info("Modelo: MILP RLT-1 con Descomposición Lineal Exacta y Cortes de Clique K_3")
solver_logger.info("=" * 90)

# ==============================================================================
# 2. PARÁMETROS MAESTROS Y CALIBRACIÓN EMPÍRICA CONAFOR / INECOL (10 ESPECIES)
# ==============================================================================

# Catálogo completo con parámetros ecofisiológicos calibrados de campo (2021-2023)
SPECIES_METADATA: Dict[int, Dict[str, Any]] = {
    0: {
        "code": "AL",
        "name": "Agave lechuguilla",
        "common": "Lechuguilla",
        "family": "Asparagaceae",
        "role": "Rosetofila",
        "quota_recipe": 42,
        "alpha_target": 42 / 658,
        "s_2021": 1.0000,
        "s_2022": 0.9435,
        "s_2023": 0.9265,
        "cost_mxn": 14.50,
        "d_depth": 0.20,
        "v_water_sens": 0.20,
        "l_light_sens": 0.40,
        "mature_height": 0.60,
        "R_rad": {1: 0.40, 6: 0.80, 20: 1.00},
        "U_uptake": {1: 0.10, 6: 0.18, 20: 0.22},
    },
    1: {
        "code": "AS",
        "name": "Agave salmiana",
        "common": "Maguey verde",
        "family": "Asparagaceae",
        "role": "Rosetofila",
        "quota_recipe": 196,
        "alpha_target": 196 / 658,
        "s_2021": 1.0000,
        "s_2022": 0.9587,
        "s_2023": 0.9082,
        "cost_mxn": 18.00,
        "d_depth": 0.40,
        "v_water_sens": 0.25,
        "l_light_sens": 0.35,
        "mature_height": 2.00,
        "R_rad": {1: 0.60, 6: 1.50, 20: 2.40},
        "U_uptake": {1: 0.20, 6: 0.45, 20: 0.60},
    },
    2: {
        "code": "AC",
        "name": "Agave scabra",
        "common": "Maguey azul",
        "family": "Asparagaceae",
        "role": "Rosetofila",
        "quota_recipe": 42,
        "alpha_target": 42 / 658,
        "s_2021": 1.0000,
        "s_2022": 0.8245,
        "s_2023": 0.7453,
        "cost_mxn": 18.50,
        "d_depth": 0.30,
        "v_water_sens": 0.74,
        "l_light_sens": 0.30,
        "mature_height": 1.00,
        "R_rad": {1: 0.50, 6: 1.10, 20: 1.50},
        "U_uptake": {1: 0.15, 6: 0.28, 20: 0.35},
    },
    3: {
        "code": "AT",
        "name": "Agave striata",
        "common": "Maguey verde",
        "family": "Asparagaceae",
        "role": "Rosetofila",
        "quota_recipe": 42,
        "alpha_target": 42 / 658,
        "s_2021": 1.0000,
        "s_2022": 0.9517,
        "s_2023": 0.9138,
        "cost_mxn": 14.50,
        "d_depth": 0.25,
        "v_water_sens": 0.24,
        "l_light_sens": 0.35,
        "mature_height": 0.80,
        "R_rad": {1: 0.45, 6: 0.90, 20: 1.20},
        "U_uptake": {1: 0.12, 6: 0.20, 20: 0.25},
    },
    4: {
        "code": "OC",
        "name": "Opuntia cantabrigiensis",
        "common": "Cuijo",
        "family": "Cactaceae",
        "role": "Cactacea",
        "quota_recipe": 49,
        "alpha_target": 49 / 658,
        "s_2021": 1.0000,
        "s_2022": 0.9272,
        "s_2023": 0.8287,
        "cost_mxn": 15.50,
        "d_depth": 0.15,
        "v_water_sens": 0.49,
        "l_light_sens": 0.50,
        "mature_height": 1.50,
        "R_rad": {1: 0.50, 6: 1.20, 20: 1.60},
        "U_uptake": {1: 0.15, 6: 0.30, 20: 0.40},
    },
    5: {
        "code": "OE",
        "name": "Opuntia engelmannii",
        "common": "Cuijo",
        "family": "Cactaceae",
        "role": "Cactacea",
        "quota_recipe": 38,
        "alpha_target": 38 / 658,
        "s_2021": 1.0000,
        "s_2022": 0.8986,
        "s_2023": 0.8194,
        "cost_mxn": 15.50,
        "d_depth": 0.15,
        "v_water_sens": 0.52,
        "l_light_sens": 0.48,
        "mature_height": 1.20,
        "R_rad": {1: 0.55, 6: 1.30, 20: 1.80},
        "U_uptake": {1: 0.18, 6: 0.35, 20: 0.45},
    },
    6: {
        "code": "OR",
        "name": "Opuntia robusta",
        "common": "Tapón",
        "family": "Cactaceae",
        "role": "Cactacea",
        "quota_recipe": 73,
        "alpha_target": 73 / 658,
        "s_2021": 1.0000,
        "s_2022": 0.9576,
        "s_2023": 0.9198,
        "cost_mxn": 20.50,
        "d_depth": 0.25,
        "v_water_sens": 0.22,
        "l_light_sens": 0.40,
        "mature_height": 2.50,
        "R_rad": {1: 0.60, 6: 1.50, 20: 2.20},
        "U_uptake": {1: 0.20, 6: 0.42, 20: 0.55},
    },
    7: {
        "code": "OS",
        "name": "Opuntia streptacantha",
        "common": "Cardón",
        "family": "Cactaceae",
        "role": "Cactacea",
        "quota_recipe": 64,
        "alpha_target": 64 / 658,
        "s_2021": 1.0000,
        "s_2022": 0.8860,
        "s_2023": 0.8525,
        "cost_mxn": 22.50,
        "d_depth": 0.35,
        "v_water_sens": 0.42,
        "l_light_sens": 0.45,
        "mature_height": 4.00,
        "R_rad": {1: 0.65, 6: 1.60, 20: 2.50},
        "U_uptake": {1: 0.22, 6: 0.48, 20: 0.65},
    },
    8: {
        "code": "PL",
        "name": "Prosopis laevigata",
        "common": "Mezquite",
        "family": "Fabaceae",
        "role": "Nodriza",
        "quota_recipe": 86,
        "alpha_target": 86 / 658,
        "s_2021": 1.0000,
        "s_2022": 0.8214,
        "s_2023": 0.8179,
        "cost_mxn": 28.50,
        "d_depth": 0.90,
        "v_water_sens": 0.25,
        "l_light_sens": 0.60,
        "mature_height": 6.00,
        "R_rad": {1: 0.80, 6: 2.50, 20: 4.50},
        "U_uptake": {1: 0.30, 6: 0.70, 20: 1.00},
    },
    9: {
        "code": "YF",
        "name": "Yucca filifera",
        "common": "Palma china",
        "family": "Asparagaceae",
        "role": "Arborescente",
        "quota_recipe": 26,
        "alpha_target": 26 / 658,
        "s_2021": 1.0000,
        "s_2022": 0.8843,
        "s_2023": 0.7263,
        "cost_mxn": 36.00,
        "d_depth": 0.45,
        "v_water_sens": 0.80,
        "l_light_sens": 0.35,
        "mature_height": 8.00,
        "R_rad": {1: 0.50, 6: 1.40, 20: 2.20},
        "U_uptake": {1: 0.15, 6: 0.35, 20: 0.50},
    },
}

MODEL_PARAMS: Dict[str, Any] = {
    "planning_years": [1, 6, 20],
    "omega_weights": {1: 0.30, 6: 0.30, 20: 0.40},
    "juvenile_vulnerability_J": {1: 1.00, 6: 0.30, 20: 0.00},
    "beta_water": 0.60,
    "beta_light": 0.25,
    "beta_nurse": 0.15,
    "fitness_critical_threshold": 0.25,
    "fitness_scale_steepness": 0.05,
    "mu_cost_penalty": 0.0005,  # 1/mu = 2000 MXN / sobreviviente (precio sombra)
    "budget_per_ha_conafor": 13200.0,
    "density_flat_slope_less_20": 658,  # pl / ha (< 20%)
    "density_steep_slope_ge_20": 524,   # pl / ha (>= 20%)
    "slope_threshold_pct": 20.0,
}

BIG_SPECIES_IDS: Tuple[int, ...] = (7, 8, 9)  # origen: modelo_dominica, categoría b (PLANTED nivel=1: O. streptacantha=7, P. laevigata=8, Y. filifera=9; HEURÍSTICO en parametros_modelo.md §6)

# ==============================================================================
# 3. DENSIDAD OBJETIVO DEPENDIENTE DE PENDIENTE (REQUERIMIENTO R2.1 / EQ. 1)
# ==============================================================================

def get_target_density(slope_pct: float, area_ha: float = 1.0) -> Tuple[int, float]:
    """Calcula la meta de densidad vegetal N_z y la densidad de referencia según pendiente.
    Norma CONAFOR:
      N_z = floor(658 * A_z) si pendiente < 20%
      N_z = ceil(524 * A_z)  si pendiente >= 20%
    """
    if slope_pct < MODEL_PARAMS["slope_threshold_pct"]:
        n_z = int(math.floor(MODEL_PARAMS["density_flat_slope_less_20"] * area_ha))
        dens_ha = float(MODEL_PARAMS["density_flat_slope_less_20"])
    else:
        n_z = int(math.ceil(MODEL_PARAMS["density_steep_slope_ge_20"] * area_ha))
        dens_ha = float(MODEL_PARAMS["density_steep_slope_ge_20"])
    return n_z, dens_ha


# ==============================================================================
# 4. CARGA Y SINCRONIZACIÓN DE DATOS (data/semiraw/)
# ==============================================================================

def load_poli31_datasets(poli31_dir: Path) -> pd.DataFrame:
    # origen: modelo_dominica, categoría a (geometría y conteos registro_oficial31.csv) / categoría b (orden de empates de área)
    reg_path = poli31_dir / "registro_oficial31.csv"
    poly31_path = poli31_dir / "poligonos_31.csv"
    utm_path = poli31_dir / "poligonos_utm.csv"

    if not reg_path.exists():
        raise FileNotFoundError(f"No se encontró registro_oficial31.csv en {poli31_dir}")

    df_reg = pd.read_csv(reg_path)

    df_wide = pd.DataFrame()
    df_wide["poligono_id"] = df_reg["poligono"].astype(int)
    df_wide["poligono"] = [f"Polígono {pid}" for pid in df_wide["poligono_id"]]
    df_wide["dimension_ha"] = df_reg["area_ha_oficial"].astype(float)
    df_wide["area_ha_digitalizada"] = df_reg["area_ha_digitalizada"].astype(float)
    df_wide["dx_m"] = df_reg["dx_m"].astype(float)
    df_wide["dy_m"] = df_reg["dy_m"].astype(float)

    species_cols = [
        "Agave lechuguilla", "Agave salmiana", "Agave scabra", "Agave striata",
        "Opuntia cantabrigiensis", "Opuntia engelmannii", "Opuntia robusta",
        "Opuntia streptacantha", "Prosopis laevigata", "Yucca filifera"
    ]

    for sp in species_cols:
        if sp in df_reg.columns:
            df_wide[sp] = df_reg[sp].fillna(0).astype(int)
        else:
            df_wide[sp] = 0

    # Polígono 29 (6.54 ha) sin plantas vivas registradas (campos vacíos)
    df_wide["sin_registro_vivas"] = (df_wide["poligono_id"] == 29)

    if poly31_path.exists():
        df_p31 = pd.read_csv(poly31_path)
        local_verts = {}
        for pid, group in df_p31.groupby("poligono"):
            local_verts[int(pid)] = list(zip(group["x"], group["y"]))
        df_wide["local_vertices"] = df_wide["poligono_id"].map(lambda pid: local_verts.get(pid, []))

    if utm_path.exists():
        df_utm = pd.read_csv(utm_path)
        utm_verts = {}
        utm_e_min = {}
        utm_n_min = {}
        for pid, group in df_utm.groupby("poligono"):
            utm_verts[int(pid)] = list(zip(group["E_utm14N"], group["N_utm14N"]))
            utm_e_min[int(pid)] = float(group["E_utm14N"].min())
            utm_n_min[int(pid)] = float(group["N_utm14N"].min())
        df_wide["utm_vertices"] = df_wide["poligono_id"].map(lambda pid: utm_verts.get(pid, []))
        df_wide["utm_e_min"] = df_wide["poligono_id"].map(lambda pid: utm_e_min.get(pid, np.nan))
        df_wide["utm_n_min"] = df_wide["poligono_id"].map(lambda pid: utm_n_min.get(pid, np.nan))

    return df_wide


def load_semiraw_datasets(poligonos_dir: Optional[Union[Path, str]] = None) -> Tuple[pd.DataFrame, pd.DataFrame, List[int]]:
    """Carga los conjuntos de datos de campo y vivero desde data/semiraw/ o desde poli31/."""
    cat_path = DATA_DIR / "catalogo_especies_consolidado.csv"
    row_path = DATA_DIR / "orden_plantacion_100m.csv"

    if not (cat_path.exists() and row_path.exists()):
        raise FileNotFoundError(
            f"Faltan archivos en {DATA_DIR}. Verifica la carpeta data/semiraw/."
        )

    df_cat = pd.read_csv(cat_path)
    df_row = pd.read_csv(row_path)

    if poligonos_dir is None:
        wide_path = DATA_DIR / "poligonos_plantas_wide.csv"
        if not wide_path.exists():
            raise FileNotFoundError(f"Falta {wide_path}")
        df_wide = pd.read_csv(wide_path)
        df_wide["sin_registro_vivas"] = False
        data_source_str = f"data/semiraw/ ({wide_path.name})"
    else:
        df_wide = load_poli31_datasets(Path(poligonos_dir))
        data_source_str = f"poli31/ ({poligonos_dir})"

    df_cat["especie"] = df_cat["especie"].str.strip()
    df_cat["id"] = np.arange(len(df_cat))
    df_cat["genero"] = df_cat["especie"].apply(lambda s: s.split()[0])

    def _assign_role(gen: str) -> str:
        if gen == "Prosopis":
            return "Nodriza"
        if gen == "Agave":
            return "Rosetofila"
        if gen == "Opuntia":
            return "Cactacea"
        return "Arborescente"

    df_cat["rol"] = df_cat["genero"].apply(_assign_role)

    # Inyectar parámetros ecofisiológicos, proporciones objetivo y costos calibrados
    df_cat["costo_vivero_mxn"] = [SPECIES_METADATA[i]["cost_mxn"] for i in range(len(df_cat))]
    df_cat["d_depth"] = [SPECIES_METADATA[i]["d_depth"] for i in range(len(df_cat))]
    df_cat["v_water_sens"] = [SPECIES_METADATA[i]["v_water_sens"] for i in range(len(df_cat))]
    df_cat["l_light_sens"] = [SPECIES_METADATA[i]["l_light_sens"] for i in range(len(df_cat))]
    df_cat["mature_height"] = [SPECIES_METADATA[i]["mature_height"] for i in range(len(df_cat))]
    df_cat["alpha_target"] = [SPECIES_METADATA[i]["alpha_target"] for i in range(len(df_cat))]
    df_cat["quota_recipe"] = [SPECIES_METADATA[i]["quota_recipe"] for i in range(len(df_cat))]

    sp_to_id: Dict[str, int] = dict(zip(df_cat["especie"], df_cat["id"]))
    baseline_row_22: List[int] = [sp_to_id[str(sp).strip()] for sp in df_row["especie"]]

    logger.info(f"Datos de campo y vivero cargados desde: {data_source_str}")
    logger.info(
        f"Catálogo: {len(df_cat)} especies | Polígonos censados: {len(df_wide)} | "
        f"Fila 100m benchmark: {len(baseline_row_22)} cepas."
    )
    return df_cat, df_wide, baseline_row_22


# ==============================================================================
# 5. NÚCLEO ECOLÓGICO MULTICOMPONENTE (REQUERIMIENTO R2.2 Y R2.3 / EQS. 2, 3, 17)
# ==============================================================================

def build_ecological_matrices(
    df_cat: pd.DataFrame,
    lam: float = 1.0,
    slope_pct: float = 6.0,
    density_per_ha: Optional[float] = None,
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Construye la matriz de interacción neta c_ij y la matriz de penalización efectiva Phi.
    Incorpora:
    1. Competencia hídrica radicular c^W con kernel biweight de Epanechnikov K(v) = (1 - v^2)^2 (Eqs. 2 y 3).
    2. Competencia lumínica foliar c^L por sombreo asimétrico de alturas.
    3. Facilitación nodriza c^B (Prosopis laevigata / amortiguación microclimática).
    4. Síntesis ponderada (Eq. 17): c_tilde = 0.60*c^W + 0.25*c^L - 0.15*c^B con normalización en [0.05, 1.00].
    5. Ponderación simétrica de vulnerabilidad: Phi_ij = c_ij * (w_i + w_j) / 2.
    """
    df = df_cat.copy()
    n = len(df)

    df["s_2023"] = df["supervivencia_2023_pct"] / 100.0
    df["inv_s2023"] = 1.0 / df["s_2023"]

    inv_min = float(df["inv_s2023"].min())
    inv_max = float(df["inv_s2023"].max())
    df["w_vuln"] = 1.0 + lam * (df["inv_s2023"] - inv_min) / max(1e-6, inv_max - inv_min)

    # Distancia media de cepas en malla hexagonal tresbolillo d
    if density_per_ha is None:
        _, density_per_ha = get_target_density(slope_pct)
    step_d = math.sqrt(20000.0 / (density_per_ha * math.sqrt(3.0)))

    years = MODEL_PARAMS["planning_years"]
    omegas = MODEL_PARAMS["omega_weights"]

    C_water = np.zeros((n, n), dtype=np.float64)
    C_light = np.zeros((n, n), dtype=np.float64)
    C_nurse = np.zeros((n, n), dtype=np.float64)

    # 1. Competencia Radicular por Agua (Eqs. 2 y 3)
    for i in range(n):
        for j in range(n):
            c_w_sum = 0.0
            for t in years:
                w_t = omegas[t]
                R_i = SPECIES_METADATA[i]["R_rad"][t]
                R_j = SPECIES_METADATA[j]["R_rad"][t]
                U_i = SPECIES_METADATA[i]["U_uptake"][t]
                U_j = SPECIES_METADATA[j]["U_uptake"][t]

                # Distancia normalizada v
                v = step_d / max(1e-4, R_j + R_i)
                # Kernel de Epanechnikov biweight
                k_val = ((1.0 - v**2)**2) if (0.0 <= v < 1.0) else 0.0

                # Partición de absorción asimétrica y complementariedad de profundidad
                d_i = SPECIES_METADATA[i]["d_depth"]
                d_j = SPECIES_METADATA[j]["d_depth"]
                niche_factor = max(0.0, 1.0 - 0.6 * abs(d_j - d_i))
                ratio_j = U_j / max(1e-4, U_j + U_i)

                c_w_sum += w_t * ratio_j * k_val * niche_factor

            C_water[j, i] = c_w_sum

    C_water_sym = (C_water + C_water.T) / 2.0

    # 2. Competencia Lumínica Asimétrica (Sombreo por altura de dosel)
    max_h = max(SPECIES_METADATA[idx]["mature_height"] for idx in range(n))
    for i in range(n):
        for j in range(n):
            H_i = SPECIES_METADATA[i]["mature_height"]
            H_j = SPECIES_METADATA[j]["mature_height"]
            l_sens_i = SPECIES_METADATA[i]["l_light_sens"]
            if H_j > H_i:
                C_light[j, i] = l_sens_i * ((H_j - H_i) / max_h) * math.exp(-step_d / 3.5)
            else:
                C_light[j, i] = 0.0

    C_light_sym = (C_light + C_light.T) / 2.0
    for i in range(n):
        C_light_sym[i, i] = 0.25 * SPECIES_METADATA[i]["l_light_sens"]

    # 3. Facilitación de Nodriza (Prosopis laevigata microclimate buffering)
    sigma_B = 3.5
    beta_nurse = {1: 0.05, 6: 0.20, 20: 0.40}
    nurse_effect = sum(omegas[t] * beta_nurse[t] for t in years) * math.exp(-(step_d**2) / (2.0 * sigma_B**2))

    prosopis_id = 8  # Prosopis laevigata
    for i in range(n):
        if i != prosopis_id:
            C_nurse[prosopis_id, i] = nurse_effect
            C_nurse[i, prosopis_id] = nurse_effect

    # 4. Síntesis Multicomponente Ponderada (Eq. 17)
    beta_W = MODEL_PARAMS["beta_water"]
    beta_L = MODEL_PARAMS["beta_light"]
    beta_N = MODEL_PARAMS["beta_nurse"]

    C_raw = beta_W * C_water_sym + beta_L * C_light_sym - beta_N * C_nurse

    # Penalización de auto-competencia intraespecífica (evitar aglomeraciones del mismo taxón)
    for i in range(n):
        C_raw[i, i] = max(C_raw.max() * 1.15, 0.85)

    # Escalamiento Min-Max a [0.05, 1.00]
    c_min = float(C_raw.min())
    c_max = float(C_raw.max())
    if c_max > c_min + 1e-6:
        C_norm = 0.05 + 0.95 * (C_raw - c_min) / (c_max - c_min)
    else:
        C_norm = np.ones((n, n), dtype=np.float64)

    np.fill_diagonal(C_norm, 1.00)

    # Matriz efectiva Phi ponderada por vulnerabilidad empírica 2023
    w = df["w_vuln"].to_numpy(dtype=np.float64)
    Phi = C_norm * (w[:, None] + w[None, :]) / 2.0

    return df, C_norm, Phi


# ==============================================================================
# 6. SIMULACIÓN MONTE CARLO GPU CON COSTOS DIFERENCIADOS (REQUERIMIENTO R2.4)
# ==============================================================================

def run_monte_carlo_rtx3060(
    df_species: pd.DataFrame,
    df_wide: pd.DataFrame,
    target_area_ha: float = 1.0,
    n_sims: int = 1_000_000,
    slope_pct: float = 6.0,
) -> pd.DataFrame:
    """Ajusta distribuciones estocásticas sobre los 30 polígonos y simula N escenarios en GPU.
    Utiliza costos unitarios de vivero diferenciados k_i in [14.50, 36.00] MXN.
    """
    t0 = time.perf_counter()
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if dev.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True

    _, target_density_ha = get_target_density(slope_pct)
    sp_names = df_species["especie"].tolist()

    # Filtrar polígonos que sí tienen registro de plantas vivas (excluir sin_registro_vivas == True como Polígono 29)
    if "sin_registro_vivas" in df_wide.columns:
        valid_mask = ~df_wide["sin_registro_vivas"]
        if not valid_mask.any():
            valid_mask = np.ones(len(df_wide), dtype=bool)
        df_valid = df_wide[valid_mask]
    else:
        df_valid = df_wide

    poly_ha = df_valid["dimension_ha"].to_numpy(dtype=np.float64)
    poly_ha_safe = np.maximum(poly_ha, 1e-6)
    established = df_valid[sp_names].to_numpy(dtype=np.float64).T

    densities_per_ha = established / poly_ha_safe[None, :]
    mean_dens = densities_per_ha.mean(axis=1)
    if densities_per_ha.shape[1] > 1:
        var_dens = densities_per_ha.var(axis=1, ddof=1)
    else:
        var_dens = np.zeros(len(mean_dens), dtype=np.float64)

    results = []
    torch.manual_seed(42)

    for _, row in df_species.iterrows():
        idx = int(row["id"]) if "id" in row and pd.notna(row["id"]) else int(_)

        # Cuota escalada con fallback defensivo en cascada (alpha_target -> proporcion_programa -> SPECIES_METADATA -> 0.10)
        if "alpha_target" in row and pd.notna(row["alpha_target"]):
            alpha_val = float(row["alpha_target"])
        elif "proporcion_programa" in row and pd.notna(row["proporcion_programa"]):
            alpha_val = float(row["proporcion_programa"])
        elif idx in SPECIES_METADATA and "alpha_target" in SPECIES_METADATA[idx]:
            alpha_val = float(SPECIES_METADATA[idx]["alpha_target"])
        else:
            alpha_val = 0.10

        target_sp_ha = alpha_val * target_density_ha
        r_i = int(round(target_sp_ha * target_area_ha))
        mu = float(mean_dens[idx]) * target_area_ha
        sigma2 = float(var_dens[idx]) * (target_area_ha**2)

        if sigma2 > mu * 1.05:
            p_nb = mu / sigma2
            r_nb = (mu**2) / (sigma2 - mu)
            dist_name = f"NegBin(r={r_nb:.1f}, p={p_nb:.2f})"
            rate = torch.distributions.Gamma(
                concentration=torch.tensor(r_nb, device=dev, dtype=torch.float32),
                rate=torch.tensor(p_nb / (1.0 - p_nb), device=dev, dtype=torch.float32),
            ).sample(torch.Size([n_sims]))
            E_samples = torch.poisson(rate)
        else:
            dist_name = f"Poisson(lambda={mu:.1f})"
            E_samples = torch.poisson(
                torch.full((n_sims,), float(mu), device=dev, dtype=torch.float32)
            )

        F_samples = torch.clamp(float(r_i) - E_samples, min=0.0)
        f_mean = float(F_samples.mean().item())
        f_std = float(F_samples.std().item())
        se = f_std / math.sqrt(n_sims)
        q50 = float(torch.quantile(F_samples, 0.50).item())
        q95 = float(torch.quantile(F_samples, 0.95).item())
        prob_shortage = float((F_samples > round(f_mean)).float().mean().item())

        cost_unit = float(row.get("costo_vivero_mxn", SPECIES_METADATA.get(idx, {}).get("cost_mxn", 20.0)))
        cost_expected = round(f_mean * cost_unit, 2)

        sp_name = str(row.get("especie", SPECIES_METADATA.get(idx, {}).get("name", f"Especie_{idx}")))
        common_name = str(row.get("nombre_comun", SPECIES_METADATA.get(idx, {}).get("common", sp_name)))

        results.append({
            "especie": sp_name,
            "nombre_comun": common_name,
            "requerimiento_ri": r_i,
            "existencia_media_Ei": round(mu, 2),
            "distribucion_ajustada": dist_name,
            "compra_esperada_E_Fi": round(f_mean, 2),
            "IC95_inf": round(f_mean - 1.96 * se, 2),
            "IC95_sup": round(f_mean + 1.96 * se, 2),
            "pedido_mediana_Q50": int(round(q50)),
            "pedido_seguro_Q95": int(round(q95)),
            "costo_unitario_MXN": cost_unit,
            "costo_esp_MXN": cost_expected,
            "prob_faltante_en_media_%": round(prob_shortage * 100.0, 1),
        })

    if dev.type == "cuda":
        torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) * 1000.0
    logger.info(
        f"Simulación Monte Carlo en {dev} ({n_sims:,} escenarios x 10 especies) completada en {dt:.2f} ms."
    )

    df_mc = pd.DataFrame(results)
    df_mc.to_csv(OUT_DIR / "monte_carlo_compras.csv", index=False)
    return df_mc


# ==============================================================================
# 7. MALLA BIDIMENSIONAL EN TRES BOLILLOS Y ASIGNACIÓN PREEXISTENTE (E_i)
# ==============================================================================

@dataclass
class HexGridGraph:
    coords: np.ndarray
    edge_u: np.ndarray
    edge_v: np.ndarray
    edge_dist: np.ndarray
    edge_weight: np.ndarray
    step_d: float
    r_crit: float
    grid_i: Optional[np.ndarray] = None
    grid_j: Optional[np.ndarray] = None
    big_mask: Optional[np.ndarray] = None
    big_index: int = 0


def build_tres_bolillos_graph(
    n_rows: int,
    n_cols: int,
    density_per_ha: float = 658.0,
    ring_level: int = 1,
    big_index: int = 0,
) -> HexGridGraph:
    """Construye la topología triangular regular en tres bolillos con distanciamiento CONAFOR."""
    step_d = math.sqrt(20000.0 / (density_per_ha * math.sqrt(3.0)))
    r_crit = step_d * 1.08 if ring_level == 1 else step_d * 1.80

    coords_list = []
    grid_i_list = []
    grid_j_list = []
    for r in range(n_rows):
        for c in range(n_cols):
            u = (c + 0.5 * (r % 2)) * step_d
            v = r * (math.sqrt(3.0) / 2.0) * step_d
            coords_list.append((u, v))
            grid_i_list.append(c)
            grid_j_list.append(r)
    coords = np.array(coords_list, dtype=np.float64)
    grid_i = np.array(grid_i_list, dtype=np.int32)
    grid_j = np.array(grid_j_list, dtype=np.int32)

    m = len(coords)
    if big_index > 1:
        big_mask = ((grid_i - grid_j) % big_index == 0)  # origen: modelo_dominica, categoría b (sub_mask en hexgarden.py L227-236; HEURÍSTICO en parametros_modelo.md §1 y §19)
    else:
        big_mask = np.ones(m, dtype=bool)

    diff = coords[:, None, :] - coords[None, :, :]
    dist_mat = np.linalg.norm(diff, axis=-1)

    u_idx, v_idx = np.where((np.triu(dist_mat, k=1) > 1e-6) & (np.triu(dist_mat, k=1) <= r_crit))
    dists = dist_mat[u_idx, v_idx]
    weights = step_d / dists

    total_possible = m * (m - 1) // 2
    sparsity_saving = 100.0 * (1.0 - len(u_idx) / max(1, total_possible))
    logger.info(
        f"Malla Tres Bolillos {n_rows}x{n_cols} (|P|={m}, d={step_d:.2f}m, R_crit={r_crit:.2f}m, big_index={big_index}): "
        f"{len(u_idx)} aristas de {total_possible} pares ({sparsity_saving:.1f}% poda de soporte compacto) | Nodos subred grandes: {int(np.sum(big_mask))}/{m}."
    )
    return HexGridGraph(
        coords, u_idx, v_idx, dists, weights, step_d, r_crit,
        grid_i=grid_i, grid_j=grid_j, big_mask=big_mask, big_index=big_index
    )


def compute_exact_quotas(proportions: np.ndarray, total_positions: int) -> np.ndarray:
    """Calcula cuotas enteras r_i garantizando conservacion exacta: sum(r_i) = |P|."""
    raw = proportions * total_positions
    quotas = np.floor(raw).astype(int)
    rem = int(total_positions - quotas.sum())
    if rem > 0:
        top_idx = np.argsort(raw - quotas)[::-1][:rem]
        quotas[top_idx] += 1
    return quotas


def build_real_preexisting_nodes_from_csv(
    df_sp: pd.DataFrame,
    df_wide: pd.DataFrame,
    graph: HexGridGraph,
    quotas_base: np.ndarray,
    poligono_id: int = 0,
    density_per_ha: float = 658.0,
    seed: int = 42,
) -> Tuple[Dict[int, int], np.ndarray]:
    """Carga plantas preexistentes reales desde poligonos_plantas_wide.csv y las fija en la malla."""
    m = len(graph.coords)
    n_sp = len(df_sp)
    sp_names = df_sp["especie"].tolist()

    if 1 <= poligono_id <= len(df_wide):
        row = df_wide[df_wide["poligono_id"] == poligono_id].iloc[0]
        ha = float(row["dimension_ha"])
        est_counts = np.array([float(row[sp]) for sp in sp_names], dtype=np.float64)
        total_est = float(est_counts.sum())
        total_target = density_per_ha * ha
        if total_est == 0.0:
            est_ratio = 0.0
            est_share = np.zeros(n_sp, dtype=np.float64)
        else:
            est_ratio = min(0.45, total_est / max(1.0, total_target))
            est_share = est_counts / total_est
        source_desc = f"Polígono {poligono_id} ({ha:.2f} Ha)"
    else:
        if "sin_registro_vivas" in df_wide.columns:
            df_valid = df_wide[~df_wide["sin_registro_vivas"]]
            if df_valid.empty:
                df_valid = df_wide
        else:
            df_valid = df_wide

        total_ha = float(df_valid["dimension_ha"].sum())
        est_counts = df_valid[sp_names].to_numpy(dtype=np.float64).sum(axis=0)
        total_est = float(est_counts.sum())
        total_target = density_per_ha * total_ha
        if total_est == 0.0:
            est_ratio = 0.0
            est_share = np.zeros(n_sp, dtype=np.float64)
        else:
            est_ratio = total_est / max(1.0, total_target)
            est_share = est_counts / total_est
        source_desc = f"Promedio {len(df_valid)} Polígonos ({total_ha:.2f} Ha)"

    n_fixed = int(round(m * est_ratio))
    if n_fixed == 0 or total_est == 0.0:
        E_i = np.zeros(n_sp, dtype=int)
        fixed_nodes = {}
        logger.info(
            f"Vegetación preexistente ({source_desc}): 0/{m} cepas fijas (0.0%) | "
            f"E_i = {E_i.tolist()}"
        )
        return fixed_nodes, E_i
    raw_E = est_share * n_fixed
    E_i = np.minimum(quotas_base, np.floor(raw_E).astype(int))
    rem = int(n_fixed - E_i.sum())
    if rem > 0:
        order = np.argsort(-(raw_E - E_i))
        for idx in order:
            if rem == 0:
                break
            if E_i[idx] < quotas_base[idx]:
                E_i[idx] += 1
                rem -= 1

    adj: List[List[int]] = [[] for _ in range(m)]
    for e in range(len(graph.edge_u)):
        u, v = int(graph.edge_u[e]), int(graph.edge_v[e])
        adj[u].append(v)
        adj[v].append(u)

    rng = np.random.default_rng(seed)
    candidates = list(range(m))
    rng.shuffle(candidates)
    fixed_nodes: Dict[int, int] = {}

    has_big_mask = (graph.big_mask is not None and not np.all(graph.big_mask))
    if has_big_mask:
        sum_E_big = sum(int(E_i[sp]) for sp in BIG_SPECIES_IDS)
        n_big_avail = int(np.sum(graph.big_mask))
        if sum_E_big > n_big_avail:
            logger.warning(
                f"Plantas preexistentes de especies grandes ({sum_E_big}) exceden los nodos disponibles en big_mask ({n_big_avail}); "
                f"el excedente se ubicará fuera de la subred para no perder plantas preexistentes."
            )

    def place_species_nodes(sp: int, count: int) -> None:
        is_big = (sp in BIG_SPECIES_IDS) and has_big_mask
        placed = 0
        if is_big:
            for p in candidates:
                if placed >= count:
                    break
                if p not in fixed_nodes and bool(graph.big_mask[p]) and all(fixed_nodes.get(nb, -1) != sp for nb in adj[p]):
                    fixed_nodes[p] = sp
                    placed += 1
            for p in candidates:
                if placed >= count:
                    break
                if p not in fixed_nodes and bool(graph.big_mask[p]):
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

    # Ubicar primero Prosopis preexistente
    prosopis_id = 8
    place_species_nodes(prosopis_id, int(E_i[prosopis_id]))

    # Ubicar resto de especies
    for sp in range(n_sp):
        if sp == prosopis_id:
            continue
        place_species_nodes(sp, int(E_i[sp]))

    logger.info(
        f"Vegetación preexistente ({source_desc}): {len(fixed_nodes)}/{m} cepas fijas "
        f"({100.0*len(fixed_nodes)/m:.1f}%) | E_i = {E_i.tolist()}"
    )
    return fixed_nodes, E_i


def compute_flexible_bounds_and_warm_quotas(
    df_sp: pd.DataFrame,
    m_nodes: int,
    quotas_base: np.ndarray,
    E_i: np.ndarray,
    tolerance_pct: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calcula las bandas [lb_i, ub_i] bajo tolerancia epsilon y cuotas objetivo heurísticas."""
    if tolerance_pct <= 1e-9:
        q = quotas_base.copy()
        return q, q.copy(), q.copy()

    proportions = df_sp["proporcion_programa"].to_numpy(dtype=np.float64)
    s_2023 = df_sp["supervivencia_2023_pct"].to_numpy(dtype=np.float64) / 100.0
    raw = proportions * m_nodes

    lb = np.floor(raw * (1.0 - tolerance_pct)).astype(int)
    ub = np.ceil(raw * (1.0 + tolerance_pct)).astype(int)

    lb = np.maximum(lb, np.maximum(1, E_i))
    ub = np.maximum(ub, lb)

    q_warm = lb.copy()
    rem = int(m_nodes - q_warm.sum())

    max_agave_total = max(int(q_warm[0:4].sum()), int(quotas_base[0:4].sum()) - 1)
    priority = [8, 6, 0, 3, 7, 4, 5, 1, 2, 9]
    for sp in priority:
        if rem <= 0:
            break
        cap = int(ub[sp] - q_warm[sp])
        if sp in (0, 1, 2, 3):
            cap = min(cap, max(0, max_agave_total - int(q_warm[0:4].sum())))
        add = min(rem, cap)
        if add > 0:
            q_warm[sp] += add
            rem -= add

    for sp in np.argsort(-s_2023):
        sp_idx = int(sp)
        if rem <= 0:
            break
        add = min(rem, int(ub[sp_idx] - q_warm[sp_idx]))
        if add > 0:
            q_warm[sp_idx] += add
            rem -= add

    return lb, ub, q_warm


def evaluate_assignment_cost(
    assignment: np.ndarray,
    graph: HexGridGraph,
    Phi: np.ndarray,
    cost_mxn: Optional[np.ndarray] = None,
    mu_cost: float = 0.0005,
    fixed_nodes: Optional[Dict[int, int]] = None,
) -> float:
    """Evalúa el costo exacto: competencia espacial + penalización financiera mu * sum(k_i * q_i)."""
    spatial_cost = float(np.sum(graph.edge_weight * Phi[assignment[graph.edge_u], assignment[graph.edge_v]]))
    if cost_mxn is not None and mu_cost > 0.0:
        fixed_nodes = fixed_nodes or {}
        new_plants_cost = sum(
            float(cost_mxn[assignment[p]]) for p in range(len(assignment)) if p not in fixed_nodes
        )
        return spatial_cost + mu_cost * new_plants_cost
    return spatial_cost


def audit_ecological_metrics(
    assignment: np.ndarray,
    graph: HexGridGraph,
    Phi: np.ndarray,
    df_sp: pd.DataFrame,
    fixed_nodes: Dict[int, int],
) -> Dict[str, Any]:
    """Audita de forma forense las métricas ecológicas, biológicas y espaciales."""
    m = len(graph.coords)
    n_edges = len(graph.edge_u)
    genera = df_sp["genero"].tolist()
    s_2023 = df_sp["supervivencia_2023_pct"].to_numpy(dtype=np.float64) / 100.0
    costs_vivero = df_sp["costo_vivero_mxn"].to_numpy(dtype=np.float64)

    comp_spatial = float(np.sum(graph.edge_weight * Phi[assignment[graph.edge_u], assignment[graph.edge_v]]))
    intra_contacts = 0
    agave_contacts = 0
    nurse_contacts = 0
    node_load = np.zeros(m, dtype=np.float64)
    node_deg = np.zeros(m, dtype=np.float64)

    for e in range(n_edges):
        u, v = int(graph.edge_u[e]), int(graph.edge_v[e])
        su, sv = int(assignment[u]), int(assignment[v])
        w_e = float(graph.edge_weight[e])
        val = w_e * float(Phi[su, sv])
        node_load[u] += val
        node_load[v] += val
        node_deg[u] += w_e
        node_deg[v] += w_e

        if su == sv:
            intra_contacts += 1
        if genera[su] == "Agave" and genera[sv] == "Agave":
            agave_contacts += 1
        if (su == 8 and sv != 8) or (sv == 8 and su != 8):
            nurse_contacts += 1

    counts = np.bincount(assignment, minlength=len(df_sp))
    surv_base_pct = float(np.mean(s_2023[assignment]) * 100.0)

    # Supervivencia espacial ajustada por amortiguación nodriza y mitigación de carga de competencia
    avg_edge_load = node_load / np.maximum(1.0, node_deg)
    surv_eff_nodes = np.clip(s_2023[assignment] * (1.0 + 0.08 * (0.557 - avg_edge_load)), 0.0, 0.995)
    surv_eff_pct = float(np.mean(surv_eff_nodes) * 100.0)

    # Gasto de vivero contabilizado únicamente para plantas nuevas adquiridas
    new_plants_mask = np.array([p not in fixed_nodes for p in range(m)], dtype=bool)
    nursery_expense = float(np.sum(costs_vivero[assignment[new_plants_mask]]))

    return {
        "comp_total": comp_spatial,
        "intra_contacts": intra_contacts,
        "agave_contacts": agave_contacts,
        "nurse_contacts": nurse_contacts,
        "prosopis_count": int(counts[8]),
        "agave_total": int(counts[0:4].sum()),
        "counts": counts,
        "surv_base_pct": surv_base_pct,
        "surv_eff_pct": surv_eff_pct,
        "gasto_vivero_mxn": round(nursery_expense, 2),
        "fixed_count": len(fixed_nodes),
    }


# ==============================================================================
# 8. WARM-START METAHEURÍSTICO PARALELO EN GPU (RTX 3060)
# ==============================================================================

def gpu_parallel_annealing_warmstart(
    graph: HexGridGraph,
    Phi: np.ndarray,
    quotas: np.ndarray,
    fixed_nodes: Optional[Dict[int, int]] = None,
    n_replicas: int = 1024,
    n_steps: int = 8000,
) -> Tuple[np.ndarray, float]:
    """Genera una solución inicial primalmente factible y compacta mediante recocido simulado en GPU."""
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    m = len(graph.coords)
    fixed_nodes = fixed_nodes or {}

    has_big_mask = (graph.big_mask is not None and not np.all(graph.big_mask))
    if has_big_mask:
        for pos, sp in fixed_nodes.items():
            if sp in BIG_SPECIES_IDS and not graph.big_mask[pos]:
                logger.warning(
                    f"Planta preexistente de especie grande (sp={sp}) en nodo pos={pos} está fuera de la subred big_mask."
                )

    rem_quotas = quotas.copy()
    for _, sp in fixed_nodes.items():
        if rem_quotas[sp] > 0:
            rem_quotas[sp] -= 1

    free_positions = [p for p in range(m) if p not in fixed_nodes]
    states_np = np.zeros((n_replicas, m), dtype=np.int64)
    rng = np.random.default_rng(42)

    if has_big_mask:
        free_big_pos = np.array([p for p in free_positions if graph.big_mask[p]], dtype=int)
        free_nonbig_pos = np.array([p for p in free_positions if not graph.big_mask[p]], dtype=int)

        rem_big_sp = np.array([sp for sp in BIG_SPECIES_IDS for _ in range(max(0, rem_quotas[sp]))], dtype=int)
        rem_other_sp = np.array([sp for sp in range(len(quotas)) if sp not in BIG_SPECIES_IDS for _ in range(max(0, rem_quotas[sp]))], dtype=int)

        if len(rem_big_sp) > len(free_big_pos):
            logger.warning(
                f"Cuota restante de especies grandes ({len(rem_big_sp)}) excede posiciones libres en big_mask ({len(free_big_pos)}). "
                f"El excedente se colocará en posiciones libres normales."
            )

        for b in range(n_replicas):
            for pos, sp in fixed_nodes.items():
                states_np[b, pos] = sp

            n_fit = min(len(rem_big_sp), len(free_big_pos))
            perm_big_pos = rng.permutation(free_big_pos)
            perm_nonbig_pos = rng.permutation(free_nonbig_pos)
            perm_big_sp = rng.permutation(rem_big_sp)

            states_np[b, perm_big_pos[:n_fit]] = perm_big_sp[:n_fit]

            leftover_sp = np.concatenate([perm_big_sp[n_fit:], rem_other_sp])
            leftover_pos = np.concatenate([perm_big_pos[n_fit:], perm_nonbig_pos])

            if len(leftover_sp) < len(leftover_pos):
                leftover_sp = np.concatenate([leftover_sp, np.zeros(len(leftover_pos) - len(leftover_sp), dtype=int)])
            else:
                leftover_sp = leftover_sp[:len(leftover_pos)]

            states_np[b, leftover_pos] = rng.permutation(leftover_sp)
    else:
        free_pool = np.repeat(np.arange(len(quotas)), np.maximum(0, rem_quotas))
        if len(free_pool) < len(free_positions):
            free_pool = np.concatenate([free_pool, np.zeros(len(free_positions) - len(free_pool), dtype=int)])
        free_pool = free_pool[:len(free_positions)]

        for b in range(n_replicas):
            for pos, sp in fixed_nodes.items():
                states_np[b, pos] = sp
            states_np[b, free_positions] = rng.permutation(free_pool)

    states = torch.tensor(states_np, device=dev, dtype=torch.long)
    Phi_t = torch.tensor(Phi, device=dev, dtype=torch.float32)
    edge_u_t = torch.tensor(graph.edge_u, device=dev, dtype=torch.long)
    edge_v_t = torch.tensor(graph.edge_v, device=dev, dtype=torch.long)
    edge_w_t = torch.tensor(graph.edge_weight, device=dev, dtype=torch.float32)
    free_pos_t = torch.tensor(free_positions, device=dev, dtype=torch.long)
    big_mask_t = torch.tensor(graph.big_mask, device=dev, dtype=torch.bool) if has_big_mask else None

    def batch_cost(st: torch.Tensor) -> torch.Tensor:
        return (Phi_t[st[:, edge_u_t], st[:, edge_v_t]] * edge_w_t[None, :]).sum(dim=1)

    curr_costs = batch_cost(states)
    best_idx = int(torch.argmin(curr_costs).item())
    best_cost = float(curr_costs[best_idx].item())
    best_state = states[best_idx].clone()

    t0 = time.perf_counter()
    n_free = len(free_positions)
    if n_free > 1:
        T_start, T_end = 2.5, 0.02
        for step in range(n_steps):
            T = T_start * ((T_end / T_start) ** (step / max(1, n_steps)))
            p_idx1 = torch.randint(0, n_free, (n_replicas,), device=dev)
            p_idx2 = torch.randint(0, n_free, (n_replicas,), device=dev)
            pos1 = free_pos_t[p_idx1]
            pos2 = free_pos_t[p_idx2]

            prop_states = states.clone()
            v1 = states[torch.arange(n_replicas, device=dev), pos1]
            v2 = states[torch.arange(n_replicas, device=dev), pos2]
            prop_states[torch.arange(n_replicas, device=dev), pos1] = v2
            prop_states[torch.arange(n_replicas, device=dev), pos2] = v1

            prop_costs = batch_cost(prop_states)
            dE = prop_costs - curr_costs
            accept = (dE <= 0.0) | (torch.rand((n_replicas,), device=dev) < torch.exp(-dE / max(1e-4, T)))

            if has_big_mask and big_mask_t is not None:
                is_v1_big = (v1 == 7) | (v1 == 8) | (v1 == 9)
                is_v2_big = (v2 == 7) | (v2 == 8) | (v2 == 9)
                v1_valid = (~is_v1_big) | big_mask_t[pos2] | (~big_mask_t[pos1])
                v2_valid = (~is_v2_big) | big_mask_t[pos1] | (~big_mask_t[pos2])
                valid_swap = v1_valid & v2_valid
                accept = accept & valid_swap

            states = torch.where(accept[:, None], prop_states, states)
            curr_costs = torch.where(accept, prop_costs, curr_costs)

            min_c = float(torch.min(curr_costs).item())
            if min_c < best_cost:
                best_cost = min_c
                best_state = states[int(torch.argmin(curr_costs).item())].clone()

    if dev.type == "cuda":
        torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) * 1000.0
    logger.info(f"Warm-Start RTX 3060 ({n_replicas} réplicas x {n_steps} pasos) concluido en {dt:.2f} ms | Costo: {best_cost:.4f}")

    best_np = best_state.cpu().numpy().astype(int)
    if dev.type == "cuda":
        torch.cuda.empty_cache()
    return best_np, best_cost


# ==============================================================================
# 9. SOLVER DUAL TRANSPARENTE (GUROBI + FALLBACK HIGHS) (REQUERIMIENTO R3.1)
# ==============================================================================

def solve_reforestation_mip(
    graph: HexGridGraph,
    Phi: np.ndarray,
    quotas: np.ndarray,
    warm_assignment: np.ndarray,
    fixed_nodes: Optional[Dict[int, int]] = None,
    tolerance_pct: float = 0.0,
    df_sp: Optional[pd.DataFrame] = None,
    E_i: Optional[np.ndarray] = None,
    time_limit: int = 120,
    cpu_threads: int = 14,
    solver_name: str = "auto",
    mu_cost: float = 0.0005,
) -> Tuple[np.ndarray, float, float, float, str]:
    """Resuelve el problema exacto de optimización espacial MIP mediante un backend dual:
    - Backend 1: Gurobi Optimizer (RLT-1 + cortes de cliques triangulares K_3).
    - Backend 2: HiGHS Branch-and-Cut (sin límites de licencia de variables) vía highspy o scipy.
    - Garantía: MIPGap auténtico calculado de cotas duales: 100 * (ObjVal - ObjBound) / ObjVal.
    """
    m = len(graph.coords)
    n_sp = len(quotas)
    n_edges = len(graph.edge_u)
    fixed_nodes = fixed_nodes or {}

    if E_i is None:
        E_i = np.zeros(n_sp, dtype=int)
        for _, sp in fixed_nodes.items():
            E_i[sp] += 1

    if df_sp is not None:
        lb_i, ub_i, q_target = compute_flexible_bounds_and_warm_quotas(
            df_sp, m, quotas, E_i, tolerance_pct
        )
        s_2023 = df_sp["supervivencia_2023_pct"].to_numpy(dtype=np.float64) / 100.0
        k_i = df_sp["costo_vivero_mxn"].to_numpy(dtype=np.float64)
    else:
        lb_i = np.maximum(E_i, np.floor(quotas * (1.0 - tolerance_pct)).astype(int))
        ub_i = np.maximum(lb_i, np.ceil(quotas * (1.0 + tolerance_pct)).astype(int))
        q_target = quotas.copy()
        s_2023 = np.ones(n_sp, dtype=np.float64)
        k_i = np.array([SPECIES_METADATA[idx]["cost_mxn"] for idx in range(n_sp)], dtype=np.float64)

    has_big_mask = (graph.big_mask is not None and not np.all(graph.big_mask))
    if has_big_mask:
        for p, sp in fixed_nodes.items():
            if sp in BIG_SPECIES_IDS and not graph.big_mask[p]:
                logger.warning(
                    f"Planta preexistente de especie grande (sp={sp}) en nodo p={p} está fuera de la subred big_index={graph.big_index}; "
                    f"se exime ese nodo para preservar factibilidad."
                )

        allowed_big_nodes = sum(
            1 for p in range(m) if graph.big_mask[p] or (p in fixed_nodes and fixed_nodes[p] in BIG_SPECIES_IDS)
        )
        sum_lb_big = sum(int(lb_i[i]) for i in BIG_SPECIES_IDS)
        if sum_lb_big > allowed_big_nodes:
            logger.warning(
                f"Suma de cotas inferiores de especies grandes ({sum_lb_big}) excede nodos permitidos en subred ({allowed_big_nodes}). "
                f"Ajustando cotas inferiores para evitar infactibilidad en MILP."
            )
            excess = sum_lb_big - allowed_big_nodes
            for i in reversed(BIG_SPECIES_IDS):
                if excess <= 0:
                    break
                reduce_by = min(excess, lb_i[i] - E_i[i])
                if reduce_by > 0:
                    lb_i[i] -= reduce_by
                    excess -= reduce_by

    # 1. Descomposición de Potencial Lineal Exacto alpha_i (técnica RLT-1)
    A_ub, b_ub = [], []
    for i in range(n_sp):
        for j in range(n_sp):
            row = np.zeros(n_sp)
            row[i] += 1.0
            row[j] += 1.0
            A_ub.append(row)
            b_ub.append(float(Phi[i, j]))
    res_lp = linprog(-q_target.astype(float), A_ub=A_ub, b_ub=b_ub, bounds=[(None, None)] * n_sp)
    alpha = res_lp.x if res_lp.success else np.zeros(n_sp)
    R = np.maximum(0.0, Phi - (alpha[:, None] + alpha[None, :]))

    W_p = np.zeros(m, dtype=np.float64)
    for e in range(n_edges):
        W_p[graph.edge_u[e]] += graph.edge_weight[e]
        W_p[graph.edge_v[e]] += graph.edge_weight[e]

    R_ag = np.zeros_like(R)
    R_ag[0:4, 0:4] = R[0:4, 0:4]
    R_op = np.zeros_like(R)
    R_op[4:8, 4:8] = R[4:8, 4:8]
    R_rem = np.maximum(0.0, R - R_ag - R_op)

    M_ag = R_ag.max(axis=1)
    M_op = R_op.max(axis=1)
    min_agave = float(R[0:4, 0:4].min())
    min_opuntia = float(R[4:8, 4:8].min())

    # Identificar cliques triangulares K_3
    edge_map: Dict[Tuple[int, int], int] = {}
    for e in range(n_edges):
        u, v = int(graph.edge_u[e]), int(graph.edge_v[e])
        edge_map[(u, v)] = e
        edge_map[(v, u)] = e

    triangles = []
    for p in range(m):
        for q in range(p + 1, m):
            if (p, q) in edge_map:
                for r in range(q + 1, m):
                    if (q, r) in edge_map and (p, r) in edge_map:
                        triangles.append((p, q, r, edge_map[(p, q)], edge_map[(q, r)], edge_map[(p, r)]))

    total_vars = m * n_sp + 3 * n_edges
    solver_logger.info(f"--- NUEVA INSTANCIA MIP: |P|={m}, Aristas={n_edges}, Variables={total_vars}, Triángulos K3={len(triangles)} ---")

    # Intentar resolver con Gurobi si fue solicitado explícitamente y entra en la licencia (<= 1800 vars)
    use_gurobi = (solver_name.lower() in ("gurobi",)) and (total_vars <= 1800)
    cost_ws = evaluate_assignment_cost(
        warm_assignment, graph, Phi, cost_mxn=k_i, mu_cost=mu_cost, fixed_nodes=fixed_nodes
    )

    if use_gurobi:
        try:
            import gurobipy as gp  # type: ignore
            from gurobipy import GRB  # type: ignore

            logging.getLogger("gurobipy").propagate = False
            env = gp.Env(empty=True)
            env.setParam("OutputFlag", 1)
            env.start()
            model = gp.Model("CONAFOR_Compact_K3", env=env)
            model.setParam("TimeLimit", time_limit)
            model.setParam("Threads", cpu_threads)
            model.setParam("MIPFocus", 1 if tolerance_pct > 0.0 else 2)
            model.setParam("Presolve", 2)
            model.setParam("Cuts", 2)

            x = model.addVars(n_sp, m, vtype=GRB.BINARY, name="x")
            z_ag = model.addVars(n_edges, lb=0.0, vtype=GRB.CONTINUOUS, name="z_ag")
            z_op = model.addVars(n_edges, lb=0.0, vtype=GRB.CONTINUOUS, name="z_op")
            z_rem = model.addVars(n_edges, lb=0.0, vtype=GRB.CONTINUOUS, name="z_rem")

            for p, sp_fixed in fixed_nodes.items():
                for i in range(n_sp):
                    val = 1.0 if i == int(sp_fixed) else 0.0
                    x[i, int(p)].LB = val
                    x[i, int(p)].UB = val

            if has_big_mask:
                for p in range(m):
                    if not graph.big_mask[p] and p not in fixed_nodes:
                        for i in BIG_SPECIES_IDS:
                            x[i, p].UB = 0.0

            for p in range(m):
                sp_init = int(warm_assignment[p])
                for i in range(n_sp):
                    x[i, p].Start = 1.0 if i == sp_init else 0.0

            for p in range(m):
                if p not in fixed_nodes:
                    model.addConstr(gp.quicksum(x[i, p] for i in range(n_sp)) == 1, name=f"one_sp_{p}")

            for i in range(n_sp):
                tot_i = gp.quicksum(x[i, p] for p in range(m))
                if int(lb_i[i]) == int(ub_i[i]):
                    model.addConstr(tot_i == int(lb_i[i]), name=f"q_eq_{i}")
                else:
                    model.addConstr(tot_i >= int(lb_i[i]), name=f"q_lb_{i}")
                    model.addConstr(tot_i <= int(ub_i[i]), name=f"q_ub_{i}")

            if tolerance_pct > 1e-9:
                max_agaves = max(int(lb_i[0:4].sum()), int(quotas[0:4].sum()) - 1)
                model.addConstr(gp.quicksum(x[i, p] for i in range(4) for p in range(m)) <= max_agaves, name="agave_cap")
                if df_sp is not None:
                    base_surv_sum = float(np.dot(quotas, s_2023))
                    warm_surv_sum = float(np.sum(s_2023[warm_assignment]))
                    min_surv = base_surv_sum + max(0.05, 0.80 * (warm_surv_sum - base_surv_sum))
                    model.addConstr(gp.quicksum(float(s_2023[i]) * x[i, p] for i in range(n_sp) for p in range(m)) >= min_surv, name="surv_floor")

            for e in range(n_edges):
                p, q = int(graph.edge_u[e]), int(graph.edge_v[e])
                y_ag_p = gp.quicksum(x[i, p] for i in range(4))
                y_ag_q = gp.quicksum(x[i, q] for i in range(4))
                y_op_p = gp.quicksum(x[i, p] for i in range(4, 8))
                y_op_q = gp.quicksum(x[i, q] for i in range(4, 8))

                model.addConstr(z_ag[e] >= min_agave * (y_ag_p + y_ag_q - 1))
                model.addConstr(z_ag[e] >= float(R_ag[1, 1]) * (x[1, p] + x[1, q] - 1))
                model.addConstr(z_ag[e] >= gp.quicksum(float(R_ag[2, j]) * x[j, q] for j in range(4)) - float(M_ag[2]) * (1 - x[2, p]))
                model.addConstr(z_ag[e] >= gp.quicksum(float(R_ag[j, 2]) * x[j, p] for j in range(4)) - float(M_ag[2]) * (1 - x[2, q]))

                model.addConstr(z_op[e] >= min_opuntia * (y_op_p + y_op_q - 1))
                model.addConstr(z_op[e] >= gp.quicksum(float(R_op[5, j]) * x[j, q] for j in range(4, 8)) - float(M_op[5]) * (1 - (x[4, p] + x[5, p] + x[7, p])))
                model.addConstr(z_op[e] >= gp.quicksum(float(R_op[j, 5]) * x[j, p] for j in range(4, 8)) - float(M_op[5]) * (1 - (x[4, q] + x[5, q] + x[7, q])))

                model.addConstr(z_rem[e] >= float(R_rem[8, 8]) * (x[8, p] + x[8, q] - 1))
                model.addConstr(z_rem[e] >= float(R_rem[9, 9]) * (x[9, p] + x[9, q] - 1))

            for p, q, r, e1, e2, e3 in triangles:
                y_ag = gp.quicksum(x[i, p] + x[i, q] + x[i, r] for i in range(4))
                y_op = gp.quicksum(x[i, p] + x[i, q] + x[i, r] for i in range(4, 8))
                model.addConstr(z_ag[e1] + z_ag[e2] + z_ag[e3] >= min_agave * (y_ag - 1))
                model.addConstr(z_ag[e1] + z_ag[e2] + z_ag[e3] >= min_agave * (2 * y_ag - 3))
                model.addConstr(z_op[e1] + z_op[e2] + z_op[e3] >= min_opuntia * (y_op - 1))
                model.addConstr(z_op[e1] + z_op[e2] + z_op[e3] >= min_opuntia * (2 * y_op - 3))

            # Función objetivo: Potenciales lineales + regularización presupuestal mu * k_i + aristas
            linear_obj = gp.quicksum(
                float(W_p[p] * alpha[i] + (mu_cost * k_i[i] if p not in fixed_nodes else 0.0)) * x[i, p]
                for p in range(m) for i in range(n_sp)
            )
            edge_obj = gp.quicksum(
                float(graph.edge_weight[e]) * (z_ag[e] + z_op[e] + z_rem[e])
                for e in range(n_edges)
            )
            model.setObjective(linear_obj + edge_obj, GRB.MINIMIZE)

            # Exportar archivo LP para auditoría y verificación formal
            lp_export_path = OUT_DIR / "modelo_conafor.lp"
            model.write(str(lp_export_path))

            t_sol_0 = time.perf_counter()
            model.optimize()
            t_sol = time.perf_counter() - t_sol_0

            if model.SolCount > 0:
                best_bound = float(model.ObjBound)
                sol = np.zeros(m, dtype=int)
                for p in range(m):
                    for i in range(n_sp):
                        if x[i, p].X > 0.5:
                            sol[p] = i
                            break
                cost_gurobi_comp = evaluate_assignment_cost(
                    sol, graph, Phi, cost_mxn=k_i, mu_cost=mu_cost, fixed_nodes=fixed_nodes
                )
                if cost_gurobi_comp <= cost_ws + 1e-6:
                    best_sol, best_cost = sol, cost_gurobi_comp
                else:
                    best_sol, best_cost = warm_assignment, cost_ws
                real_gap = 100.0 * (best_cost - best_bound) / max(1e-6, abs(best_cost))
                real_gap = max(0.0, float(real_gap))
                solver_tag = f"Gurobi K3 ({cpu_threads} hilos)"
                solver_logger.info(
                    f"Gurobi Optimizado en {t_sol:.2f}s | ObjVal={best_cost:.4f} | BestBound={best_bound:.4f} | MIPGap={real_gap:.2f}%"
                )
                return best_sol, best_cost, best_bound, real_gap, solver_tag

        except Exception as e:
            logger.warning(f"Excepción en Gurobi ({e}); activando fallback automático e irrestricto a HiGHS.")
            solver_logger.warning(f"Excepción Gurobi: {e}. Activando HiGHS fallback.")

    # --------------------------------------------------------------------------
    # BACKEND HIGHS (Vía scipy.optimize.milp o highspy con modelo matricial exacto)
    # --------------------------------------------------------------------------
    logger.info(">>> Ejecutando Solver HiGHS (Branch-and-Cut, capacidad irrestricta)...")
    t_highs_0 = time.perf_counter()

    # Construir vectores para SciPy / HiGHS
    # Variables: x_ip [0 .. m*n_sp - 1], z_ag [0 .. n_edges-1], z_op, z_rem
    c_vec = np.zeros(total_vars, dtype=np.float64)
    for p in range(m):
        for i in range(n_sp):
            mu_term = (mu_cost * k_i[i]) if p not in fixed_nodes else 0.0
            c_vec[p * n_sp + i] = float(W_p[p] * alpha[i] + mu_term)
    for e in range(n_edges):
        w_e = float(graph.edge_weight[e])
        c_vec[m * n_sp + e] = w_e
        c_vec[m * n_sp + n_edges + e] = w_e
        c_vec[m * n_sp + 2 * n_edges + e] = w_e

    # Integrality: 1 para x_ip, 0 para variables continuas z
    integrality = np.zeros(total_vars, dtype=int)
    integrality[:m * n_sp] = 1

    # Cotas de variables
    lb_bounds = np.zeros(total_vars, dtype=np.float64)
    ub_bounds = np.ones(total_vars, dtype=np.float64)
    ub_bounds[m * n_sp:] = np.inf

    for p, sp_fixed in fixed_nodes.items():
        for i in range(n_sp):
            idx = int(p) * n_sp + i
            val = 1.0 if i == int(sp_fixed) else 0.0
            lb_bounds[idx] = val
            ub_bounds[idx] = val

    if has_big_mask:
        for p in range(m):
            if not graph.big_mask[p] and p not in fixed_nodes:
                for i in BIG_SPECIES_IDS:
                    ub_bounds[p * n_sp + i] = 0.0

    # Construcción de la matriz de restricciones dispersa A_mat
    constrs_rows = []
    lhs_list, rhs_list = [], []

    # 1. Asignación unívoca por nodo
    for p in range(m):
        if p not in fixed_nodes:
            row_dict = {p * n_sp + i: 1.0 for i in range(n_sp)}
            constrs_rows.append(row_dict)
            lhs_list.append(1.0)
            rhs_list.append(1.0)

    # 2. Cuotas por especie
    for i in range(n_sp):
        row_dict = {p * n_sp + i: 1.0 for p in range(m)}
        constrs_rows.append(row_dict)
        lhs_list.append(float(lb_i[i]))
        rhs_list.append(float(ub_i[i]))

    # 3. Restricciones de holgura
    if tolerance_pct > 1e-9:
        max_agaves = max(int(lb_i[0:4].sum()), int(quotas[0:4].sum()) - 1)
        row_agave = {p * n_sp + i: 1.0 for p in range(m) for i in range(4)}
        constrs_rows.append(row_agave)
        lhs_list.append(-np.inf)
        rhs_list.append(float(max_agaves))

        if df_sp is not None:
            base_surv_sum = float(np.dot(quotas, s_2023))
            warm_surv_sum = float(np.sum(s_2023[warm_assignment]))
            min_surv = base_surv_sum + max(0.05, 0.80 * (warm_surv_sum - base_surv_sum))
            row_surv = {p * n_sp + i: float(s_2023[i]) for p in range(m) for i in range(n_sp)}
            constrs_rows.append(row_surv)
            lhs_list.append(min_surv)
            rhs_list.append(np.inf)

    # 4. Cortes compactos por arista
    for e in range(n_edges):
        p, q = int(graph.edge_u[e]), int(graph.edge_v[e])
        z_ag_idx = m * n_sp + e
        z_op_idx = m * n_sp + n_edges + e
        z_rem_idx = m * n_sp + 2 * n_edges + e

        # Agave cut 1
        r1 = {z_ag_idx: 1.0}
        for i in range(4):
            r1[p * n_sp + i] = r1.get(p * n_sp + i, 0.0) - min_agave
            r1[q * n_sp + i] = r1.get(q * n_sp + i, 0.0) - min_agave
        constrs_rows.append(r1)
        lhs_list.append(-min_agave)
        rhs_list.append(np.inf)

        # Agave cut 2
        r2 = {z_ag_idx: 1.0, p * n_sp + 1: -float(R_ag[1, 1]), q * n_sp + 1: -float(R_ag[1, 1])}
        constrs_rows.append(r2)
        lhs_list.append(-float(R_ag[1, 1]))
        rhs_list.append(np.inf)

        # Opuntia cut 1
        r3 = {z_op_idx: 1.0}
        for i in range(4, 8):
            r3[p * n_sp + i] = r3.get(p * n_sp + i, 0.0) - min_opuntia
            r3[q * n_sp + i] = r3.get(q * n_sp + i, 0.0) - min_opuntia
        constrs_rows.append(r3)
        lhs_list.append(-min_opuntia)
        rhs_list.append(np.inf)

        # Residual Prosopis y Yucca
        constrs_rows.append({z_rem_idx: 1.0, p * n_sp + 8: -float(R_rem[8, 8]), q * n_sp + 8: -float(R_rem[8, 8])})
        lhs_list.append(-float(R_rem[8, 8]))
        rhs_list.append(np.inf)

        constrs_rows.append({z_rem_idx: 1.0, p * n_sp + 9: -float(R_rem[9, 9]), q * n_sp + 9: -float(R_rem[9, 9])})
        lhs_list.append(-float(R_rem[9, 9]))
        rhs_list.append(np.inf)

    # 5. Cliques triangulares K_3
    for p, q, r, e1, e2, e3 in triangles:
        row_tri_ag = {
            m * n_sp + e1: 1.0,
            m * n_sp + e2: 1.0,
            m * n_sp + e3: 1.0,
        }
        for i in range(4):
            row_tri_ag[p * n_sp + i] = row_tri_ag.get(p * n_sp + i, 0.0) - min_agave
            row_tri_ag[q * n_sp + i] = row_tri_ag.get(q * n_sp + i, 0.0) - min_agave
            row_tri_ag[r * n_sp + i] = row_tri_ag.get(r * n_sp + i, 0.0) - min_agave
        constrs_rows.append(row_tri_ag)
        lhs_list.append(-min_agave)
        rhs_list.append(np.inf)

    # Conversión a matriz dispersa CSC
    n_constrs = len(constrs_rows)
    A_dok = dok_matrix((n_constrs, total_vars), dtype=np.float64)
    for r_idx, r_dict in enumerate(constrs_rows):
        for col_idx, val in r_dict.items():
            A_dok[r_idx, col_idx] = val
    A_csc = A_dok.tocsc()

    res_highs = milp(
        c=c_vec,
        integrality=integrality,
        constraints=LinearConstraint(A_csc, np.array(lhs_list), np.array(rhs_list)),
        bounds=Bounds(lb_bounds, ub_bounds),
        options={"time_limit": float(time_limit), "disp": False},
    )

    t_highs = time.perf_counter() - t_highs_0
    if res_highs.x is not None:
        sol = np.zeros(m, dtype=int)
        for p in range(m):
            sp_vals = [res_highs.x[p * n_sp + i] for i in range(n_sp)]
            sol[p] = int(np.argmax(sp_vals))

        cost_highs_comp = evaluate_assignment_cost(
            sol, graph, Phi, cost_mxn=k_i, mu_cost=mu_cost, fixed_nodes=fixed_nodes
        )
        cost_ws_comp = evaluate_assignment_cost(
            warm_assignment, graph, Phi, cost_mxn=k_i, mu_cost=mu_cost, fixed_nodes=fixed_nodes
        )

        if cost_highs_comp <= cost_ws_comp + 1e-6:
            best_sol, best_cost = sol, cost_highs_comp
        else:
            best_sol, best_cost = warm_assignment, cost_ws_comp

        best_bound = float(res_highs.mip_dual_bound) if hasattr(res_highs, "mip_dual_bound") and res_highs.mip_dual_bound is not None else 0.0
        real_gap = 100.0 * (best_cost - best_bound) / max(1e-6, abs(best_cost))
        real_gap = max(0.0, float(real_gap))
        solver_tag = f"HiGHS Branch-and-Cut ({cpu_threads} hilos)"
        solver_logger.info(
            f"HiGHS Optimizado en {t_highs:.2f}s | ObjVal={best_cost:.4f} | BestBound={best_bound:.4f} | MIPGap={real_gap:.2f}%"
        )
        return best_sol, best_cost, best_bound, real_gap, solver_tag

    # Si el tiempo expiró sin solución entera nueva, retornar warmstart pero registrando cota auténtica
    best_bound = float(getattr(res_highs, "mip_dual_bound", 0.0) or 0.0)
    real_gap = 100.0 * (cost_ws - best_bound) / max(1e-6, abs(cost_ws))
    real_gap = max(0.0, float(real_gap))
    return warm_assignment, cost_ws, best_bound, real_gap, f"HiGHS WarmStart ({cpu_threads} hilos)"


# Alias para compatibilidad con código existente
solve_exact_ryzen6800h = solve_reforestation_mip


# ==============================================================================
# 10. DESCOMPOSICIÓN DE DOMINIO ESPACIAL (SPATIAL TILING / RED-BLACK SWEEPS)
# ==============================================================================

class SpatialTiler:
    """Implementa descomposición de dominios espaciales en retículas rectangulares tresbolillo
    mediante barridos en tablero de ajedrez (Red-Black sweeps) e intercambio de condiciones de frontera (Halo).
    """

    def __init__(
        self,
        tile_rows: int = 6,
        tile_cols: int = 11,
        slope_pct: float = 6.0,
        ring_level: int = 1,
        big_index: int = 0,
    ):
        self.tile_rows = tile_rows
        self.tile_cols = tile_cols
        self.slope_pct = slope_pct
        self.ring_level = ring_level
        self.big_index = big_index
        _, self.density_per_ha = get_target_density(slope_pct)

    def solve_tiled(
        self,
        global_rows: int,
        global_cols: int,
        df_sp: pd.DataFrame,
        Phi: np.ndarray,
        time_limit_per_tile: int = 60,
        cpu_threads: int = 14,
        tolerance_pct: float = 0.0,
    ) -> Tuple[np.ndarray, HexGridGraph, Dict[str, Any]]:
        """Ejecuta la optimización dividiendo el terreno en teselas coordinadas."""
        global_graph = build_tres_bolillos_graph(
            global_rows, global_cols, density_per_ha=self.density_per_ha, ring_level=self.ring_level, big_index=self.big_index
        )
        total_m = global_rows * global_cols
        global_assignment = np.zeros(total_m, dtype=int)

        n_tiles_r = math.ceil(global_rows / self.tile_rows)
        n_tiles_c = math.ceil(global_cols / self.tile_cols)
        logger.info(
            f"Tiling Espacial Activado: Malla Global {global_rows}x{global_cols} (|P|={total_m}) "
            f"particionada en {n_tiles_r}x{n_tiles_c} = {n_tiles_r * n_tiles_c} teselas de {self.tile_rows}x{self.tile_cols}."
        )

        tile_proportions = df_sp["proporcion_programa"].to_numpy(dtype=np.float64)
        tile_nodes = self.tile_rows * self.tile_cols
        tile_quotas = compute_exact_quotas(tile_proportions, tile_nodes)

        tile_graph = build_tres_bolillos_graph(
            self.tile_rows, self.tile_cols, density_per_ha=self.density_per_ha, ring_level=self.ring_level, big_index=self.big_index
        )

        # Fase 1: Resolver teselas Rojas ((tr + tc) % 2 == 0)
        logger.info("Fase 1: Resolviendo teselas Rojas (independientes)...")
        for tr in range(n_tiles_r):
            for tc in range(n_tiles_c):
                if (tr + tc) % 2 == 0:
                    warm_tile, _ = gpu_parallel_annealing_warmstart(
                        tile_graph, Phi, tile_quotas, n_replicas=256, n_steps=3000
                    )
                    opt_tile, _, _, _, _ = solve_reforestation_mip(
                        tile_graph, Phi, tile_quotas, warm_tile,
                        time_limit=time_limit_per_tile, cpu_threads=cpu_threads, tolerance_pct=tolerance_pct, df_sp=df_sp
                    )
                    # Mapear a la cuadrícula global
                    for lr in range(self.tile_rows):
                        gr = tr * self.tile_rows + lr
                        if gr >= global_rows:
                            continue
                        for lc in range(self.tile_cols):
                            gc = tc * self.tile_cols + lc
                            if gc >= global_cols:
                                continue
                            global_assignment[gr * global_cols + gc] = opt_tile[lr * self.tile_cols + lc]

        # Fase 2: Resolver teselas Negras ((tr + tc) % 2 == 1) con condiciones de frontera (Halo)
        logger.info("Fase 2: Resolviendo teselas Negras acopladas mediante Halo de frontera...")
        for tr in range(n_tiles_r):
            for tc in range(n_tiles_c):
                if (tr + tc) % 2 == 1:
                    # 1. Identificar nodos núcleo de la tesela
                    core_global = []
                    for lr in range(self.tile_rows):
                        gr = tr * self.tile_rows + lr
                        if gr >= global_rows:
                            continue
                        for lc in range(self.tile_cols):
                            gc = tc * self.tile_cols + lc
                            if gc >= global_cols:
                                continue
                            core_global.append(gr * global_cols + gc)
                    core_set = set(core_global)
                    n_core = len(core_global)
                    if n_core == 0:
                        continue

                    # 2. Identificar nodos halo (adyacentes en teselas Rojas resueltas)
                    halo_global_set = set()
                    for e in range(len(global_graph.edge_u)):
                        u, v = int(global_graph.edge_u[e]), int(global_graph.edge_v[e])
                        if u in core_set and v not in core_set:
                            halo_global_set.add(v)
                        elif v in core_set and u not in core_set:
                            halo_global_set.add(u)
                    halo_global = sorted(list(halo_global_set))
                    n_halo = len(halo_global)

                    # 3. Construir subgrafo local (núcleo + halo)
                    node_map = {g: idx for idx, g in enumerate(core_global)}
                    for j, g in enumerate(halo_global):
                        node_map[g] = n_core + j
                    sub_m = n_core + n_halo

                    sub_coords = np.zeros((sub_m, 2), dtype=np.float64)
                    for g, l_idx in node_map.items():
                        sub_coords[l_idx] = global_graph.coords[g]

                    sub_u, sub_v, sub_d, sub_w = [], [], [], []
                    for e in range(len(global_graph.edge_u)):
                        u, v = int(global_graph.edge_u[e]), int(global_graph.edge_v[e])
                        if u in node_map and v in node_map:
                            if u in core_set or v in core_set:
                                sub_u.append(node_map[u])
                                sub_v.append(node_map[v])
                                sub_d.append(global_graph.edge_dist[e])
                                sub_w.append(global_graph.edge_weight[e])

                    sub_big_mask = np.zeros(sub_m, dtype=bool)
                    for g, l_idx in node_map.items():
                        sub_big_mask[l_idx] = global_graph.big_mask[g]

                    sub_graph = HexGridGraph(
                        sub_coords,
                        np.array(sub_u, dtype=int),
                        np.array(sub_v, dtype=int),
                        np.array(sub_d, dtype=np.float64),
                        np.array(sub_w, dtype=np.float64),
                        global_graph.step_d,
                        global_graph.r_crit,
                        big_mask=sub_big_mask,
                        big_index=self.big_index
                    )

                    # 4. Fijar especies en los nodos halo
                    halo_fixed_nodes = {n_core + j: int(global_assignment[g]) for j, g in enumerate(halo_global)}
                    halo_E_i = np.zeros(len(tile_quotas), dtype=int)
                    for sp in halo_fixed_nodes.values():
                        halo_E_i[sp] += 1

                    # Ajustar cuotas para los nodos núcleo
                    if n_core == tile_nodes:
                        core_quotas = tile_quotas
                    else:
                        core_quotas = compute_exact_quotas(tile_proportions, n_core)
                    sub_quotas = core_quotas + halo_E_i

                    # 5. Warmstart
                    warm_core, _ = gpu_parallel_annealing_warmstart(
                        tile_graph, Phi, core_quotas, n_replicas=256, n_steps=3000
                    ) if n_core == tile_nodes else (np.repeat(np.arange(len(core_quotas)), core_quotas)[:n_core], 0.0)

                    warm_sub = np.zeros(sub_m, dtype=int)
                    warm_sub[:n_core] = warm_core[:n_core]
                    for l_idx, sp in halo_fixed_nodes.items():
                        warm_sub[l_idx] = sp

                    # 6. Optimización exacta acoplada
                    opt_sub, _, _, _, _ = solve_reforestation_mip(
                        sub_graph, Phi, sub_quotas, warm_sub,
                        fixed_nodes=halo_fixed_nodes,
                        tolerance_pct=tolerance_pct, df_sp=df_sp, E_i=halo_E_i,
                        time_limit=time_limit_per_tile, cpu_threads=cpu_threads,
                        solver_name="highs", mu_cost=0.0005
                    )

                    # 7. Asignar exclusivamente los nodos núcleo a la cuadrícula global
                    for k in range(n_core):
                        global_assignment[core_global[k]] = opt_sub[k]

        metrics = audit_ecological_metrics(global_assignment, global_graph, Phi, df_sp, {})
        return global_assignment, global_graph, metrics



# ==============================================================================
# 11. EXPORTACIÓN DE VISUALIZACIONES CIENTÍFICAS Y PROYECCIÓN DE RELIEVE
# ==============================================================================

def build_relief_terrain(
    poligono_id: int = 12,
    slope_deg: float = 6.0,
    seed: int = 0,
    poli31_dir: Path = POLI31_DIR,
) -> Any:
    """Construye un objeto Terrain desde terreno.py con relieve topográfico.

    # origen: modelo_dominica, categoría a (plano SRTM 30m) y categoría b (lomerío fractal sintético)
    """
    import terreno
    from terreno import Terrain, spec_from

    poligonos_file = poli31_dir / "poligonos_31.csv"
    utm_file = poli31_dir / "poligonos_utm.csv"
    dem_pts_file = poli31_dir / "dem_srtm_puntos.csv"

    if poligonos_file.exists() and 1 <= poligono_id <= 31:
        terrain_obj = Terrain.from_poligonos(
            str(poligonos_file),
            pid=poligono_id,
            utm=str(utm_file) if utm_file.exists() else None,
            dem_pts=str(dem_pts_file) if dem_pts_file.exists() else None,
            slope_deg=slope_deg,
            seed=seed,
        )
        terrain_obj.zonas(pend_pct=20.0, min_ha=0.10)
    else:
        spec = spec_from("mixto", slope_deg=slope_deg, seed=seed)
        terrain_obj = Terrain(spec)
        terrain_obj.zonas(pend_pct=20.0, min_ha=0.10)

    return terrain_obj


def fit_graph_coords_to_polygon(
    graph_coords: np.ndarray,
    terrain: Any,
) -> Tuple[np.ndarray, float, Tuple[float, float]]:
    """Encaja e interpola las coordenadas de la malla dentro del interior del polígono `terrain.polygon`.

    Busca una traslación (dx, dy) y escala s <= 1.0 que maximice la cantidad de nodos
    que caen estrictamente dentro de terrain.polygon.
    """
    coords = np.asarray(graph_coords, dtype=np.float64)
    if terrain.polygon is None:
        cx_t, cy_t = terrain.width / 2.0, terrain.height / 2.0
        cx_m = (coords[:, 0].min() + coords[:, 0].max()) / 2.0
        cy_m = (coords[:, 1].min() + coords[:, 1].max()) / 2.0
        shift = (cx_t - cx_m, cy_t - cy_m)
        return coords + list(shift), 1.0, shift

    poly = terrain.polygon
    min_px, max_px = poly[:, 0].min(), poly[:, 0].max()
    min_py, max_py = poly[:, 1].min(), poly[:, 1].max()

    m_w = coords[:, 0].max() - coords[:, 0].min()
    m_h = coords[:, 1].max() - coords[:, 1].min()

    best_count = -1
    best_scale = 1.0
    best_shift = (0.0, 0.0)

    for scale in [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]:
        sc_coords = coords * scale
        sc_w = m_w * scale
        sc_h = m_h * scale

        if sc_w > (max_px - min_px) or sc_h > (max_py - min_py):
            continue

        xs = np.linspace(min_px, max_px - sc_w, 40)
        ys = np.linspace(min_py, max_py - sc_h, 40)

        for dx in xs:
            for dy in ys:
                test_p = sc_coords + [dx - sc_coords[:, 0].min(), dy - sc_coords[:, 1].min()]
                inside_flags = terrain.inside(test_p)
                c_in = int(inside_flags.sum())
                if c_in > best_count:
                    best_count = c_in
                    best_scale = scale
                    best_shift = (dx - sc_coords[:, 0].min(), dy - sc_coords[:, 1].min())
                    if best_count == len(coords) and scale == 1.0:
                        break
            if best_count == len(coords) and scale == 1.0:
                break
        if best_count == len(coords) and scale == 1.0:
            break

    final_coords = coords * best_scale + list(best_shift)
    return final_coords, best_scale, best_shift


def export_relief_visualization(
    df_species: pd.DataFrame,
    graph: HexGridGraph,
    assignment: np.ndarray,
    fixed_nodes: Dict[int, int],
    terrain: Any,
    suffix: str = "",
    poligono_id: int = 12,
) -> None:
    """Proyecta la asignación en tres bolillos sobre el relieve (curvas de nivel y sombreado de terreno.py).

    # origen: modelo_dominica, categoría a (plano SRTM 30m) y categoría b (lomerío fractal sintético)
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    from matplotlib.patches import Polygon as MplPolygon

    fig, ax = plt.subplots(figsize=(11, 8.5), dpi=200)

    # 1. Transformar y encajar coordenadas de la malla dentro del polígono
    proj_coords, scale_used, shift_used = fit_graph_coords_to_polygon(graph.coords, terrain)

    # 2. Sombreado topográfico
    ax.set_facecolor("#d0d0d0")
    ls = LightSource(azdeg=315, altdeg=40)
    rgb_shade = ls.shade(terrain.elev, cmap=plt.get_cmap("terrain"), vert_exag=1.5, blend_mode="overlay")

    xs = (np.arange(terrain.nx) + 0.5) * terrain.cx
    ys = (np.arange(terrain.ny) + 0.5) * terrain.cy

    if terrain.polygon is not None:
        gx_, gy_ = np.meshgrid(xs, ys)
        in_mask = terrain.inside(np.c_[gx_.ravel(), gy_.ravel()]).reshape(terrain.ny, terrain.nx)
        rgb_masked = np.copy(rgb_shade)
        rgb_masked[~in_mask] = [0.81, 0.81, 0.81, 1.0]
        ax.imshow(rgb_masked, origin="lower", extent=[0, terrain.width, 0, terrain.height], zorder=1)

        poly_patch = MplPolygon(
            terrain.polygon, closed=True, facecolor="none", edgecolor="#333333", linewidth=1.8, zorder=5
        )
        ax.add_patch(poly_patch)
    else:
        ax.imshow(rgb_shade, origin="lower", extent=[0, terrain.width, 0, terrain.height], zorder=1)

    # 3. Curvas de nivel cada 1 m
    z_min, z_max = float(np.nanmin(terrain.elev)), float(np.nanmax(terrain.elev))
    step = 1.0 if (z_max - z_min <= 25.0) else (2.0 if (z_max - z_min <= 60.0) else 5.0)
    levels = np.arange(np.floor(z_min), np.ceil(z_max) + step, step)

    cs = ax.contour(xs, ys, terrain.elev, levels=levels, colors="k", linewidths=0.4, alpha=0.45, zorder=2)
    ax.clabel(cs, inline=True, fontsize=6, fmt="%.0f", colors="#222222")

    # 4. Zonas con pendiente >= 20% (zone > 0)
    if hasattr(terrain, "zone") and terrain.zone is not None:
        steep_mask = (terrain.zone > 0)
        if terrain.polygon is not None:
            steep_mask = steep_mask & in_mask
        if np.any(steep_mask):
            steep_overlay = np.zeros((*terrain.elev.shape, 4), dtype=np.float32)
            steep_overlay[steep_mask] = [0.84, 0.19, 0.12, 0.35]
            ax.imshow(steep_overlay, origin="lower", extent=[0, terrain.width, 0, terrain.height], zorder=3)
            ax.contour(xs, ys, steep_mask, levels=[0.5], colors=["#b30000"], linewidths=1.2, linestyles="--", zorder=3)

    # 5. Aristas de la malla
    for e in range(len(graph.edge_u)):
        u, v = int(graph.edge_u[e]), int(graph.edge_v[e])
        ax.plot(
            [proj_coords[u, 0], proj_coords[v, 0]],
            [proj_coords[u, 1], proj_coords[v, 1]],
            color="#333333", linewidth=0.8, alpha=0.7, zorder=6
        )

    # 6. Nodos coloreados por especie
    cmap = plt.get_cmap("tab10")
    for _, row in df_species.iterrows():
        sp_id = int(row["id"])
        mask = (assignment == sp_id)
        if np.any(mask):
            ax.scatter(
                proj_coords[mask, 0],
                proj_coords[mask, 1],
                s=150,
                color=cmap(sp_id),
                edgecolors="black",
                linewidths=0.8,
                label=f"{row['especie']} (n={mask.sum()})",
                zorder=7,
            )

    # 7. Plantas preexistentes E_i
    if fixed_nodes:
        f_idx = list(fixed_nodes.keys())
        ax.scatter(
            proj_coords[f_idx, 0],
            proj_coords[f_idx, 1],
            s=260,
            facecolors="none",
            edgecolors="red",
            linewidths=2.2,
            label=f"Planta Preexistente E_i (n={len(f_idx)})",
            zorder=8,
        )

    ax.set_aspect("equal")
    ax.set_xlabel("Distancia Local X (m)")
    ax.set_ylabel("Distancia Local Y (m)")

    title_tag = suffix.replace("_", " ").strip() if suffix else "0% Holgura"
    poly_str = f"Polígono {poligono_id}" if terrain.polygon is not None else "Terreno Rectangular"
    ax.set_title(
        f"Asignación Óptima Tres Bolillos sobre Relieve ({poly_str} | {title_tag})",
        fontsize=11, pad=12
    )

    caption_text = (
        "Plano regional: SRTM 30 m real (5 pts) | Relieve local y curvas de nivel: lomerío fractal sintético (terreno.py)\n"
        "Área roja punteada: Pendiente ≥ 20% (Norma CONAFOR)"
    )
    plt.figtext(
        0.5, 0.01, caption_text, ha="center", fontsize=8,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f0f0", edgecolor="#cccccc", alpha=0.9)
    )

    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8.5, frameon=True)
    plt.tight_layout(rect=[0, 0.05, 1, 1])

    out_name = f"mapa_tres_bolillos_relieve{suffix}.png" if suffix else "mapa_tres_bolillos_relieve.png"
    plt.savefig(OUT_DIR / out_name)
    plt.close()


def export_visualizations(
    df_species: pd.DataFrame,
    Phi: np.ndarray,
    graph: HexGridGraph,
    assignment: np.ndarray,
    fixed_nodes: Dict[int, int],
    suffix: str = "",
    terrain: Optional[Any] = None,
    poligono_id: int = 12,
) -> None:
    """Genera mapas espaciales en tres bolillos y mapas térmicos de competencia Phi."""
    if suffix == "" or suffix == "_0pct":
        fig, ax = plt.subplots(figsize=(9, 7.5), dpi=200)
        im = ax.imshow(Phi, cmap="YlOrRd")
        names = [f"{r['especie']} (w={r['w_vuln']:.2f})" for _, r in df_species.iterrows()]
        ax.set_xticks(range(len(names)))
        ax.set_yticks(range(len(names)))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8.5)
        ax.set_yticklabels(names, fontsize=8.5)
        for i in range(len(names)):
            for j in range(len(names)):
                ax.text(
                    j, i, f"{Phi[i, j]:.2f}",
                    ha="center", va="center",
                    color="white" if Phi[i, j] > 0.85 else "black",
                    fontsize=7.5,
                )
        plt.colorbar(im, ax=ax, label="Penalización Efectiva $\\Phi_{ij} = c_{ij}(w_i+w_j)/2$")
        ax.set_title("Matriz de Competencia Ponderada por Inverso de Supervivencia 2023", fontsize=11, pad=12)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "matriz_competencia_phi.png")
        plt.close()

    fig, ax = plt.subplots(figsize=(11, 7.5), dpi=200)
    for e in range(len(graph.edge_u)):
        u, v = int(graph.edge_u[e]), int(graph.edge_v[e])
        ax.plot(
            [graph.coords[u, 0], graph.coords[v, 0]],
            [graph.coords[u, 1], graph.coords[v, 1]],
            color="#cccccc", linewidth=0.8, zorder=1,
        )

    cmap = plt.get_cmap("tab10")
    for _, row in df_species.iterrows():
        sp_id = int(row["id"])
        mask = (assignment == sp_id)
        if np.any(mask):
            ax.scatter(
                graph.coords[mask, 0],
                graph.coords[mask, 1],
                s=160,
                color=cmap(sp_id),
                edgecolors="black",
                linewidths=0.8,
                label=f"{row['especie']} (n={mask.sum()})",
                zorder=3,
            )

    if fixed_nodes:
        f_idx = list(fixed_nodes.keys())
        ax.scatter(
            graph.coords[f_idx, 0],
            graph.coords[f_idx, 1],
            s=280,
            facecolors="none",
            edgecolors="red",
            linewidths=2.2,
            label=f"Planta Preexistente E_i (n={len(f_idx)})",
            zorder=4,
        )

    ax.set_aspect("equal")
    ax.set_xlabel("Distancia Longitudinal X (m)")
    ax.set_ylabel("Distancia Transversal Y (m)")
    title_tag = suffix.replace("_", " ").strip() if suffix else "0% Holgura"
    ax.set_title(f"Distribución Óptima en Malla 2D Tres Bolillos ({title_tag})", fontsize=11)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8.5, frameon=True)
    plt.tight_layout()
    out_name = f"mapa_tres_bolillos_optimo{suffix}.png" if suffix else "mapa_tres_bolillos_optimo.png"
    plt.savefig(OUT_DIR / out_name)
    plt.close()

    if terrain is not None:
        export_relief_visualization(
            df_species, graph, assignment, fixed_nodes, terrain, suffix=suffix, poligono_id=poligono_id
        )




# ==============================================================================
# 12. EJECUCIÓN PRINCIPAL Y CLI COMPLETO (RELEVO Y MULTI-ESCENARIOS)
# ==============================================================================

def main() -> None:
    default_threads = max(1, (os.cpu_count() or 16) - 2)

    parser = argparse.ArgumentParser(
        description="Pipeline REFORESTATHON Robustificado (MIP Dual + ZOI Epanechnikov + CONAFOR)"
    )
    parser.add_argument("--rows", type=int, default=6, help="Filas de la malla tresbolillo")
    parser.add_argument("--cols", type=int, default=11, help="Columnas de la malla tresbolillo")
    parser.add_argument("--ring", type=int, default=1, choices=[1, 2], help="Anillo de vecindad N(p)")
    parser.add_argument("--time-limit", type=int, default=90, help="Tiempo límite del solver (s)")
    parser.add_argument("--threads", type=int, default=default_threads, help="Hilos de CPU para el solver")
    parser.add_argument("--poligono-id", type=int, default=0, help="ID del polígono censado (1..31) o 0 para promedio")
    parser.add_argument("--poligonos-dir", type=str, default=None, help="Directorio de datos de polígonos (e.g. data/poli31)")
    parser.add_argument("--polygon-ha", type=float, default=1.0, help="Hectáreas si --poligono-id es 0")
    parser.add_argument("--slope-pct", "--slope", type=float, default=6.0, help="Pendiente del terreno (%%) para CONAFOR Eq. 1")
    parser.add_argument("--relief-slope-deg", type=float, default=6.0, help="Pendiente media del lomerío sintético en grados (default: 6.0° ~ 10.5%%, modelo_dominica §19.11)")
    parser.add_argument("--solver", type=str, default="highs", choices=["highs", "gurobi", "auto"], help="Backend del solver MIP")
    parser.add_argument("--mu", type=float, default=0.0005, help="Precio sombra presupuestal (Ecs. 4, 8, 9)")
    parser.add_argument("--tiling", action="store_true", help="Activar descomposición de dominio espacial (tiling)")
    parser.add_argument("--tile-rows", type=int, default=6, help="Filas por tesela si --tiling está activo")
    parser.add_argument("--tile-cols", type=int, default=11, help="Columnas por tesela si --tiling está activo")
    parser.add_argument("--big-index", type=int, default=0, help="Índice de subred para especies grandes (7,8,9): 0=desactivado (default), 3=1 de cada 3 nodos")
    parser.add_argument("--plot-relief", action="store_true", help="Proyectar gráficos de asignación sobre el relieve (curvas de nivel y sombreado de terreno.py)")
    parser.add_argument("--relief-poligono-id", type=int, default=12, help="ID del polígono de poli31 (1..31) para recortar el relieve cuando --poligono-id es 0 (default: 12)")
    args = parser.parse_args()

    logger.info("=== INICIANDO PIPELINE REFORESTATHON (RYZEN 7 6800H + RTX 3060) ===")
    if torch.cuda.is_available():
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        logger.info(f"GPU Activa: {torch.cuda.get_device_name(0)} ({vram_gb:.1f} GB VRAM, CUDA {torch.version.cuda})")
    logger.info(f"Hilos de CPU asignados: {args.threads} | Solver seleccionado: {args.solver} | Pendiente: {args.slope_pct}%")

    poligonos_dir = args.poligonos_dir
    if poligonos_dir is None and args.poligono_id == 31:
        poligonos_dir = POLI31_DIR

    # Construir objeto Terrain si se solicita proyección sobre relieve
    relief_pid = args.poligono_id if (1 <= args.poligono_id <= 31) else args.relief_poligono_id
    terrain_obj = None
    if args.plot_relief:
        relief_dir = Path(poligonos_dir) if poligonos_dir is not None else POLI31_DIR
        if not (relief_dir / "poligonos_31.csv").exists():
            relief_dir = POLI31_DIR
        logger.info(
            f"Construyendo terreno topográfico para Polígono ID={relief_pid} "
            f"(slope_deg={args.relief_slope_deg}° ~ {math.tan(math.radians(args.relief_slope_deg))*100:.1f}% pendiente media)..."
        )
        terrain_obj = build_relief_terrain(
            poligono_id=relief_pid,
            slope_deg=args.relief_slope_deg,
            seed=42,
            poli31_dir=relief_dir,
        )

    # 1. Cargar datos desde data/semiraw/ o poli31/
    df_cat, df_wide, baseline_row_22 = load_semiraw_datasets(poligonos_dir=poligonos_dir)

    target_density_val, density_ref_ha = get_target_density(args.slope_pct, args.polygon_ha)
    logger.info(
        f"Topografía CONAFOR (Pendiente {args.slope_pct}%): "
        f"Densidad Objetivo N_z = {target_density_val} pl ({density_ref_ha:.0f} pl/ha)."
    )

    if 1 <= args.poligono_id <= len(df_wide):
        poly_row = df_wide[df_wide["poligono_id"] == args.poligono_id].iloc[0]
        target_ha = float(poly_row["dimension_ha"])
        logger.info(f"Simulando {poly_row['poligono']} (ID={args.poligono_id}, Área={target_ha:.2f} Ha)")
    else:
        target_ha = args.polygon_ha
        logger.info(f"Simulando predio estándar de {target_ha:.2f} Ha")

    # 2. Construir matrices ecológicas y pesos empíricos de supervivencia 2023
    df_sp, C_norm, Phi = build_ecological_matrices(df_cat, lam=1.0, slope_pct=args.slope_pct, density_per_ha=density_ref_ha)
    logger.info(
        "\nCatálogo Consolidado y Calibración Ecológica:\n"
        + df_sp[[
            "especie", "nombre_comun", "costo_vivero_mxn", "supervivencia_2023_pct", "v_water_sens", "w_vuln"
        ]].to_string(index=False)
    )

    # 3. Simulación Monte Carlo en GPU con costos diferenciados
    df_mc = run_monte_carlo_rtx3060(
        df_sp, df_wide, target_area_ha=target_ha, n_sims=1_000_000, slope_pct=args.slope_pct
    )
    logger.info(
        f"\nResultados Monte Carlo de Compra ({target_ha:.2f} Ha, Gasto Estimado = ${df_mc['costo_esp_MXN'].sum():,.2f} MXN):\n"
        + df_mc[[
            "especie", "requerimiento_ri", "existencia_media_Ei", "compra_esperada_E_Fi",
            "costo_unitario_MXN", "costo_esp_MXN", "pedido_seguro_Q95"
        ]].to_string(index=False)
    )

    # 4. Modo Tiling (Descomposición de dominio multi-hectárea)
    if args.tiling or (args.rows * args.cols > 150):
        tiler = SpatialTiler(
            tile_rows=args.tile_rows,
            tile_cols=args.tile_cols,
            slope_pct=args.slope_pct,
            ring_level=args.ring,
            big_index=args.big_index,
        )
        tiled_assignment, tiled_graph, tiled_metrics = tiler.solve_tiled(
            global_rows=args.rows,
            global_cols=args.cols,
            df_sp=df_sp,
            Phi=Phi,
            time_limit_per_tile=args.time_limit,
            cpu_threads=args.threads,
        )
        logger.info(f"Métricas Globales Dominio Tiled: Supervivencia={tiled_metrics['surv_eff_pct']:.2f}% | Contactos Nodriza={tiled_metrics['nurse_contacts']}")

    # 5. Benchmark 1D sobre orden_plantacion_100m.csv (22 posiciones)
    graph_1d = build_tres_bolillos_graph(
        n_rows=1, n_cols=len(baseline_row_22), density_per_ha=density_ref_ha, ring_level=1
    )
    base_arr = np.array(baseline_row_22, dtype=int)
    base_cost_1d = evaluate_assignment_cost(base_arr, graph_1d, Phi)
    quotas_22 = np.bincount(base_arr, minlength=len(df_sp))
    warm_1d, _ = gpu_parallel_annealing_warmstart(graph_1d, Phi, quotas_22, n_replicas=512, n_steps=3000)
    opt_1d, opt_cost_1d, bound_1d, gap_1d, solver_1d_tag = solve_reforestation_mip(
        graph_1d, Phi, quotas_22, warm_1d, tolerance_pct=0.0, df_sp=df_sp,
        time_limit=20, cpu_threads=args.threads, solver_name=args.solver, mu_cost=args.mu
    )
    logger.info(
        f"\n[Benchmark orden_plantacion_100m.csv ({solver_1d_tag})] Costo Original = {base_cost_1d:.4f} | "
        f"Costo Óptimo = {opt_cost_1d:.4f} | BestBound = {bound_1d:.4f} | MIPGap = {gap_1d:.2f}% "
        f"(Reducción = {100.0*(base_cost_1d - opt_cost_1d)/base_cost_1d:.2f}%)"
    )

    # 6. Optimización en Malla 2D Tres Bolillos con Vegetación Preexistente y Holgura (0%, 5%, 10%)
    graph_2d = build_tres_bolillos_graph(
        n_rows=args.rows, n_cols=args.cols, density_per_ha=density_ref_ha, ring_level=args.ring, big_index=args.big_index
    )
    m_nodes = args.rows * args.cols
    proportions = df_sp["proporcion_programa"].to_numpy(dtype=np.float64)
    quotas_2d = compute_exact_quotas(proportions, m_nodes)

    fixed_nodes_2d, E_i_2d = build_real_preexisting_nodes_from_csv(
        df_sp, df_wide, graph_2d, quotas_2d,
        poligono_id=args.poligono_id, density_per_ha=density_ref_ha, seed=42
    )

    # Costo base aleatorio respetando plantas fijas
    rng = np.random.default_rng(123)
    rem_q_init = np.maximum(0, quotas_2d - E_i_2d)
    free_pos_init = [p for p in range(m_nodes) if p not in fixed_nodes_2d]
    rand_assign = np.zeros(m_nodes, dtype=int)
    for p, sp in fixed_nodes_2d.items():
        rand_assign[p] = sp

    if args.big_index > 1 and graph_2d.big_mask is not None:
        big_sp_list = []
        for sp in BIG_SPECIES_IDS:
            big_sp_list.extend([sp] * rem_q_init[sp])
        other_sp_list = []
        for sp in range(len(df_sp)):
            if sp not in BIG_SPECIES_IDS:
                other_sp_list.extend([sp] * rem_q_init[sp])
        rng.shuffle(big_sp_list)
        rng.shuffle(other_sp_list)
        free_big = [p for p in free_pos_init if graph_2d.big_mask[p]]
        free_nonbig = [p for p in free_pos_init if not graph_2d.big_mask[p]]
        rng.shuffle(free_big)
        rng.shuffle(free_nonbig)
        
        assignments = {}
        for sp in big_sp_list:
            if free_big: assignments[free_big.pop()] = sp
            elif free_nonbig: assignments[free_nonbig.pop()] = sp
        for sp in other_sp_list:
            if free_big: assignments[free_big.pop()] = sp
            elif free_nonbig: assignments[free_nonbig.pop()] = sp
            
        for p, sp in assignments.items():
            rand_assign[p] = sp
    else:
        rand_pool = np.repeat(np.arange(len(df_sp)), rem_q_init)
        rand_assign[free_pos_init] = rng.permutation(rand_pool[:len(free_pos_init)])
    init_cost_2d = evaluate_assignment_cost(rand_assign, graph_2d, Phi)

    comparativa_rows = []
    slack_levels = [0.00, 0.05, 0.10]

    for tol in slack_levels:
        tag_pct = int(round(tol * 100))
        logger.info(
            "\n" + "=" * 80 +
            f"\n>>> EJECUTANDO MALLA 2D ({args.rows}x{args.cols}) | ESCENARIO HOLGURA +/- {tag_pct}%\n" +
            "=" * 80
        )

        lb_i, ub_i, q_warm_target = compute_flexible_bounds_and_warm_quotas(
            df_sp, m_nodes, quotas_2d, E_i_2d, tolerance_pct=tol
        )
        logger.info(
            f"Cotas [L_i, U_i] (+/-{tag_pct}%): "
            + ", ".join(f"{df_sp.loc[i, 'especie'].split()[1][:4]}:[{lb_i[i]},{ub_i[i]}]" for i in range(len(df_sp)))
        )

        warm_2d, warm_cost_2d = gpu_parallel_annealing_warmstart(
            graph_2d, Phi, q_warm_target, fixed_nodes=fixed_nodes_2d, n_replicas=1024, n_steps=8000
        )

        opt_2d, exact_cost_2d, best_bound_2d, gap_2d, solver_used = solve_reforestation_mip(
            graph_2d, Phi, quotas_2d, warm_2d,
            fixed_nodes=fixed_nodes_2d, tolerance_pct=tol, df_sp=df_sp, E_i=E_i_2d,
            time_limit=args.time_limit, cpu_threads=args.threads, solver_name=args.solver, mu_cost=args.mu
        )

        metrics = audit_ecological_metrics(opt_2d, graph_2d, Phi, df_sp, fixed_nodes_2d)

        logger.info(
            f"[Resultado +/-{tag_pct}% | {solver_used}] Aleatorio = {init_cost_2d:.4f} | "
            f"Warm-Start GPU = {warm_cost_2d:.4f} | Exacto Compuesto Z = {exact_cost_2d:.4f} (Phi = {metrics['comp_total']:.4f}) | "
            f"BestBound = {best_bound_2d:.4f} | MIPGap = {gap_2d:.2f}% "
            f"(Reducción Competencia: {100.0*(init_cost_2d - metrics['comp_total'])/init_cost_2d:.2f}%)"
        )
        logger.info(
            f"[Ecología +/-{tag_pct}%] Supervivencia Base = {metrics['surv_base_pct']:.2f}% | "
            f"Supervivencia Efectiva = {metrics['surv_eff_pct']:.2f}% | "
            f"Nodrizas = {metrics['nurse_contacts']} | Intra = {metrics['intra_contacts']} | "
            f"Agave-Agave = {metrics['agave_contacts']} | Gasto Vivero = ${metrics['gasto_vivero_mxn']:.2f} MXN"
        )

        df_out = pd.DataFrame({
            "posicion_p": np.arange(m_nodes),
            "x_m": np.round(graph_2d.coords[:, 0], 2),
            "y_m": np.round(graph_2d.coords[:, 1], 2),
            "especie_id": opt_2d,
            "especie": [df_sp.loc[i, "especie"] for i in opt_2d],
            "nombre_comun": [df_sp.loc[i, "nombre_comun"] for i in opt_2d],
            "costo_vivero_mxn": [df_sp.loc[i, "costo_vivero_mxn"] for i in opt_2d],
            "supervivencia_2023_pct": [df_sp.loc[i, "supervivencia_2023_pct"] for i in opt_2d],
            "es_preexistente": [p in fixed_nodes_2d for p in range(m_nodes)],
        })

        if tag_pct == 0:
            df_out.to_csv(OUT_DIR / "asignacion_optima_2d.csv", index=False)
            export_visualizations(
                df_sp, Phi, graph_2d, opt_2d, fixed_nodes_2d, suffix="",
                terrain=terrain_obj, poligono_id=relief_pid
            )

        df_out.to_csv(OUT_DIR / f"asignacion_optima_2d_holgura_{tag_pct}pct.csv", index=False)
        export_visualizations(
            df_sp, Phi, graph_2d, opt_2d, fixed_nodes_2d, suffix=f"_{tag_pct}pct",
            terrain=terrain_obj, poligono_id=relief_pid
        )

        comparativa_rows.append({
            "Escenario": f"Holgura +/- {tag_pct}%",
            "Preexistentes_Fijas_Ei": metrics["fixed_count"],
            "Costo_Aleatorio": round(init_cost_2d, 4),
            "Costo_WarmStart_GPU": round(warm_cost_2d, 4),
            "Costo_Optimo_Compuesto_Z": round(exact_cost_2d, 4),
            "Costo_Optimo_Phi": round(metrics["comp_total"], 4),
            "BestBound_Teorico": round(best_bound_2d, 4),
            "MIPGap_%": round(gap_2d, 2),
            "Reduccion_Competencia_%": round(100.0 * (init_cost_2d - metrics["comp_total"]) / init_cost_2d, 2),
            "Supervivencia_Base_2023_%": round(metrics["surv_base_pct"], 2),
            "Supervivencia_Efectiva_Espacial_%": round(metrics["surv_eff_pct"], 2),
            "Interacciones_Nodriza": metrics["nurse_contacts"],
            "Contactos_Intraespecificos": metrics["intra_contacts"],
            "Contactos_Agave_Agave": metrics["agave_contacts"],
            "Mezquites_Totales": metrics["prosopis_count"],
            "Agaves_Totales": metrics["agave_total"],
            "Gasto_Vivero_MXN": metrics["gasto_vivero_mxn"],
            "Solver_Utilizado": solver_used,
            "Cuotas_Finales": str(metrics["counts"].tolist()),
        })

    df_comp = pd.DataFrame(comparativa_rows)
    df_comp.to_csv(OUT_DIR / "comparativa_holgura_0_5_10.csv", index=False)
    logger.info(
        "\n" + "=" * 105 +
        "\nTABLA COMPARATIVA FINAL: IMPACTO DE LA HOLGURA (0% vs 5% vs 10%) Y AUDITORÍA MATEMÁTICA FORENSE\n" +
        "=" * 105 + "\n" +
        df_comp[[
            "Escenario", "Costo_Optimo_Compuesto_Z", "Costo_Optimo_Phi", "BestBound_Teorico", "MIPGap_%",
            "Supervivencia_Base_2023_%", "Supervivencia_Efectiva_Espacial_%",
            "Interacciones_Nodriza", "Contactos_Agave_Agave", "Gasto_Vivero_MXN", "Solver_Utilizado"
        ]].to_string(index=False)
    )
    logger.info(f"=== PIPELINE COMPLETADO EXITOSAMENTE. Salidas guardadas en: {OUT_DIR} ===")


if __name__ == "__main__":
    main()
