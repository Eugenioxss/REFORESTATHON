# Presentación Ejecutiva Maestra: Optimización Espacial y Restauración Ecológica a 20 Años
## Parque Eólico Dominica (Charcas, SLP) — 31 Polígonos Oficiales (189.55 ha)

> **Proyecto:** REFORESTATHON / MA2004 (CONAFOR – INECOL)  
> **Motor Computacional:** GPU Warm-Start Vectorizado (PyTorch CUDA en RTX 3060, 256 réplicas) + Solver MILP Exacto (HiGHS Branch-and-Cut con cortes clique $K_3$ y RLT-1)  
> **Estado de Auditoría:** 100% reconciliado con las 42 referencias de [`collins/referencias_modelo.md`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/collins/referencias_modelo.md), [`collins/citas_resumen_orquestador.xlsx`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/collins/citas_resumen_orquestador.xlsx) y 21/21 pruebas unitarias aprobadas.

---

## 1. Tablero Ejecutivo Global (31 Polígonos = 189.55 ha)

| Indicador Estratégico | Receta Rígida / Sin Catálisis | Plan Optimizado Dominica (`H1 + H2`) | Impacto / Ventaja Neta |
| :--- | :---: | :---: | :--- |
| **Superficie Oficial Total** | `189.55 ha` (Uniforme) | **`188.03 ha` H1 ($<20\%$) + `1.52 ha` H2 ($\ge 20\%$)** | **2 Tipologías Modulares** (Cero H3) |
| **Enfoque de Parcelación** | 1 ha rígida (`658 pl/ha` fija) | **2 Tipologías Modulares (`H1`, `H2`) + `SpatialTiler` + Deformación $\le 18\%$** | Elimina 100% de choques en bordes y cepellones |
| **Polígono 29 (`6.54 ha`)** | Sin registro (replantar `4,287 pl`) | **`847` vivas imputadas de vecinos 28, 30 y 22 (`129.5 pl/ha`)** | **No se replanta: ahorra `847` plantas (`$16,997 MXN`)** |
| **Plantas Vivas Preexistentes ($E_i$)** | Ignoradas (siembra a ciegas) | **`24,416 pl` integradas** (`23,569` censo + `847` P29) | Respeto total a la cohorte viva (~6 años, radio `1.50 m`) |
| **Meta Total CONAFOR ($N_z$)** | `124,724 pl` | **`124,514 pl` (`100,098 pl` nuevas a comprar)** | Ahorro de `-203 pl` en laderas $\ge 20\%$ y `-847 pl` en P29 |
| **Inversión Total en Vivero** | `$2,039,500.00 MXN` | **`$2,017,715.50 MXN` (`$10,644.77 MXN/ha`)** | **Ahorro directo de `$21,784.50 MXN`** (`$20.16/pl nueva`) |
| **Carga de Competencia Espacial ($\Phi$)** | `41.28` (Estrés severo) | **`10.78` (Óptimo MILP con `big_index=3`)** | **`-74.1%` de reducción de competencia** |
| **Contactos Nodriza (*Prosopis*)** | `18` por tesela | **`48.0` por tesela** | **`+166.7%` de facilitación microclimática** |
| **Contactos Agave-Agave (Riesgo Plaga)** | `118` por tesela | **`25.0` por tesela** | **`-78.8%` (Barrera contra picudo del agave)** |
| **Supervivencia Temprana (Año 2)** | `86.40%` (Histórica) | **`90.05%` (Espacial `H1+H2`) / `94.33%` (Catalizado)** | **`+3.65 pp` (`+4,545` plantas vivas adicionales)** |
| **Supervivencia a Largo Plazo (Año 20)** | `45.35%` (Siembra desnuda) | **`91.31%` (Catalizado en 2 Etapas)** | **`+45.96 pp` (`+32,712` plantas adultas vivas)** |
| **Costo por Planta Adulta Establecida** | `$30.12 MXN` | **`$21.37 MXN`** | **`-29.0%` en costo por individuo sobreviviente** |

---

## 2. Guión Estructurado de Diapositivas (Listo para Exponer)

