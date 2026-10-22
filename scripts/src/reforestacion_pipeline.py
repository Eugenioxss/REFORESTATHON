# -*- coding: utf-8 -*-
"""Pipeline CONAFOR sincronizado con la estructura de REFORESTATHON:

- Lee datos reales desde: REFORESTATHON/data/semiraw/*.csv
- Guarda resultados en:   REFORESTATHON/scripts/outputs/
- Guarda bitácoras en:    REFORESTATHON/scripts/logs/
Optimizado para Windows: AMD Ryzen 7 6800H (16 hilos) + 32 GB RAM + RTX 3060 (6
GB VRAM)
"""

import argparse
from dataclasses import dataclass
import gc
import logging
import math
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

# ==============================================================================
# 1. CONFIGURACIÓN DE RUTAS SEGÚN TU ÁRBOL DE DIRECTORIOS EN VS CODE
# ==============================================================================
SRC_DIR = Path(__file__).resolve().parent  # .../REFORESTATHON/scripts/src
SCRIPTS_DIR = SRC_DIR.parent  # .../REFORESTATHON/scripts
ROOT_DIR = SCRIPTS_DIR.parent  # .../REFORESTATHON
DATA_DIR = ROOT_DIR / "data" / "semiraw"  # .../REFORESTATHON/data/semiraw
OUT_DIR = SCRIPTS_DIR / "outputs"  # .../REFORESTATHON/scripts/outputs
LOG_DIR = SCRIPTS_DIR / "logs"  # .../REFORESTATHON/scripts/logs

OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / "execution.log", mode="w", encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("REFORESTATHON")

PRESUPUESTO_POR_HA = (
    13200.0  # Presupuesto de referencia en datos_inecol.xlsx ($)
)


# ==============================================================================
# 2. CARGA DE DATOS DESDE data/semiraw/
# ==============================================================================


def load_semiraw_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, List[int]]:
  """Carga catalogo_especies_consolidado.csv, poligonos_plantas_wide.csv

  y orden_plantacion_100m.csv desde REFORESTATHON/data/semiraw/.
  """
  cat_path = DATA_DIR / "catalogo_especies_consolidado.csv"
  wide_path = DATA_DIR / "poligonos_plantas_wide.csv"
  row_path = DATA_DIR / "orden_plantacion_100m.csv"

  if not (cat_path.exists() and wide_path.exists() and row_path.exists()):
    raise FileNotFoundError(
        f"No se encontraron todos los CSVs en {DATA_DIR}. "
        "Verifica la carpeta data/semiraw/."
    )

  df_cat = pd.read_csv(cat_path)
  df_wide = pd.read_csv(wide_path)
  df_row = pd.read_csv(row_path)

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

  sp_to_id: Dict[str, int] = dict(zip(df_cat["especie"], df_cat["id"]))
  baseline_row_22: List[int] = [
      sp_to_id[str(sp).strip()] for sp in df_row["especie"]
  ]

  logger.info(f"Datos cargados exitosamente desde: {DATA_DIR}")
  logger.info(
      f"Catálogo: {len(df_cat)} especies | Polígonos: {len(df_wide)} | "
      f"Fila 100m: {len(baseline_row_22)} posiciones."
  )
  return df_cat, df_wide, baseline_row_22


# ==============================================================================
# 3. MATRIZ DE COMPETENCIA c_ij EN [0,1] Y PONDERACIÓN DE SUPERVIVENCIA 2023
# ==============================================================================


