# Métricas de Línea Base (`trabajo\base\`)

## 1. Configuración y Argumentos de Ejecución
- **Script ejecutado**: `d:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\base\scripts\src\reforestacion_pipeline.py`
- **Comando exacto**:
  ```powershell
  & "d:\Codingggg\Notas\Estocastico\REFORESTATHON\.venv\Scripts\python.exe" "d:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\base\scripts\src\reforestacion_pipeline.py" --time-limit 30 --solver highs
  ```
- **Argumentos efectivos**:
  - `--rows 6 --cols 11` ($|\mathcal{P}| = 66$ nodos, $165$ aristas, $100$ triángulos $K_3$, $1155$ variables MIP)
  - `--ring 1`
  - `--time-limit 30`
  - `--threads 14`
  - `--poligono-id 0` (Promedio 30 Polígonos, $183.01$ Ha; simulación sobre predio estándar `--polygon-ha 1.0`)
  - `--slope-pct 6.0` (Densidad objetivo $N_z = 658$ pl/ha)
  - `--solver highs` (HiGHS Branch-and-Cut)
  - `--mu 0.0005`
- **Tiempo total de pared del pipeline**: `50.70 s` (23:47:18.500 a 23:48:09.204)

---

## 2. Resultados del Solver Exacto (MILP)

| Instancia / Escenario | Nodos $\|\mathcal{P}\|$ | Variables MIP | Valor Objetivo Compuesto ($Z$ / `ObjVal`) | Costo Espacial ($\Phi$) | `BestBound` (Cota Dual) | `MIPGap` (%) | Tiempo Solver (s) | Tiempo Warm-Start GPU (ms) | Supervivencia Base 2023 (%) | Supervivencia Efectiva (%) | Contactos Nodriza | Contactos Intra | Contactos Agave-Agave | Gasto Vivero (MXN) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Benchmark 1D (`orden_plantacion_100m.csv`)** | 22 | 283 | **1.5998** | 1.3783 (warm) / 1.4246 (orig) | **1.5905** | **0.58%** | 0.04 s | 4671.60 ms | — | — | — | — | — | — |
| **Malla 2D (6x11) — Holgura ±0%** | 66 | 1155 | **12.4293** | **11.8883** | **12.1314** | **2.40%** | 0.20 s | 11348.58 ms | 86.40% | 89.75% | 46 | 1 | 28 | $1,082.00 |
| **Malla 2D (6x11) — Holgura ±5%** | 66 | 1155 | **11.2935** | **10.7532** | **10.9052** | **3.44%** | 0.26 s | 13510.60 ms | 86.63% | 90.03% | 42 | 0 | 26 | $1,080.50 |
| **Malla 2D (6x11) — Holgura ±10%** | 66 | 1155 | **11.1725** | **10.6295** | **10.6935** | **4.29%** | 0.19 s | 12794.22 ms | 86.94% | 90.36% | 42 | 0 | 28 | $1,086.00 |

---

## 3. Otras Métricas de Referencia (Monte Carlo y Preexistentes)
- **Simulación Monte Carlo GPU (1,000,000 escenarios, 1.00 Ha)**:
  - Tiempo GPU: `807.70 ms`
  - Gasto esperado de compra: `$10,607.06 MXN`
- **Vegetación preexistente fija en malla 2D (6x11, `--poligono-id 0`)**:
  - `13/66` cepas fijas (`19.7%`), `E_i = [1, 4, 1, 1, 1, 1, 1, 1, 2, 0]`
  - Costo aleatorio inicial (semilla 123): `39.7542`