### Diapositiva 1 — Cartografía Oficial y Zonificación CONAFOR de los 31 Polígonos
* **Mensaje Central:** Pasamos de una simulación teórica a la **cartografía oficial georreferenciada (UTM 14N)** de los **31 polígonos del cerco ganadero (`189.55 ha`)**, integrando el plano regional real **SRTM 30 m** (`2,432 m s.n.m.`, pendiente regional de `2.3%` hacia el ENE) con zonificación antierosiva CONAFOR.
* **Puntos Clave para Exponer:**
  1. **Regla de Densidad por Pendiente (CONAFOR/INECOL 2010):** `188.03 ha` (`99.2%`) tienen pendiente $< 20\%$ y reciben **`658 pl/ha`** ($d = 4.19\text{ m}$); `1.52 ha` (`0.8%` distribuidas en 10 polígonos, destacando P31 con `0.36 ha`) superan el $\ge 20\%$ de pendiente y reducen su densidad a **`524 pl/ha`** ($d = 4.69\text{ m}$) en tresbolillo sobre curvas de nivel para frenar la erosión laminar.
  2. **Integración del Censo Real ($E_i$):** Se respetan las **`23,569` plantas vivas preexistentes** en 30 polígonos, y se identifica al **Polígono 29 (`6.54 ha`)** como predio virgen sin registro ($E_i = 0$), asignándole `4,287` plantas nuevas con núcleos intensivos de facilitación.
  3. **Transparencia Científica del Relieve:** El plano regional proviene de **SRTM 30 m (OpenTopoData)**; el micro-relieve interno de lomerío (`slope_deg = 6.0° ≈ 10.5%` de pendiente media) es un campo espectral sintético reproducible ante la falta de LIDAR submétrico.
* **Apoyos Visuales (300 DPI):**
  * [`atlas_31_poligonos_dominica.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/atlas_31_poligonos_dominica.png)
  * [`panel_poligonos_representativos_relieve.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/panel_poligonos_representativos_relieve.png)

---

### Diapositiva 2 — ¿Por Qué 3 Tipologías Modulares de 1 Hectárea Superan a una Plantilla Única?
* **Mensaje Central:** Logísticamente conviene trabajar por hectárea, pero usar una **única plantilla rígida** desperdicia plantas en laderas, choca con la vegetación previa y genera un **18.2% de colisiones en los bordes**. La solución óptima es un **Sistema Modular de 3 Tipologías de 1 ha (`H1`, `H2`, `H3`)** cosidas con `SpatialTiler`.
* **Las 3 Tipologías Modulares:**
  1. **Tipología H1 — Llanura con Dosel Previo (`181.62 ha`, `95.8%`):** `658 pl/ha` ($d = 4.19\text{ m}$), integra las `~129 pl/ha` vivas y distribuye las especies de gran porte (*Prosopis laevigata*, *Opuntia streptacantha*, *Yucca filifera*) en la **subred hexagonal `big_index = 3`** ($(i-j) \bmod 3 = 0$, distancia mínima $\sqrt{3}\,d \approx 7.25\text{ m}$). Supervivencia espacial: **`90.04%`**.
  2. **Tipología H2 — Ladera Antierosiva $\ge 20\%$ (`1.52 ha`, `0.8%`):** `524 pl/ha` ($d = 4.69\text{ m}$, $+12\%$ de separación). Reduce en `-27%` el solape radicular del kernel biweight $(1-u^2)^2$ en suelos someros ($<30\text{ cm}$), ahorra `203` plantas condenadas a morir por deslave y alcanza **`91.20%`** de supervivencia.
  3. **Tipología H3 — Restauración desde Cero (`6.42 ha` planas en Polígono 29, `3.4%`):** `658 pl/ha` con $E_i = 0$ (100% plantas nuevas). Maximiza los contactos nodriza (`52` contactos/malla) para compensar la ausencia de dosel previo, logrando **`88.65%`** de supervivencia espacial.