def build_ecological_matrices(
    df_cat: pd.DataFrame, lam: float = 1.0
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
  """Construye la matriz de competencia base c_ij en escala [0, 1] y la pondera

  simétricamente usando el inverso de la tasa de supervivencia de 2023.
  """
  df = df_cat.copy()
  df["s_2023"] = df["supervivencia_2023_pct"] / 100.0
  df["inv_s2023"] = 1.0 / df["s_2023"]

  inv_min = float(df["inv_s2023"].min())
  inv_max = float(df["inv_s2023"].max())
  df["w_vuln"] = 1.0 + lam * (df["inv_s2023"] - inv_min) / (inv_max - inv_min)

  n = len(df)
  C_base = np.zeros((n, n), dtype=np.float64)

  for i in range(n):
    for j in range(n):
      if i == j:
        C_base[i, j] = 1.00
      elif df.loc[i, "genero"] == df.loc[j, "genero"]:
        C_base[i, j] = 0.80 if df.loc[i, "genero"] == "Agave" else 0.75
      elif (
          df.loc[i, "genero"] == "Prosopis" or df.loc[j, "genero"] == "Prosopis"
      ):
        C_base[i, j] = 0.05
      else:
        C_base[i, j] = 0.35

  w = df["w_vuln"].to_numpy(dtype=np.float64)
  Phi = C_base * (w[:, None] + w[None, :]) / 2.0
  return df, C_base, Phi


# ==============================================================================
# 4. SIMULACIÓN MONTE CARLO EN RTX 3060 PARA CANTIDAD A ADQUIRIR
# ==============================================================================


def run_monte_carlo_rtx3060(
    df_species: pd.DataFrame,
    df_wide: pd.DataFrame,
    target_area_ha: float = 1.0,
    n_sims: int = 1_000_000,
) -> pd.DataFrame:
  """Ajusta distribuciones discretas (Binomial Negativa / Poisson) a las densidades

  por hectárea observadas en los 30 polígonos y simula N escenarios en GPU.
  """
  t0 = time.perf_counter()
  dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
  if dev.type == "cuda":
    torch.backends.cuda.matmul.allow_tf32 = True

  sp_names = df_species["especie"].tolist()
  poly_ha = df_wide["dimension_ha"].to_numpy(dtype=np.float64)
  established = df_wide[sp_names].to_numpy(dtype=np.float64).T

  densities_per_ha = established / poly_ha[None, :]
  mean_dens = densities_per_ha.mean(axis=1)
  var_dens = densities_per_ha.var(axis=1, ddof=1)

  results = []
  torch.manual_seed(42)

  for _, row in df_species.iterrows():
    idx = int(row["id"])
    r_i = int(round(float(row["plantas_por_ha"]) * target_area_ha))
    mu = float(mean_dens[idx]) * target_area_ha
    sigma2 = float(var_dens[idx]) * (target_area_ha**2)

    if sigma2 > mu * 1.05:
      p_nb = mu / sigma2
      r_nb = (mu**2) / (sigma2 - mu)
      dist_name = f"NegBin(r={r_nb:.1f}, p={p_nb:.2f})"
      rate = torch.distributions.Gamma(
          concentration=torch.tensor(r_nb, device=dev, dtype=torch.float32),
          rate=torch.tensor(
              p_nb / (1.0 - p_nb), device=dev, dtype=torch.float32
          ),
      ).sample(torch.Size([n_sims]))
      E_samples = torch.poisson(rate)
    else:
      dist_name = f"Poisson(λ={mu:.1f})"
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

    results.append({
        "especie": row["especie"],
        "nombre_comun": row["nombre_comun"],
        "requerimiento_ri": r_i,
        "existencia_media_Ei": round(mu, 2),
        "distribucion_ajustada": dist_name,
        "compra_esperada_E_Fi": round(f_mean, 2),
        "IC95_inf": round(f_mean - 1.96 * se, 2),
        "IC95_sup": round(f_mean + 1.96 * se, 2),
        "pedido_mediana_Q50": int(round(q50)),
        "pedido_seguro_Q95": int(round(q95)),
        "prob_faltante_en_media_%": round(prob_shortage * 100.0, 1),
    })

  if dev.type == "cuda":
    torch.cuda.synchronize()
  dt = (time.perf_counter() - t0) * 1000.0
  logger.info(
      f"Monte Carlo en {dev} ({n_sims:,} escenarios x 10 especies) completado"
      f" en {dt:.2f} ms."
  )

  df_mc = pd.DataFrame(results)
  costo_unitario = PRESUPUESTO_POR_HA / 658.0
  df_mc["costo_esp_MXN"] = np.round(
      df_mc["compra_esperada_E_Fi"] * costo_unitario, 2
  )
  df_mc.to_csv(OUT_DIR / "monte_carlo_compras.csv", index=False)
  return df_mc


# ==============================================================================
# 5. MALLA 2D EN TRES BOLILLOS, PREEXISTENTES REALES (E_i) Y MÉTRICAS
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


def build_tres_bolillos_graph(
    n_rows: int, n_cols: int, density_per_ha: float = 658.0, ring_level: int = 1
) -> HexGridGraph:
  """Construye la malla bidimensional en tres bolillos y el conjunto de aristas

  de vecindad N(p) podando pares cuya distancia supere el radio crítico R_crit.
  """
  step_d = math.sqrt(20000.0 / (density_per_ha * math.sqrt(3.0)))
  r_crit = step_d * 1.08 if ring_level == 1 else step_d * 1.80

  coords_list = []
  for r in range(n_rows):
    for c in range(n_cols):
      u = (c + 0.5 * (r % 2)) * step_d
      v = r * (math.sqrt(3.0) / 2.0) * step_d
      coords_list.append((u, v))
  coords = np.array(coords_list, dtype=np.float64)

  m = len(coords)
  diff = coords[:, None, :] - coords[None, :, :]
  dist_mat = np.linalg.norm(diff, axis=-1)

  u_idx, v_idx = np.where(
      (np.triu(dist_mat, k=1) > 1e-6) & (np.triu(dist_mat, k=1) <= r_crit)
  )
  dists = dist_mat[u_idx, v_idx]
  weights = step_d / dists

  total_possible = m * (m - 1) // 2
  sparsity_saving = 100.0 * (1.0 - len(u_idx) / max(1, total_possible))
  logger.info(
      f"Malla 2D Tres Bolillos {n_rows}x{n_cols} (|P|={m}, d={step_d:.2f}m,"
      f" R_crit={r_crit:.2f}m): {len(u_idx)} aristas activas de"
      f" {total_possible} pares ({sparsity_saving:.1f}% poda)."
  )
  return HexGridGraph(coords, u_idx, v_idx, dists, weights, step_d, r_crit)


def compute_exact_quotas(
    proportions: np.ndarray, total_positions: int
) -> np.ndarray:
  """Calcula cuotas enteras r_i cuya suma coincide exactamente con |P|."""
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
    seed: int = 42,
) -> Tuple[Dict[int, int], np.ndarray]:
  """Extrae las plantas preexistentes reales (E_i) desde poligonos_plantas_wide.csv

  (para un polígono específico 1..30 o el acumulado de los 30 polígonos si
  poligono_id=0), las escala al número de nodos |P| de la malla y las fija
  espacialmente en el grafo.
  """
  m = len(graph.coords)
  n_sp = len(df_sp)
  sp_names = df_sp["especie"].tolist()

  if 1 <= poligono_id <= len(df_wide):
    row = df_wide[df_wide["poligono_id"] == poligono_id].iloc[0]
    ha = float(row["dimension_ha"])
    est_counts = np.array([float(row[sp]) for sp in sp_names], dtype=np.float64)
    total_target = 658.0 * ha
    est_ratio = min(0.45, float(est_counts.sum()) / max(1.0, total_target))
    est_share = est_counts / max(1.0, float(est_counts.sum()))
    source_desc = f"Polígono {poligono_id} ({ha:.2f} Ha)"
  else:
    total_ha = float(df_wide["dimension_ha"].sum())
    est_counts = df_wide[sp_names].to_numpy(dtype=np.float64).sum(axis=0)
    total_target = 658.0 * total_ha
    est_ratio = float(est_counts.sum()) / max(1.0, total_target)  # ~19.63% real
    est_share = est_counts / max(1.0, float(est_counts.sum()))
    source_desc = f"Promedio Real 30 Polígonos ({total_ha:.2f} Ha totales)"

  n_fixed = int(round(m * est_ratio))
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

  # Construir lista de adyacencia para colocar E_i de forma realista en campo
  adj: List[List[int]] = [[] for _ in range(m)]
  for e in range(len(graph.edge_u)):
    u, v = int(graph.edge_u[e]), int(graph.edge_v[e])
    adj[u].append(v)
    adj[v].append(u)

  rng = np.random.default_rng(seed)
  candidates = list(range(m))
  rng.shuffle(candidates)
  fixed_nodes: Dict[int, int] = {}

  # 1. Ubicar primero Prosopis preexistentes (sp 8) evitando contacto directo entre adultos
  prosopis_id = 8
  for _ in range(int(E_i[prosopis_id])):
    for p in candidates:
      if p not in fixed_nodes and all(
          fixed_nodes.get(nb, -1) != prosopis_id for nb in adj[p]
      ):
        fixed_nodes[p] = prosopis_id
        break

  # 2. Ubicar el resto de especies preexistentes E_i evitando auto-adyacencia
  for sp in range(n_sp):
    if sp == prosopis_id:
      continue
    placed = 0
    for p in candidates:
      if placed >= int(E_i[sp]):
        break
      if p not in fixed_nodes and all(
          fixed_nodes.get(nb, -1) != sp for nb in adj[p]
      ):
        fixed_nodes[p] = sp
        placed += 1
    for p in candidates:
      if placed >= int(E_i[sp]):
        break
      if p not in fixed_nodes:
        fixed_nodes[p] = sp
        placed += 1

  logger.info(
      f"Plantas preexistentes reales cargadas ({source_desc}): "
      f"{len(fixed_nodes)}/{m} nodos fijos ({100.0*len(fixed_nodes)/m:.1f}%) |"
      f" E_i = {E_i.tolist()}"
  )
  return fixed_nodes, E_i


