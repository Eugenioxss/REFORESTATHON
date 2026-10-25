# Resumen Estadístico y Numérico del Entregable 3 (REFORESTATHON)
**Simulación Estocástica de Siembra en 1 Hectárea (100 m × 100 m, Pendiente 6°, Sitio Dominica)**
*Generado tras 1,000 corridas en laptop ASUS ROG Strix G513RM (AMD Ryzen 7 6800H, 8 nucleos / 16 hilos, 32 GB RAM DDR5).*

---

## 1. Parámetros del Terreno y Vegetación Preexistente (\nu_i)
- **Densidad Preexistente Censada (INECOL, 30 polígonos):** Media $\mu = 129.27$ pl/ha, Desviación Estándar $\sigma = 3.53$ pl/ha, Error Estándar $EE = 0.112$ pl/ha.
- **Intervalo de Confianza del 95% (\nu):** $[122.00, 136.00]$ pl/ha.
- **Meta de Densidad Total (CONAFOR, Pendiente 6°):** $N_{\text{total}} = 658$ pl/ha.
- **Demanda Neta de Suministro ($N_{\text{sembrar}}$):** Media $= 528.73$ pl/ha, $IC_{95\%} = [522.00, 536.00]$ pl/ha.

---

## 2. Presupuesto y Costos Oficiales por Especie en 1 Hectárea
Precios unitarios oficiales ($k_i$):
- *Agave lechuguilla* (AL): $26.00 MXN
- *Agave striata* (AT): $26.00 MXN
- *Agave scabra* (AC): $26.00 MXN
- *Agave salmiana* (AS): $26.00 MXN
- *Opuntia cantabrigiensis* (OC): $18.00 MXN
- *Opuntia engelmannii* (OE): $21.00 MXN
- *Opuntia robusta* (OR): $18.00 MXN
- *Opuntia streptacantha* (OS): $18.00 MXN
- *Prosopis laevigata* (PL): $26.50 MXN
- *Yucca filifera* (YF): $26.00 MXN

**Gasto Total de Compra en Vivero (1 Ha):**
- **Costo de Compra Base:** Media $= \$12,491.85$ MXN ($\\pm \$92.96$ MXN).
- **Costo con Fondo de Reemplazo (5% contingencia):** Media $= \$13,116.45$ MXN ($\\pm \$97.61$ MXN).

---

## 3. Impacto Ecológico: Siembra Aleatoria vs Optimización con Recocido Simulado
Comparativa estadística empírica de 1,000 corridas en 1 hectárea ($n=1,000$):

| Métrica Ecológica | Inicial Aleatorio | Optimizado Recocido | $\Delta$ Absoluto | Cambio Relativo | Significancia |
|---|---|---|---|---|---|
| **Aptitud Media (F_bar)** | 0.5429 | 0.5688 | +0.0259 | +4.76% | *** (p < 0.001) |
| **Aptitud Aislada Teórica (F_aislada)** | 0.5938 | 0.5938 | 0.0000 | 0.00% | n.s. |
| **Pérdida por Competencia (%)** | 8.5739% | 4.2183% | -4.3556% | -50.80% | *** (p < 0.001) |
| **Sobrevivientes Esperados (Phi, plantas)** | 487.8522 pl | 509.4381 pl | +21.5860 pl | +4.42% | *** (p < 0.001) |
| **Mortalidad Proxy (%)** | 7.7310% | 3.6482% | -4.0828% | -52.81% | *** (p < 0.001) |
| **Presión Hídrica (H_W)** | 0.1789 | 0.1532 | -0.0257 | -14.34% | *** (p < 0.001) |
| **Presión Lumínica (H_L)** | 0.0389 | 0.0343 | -0.0046 | -11.79% | *** (p < 0.001) |
| **Facilitación Nodriza (H_B)** | 0.0169 | 0.0158 | -0.0011 | -6.35% | *** (p < 0.001) |
| **Presión Nitrógeno/Nutrientes (H_N)** | 0.0035 | 0.0033 | -0.0002 | -4.55% | *** (p < 0.001) |
| **Índice de Interferencia por Pares (Phi_Eq17)** | 127.3258 | 101.3982 | -25.9276 | -20.36% | *** (p < 0.001) |

> **Hallazgo Clave:** La optimización estocástica incrementa la aptitud biológica media en **+4.76%**, ganando en promedio **+21.6 árboles/plantas sobrevivientes adicionales por hectárea**, reduciendo la interferencia de pares vecinos en **20.36%** (evaluada mediante la matriz pura $\Phi_{\text{Eq17}}$ de la Ecuación 17) de manera altamente significativa ($p < 0.001$).

---

## 4. Cadena de Markov del Proceso de Siembra Secuencial en Campo (Recorrido Boustrophedon)
- **Entropía del Proceso Aleatorio:** $H(X)_{\text{rand}} = 2.9566$ bits/símbolo.
- **Entropía del Proceso Optimizado:** $H(X)_{\text{opt}} = 2.9790$ bits/símbolo.
- **Entropía de la Red Espacial de Vecinos:** $H(X)_{\text{espacial}} = 2.9340$ bits/símbolo.
- **Distribución Estacionaria $\pi$ y Tiempos Medios de Retorno $\mu_{ii} = 1/\pi_i$ (pasos de plantación secuencial):**
  - **AL:** $\pi_{AL} = 0.0716$, $\mu_{AL} = 13.96$ pasos.
  - **AT:** $\pi_{AT} = 0.0721$, $\mu_{AT} = 13.87$ pasos.
  - **AC:** $\pi_{AC} = 0.0713$, $\mu_{AC} = 14.03$ pasos.
  - **AS:** $\pi_{AS} = 0.3053$, $\mu_{AS} = 3.28$ pasos.
  - **OC:** $\pi_{OC} = 0.0812$, $\mu_{OC} = 12.31$ pasos.
  - **OE:** $\pi_{OE} = 0.0620$, $\mu_{OE} = 16.13$ pasos.
  - **OR:** $\pi_{OR} = 0.0967$, $\mu_{OR} = 10.34$ pasos.
  - **OS:** $\pi_{OS} = 0.0873$, $\mu_{OS} = 11.45$ pasos.
  - **PL:** $\pi_{PL} = 0.1161$, $\mu_{PL} = 8.61$ pasos.
  - **YF:** $\pi_{YF} = 0.0363$, $\mu_{YF} = 27.57$ pasos.

---

## 5. Archivos de Resultados Guardados
1. `sim_1000_corridas_resumen.csv`: 1,000 corridas completas con todas las variables ecológicas y financieras.
2. `tabla_existentes_y_suministro_especie.csv`: Estadísticos descriptivos e inferenciales por especie.
3. `tabla_competencia_1ha.csv`: Matriz comparativa de desempeño y pruebas de hipótesis pareadas.
4. `matriz_transicion_markov_secuencial_opt.csv`: Matriz $10 \times 10$ de probabilidades de transición en plantación secuencial optimizada.
5. `matriz_transicion_markov_secuencial_rand.csv`: Matriz $10 \times 10$ de probabilidades en plantación aleatoria.
6. `matriz_transicion_markov_vecinos_opt.csv`: Matriz espacial de adyacencia en los vecinos inmediatos en tresbolillo.
7. `orden_plantacion_ejemplo_1ha.csv`: Bitácora secuencial paso a paso del predio de 1 hectárea ($s=1$).
8. `resumen_estadistico_entregable3.json`: Datos estructurados listos para integración programática.