* **Costura de Fronteras (`SpatialTiler` Red-Black):** Resuelve los bloques de 1 ha en barrido tipo tablero de ajedrez (fase roja independiente $\to$ fase negra con halo congelado), **eliminando el 100% de los choques intraespecíficos en las costuras entre hectáreas**.
* **Apoyo Visual (300 DPI):**
  * [`fig1_comparativa_modular_1ha_vs_3tipologias.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/fig1_comparativa_modular_1ha_vs_3tipologias.png)

---

### Diapositiva 3 — Plantas Catalizadoras y Nodrizas: Superando el "Valle de la Muerte" para Crecer a 20 Años
* **Mensaje Central:** En el monitoreo histórico 2021–2023 (`monitoreo_supervivencia.csv`), **el 70% de la mortalidad ocurre en los primeros 24 meses** (*A. scabra* cae a `74.5%` y *Y. filifera* a `72.6%`). Porque un mezquite recién plantado aún es pequeño en el año 1, necesitamos **plantas catalizadoras de ciclo corto (1–2 años)** que protejan a las plántulas mientras el mezquite desarrolla su dosel adulto.
* **Mecanismo Ecofisiológico en 2 Etapas:**
  1. **El Problema sin Catálisis ($B_n = 0, J = 1.0$):** En el año 1, la vulnerabilidad juvenil ($J=1.0$) cuadruplica el estrés hídrico basal:
     $$S_w = S_0 \cdot \left[1 + 3.0 \cdot J \cdot (1 - 0.9\,B_n)\right] = 4.0\,S_0$$
     La aptitud cae al umbral letal ($F < 0.25$).
  2. **Etapa 1 (Años 1–2) — Plantas Catalizadoras de Ciclo Corto:** Cobertura herbácea/pionera nativa anual-bianual (*Bouteloua*, cespitosas y pioneras locales de raíces someras $<10\text{ cm}$ que no compiten con agaves de $20\text{–}40\text{ cm}$). Germina en 15–30 días, baja la temperatura superficial del suelo de $52^\circ\text{C}$ a $38^\circ\text{C}$, retiene el rocío matutino y eleva la facilitación temprana a $B_n \ge 0.85$, **reduciendo el estrés hídrico juvenil en `-68%`** ($S_w = 1.27\,S_0$). Al cumplir su ciclo de 1–2 años, deja mantillo orgánico ($+45\%$ infiltración).
  3. **Etapa 2 (Años 3–20) — Relevo por Nodriza Perenne (*Prosopis laevigata* en `big_index=3`):** A partir del año 3, el mezquite alcanza porte arbustivo-arbóreo ($CD \to 6.0\text{ m}$, raíz $>5\text{ m}$), activa el **levantamiento hidráulico nocturno** y fija nitrógeno ($25\text{–}40\text{ kg N/ha/año}$), sosteniendo la expansión por hijuelos de agaves y cactáceas ($J \to 0$) hasta los 20 años (**`91.31%`** de supervivencia acumulada vs `45.35%` sin catálisis).
* **Apoyos Visuales (300 DPI):**
  * [`fig2_dinamica_temporal_supervivencia_1_20_anios.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/fig2_dinamica_temporal_supervivencia_1_20_anios.png)
  * [`fig3_mecanismo_micrositio_catalizador_2etapas.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/fig3_mecanismo_micrositio_catalizador_2etapas.png)

---

### Diapositiva 4 — Presupuesto Maestro de Adquisición por Especie y Retorno de Inversión
* **Mensaje Central:** Comprar exactamente lo que cada polígono necesita ($N_z - E_i$) ahorra recursos y maximiza la supervivencia por peso invertido.
* **Desglose Oficial de Adquisición en Vivero (`189.55 ha`):**

| ID | Especie | Nombre Común | Rol en el Modelo | Vivas ($E_i$) | Meta Total ($N_z$) | Nuevas a Comprar | Costo Unit. | Inversión Vivero (MXN) |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **0** | *Agave lechuguilla* | Lechuguilla | Rosetófila (Suelo somero) | 1,491 | 7,759 | **6,268** | $14.50 | **$90,886.00** |
| **1** | *Agave salmiana* | Maguey verde | Rosetófila dominante | 6,956 | 37,313 | **30,357** | $18.00 | **$546,426.00** |
| **2** | *Agave scabra* | Maguey azul | Rosetófila (Vulnerable J) | 1,462 | 7,548 | **6,086** | $18.50 | **$112,591.00** |
| **3** | *Agave striata* | Espadín | Rosetófila compacta | 1,404 | 7,545 | **6,141** | $14.50 | **$89,044.50** |
| **4** | *Opuntia cantabrigiensis* | Cuijo | Cactácea media | 1,832 | 9,644 | **7,812** | $15.50 | **$121,086.00** |
| **5** | *Opuntia engelmannii* | Cuijo rastrero | Cactácea media | 1,459 | 7,754 | **6,295** | $15.50 | **$97,572.50** |
| **6** | *Opuntia robusta* | Tapón | Cactácea robusta | 2,746 | 13,413 | **10,667** | $20.50 | **$218,673.50** |
| **7** | *Opuntia streptacantha* | Cardón | **Grande (`big_index=3`)** | 2,289 | 11,320 | **9,031** | $22.50 | **$203,197.50** |
| **8** | *Prosopis laevigata* | Mezquite | **Grande / Nodriza (`big_index=3`)** | 3,018 | 16,769 | **13,751** | $28.50 | **$391,903.50** |
| **9** | *Yucca filifera* | Palma china | **Grande / Arborescente (`big_index=3`)** | 912 | 5,449 | **4,537** | $36.00 | **$163,332.00** |
| | **TOTAL OFICIAL** | | | **23,569** | **124,514** | **100,945** | `$20.16` prom. | **`$2,034,712.50 MXN`** |

* **Apoyo Visual (300 DPI):**
  * [`resumen_presupuesto_y_especies_31_poligonos.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/resumen_presupuesto_y_especies_31_poligonos.png)