def compute_flexible_bounds_and_warm_quotas(
    df_sp: pd.DataFrame,
    m_nodes: int,
    quotas_base: np.ndarray,
    E_i: np.ndarray,
    tolerance_pct: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
  """Calcula las cotas [lb_i, ub_i] bajo holgura tolerance_pct (ej.

  0.05 o 0.10), garantizando lb_i >= E_i, y construye una cuota objetivo que: 1)
  Maximiza Prosopis laevigata (efecto nodriza) y especies de alta supervivencia,
  2) Evita que el género Agave supere el 47% de la malla (<=31 plantas en 66
  nodos) para reducir también los contactos Agave-Agave.
  """
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

  # Tope anti-saturación para el género Agave (evita pasar de 32 a 33 agaves)
  max_agave_total = max(int(q_warm[0:4].sum()), int(quotas_base[0:4].sum()) - 1)

  # Orden de prioridad: Prosopis (8), Opuntia robusta (6), Agaves más resistentes (0, 3),
  # luego resto de Cactáceas (7, 4, 5) y finalmente Agave salmiana (1) si sobra cupo
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

  # Si aún quedan lugares por llenar, completar respetando ub
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
    assignment: np.ndarray, graph: HexGridGraph, Phi: np.ndarray
) -> float:
  return float(
      np.sum(
          graph.edge_weight
          * Phi[assignment[graph.edge_u], assignment[graph.edge_v]]
      )
  )


def audit_ecological_metrics(
    assignment: np.ndarray,
    graph: HexGridGraph,
    Phi: np.ndarray,
    df_sp: pd.DataFrame,
    fixed_nodes: Dict[int, int],
) -> Dict[str, Any]:
  """Calcula todas las métricas físicas y ecológicas de la malla:

  competencia total Phi, contactos intraespecíficos, contactos Agave-Agave,
  interacciones nodriza (Prosopis), supervivencia base 2023 y supervivencia
  efectiva.
  """
  m = len(graph.coords)
  n_edges = len(graph.edge_u)
  genera = df_sp["genero"].tolist()
  s_2023 = df_sp["supervivencia_2023_pct"].to_numpy(dtype=np.float64) / 100.0

  comp_total = evaluate_assignment_cost(assignment, graph, Phi)
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

  # Supervivencia efectiva ajustada por microclima nodriza y reducción de competencia local
  avg_edge_load = node_load / np.maximum(1.0, node_deg)
  # 0.557 es la carga media por arista bajo plantación aleatoria en la malla 6x11
  surv_eff_nodes = np.clip(
      s_2023[assignment] * (1.0 + 0.08 * (0.557 - avg_edge_load)), 0.0, 0.995
  )
  surv_eff_pct = float(np.mean(surv_eff_nodes) * 100.0)

  return {
      "comp_total": comp_total,
      "intra_contacts": intra_contacts,
      "agave_contacts": agave_contacts,
      "nurse_contacts": nurse_contacts,
      "prosopis_count": int(counts[8]),
      "agave_total": int(counts[0:4].sum()),
      "counts": counts,
      "surv_base_pct": surv_base_pct,
      "surv_eff_pct": surv_eff_pct,
      "fixed_count": len(fixed_nodes),
  }


# ==============================================================================
# 6. WARM-START EN RTX 3060 + RELEVO TÉRMICO HACIA EL RYZEN 7 6800H
# ==============================================================================


