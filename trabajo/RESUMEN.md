# Resumen Ejecutivo de Orquestación, Integración, Auditoría Científica y Mapeo de 31 Polígonos (`RESUMEN.md`)

**Orquestador**: Argon  
**Directorio de trabajo**: `d:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\`  
**Actualización**: 23 de octubre de 2026 (Integra reconciliación con auditoría de Collins `collins/citas_resumen_orquestador.xlsx` + `referencias_modelo.md`, análisis de tipologías de hectárea y plantas catalizadoras a 20 años, y mapeo completo de los 31 polígonos oficiales en GPU + HiGHS).

---

## 1. Arquitectura de Orquestación por Fases y Subagentes

### Fase I — Integración Base del Pipeline (`Subagentes 1, 2 y 3`)
1. **Subagente 1 (`trabajo/subagente_1/`, `53047da1-957b-4218-8475-faf1bb79c1c3`, `flash`)**:
   - Importó los archivos oficiales de `poli31/` (31 polígonos en UTM 14N, `189.55 ha` totales).
   - Implementó `load_poli31_datasets` y adaptó `load_semiraw_datasets` con `--poligonos-dir` y `--poligono-id 1..31`.
   - Manejó explícitamente el **Polígono 29 (`6.54 ha`, sin registro de plantas vivas en `registro_oficial31.csv`)** con $E_i = 0$ y bandera `sin_registro_vivas = True` (excluyéndolo del muestreo empírico de densidades en `run_monte_carlo_rtx3060` para no sesgar la media de los 30 polígonos censados).
2. **Subagente 2 (`trabajo/subagente_2/`, `8991aa01-5cd9-4110-9e23-272026052034`, `flash` / `flash_lite`)**:
   - Implementó la restricción de subred `--big-index` (`(i - j) % big_index == 0`) para las 3 especies de mayor porte (`7: Opuntia streptacantha`, `8: Prosopis laevigata`, `9: Yucca filifera`) en `HexGridGraph`, ubicación de preexistentes, warm-start en GPU (`gpu_parallel_annealing_warmstart`), solver MILP exacto (Gurobi/HiGHS) y `SpatialTiler`.
   - En `modelo_dominica` (§1 y §19), `big_index = 3` es el valor estructural activo por diseño (restringe especies de nivel 1 a 1 de cada 3 nodos, separados por $\sqrt{3}\,a \approx 7.25\text{ m}$); en el CLI de `REFORESTATHON` se dejó `--big-index 0` por defecto únicamente para conservar retrocompatibilidad con la línea base histórica, activándose con `--big-index 3`.
3. **Subagente 3 (`trabajo/subagente_3/`, `ef8bf505-2b0b-4fb3-92ce-ed440d3b5569`, `flash`)**:
   - Integró `terreno.py` sin modificarlo y añadió `--plot-relief` y `--relief-slope-deg` para proyectar las asignaciones sobre el relieve sombreado (`LightSource`), curvas de nivel, zonas con pendiente $\ge 20\%$ y recorte al polígono UTM, declarando explícitamente qué parte es real (**SRTM 30 m de 5 puntos**, ref. #28) y qué parte es sintética (**lomerío espectral `_band_fractal`**, sección H de `referencias_modelo.md`).

---

### Fase II — Reconciliación Forense con Collins, Estrategia Modular/Catalizadoras y Mapeo de los 31 Polígonos (`Subagentes A, B y C`)

1. **[Subagente A — Auditoría Científica y Reconciliación con Collins](conversation://262a04be-865d-4212-9a0b-d5cc51e20ba1) (`flash`)**:
   - Resolvió las **12 observaciones** de [`collins/citas_resumen_orquestador.xlsx`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/collins/citas_resumen_orquestador.xlsx) en [`trabajo/PARAMETROS_DOMINICA.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PARAMETROS_DOMINICA.md) y documentó el dictamen completo en [`trabajo/AUDITORIA_COLLINS_RESUELTA.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/AUDITORIA_COLLINS_RESUELTA.md).
   - **Desacoplamiento físico de unidades de pendiente (Observación #10)**: En `reforestacion_pipeline_integrado.py` se separó `--slope-pct` (pendiente porcentual para la norma CONAFOR del $20\%$) de `--relief-slope-deg` (ángulo en grados del generador fractal `terreno.py`, default $6.0^\circ \approx 10.5\%$ de pendiente media, calibrado en §19.11 de `parametros_modelo.md` para que el $0.8\%$ del sitio supere el $20\%$).
2. **[Subagente B — Estratega Ecológico: 3 Tipologías de Hectárea y Plantas Catalizadoras](conversation://359bcc6e-aef6-4524-970d-769083853fea) (`flash`)**:
   - Evaluó cuantitativamente el **Sistema Modular de 3 Tipologías de Hectárea (H1, H2, H3)** acopladas con `SpatialTiler` frente a una plantilla rígida única de 1 ha.
   - Modeló la trayectoria ecofisiológica de **Establecimiento Catalizado en 2 Etapas (0 a 20 años)**: cobertura herbácea/pionera de ciclo corto (1–2 años) para amortiguar el cuello de botella juvenil ($J=1.0$, donde ocurre el $70\%$ de la mortalidad histórica según `monitoreo_supervivencia.csv`) combinada con *Prosopis laevigata* como nodriza perenne en la subred `big_index=3` para los años 3–20.
   - Documentó todo en [`trabajo/ESTRATEGIA_HECTAREAS_Y_CATALIZADORAS.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/ESTRATEGIA_HECTAREAS_Y_CATALIZADORAS.md) y generó las figuras de alta resolución `fig1`, `fig2` y `fig3` (300 DPI).