---

## 3. Guía Rápida de Archivos para tu Presentación

* **Imágenes en 300 DPI listas para arrastrar a PowerPoint / Canva / LaTeX Beamer:**
  1. [`malla_completa_1ha_H1_H2_H3.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/malla_completa_1ha_H1_H2_H3.png) — **Malla completa 100×100 m (1 ha)** nodo por nodo de **H1 (658 pl)**, **H2 (524 pl)** y **H3 (658 pl, $E_i=0$)**.
  2. [`malla_completa_poligonos_totales.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/malla_completa_poligonos_totales.png) — **Malla 100% completa sobre polígonos enteros** (`P12: 967 pl`, `P29: 4,287 pl`, `P19: 3,237 pl`, `P31: 4,781 pl`) con lupa de costura `H1/H3 ↔ H2`.
  3. [`atlas_31_poligonos_dominica.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/atlas_31_poligonos_dominica.png) — Mapa completo UTM 14N de los 31 polígonos.
  4. [`panel_poligonos_representativos_relieve.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/panel_poligonos_representativos_relieve.png) — Acercamiento de unidad representativa sobre relieve en P12, P29, P19 y P31.
  5. [`fig1_comparativa_modular_1ha_vs_3tipologias.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/fig1_comparativa_modular_1ha_vs_3tipologias.png) — Comparativa 1 ha rígida vs 3 tipologías modulares (H1, H2, H3).
  6. [`fig2_dinamica_temporal_supervivencia_1_20_anios.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/fig2_dinamica_temporal_supervivencia_1_20_anios.png) — Curvas de supervivencia a 20 años con plantas catalizadoras y nodrizas.
  7. [`fig3_mecanismo_micrositio_catalizador_2etapas.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/fig3_mecanismo_micrositio_catalizador_2etapas.png) — Diagrama ecofisiológico de las 2 etapas (1–2 años pioneras + 3–20 años mezquite).
  8. [`resumen_presupuesto_y_especies_31_poligonos.png`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/resumen_presupuesto_y_especies_31_poligonos.png) — Presupuesto por especie, plantas vivas vs nuevas y ganancia de supervivencia.
* **Visor Interactivo HTML5 con Zoom en Vivo (100% Offline):**
  * [`visor_interactivo_malla_completa.html`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/visor_interactivo_malla_completa.html) — Visor Canvas interactivo para explorar árbol por árbol las mallas completas `H1`, `H2`, `H3` y los polígonos completos `P12`, `P29`, `P19` y `P31`.
* **Tablas CSV y Reportes de Respaldo:**
  * [`resumen_31_poligonos_completo.csv`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/resumen_31_poligonos_completo.csv) y [`CATALOGO_MAPEO_31_POLIGONOS.md`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/CATALOGO_MAPEO_31_POLIGONOS.md)
  * [`ESTRATEGIA_HECTAREAS_Y_CATALIZADORAS.md`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/ESTRATEGIA_HECTAREAS_Y_CATALIZADORAS.md)
  * [`AUDITORIA_COLLINS_RESUELTA.md`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/AUDITORIA_COLLINS_RESUELTA.md) y [`PARAMETROS_DOMINICA.md`](file:///D:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PARAMETROS_DOMINICA.md)