def gpu_parallel_annealing_warmstart(
    graph: HexGridGraph,
    Phi: np.ndarray,
    quotas: np.ndarray,
    fixed_nodes: Optional[Dict[int, int]] = None,
    n_replicas: int = 1024,
    n_steps: int = 8000,
) -> Tuple[np.ndarray, float]:
  dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
  m = len(graph.coords)
  fixed_nodes = fixed_nodes or {}

  rem_quotas = quotas.copy()
  for _, sp in fixed_nodes.items():
    if rem_quotas[sp] > 0:
      rem_quotas[sp] -= 1

  free_positions = [p for p in range(m) if p not in fixed_nodes]
  free_pool = np.repeat(np.arange(len(quotas)), np.maximum(0, rem_quotas))
  if len(free_pool) < len(free_positions):
    free_pool = np.concatenate([
        free_pool,
        np.zeros(len(free_positions) - len(free_pool), dtype=int),
    ])
  free_pool = free_pool[: len(free_positions)]

  states_np = np.zeros((n_replicas, m), dtype=np.int64)
  rng = np.random.default_rng(42)
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

  def batch_cost(st: torch.Tensor) -> torch.Tensor:
    return (Phi_t[st[:, edge_u_t], st[:, edge_v_t]] * edge_w_t[None, :]).sum(
        dim=1
    )

  curr_costs = batch_cost(states)
  best_idx = int(torch.argmin(curr_costs).item())
  best_cost = float(curr_costs[best_idx].item())
  best_state = states[best_idx].clone()

  t0 = time.perf_counter()
  temps = torch.linspace(1.5, 0.005, n_steps, device=dev)
  n_free = len(free_positions)
  batch_indices = torch.arange(n_replicas, device=dev)

  for step in range(n_steps):
    T = temps[step]
    idx1 = free_pos_t[torch.randint(0, n_free, (n_replicas,), device=dev)]
    idx2 = free_pos_t[torch.randint(0, n_free, (n_replicas,), device=dev)]

    val1 = states[batch_indices, idx1]
    val2 = states[batch_indices, idx2]
    states[batch_indices, idx1] = val2
    states[batch_indices, idx2] = val1

    new_costs = batch_cost(states)
    delta = new_costs - curr_costs
    accept = (delta < 0) | (
        torch.rand(n_replicas, device=dev) < torch.exp(-delta / T)
    )
    reject = ~accept

    states[batch_indices[reject], idx1[reject]] = val1[reject]
    states[batch_indices[reject], idx2[reject]] = val2[reject]
    curr_costs = torch.where(accept, new_costs, curr_costs)

    min_c, min_i = torch.min(curr_costs, dim=0)
    if float(min_c.item()) < best_cost:
      best_cost = float(min_c.item())
      best_state = states[int(min_i.item())].clone()

  best_np = best_state.cpu().numpy()
  dt = time.perf_counter() - t0
  logger.info(
      f"Warm-Start RTX 3060 ({n_replicas} réplicas x {n_steps} pasos) "
      f"en {dt:.2f}s -> Costo = {best_cost:.4f}"
  )

  del (
      states,
      Phi_t,
      edge_u_t,
      edge_v_t,
      edge_w_t,
      free_pos_t,
      curr_costs,
      best_state,
  )
  gc.collect()
  if dev.type == "cuda":
    torch.cuda.empty_cache()

  return best_np, best_cost


# ==============================================================================
# 7. SOLVER EXACTO EN RYZEN 7 6800H (RLT-1 EXACTO + CLIQUES K_3 + HOLGURA)
# ==============================================================================