3. **[Subagente C — Ejecutor Maestro del Mapeo de los 31 Polígonos Oficiales](conversation://bb3ab429-b9d4-4679-b273-4ce7730b574f) (`flash`)**:
   - Ejecutó la zonificación topográfica (`seed=1` unificado del DEM regional), el warm-start en GPU RTX 3060 y el solver MILP HiGHS sobre los **31 polígonos oficiales (`189.55 ha`)**.
   - Generó [`CATALOGO_MAPEO_31_POLIGONOS.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/CATALOGO_MAPEO_31_POLIGONOS.md), [`resumen_31_poligonos_completo.csv`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/resumen_31_poligonos_completo.csv) y los mapas cartográficos en 300 DPI (`atlas_31_poligonos_dominica.png`, `panel_poligonos_representativos_relieve.png`, `resumen_presupuesto_y_especies_31_poligonos.png`).

---

## 2. Síntesis de Reconciliación con la Auditoría de Collins (`citas_resumen_orquestador.xlsx`)

Todas las observaciones señaladas por Collins fueron verificadas contra `parametros_modelo.md`, `poligonos_oficiales_31.md` y [`collins/referencias_modelo.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/collins/referencias_modelo.md):

1. **Kernel de distancia (§3)**: Tanto `modelo_dominica` como `REFORESTATHON` evalúan el **kernel biweight (cuadrático)** $K(u) = (1 - u^2)^2$ (con constante de normalización $\frac{15}{16}$ en estadística no paramétrica) para $|u| \le 1$, no el kernel lineal de Epanechnikov $(1-u^2)_+$. Respaldo secundario (Wikipedia); referencias primarias (Epanechnikov 1969; Silverman 1986) sin verificar en texto completo.
2. **Niveles de talla en §6**: `parametros_modelo.md` §6 define `"Nivel (grande, mediano, pequeño): HEURÍSTICO"` (tres niveles). La partición binaria operativa de las 3 especies de nivel grande `(7: O. streptacantha, 8: P. laevigata, 9: Y. filifera)` para la subred `big_index=3` corresponde a §19.
3. **Diámetros de copa adulta (§19.3)**: En `parametros_modelo.md` §19.3, *A. lechuguilla* (`0.60 m`) y *A. striata* (`1.20 m`) son derivados de tallas botánicas (FEIS #29 y longitud de hoja), mientras que *A. scabra* (`1.75 m`) y *A. salmiana* (`3.60 m`) provienen de fuente secundaria (#33 Wikipedia). Las **6 copas adultas `[guessing]` sin fuente** de §19.3 son: *O. cantabrigiensis* (`2.0 m`), *O. engelmannii* (`2.5 m`), *O. robusta* (`3.0 m`), *O. streptacantha* (`3.5 m`), *Prosopis laevigata* (`6.0 m`) y *Yucca filifera* (`3.0 m`).
4. **Edades ontogenéticas y pesos (§2)**: En `modelo_dominica` §2 son `ages = (1, 6, 20)` años con pesos `age_w = (0.3, 0.3, 0.4)` (`HEURÍSTICO`). La sección §19.9 corresponde al análisis de sensibilidad a la pendiente media del relieve simulado.
5. **Cohorte viva preexistente (§18.2 y §19)**: Tiene una edad estimada de `6 años` (`COHORT_AGE = 6`, `[likely]`) y su tamaño sigue la curva monomolecular $f(t+6) = f_0 + (1-f_0)(1 - e^{-(t+6)/\tau})$ con $\tau$ por especie. La sección §19.4 documenta el tresbolillo y zonas de pendiente CONAFOR.
6. **Vínculo aptitud $\to$ supervivencia $g(F)$ (§4)**: En `modelo_dominica` §4 es la función logística $g(F) = 1 / (1 + \exp[-(F - 0.25)/0.05])$ con `dead_thr = 0.25` y `slope = 0.05` (`PLACEHOLDER`, no calibrado con mortalidad observada). En `REFORESTATHON` las tasas de supervivencia base 2021–2023 provienen del monitoreo empírico (`monitoreo_supervivencia.csv`).
7. **Radio de truncamiento (§1 y §12)**: En `modelo_dominica` §1 es `range_m = 14 m` (`HEURÍSTICO`, inerte al $\pm 30\%$ en §12); `MAX_R = 10 m` era propio de una versión previa de `REFORESTATHON`. §19.7 documenta las pruebas en el Polígono 12.
8. **Parámetros matriciales de `REFORESTATHON`**: `B_SAME`, `B_DIFF` y `STRESS_W` pertenecen a `REFORESTATHON`, no a `parametros_modelo.md` (§19.8 describe los 31 terrenos simulados).
9. **Empates de área oficial (§19.1)**: En `poligonos_oficiales_31.md` y §19.1, los empates reales de área oficial son **`8.0 ha`** (5 polígonos: P3, P4, P9, P10, P21), **`5.64 ha`** (2 polígonos: P16, P24) y **`5.4 ha`** (2 polígonos: P1, P15), resueltos por orden de lectura del mapa. `1.47 ha` es única del Polígono 12.
10. **Unidades de pendiente (`slope_deg = 6.0°` vs `20%` CONAFOR)**: Desacoplado en CLI mediante `--relief-slope-deg 6.0` (grados en `terreno.py`, equivalente a $\tan(6^\circ) \approx 10.5\%$ de pendiente media) y `--slope-pct` (porcentaje para la regla CONAFOR de $20\%$).
11. **Orden de `PLANTED` en `hexgarden.py`**: Documentado como deliberado en `poligonos_oficiales_31.md` (`lechuguilla, striata, scabra, salmiana, ...`). `REFORESTATHON` cruza por nombre científico explícito, evitando cualquier desfase.
12. **`big_index = 3` vs `0`**: Documentado que `3` es el valor por diseño en `modelo_dominica` (§19) y `0` es la guarda de retrocompatibilidad en el CLI de `REFORESTATHON`.

---

## 3. Resultados Consolidados del Mapeo de los 31 Polígonos Oficiales (`189.55 ha`)

Ejecutado con `seed=1` (DEM regional unificado SRTM 30 m + lomerío fractal a $6.0^\circ$), `big_index=3`, warm-start en GPU RTX 3060 (256 réplicas) y solver exacto HiGHS Branch-and-Cut:

| Métrica Global del Parque Eólico Dominica | Valor Oficial Consolidado | Respaldo / Fuente |
| :--- | :---: | :--- |
| **Superficie Oficial Total (31 Polígonos)** | **`189.55 ha`** | Mapa oficial cerco ganadero UTM 14N (`poli31/`) |
| **Superficie Plana ($< 20\%$ pendiente, Tipología H1)** | **`188.03 ha` (`99.2%`)** | `658 pl/ha` (Ficha CONAFOR/INECOL 2010; incluye `6.42 ha` de P29) |
| **Superficie en Ladera ($\ge 20\%$ pendiente, Tipología H2)** | **`1.52 ha` (`0.8%`)** | `524 pl/ha` en 10 polígonos (P1, P8, P10, P18, P22, P24, P25, P28, P29, P31) |
| **Plantas Vivas Preexistentes ($E_i$)** | **`24,416 pl`** | `23,569` censadas en 30 polígonos + **`847` imputadas en Polígono 29** desde vecinos `28, 30 y 22` (`129.5 pl/ha`) |
| **Meta Total de Plantación CONAFOR ($N_z$)** | **`124,514 pl`** | $\lfloor 658 A_{<20\%} \rfloor + \lceil 524 A_{\ge 20\%} \rceil$ por polígono |
| **Plantas Nuevas a Adquirir en Vivero ($N_z - E_i$)** | **`100,098 pl`** | Desglosadas por especie y polígono en `resumen_31_poligonos_completo.csv` (ahorra replantar `847` en P29) |
| **Inversión Total en Vivero** | **`$2,017,715.50 MXN`** | Promedio: `$10,644.77 MXN/ha` (`$20.16 MXN/planta nueva`; ahorro extra de `$16,997 MXN` en P29) |
| **Supervivencia Base Histórica (Monitoreo 2023)** | **`86.40%`** | `monitoreo_supervivencia.csv` (2021–2023) |
| **Supervivencia Efectiva Espacial (Año 2, tresbolillo + `big_index=3`)** | **`89.69%` (`90.05%` con H1+H2)** | **`+3.29%` a `+3.65%` de ganancia neta** (`+4,545` plantas vivas adicionales) |
| **Supervivencia a Largo Plazo (Año 20, Catalizado 2 Etapas)** | **`91.31%` (vs `45.35%` sin catálisis)** | **`+45.96 pp` de ganancia a 20 años** (`+32,712` plantas adultas vivas) |

---

## 4. Índice Maestro de Entregables y Apoyos Visuales (300 DPI)

### Documentos Ejecutivos y Técnicos
1. [`PRESENTACION_EJECUTIVA_MAESTRA.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/PRESENTACION_EJECUTIVA_MAESTRA.md): Guía maestra de presentación y diapositivas lista para exponer.
2. [`trabajo/ESTRATEGIA_HECTAREAS_Y_CATALIZADORAS.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/ESTRATEGIA_HECTAREAS_Y_CATALIZADORAS.md): Análisis estratégico de 1 ha rígida vs 3 tipologías modulares (H1, H2, H3) y plantas catalizadoras/nodrizas a 20 años.
3. [`trabajo/integracion/outputs_presentacion/CATALOGO_MAPEO_31_POLIGONOS.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/CATALOGO_MAPEO_31_POLIGONOS.md): Catálogo completo de los 31 polígonos oficiales y presupuesto de vivero por especie.
4. [`trabajo/AUDITORIA_COLLINS_RESUELTA.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/AUDITORIA_COLLINS_RESUELTA.md) y [`trabajo/PARAMETROS_DOMINICA.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PARAMETROS_DOMINICA.md): Auditoría científica reconciliada al 100% con las observaciones y referencias de Collins.

### Apoyos Visuales en 300 DPI y Visor Interactivo (`trabajo/integracion/outputs_presentacion/`)
1. [`malla_completa_1ha_H1_H2_H3.png`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/malla_completa_1ha_H1_H2_H3.png): **Malla completa 100×100 m (1 ha)** nodo a nodo de las 3 tipologías modulares: **H1** (`658` nodos, $d=4.19\text{ m}$, `129` vivas + `529` nuevas), **H2** (`524` nodos, $d=4.69\text{ m}$ en curva de nivel $\ge 20\%$) y **H3** (`658` nodos, $E_i=0$).
2. [`malla_completa_poligonos_totales.png`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/malla_completa_poligonos_totales.png): **Mapeo 100% completo de todas las plantas** sobre polígonos enteros (`P12: 967 pl`, `P29: 4,287 pl`, `P19: 3,237 pl`, `P31: 4,781 pl`) con lupa de costura `H1/H3 ↔ H2`.
3. [`visor_interactivo_malla_completa.html`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/visor_interactivo_malla_completa.html): **Visor interactivo HTML5 Canvas (offline)** con zoom/pan a 60 FPS para inspeccionar árbol por árbol las 7 vistas completas (`15,112` nodos y `44,471` aristas).
4. [`atlas_31_poligonos_dominica.png`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/atlas_31_poligonos_dominica.png): Mapa cartográfico UTM 14N de los 31 polígonos sobre relieve SRTM 30 m con manchas de pendiente $\ge 20\%$ y supervivencia efectiva.
5. [`panel_poligonos_representativos_relieve.png`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/panel_poligonos_representativos_relieve.png): Panel 2x2 de relieve y unidad representativa (`big_index=3`) en Polígonos 12, 29, 19 y 31.
6. [`resumen_presupuesto_y_especies_31_poligonos.png`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/resumen_presupuesto_y_especies_31_poligonos.png): Desglose de plantas preexistentes vs nuevas, presupuesto de vivero (`$2,034,712.50 MXN`) y ganancia de supervivencia por especie.
7. [`fig1_comparativa_modular_1ha_vs_3tipologias.png`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/fig1_comparativa_modular_1ha_vs_3tipologias.png): Comparativa entre plantilla rígida de 1 ha y Sistema Modular de 3 Tipologías (H1, H2, H3) + `SpatialTiler`.
8. [`fig2_dinamica_temporal_supervivencia_1_20_anios.png`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/fig2_dinamica_temporal_supervivencia_1_20_anios.png): Curvas de supervivencia de 0 a 20 años superando el cuello de botella juvenil (años 1–2).
9. [`fig3_mecanismo_micrositio_catalizador_2etapas.png`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/outputs_presentacion/fig3_mecanismo_micrositio_catalizador_2etapas.png): Infografía ecofisiológica del micrositio catalizador en 2 etapas (cobertura pionera 1–2 años + *Prosopis* adulto 3–20 años).
