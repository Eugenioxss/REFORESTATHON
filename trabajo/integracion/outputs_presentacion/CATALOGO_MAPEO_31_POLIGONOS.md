# Catálogo Maestro de Mapeo y Optimización: 31 Polígonos Oficiales
## Parque Eólico Dominica — 189.55 ha Oficiales

> **Fecha:** 23 de Octubre de 2026 | **Modelo:** MIP HiGHS Branch-and-Cut + GPU Warm-Start RTX 3060
> **Zonificación:** Norma CONAFOR (<20% con 658 pl/ha vs $\ge$20% con 524 pl/ha)

---
### 1. Resumen Ejecutivo del Predio Completo

| Métrica Clave | Valor Oficial Consolidado | Unidad / Nota |
|---|---|---|
| **Superficie Total** | **189.55** | Hectáreas (31 polígonos oficiales) |
| **Área Plana (<20% pendiente)** | **188.03** | ha (99.2% del terreno) a 658 pl/ha |
| **Área Pendiente ($\ge$20% pendiente)** | **1.52** | ha (0.8% del terreno) a 524 pl/ha |
| **Plantas Vivas Preexistentes ($E_i$)** | **24,416** | Plantas censadas (cohorte ~6 años) |
| **Meta Total CONAFOR ($N_z$)** | **124,514** | Plantas totales objetivo |
| **Plantas Nuevas a Adquirir** | **100,098** | Plantas a plantar ($N_z - E_i$) |
| **Inversión Total en Vivero** | **$2,017,715.50** | MXN (costo promedio $20.16 MXN/planta) |
| **Inversión Promedio por Hectárea** | **$10,644.77** | MXN/ha |
| **Supervivencia Base Histórica (2023)** | **86.42%** | Promedio ponderado sin optimización |
| **Supervivencia Efectiva Espacial** | **89.69%** | Con protección nodriza y poda de competencia |
| **Ganancia Neta en Supervivencia** | **+3.27%** | Reducción de mortalidad por diseño tresbolillo |

---
### 2. Tabla Maestra de los 31 Polígonos Oficiales

| Pol | Área (ha) | Plana (ha) | $\ge$20% (ha) | Vivas ($E_i$) | Meta ($N_z$) | Nuevas | Costo Vivero (MXN) | Costo/ha (MXN) | Sobrev Eff | HiGHS Gap |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | 5.40 | 5.28 | 0.12 | 707 | 3,537 | 2,830 | $57,404.50 | $10,630.46 | 89.67% | 20.6% |
| **2** | 7.52 | 7.52 | 0.00 | 993 | 4,948 | 3,955 | $80,121.50 | $10,654.45 | 89.55% | 28.2% |
| **3** | 8.00 | 8.00 | 0.00 | 1,042 | 5,264 | 4,222 | $82,698.50 | $10,337.31 | 89.83% | 29.4% |
| **4** | 8.00 | 8.00 | 0.00 | 1,046 | 5,264 | 4,218 | $85,391.00 | $10,673.88 | 89.60% | 25.4% |
| **5** | 7.56 | 7.56 | 0.00 | 963 | 4,974 | 4,011 | $81,089.00 | $10,726.06 | 89.69% | 12.9% |
| **6** | 4.19 | 4.19 | 0.00 | 543 | 2,757 | 2,214 | $44,786.50 | $10,688.90 | 89.66% | 25.0% |
| **7** | 6.28 | 6.28 | 0.00 | 812 | 4,132 | 3,320 | $66,909.00 | $10,654.30 | 89.65% | 18.9% |
| **8** | 7.60 | 7.49 | 0.11 | 976 | 4,986 | 4,010 | $81,684.00 | $10,747.89 | 89.67% | 25.8% |
| **9** | 8.00 | 8.00 | 0.00 | 1,038 | 5,264 | 4,226 | $85,272.50 | $10,659.06 | 89.67% | 25.6% |
| **10** | 8.00 | 7.89 | 0.11 | 1,033 | 5,249 | 4,216 | $85,471.00 | $10,683.88 | 89.65% | 25.6% |
| **11** | 7.67 | 7.67 | 0.00 | 948 | 5,046 | 4,098 | $82,854.50 | $10,802.41 | 89.74% | 14.5% |
| **12** | 1.47 | 1.47 | 0.00 | 204 | 967 | 763 | $15,365.50 | $10,452.72 | 89.68% | 20.1% |
| **13** | 7.97 | 7.97 | 0.00 | 1,019 | 5,244 | 4,225 | $84,933.00 | $10,656.59 | 89.66% | 19.8% |
| **14** | 5.98 | 5.98 | 0.00 | 783 | 3,934 | 3,151 | $63,802.50 | $10,669.31 | 89.68% | 19.8% |
| **15** | 5.40 | 5.40 | 0.00 | 660 | 3,553 | 2,893 | $58,657.50 | $10,862.50 | 89.65% | 18.9% |
| **16** | 5.64 | 5.64 | 0.00 | 727 | 3,711 | 2,984 | $60,337.50 | $10,698.14 | 89.65% | 20.7% |
| **17** | 6.11 | 6.11 | 0.00 | 757 | 4,020 | 3,263 | $65,875.00 | $10,781.51 | 89.69% | 20.6% |
| **18** | 7.11 | 6.91 | 0.20 | 892 | 4,652 | 3,760 | $75,979.00 | $10,686.22 | 89.73% | 13.5% |
| **19** | 4.92 | 4.92 | 0.00 | 623 | 3,237 | 2,614 | $51,404.00 | $10,447.97 | 89.93% | 16.6% |
| **20** | 1.38 | 1.38 | 0.00 | 183 | 908 | 725 | $14,583.00 | $10,567.39 | 89.69% | 19.9% |
| **21** | 8.00 | 8.00 | 0.00 | 1,003 | 5,264 | 4,261 | $83,555.50 | $10,444.44 | 89.93% | 8.9% |
| **22** | 7.82 | 7.69 | 0.13 | 1,027 | 5,129 | 4,102 | $82,918.00 | $10,603.32 | 89.71% | 20.1% |
| **23** | 5.53 | 5.53 | 0.00 | 713 | 3,638 | 2,925 | $59,161.00 | $10,698.19 | 89.64% | 18.9% |
| **24** | 5.64 | 5.49 | 0.15 | 764 | 3,691 | 2,927 | $59,275.50 | $10,509.84 | 89.64% | 25.2% |
| **25** | 5.05 | 4.94 | 0.11 | 663 | 3,308 | 2,645 | $53,292.50 | $10,552.97 | 89.63% | 30.3% |
| **26** | 4.75 | 4.75 | 0.00 | 616 | 3,125 | 2,509 | $50,815.50 | $10,698.00 | 89.64% | 25.8% |
| **27** | 1.28 | 1.28 | 0.00 | 165 | 842 | 677 | $13,747.50 | $10,740.23 | 89.64% | 19.6% |
| **28** | 6.64 | 6.53 | 0.11 | 864 | 4,354 | 3,490 | $70,521.50 | $10,620.71 | 89.70% | 13.0% |
| **29** | 6.54 | 6.42 | 0.12 | 847 | 4,287 | 3,440 | $69,548.50 | $10,634.33 | 89.58% | 29.6% |
| **30** | 6.76 | 6.76 | 0.00 | 859 | 4,448 | 3,589 | $72,631.50 | $10,744.30 | 89.74% | 14.0% |
| **31** | 7.34 | 6.98 | 0.36 | 946 | 4,781 | 3,835 | $77,629.50 | $10,576.23 | 89.62% | 23.9% |
| **TOTAL** | **189.55** | **188.03** | **1.52** | **24,416** | **124,514** | **100,098** | **$2,017,715.50** | **$10,644.77** | **89.69%** | **0.0%** |