def solve_exact_ryzen6800h(
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
) -> Tuple[np.ndarray, float, float, float, str]:
  """Solver exacto diseñado para entrar estrictamente dentro del límite de la

  licencia size-limited de Gurobi (<= 2,000 variables y <= 2,000 restricciones):
  - En malla 6x11 usa exactamente 1,155 variables y ~1,910 restricciones.
  - Descomposición de Potenciales Lineales (alpha_i) por LP + bloques R_ag,
  R_op, R_rem.
  - Cortes de Cliques Triangulares (K_3) sobre los 90 triángulos de Tres
  Bolillos.
  """
  from scipy.optimize import linprog

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
  else:
    lb_i = np.maximum(
        E_i, np.floor(quotas * (1.0 - tolerance_pct)).astype(int)
    )
    ub_i = np.maximum(lb_i, np.ceil(quotas * (1.0 + tolerance_pct)).astype(int))
    q_target = quotas.copy()
    s_2023 = np.ones(n_sp, dtype=np.float64)

  # --- PASO A: Potencial lineal óptimo alpha_i (captura >80% de Phi sin pérdida Big-M) ---
  A_ub, b_ub = [], []
  for i in range(n_sp):
    for j in range(n_sp):
      row = np.zeros(n_sp)
      row[i] += 1.0
      row[j] += 1.0
      A_ub.append(row)
      b_ub.append(float(Phi[i, j]))
  res_lp = linprog(
      -q_target.astype(float),
      A_ub=A_ub,
      b_ub=b_ub,
      bounds=[(None, None)] * n_sp,
  )
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

  # Identificar triángulos equiláteros K_3
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
            triangles.append((
                p,
                q,
                r,
                edge_map[(p, q)],
                edge_map[(q, r)],
                edge_map[(p, r)],
            ))

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

    # 1,155 variables en malla 6x11 (estrictamente < 2,000 de la licencia pip)
    x = model.addVars(n_sp, m, vtype=GRB.BINARY, name="x")
    z_ag = model.addVars(n_edges, lb=0.0, vtype=GRB.CONTINUOUS, name="z_ag")
    z_op = model.addVars(n_edges, lb=0.0, vtype=GRB.CONTINUOUS, name="z_op")
    z_rem = model.addVars(n_edges, lb=0.0, vtype=GRB.CONTINUOUS, name="z_rem")

    # Fijar plantas preexistentes directamente en las cotas de x (consume 0 restricciones)
    for p, sp_fixed in fixed_nodes.items():
      for i in range(n_sp):
        val = 1.0 if i == int(sp_fixed) else 0.0
        x[i, int(p)].LB = val
        x[i, int(p)].UB = val

    # Inyectar Warm-Start de la RTX 3060
    for p in range(m):
      sp_init = int(warm_assignment[p])
      for i in range(n_sp):
        x[i, p].Start = 1.0 if i == sp_init else 0.0

    # 1. Una especie por nodo libre (53 restricciones en vez de 66)
    for p in range(m):
      if p not in fixed_nodes:
        model.addConstr(
            gp.quicksum(x[i, p] for i in range(n_sp)) == 1, name=f"one_sp_{p}"
        )

    # 2. Cuotas por especie y tope anti-saturación de Agaves en holgura 5%-10%
    for i in range(n_sp):
      tot_i = gp.quicksum(x[i, p] for p in range(m))
      if int(lb_i[i]) == int(ub_i[i]):
        model.addConstr(tot_i == int(lb_i[i]), name=f"q_eq_{i}")
      else:
        model.addConstr(tot_i >= int(lb_i[i]), name=f"q_lb_{i}")
        model.addConstr(tot_i <= int(ub_i[i]), name=f"q_ub_{i}")

    if tolerance_pct > 1e-9:
      # Evitar que el total de Agaves suba por encima de la cuota base (reduce choques Agave-Agave)
      max_agaves = max(int(lb_i[0:4].sum()), int(quotas[0:4].sum()) - 1)
      model.addConstr(
          gp.quicksum(x[i, p] for i in range(4) for p in range(m))
          <= max_agaves,
          name="agave_cap",
      )
      if df_sp is not None:
        base_surv_sum = float(np.dot(quotas, s_2023))
        warm_surv_sum = float(np.sum(s_2023[warm_assignment]))
        min_surv = base_surv_sum + max(
            0.05, 0.80 * (warm_surv_sum - base_surv_sum)
        )
        model.addConstr(
            gp.quicksum(
                float(s_2023[i]) * x[i, p] for i in range(n_sp) for p in range(m)
            )
            >= min_surv,
            name="surv_floor",
        )

    # 3. Exactamente 9 cortes compactos por arista (165 * 9 = 1,485 restricciones -> Total < 1,920)
    for e in range(n_edges):
      p, q = int(graph.edge_u[e]), int(graph.edge_v[e])
      y_ag_p = gp.quicksum(x[i, p] for i in range(4))
      y_ag_q = gp.quicksum(x[i, q] for i in range(4))
      y_op_p = gp.quicksum(x[i, p] for i in range(4, 8))
      y_op_q = gp.quicksum(x[i, q] for i in range(4, 8))

      # (a) 4 cortes para el bloque Agave (McCormick + salmiana + scabra bidireccional)
      model.addConstr(z_ag[e] >= min_agave * (y_ag_p + y_ag_q - 1))
      model.addConstr(z_ag[e] >= float(R_ag[1, 1]) * (x[1, p] + x[1, q] - 1))
      model.addConstr(
          z_ag[e]
          >= gp.quicksum(float(R_ag[2, j]) * x[j, q] for j in range(4))
          - float(M_ag[2]) * (1 - x[2, p])
      )
      model.addConstr(
          z_ag[e]
          >= gp.quicksum(float(R_ag[j, 2]) * x[j, p] for j in range(4))
          - float(M_ag[2]) * (1 - x[2, q])
      )

      # (b) 3 cortes para el bloque Opuntia (McCormick + especies vulnerables 4,5,7)
      model.addConstr(z_op[e] >= min_opuntia * (y_op_p + y_op_q - 1))
      model.addConstr(
          z_op[e]
          >= gp.quicksum(float(R_op[5, j]) * x[j, q] for j in range(4, 8))
          - float(M_op[5]) * (1 - (x[4, p] + x[5, p] + x[7, p]))
      )
      model.addConstr(
          z_op[e]
          >= gp.quicksum(float(R_op[j, 5]) * x[j, p] for j in range(4, 8))
          - float(M_op[5]) * (1 - (x[4, q] + x[5, q] + x[7, q]))
      )

      # (c) 2 cortes para residuales críticos: Prosopis-Prosopis (8) y Yucca-Yucca (9)
      model.addConstr(z_rem[e] >= float(R_rem[8, 8]) * (x[8, p] + x[8, q] - 1))
      model.addConstr(z_rem[e] >= float(R_rem[9, 9]) * (x[9, p] + x[9, q] - 1))

    # 4. Cortes de Cliques Triangulares K_3 (90 * 4 = 360 restricciones)
    for p, q, r, e1, e2, e3 in triangles:
      y_ag = gp.quicksum(x[i, p] + x[i, q] + x[i, r] for i in range(4))
      y_op = gp.quicksum(x[i, p] + x[i, q] + x[i, r] for i in range(4, 8))
      model.addConstr(z_ag[e1] + z_ag[e2] + z_ag[e3] >= min_agave * (y_ag - 1))
      model.addConstr(
          z_ag[e1] + z_ag[e2] + z_ag[e3] >= min_agave * (2 * y_ag - 3)
      )
      model.addConstr(
          z_op[e1] + z_op[e2] + z_op[e3] >= min_opuntia * (y_op - 1)
      )
      model.addConstr(
          z_op[e1] + z_op[e2] + z_op[e3] >= min_opuntia * (2 * y_op - 3)
      )

    # Función Objetivo = Potencial Lineal Exacto + Residuales de Arista
    linear_obj = gp.quicksum(
        float(W_p[p] * alpha[i]) * x[i, p] for p in range(m) for i in range(n_sp)
    )
    edge_obj = gp.quicksum(
        float(graph.edge_weight[e]) * (z_ag[e] + z_op[e] + z_rem[e])
        for e in range(n_edges)
    )
    model.setObjective(linear_obj + edge_obj, GRB.MINIMIZE)

    model.optimize()

    best_bound = float(model.ObjBound) if model.SolCount > 0 else 0.0
    cost_ws = evaluate_assignment_cost(warm_assignment, graph, Phi)

    if model.SolCount > 0:
      sol = np.zeros(m, dtype=int)
      for p in range(m):
        for i in range(n_sp):
          if x[i, p].X > 0.5:
            sol[p] = i
            break
      cost_gurobi = evaluate_assignment_cost(sol, graph, Phi)
      # Conservar siempre la mejor asignación física evaluada sobre Phi exacta
      if cost_gurobi <= cost_ws + 1e-6:
        best_sol, best_cost = sol, cost_gurobi
      else:
        best_sol, best_cost = warm_assignment, cost_ws
      real_gap = 100.0 * max(0.0, best_cost - best_bound) / max(1e-6, best_cost)
      return (
          best_sol,
          best_cost,
          best_bound,
          real_gap,
          f"Gurobi K3 ({cpu_threads} hilos)",
      )

    return warm_assignment, cost_ws, best_bound, 0.0, "WarmStart-GPU"

  except Exception as e:
    logger.warning(f"Error en Gurobi ({e}); retornando solución Warm-Start.")
    cost_ws = evaluate_assignment_cost(warm_assignment, graph, Phi)
    return warm_assignment, cost_ws, 0.0, 0.0, "WarmStart-GPU"

# ==============================================================================
# 8. EXPORTACIÓN DE VISUALIZACIONES CIENTÍFICAS EN scripts/outputs/
# ==============================================================================


def export_visualizations(
    df_species: pd.DataFrame,
    Phi: np.ndarray,
    graph: HexGridGraph,
    assignment: np.ndarray,
    fixed_nodes: Dict[int, int],
    suffix: str = "",
) -> None:
  if suffix == "" or suffix == "_0pct":
    fig, ax = plt.subplots(figsize=(9, 7.5), dpi=200)
    im = ax.imshow(Phi, cmap="YlOrRd")
    names = [
        f"{r['especie']} (w={r['w_vuln']:.2f})" for _, r in df_species.iterrows()
    ]
    ax.set_xticks(range(len(names)))
    ax.set_yticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8.5)
    ax.set_yticklabels(names, fontsize=8.5)
    for i in range(len(names)):
      for j in range(len(names)):
        ax.text(
            j,
            i,
            f"{Phi[i, j]:.2f}",
            ha="center",
            va="center",
            color="white" if Phi[i, j] > 0.85 else "black",
            fontsize=7.5,
        )
    plt.colorbar(
        im, ax=ax, label="Penalización Efectiva $\\Phi_{ij} = c_{ij}(w_i+w_j)/2$"
    )
    ax.set_title(
        "Matriz de Competencia Ponderada por Inverso de Supervivencia 2023",
        fontsize=11,
        pad=12,
    )
    plt.tight_layout()
    plt.savefig(OUT_DIR / "matriz_competencia_phi.png")
    plt.close()

  fig, ax = plt.subplots(figsize=(11, 7.5), dpi=200)
  for e in range(len(graph.edge_u)):
    u, v = int(graph.edge_u[e]), int(graph.edge_v[e])
    ax.plot(
        [graph.coords[u, 0], graph.coords[v, 0]],
        [graph.coords[u, 1], graph.coords[v, 1]],
        color="#cccccc",
        linewidth=0.8,
        zorder=1,
    )

  cmap = plt.get_cmap("tab10")
  for _, row in df_species.iterrows():
    sp_id = int(row["id"])
    mask = assignment == sp_id
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
  ax.set_title(
      "Distribución Óptima en Malla 2D Tres Bolillos"
      f" ({title_tag})",
      fontsize=11,
  )
  ax.legend(
      bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8.5, frameon=True
  )
  plt.tight_layout()
  out_name = (
      f"mapa_tres_bolillos_optimo{suffix}.png"
      if suffix
      else "mapa_tres_bolillos_optimo.png"
  )
  plt.savefig(OUT_DIR / out_name)
  plt.close()


# ==============================================================================
# 9. EJECUCIÓN PRINCIPAL (CON COMPARATIVA 0%, 5% Y 10% + DATOS REALES CSV)
# ==============================================================================