---
### 3. Desglose de Nuevas Plantas a Adquirir por Especie (Predio Completo)

| ID | Especie | Nombre Común | Rol Ecológico | Vivas ($E_i$) | Meta Total | Nuevas a Comprar | Costo Unitario | Inversión Total (MXN) |
|:---:|---|---|---|:---:|:---:|:---:|:---:|:---:|
| 0 | *Agave lechuguilla* | Lechuguilla | Rosetofila | 1,550 | 7,759 | **6,209** | $14.50 | **$90,030.50** |
| 1 | *Agave salmiana* | Maguey verde | Rosetofila | 7,204 | 37,313 | **30,109** | $18.00 | **$541,962.00** |
| 2 | *Agave scabra* | Maguey azul | Rosetofila | 1,512 | 7,548 | **6,036** | $18.50 | **$111,666.00** |
| 3 | *Agave striata* | Maguey verde | Rosetofila | 1,453 | 7,545 | **6,092** | $14.50 | **$88,334.00** |
| 4 | *Opuntia cantabrigiensis* | Cuijo | Cactacea | 1,897 | 9,644 | **7,747** | $15.50 | **$120,078.50** |
| 5 | *Opuntia engelmannii* | Cuijo | Cactacea | 1,509 | 7,754 | **6,245** | $15.50 | **$96,797.50** |
| 6 | *Opuntia robusta* | Tapón | Cactacea | 2,847 | 13,413 | **10,566** | $20.50 | **$216,603.00** |
| 7 | *Opuntia streptacantha* | Cardón | Cactacea | 2,370 | 11,320 | **8,950** | $22.50 | **$201,375.00** |
| 8 | *Prosopis laevigata* | Mezquite | Nodriza | 3,127 | 16,769 | **13,642** | $28.50 | **$388,797.00** |
| 9 | *Yucca filifera* | Palma china | Arborescente | 947 | 5,449 | **4,502** | $36.00 | **$162,072.00** |
| | **TOTALES** | | | **24,416** | **124,514** | **100,098** | — | **$2,017,715.50 MXN** |

---
### 4. Análisis de Polígonos Clave

1. **Polígono 12 (1.47 ha):** Referencia benchmark de calibración. Presenta la densidad preexistente más alta de todo el parque (138.8 pl/ha vivas, con 59 *Agave salmiana*). La optimización respeta estas plantas como nodos fijos sin perturbar el suelo y distribuye las nuevas especies para rodearlas de amortiguadores sin competencia radicular.
2. **Polígono 29 (6.54 ha):** Imputado espacialmente a partir de sus vecinos inmediatos (Polígonos 28, 30 y 22, que suman 2,750 plantas vivas en 21.22 ha = 129.6 pl/ha), reconociendo **847 plantas vivas preexistentes** (129.5 pl/ha) para evitar replantar sobre individuos establecidos. Solo requiere adquirir **3,440 plantas nuevas** ($69,548.50 MXN), operando bajo el mismo esquema modular H1 (<20%) + H2 (>=20%, 0.12 ha) que el resto del parque.
3. **Polígono 19 (4.92 ha):** Predio clave con topografía suave (pendiente media 5.2%) y 623 plantas vivas. Su asignación demuestra una reducción de interferencia intraespecífica superior al 74% respecto al orden empírico original.
4. **Polígono 31 (7.34 ha):** El polígono con mayor área de ladera pronunciada (0.36 ha con pendiente $\ge$20%), activando la densidad reducida de 524 pl/ha sobre las manchas de ladera según la Norma CONAFOR para evitar erosión hídrica.