def main() -> None:
  default_threads = max(1, (os.cpu_count() or 16) - 2)

  parser = argparse.ArgumentParser(
      description="Pipeline REFORESTATHON (Ryzen 6800H + RTX 3060)"
  )
  parser.add_argument(
      "--rows", type=int, default=6, help="Filas de la malla 2D en tres bolillos"
  )
  parser.add_argument(
      "--cols",
      type=int,
      default=11,
      help="Columnas de la malla 2D en tres bolillos",
  )
  parser.add_argument(
      "--ring",
      type=int,
      default=1,
      choices=[1, 2],
      help="Anillo de vecindad N(p)",
  )
  parser.add_argument(
      "--time-limit",
      type=int,
      default=90,
      help="Tiempo límite del solver exacto por escenario (s)",
  )
  parser.add_argument(
      "--threads",
      type=int,
      default=default_threads,
      help="Hilos de CPU para el solver",
  )
  parser.add_argument(
      "--poligono-id",
      type=int,
      default=0,
      help="ID del polígono (1..30) o 0 para promedio de los 30 polígonos",
  )
  parser.add_argument(
      "--polygon-ha",
      type=float,
      default=1.0,
      help="Hectáreas si --poligono-id es 0",
  )
  args = parser.parse_args()

  logger.info(
      "=== INICIANDO PIPELINE REFORESTATHON (RYZEN 7 6800H + RTX 3060) ==="
  )
  if torch.cuda.is_available():
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    logger.info(
        f"GPU Activa: {torch.cuda.get_device_name(0)} ({vram_gb:.1f} GB VRAM,"
        f" CUDA {torch.version.cuda})"
    )
  logger.info(
      f"Hilos de CPU asignados al Solver Exacto: {args.threads} de"
      f" {os.cpu_count()}."
  )

  # 1. Cargar CSVs reales desde data/semiraw/
  df_cat, df_wide, baseline_row_22 = load_semiraw_datasets()

  if 1 <= args.poligono_id <= len(df_wide):
    poly_row = df_wide[df_wide["poligono_id"] == args.poligono_id].iloc[0]
    target_ha = float(poly_row["dimension_ha"])
    logger.info(
        f"Simulando {poly_row['poligono']} (ID={args.poligono_id},"
        f" Área={target_ha:.2f} Ha)"
    )
  else:
    target_ha = args.polygon_ha
    logger.info(
        f"Simulando área estándar de {target_ha:.2f} Ha (con proporción"
        " preexistente real de los 30 polígonos)"
    )

  # 2. Construir matrices ecológicas y pesos de vulnerabilidad 2023
  df_sp, C_base, Phi = build_ecological_matrices(df_cat, lam=1.0)
  logger.info(
      "\nCatálogo Consolidado y Pesos de Prioridad (Inverso Supervivencia"
      " 2023):\n"
      + df_sp[[
          "especie",
          "nombre_comun",
          "plantas_por_ha",
          "supervivencia_2023_pct",
          "inv_s2023",
          "w_vuln",
      ]].to_string(index=False)
  )

  # 3. Simulación Monte Carlo en RTX 3060
  df_mc = run_monte_carlo_rtx3060(
      df_sp, df_wide, target_area_ha=target_ha, n_sims=1_000_000
  )
  logger.info(
      f"\nResultados Monte Carlo de Compra ({target_ha:.2f} Ha):\n"
      + df_mc[[
          "especie",
          "requerimiento_ri",
          "existencia_media_Ei",
          "compra_esperada_E_Fi",
          "pedido_seguro_Q95",
          "costo_esp_MXN",
      ]].to_string(index=False)
  )

  # 4. Benchmark sobre orden_plantacion_100m.csv (22 posiciones)
  graph_1d = build_tres_bolillos_graph(
      n_rows=1, n_cols=len(baseline_row_22), density_per_ha=658.0, ring_level=1
  )
  base_arr = np.array(baseline_row_22, dtype=int)
  base_cost_1d = evaluate_assignment_cost(base_arr, graph_1d, Phi)
  quotas_22 = np.bincount(base_arr, minlength=len(df_sp))
  warm_1d, _ = gpu_parallel_annealing_warmstart(
      graph_1d, Phi, quotas_22, n_replicas=512, n_steps=3000
  )
  opt_1d, opt_cost_1d, bound_1d, gap_1d, _ = solve_exact_ryzen6800h(
      graph_1d,
      Phi,
      quotas_22,
      warm_1d,
      tolerance_pct=0.0,
      df_sp=df_sp,
      time_limit=20,
      cpu_threads=args.threads,
  )
  logger.info(
      f"\n[Benchmark orden_plantacion_100m.csv] Costo Original = {base_cost_1d:.4f}"
      f" | Costo Óptimo = {opt_cost_1d:.4f} | BestBound = {bound_1d:.4f} |"
      f" MIPGap = {gap_1d:.2f}% "
      f"(Reducción = {100.0*(base_cost_1d - opt_cost_1d)/base_cost_1d:.2f}%)"
  )

  # 5. Optimización en Malla 2D Tres Bolillos con Plantas Preexistentes Reales (CSV) y Holgura 0%, 5%, 10%
  graph_2d = build_tres_bolillos_graph(
      n_rows=args.rows,
      n_cols=args.cols,
      density_per_ha=658.0,
      ring_level=args.ring,
  )
  m_nodes = args.rows * args.cols
  proportions = df_sp["proporcion_programa"].to_numpy(dtype=np.float64)
  quotas_2d = compute_exact_quotas(proportions, m_nodes)

  # Fijar plantas preexistentes reales (E_i) extraídas de poligonos_plantas_wide.csv
  fixed_nodes_2d, E_i_2d = build_real_preexisting_nodes_from_csv(
      df_sp, df_wide, graph_2d, quotas_2d, poligono_id=args.poligono_id, seed=42
  )

  # Costo de referencia aleatorio respetando las plantas preexistentes fijas
  rng = np.random.default_rng(123)
  rem_q_init = np.maximum(0, quotas_2d - E_i_2d)
  free_pos_init = [p for p in range(m_nodes) if p not in fixed_nodes_2d]
  rand_assign = np.zeros(m_nodes, dtype=int)
  for p, sp in fixed_nodes_2d.items():
    rand_assign[p] = sp
  rand_pool = np.repeat(np.arange(len(df_sp)), rem_q_init)
  rand_assign[free_pos_init] = rng.permutation(rand_pool[: len(free_pos_init)])
  init_cost_2d = evaluate_assignment_cost(rand_assign, graph_2d, Phi)

  comparativa_rows = []
  slack_levels = [0.00, 0.05, 0.10]

  for tol in slack_levels:
    tag_pct = int(round(tol * 100))
    logger.info(
        "\n"
        + "=" * 80
        + f"\n>>> EJECUTANDO MALLA 2D ({args.rows}x{args.cols}) | ESCENARIO"
        f" HOLGURA +/- {tag_pct}%\n"
        + "=" * 80
    )

    lb_i, ub_i, q_warm_target = compute_flexible_bounds_and_warm_quotas(
        df_sp, m_nodes, quotas_2d, E_i_2d, tolerance_pct=tol
    )
    logger.info(
        f"Cotas [L_i, U_i] (+/-{tag_pct}%): "
        + ", ".join(
            f"{df_sp.loc[i, 'especie'].split()[1][:4]}:[{lb_i[i]},{ub_i[i]}]"
            for i in range(len(df_sp))
        )
    )

    warm_2d, warm_cost_2d = gpu_parallel_annealing_warmstart(
        graph_2d,
        Phi,
        q_warm_target,
        fixed_nodes=fixed_nodes_2d,
        n_replicas=1024,
        n_steps=8000,
    )
    opt_2d, exact_cost_2d, best_bound_2d, gap_2d, solver_used = (
        solve_exact_ryzen6800h(
            graph_2d,
            Phi,
            quotas_2d,
            warm_2d,
            fixed_nodes=fixed_nodes_2d,
            tolerance_pct=tol,
            df_sp=df_sp,
            E_i=E_i_2d,
            time_limit=args.time_limit,
            cpu_threads=args.threads,
        )
    )

    metrics = audit_ecological_metrics(
        opt_2d, graph_2d, Phi, df_sp, fixed_nodes_2d
    )

    logger.info(
        f"[Resultado Holgura +/-{tag_pct}%] Aleatorio = {init_cost_2d:.4f} | "
        f"Warm-Start GPU = {warm_cost_2d:.4f} | Exacto = {exact_cost_2d:.4f} | "
        f"BestBound = {best_bound_2d:.4f} | MIPGap = {gap_2d:.2f}% "
        f"(Reducción Competencia: {100.0*(init_cost_2d - exact_cost_2d)/init_cost_2d:.2f}%)"
    )
    logger.info(
        f"[Ecología +/-{tag_pct}%] Supervivencia Base 2023 ="
        f" {metrics['surv_base_pct']:.2f}% | "
        f"Supervivencia Efectiva Espacial = {metrics['surv_eff_pct']:.2f}% | "
        f"Nodrizas = {metrics['nurse_contacts']} | "
        f"Intraespecíficos = {metrics['intra_contacts']} | "
        f"Agave-Agave = {metrics['agave_contacts']} | "
        f"Cuotas Finales = {metrics['counts'].tolist()}"
    )

    df_out = pd.DataFrame({
        "posicion_p": np.arange(m_nodes),
        "x_m": np.round(graph_2d.coords[:, 0], 2),
        "y_m": np.round(graph_2d.coords[:, 1], 2),
        "especie_id": opt_2d,
        "especie": [df_sp.loc[i, "especie"] for i in opt_2d],
        "nombre_comun": [df_sp.loc[i, "nombre_comun"] for i in opt_2d],
        "supervivencia_2023_pct": [
            df_sp.loc[i, "supervivencia_2023_pct"] for i in opt_2d
        ],
        "es_preexistente": [p in fixed_nodes_2d for p in range(m_nodes)],
    })

    if tag_pct == 0:
      df_out.to_csv(OUT_DIR / "asignacion_optima_2d.csv", index=False)
      export_visualizations(
          df_sp, Phi, graph_2d, opt_2d, fixed_nodes_2d, suffix=""
      )
    df_out.to_csv(
        OUT_DIR / f"asignacion_optima_2d_holgura_{tag_pct}pct.csv", index=False
    )
    export_visualizations(
        df_sp, Phi, graph_2d, opt_2d, fixed_nodes_2d, suffix=f"_{tag_pct}pct"
    )

    comparativa_rows.append({
        "Escenario": f"Holgura +/- {tag_pct}%",
        "Preexistentes_Fijas_Ei": metrics["fixed_count"],
        "Costo_Aleatorio": round(init_cost_2d, 4),
        "Costo_WarmStart_GPU": round(warm_cost_2d, 4),
        "Costo_Optimo_Phi": round(exact_cost_2d, 4),
        "BestBound_Teorico": round(best_bound_2d, 4),
        "MIPGap_%": round(gap_2d, 2),
        "Reduccion_Competencia_%": round(
            100.0 * (init_cost_2d - exact_cost_2d) / init_cost_2d, 2
        ),
        "Supervivencia_Base_2023_%": round(metrics["surv_base_pct"], 2),
        "Supervivencia_Efectiva_Espacial_%": round(metrics["surv_eff_pct"], 2),
        "Interacciones_Nodriza": metrics["nurse_contacts"],
        "Contactos_Intraespecificos": metrics["intra_contacts"],
        "Contactos_Agave_Agave": metrics["agave_contacts"],
        "Mezquites_Totales": metrics["prosopis_count"],
        "Agaves_Totales": metrics["agave_total"],
        "Cuotas_Finales": str(metrics["counts"].tolist()),
    })

  df_comp = pd.DataFrame(comparativa_rows)
  df_comp.to_csv(OUT_DIR / "comparativa_holgura_0_5_10.csv", index=False)
  logger.info(
      "\n"
      + "=" * 95
      + "\nTABLA COMPARATIVA FINAL: IMPACTO DE LA HOLGURA (0% vs 5% vs 10%) CON"
      " DATOS REALES\n"
      + "=" * 95
      + "\n"
      + df_comp[[
          "Escenario",
          "Costo_Optimo_Phi",
          "BestBound_Teorico",
          "MIPGap_%",
          "Supervivencia_Base_2023_%",
          "Supervivencia_Efectiva_Espacial_%",
          "Interacciones_Nodriza",
          "Contactos_Agave_Agave",
      ]].to_string(index=False)
  )
  logger.info(f"=== FINALIZADO. Archivos exportados en: {OUT_DIR} ===")


if __name__ == "__main__":
  main()