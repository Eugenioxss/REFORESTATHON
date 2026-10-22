# Resumen Ejecutivo de Orquestación, Integración y Validación (`RESUMEN.md`)

**Orquestador**: Argon  
**Directorio de trabajo aislado**: `d:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\`  
**Estado de archivos originales**: Intactos (0 modificaciones en `REFORESTATHON` raíz y 0 modificaciones en `modelo_dominica`).

---

## 1. Trabajo Realizado por Fase y por Subagente

### Paso 0 y Paso 1 — Línea Base, Auditoría de Parámetros y Planificación (Orquestador)
1. **Línea Base (`trabajo/base/`)**:
   - Se copió `scripts/src/reforestacion_pipeline.py` y `data/semiraw/*` a `trabajo/base/`.
   - Se ejecutó el solver exacto (`--time-limit 30 --solver highs`) y se documentaron las métricas de referencia en [`trabajo/base/METRICAS_BASE.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/base/METRICAS_BASE.md).
2. **Auditoría Botánica y Matemática (`trabajo/PARAMETROS_DOMINICA.md`)**:
   - Se auditaron exhaustivamente los archivos de `modelo_dominica` (`README.md`, `parametros_modelo.md`, `hexgarden.py`, `terreno.py`, `pipeline.py`, `poli31/*`) frente a `REFORESTATHON`.
   - Se verificó el mapeo de especies entre ambos proyectos: aunque `hexgarden.PLANTED` intercambia las posiciones 1 (*Agave striata*) y 3 (*Agave salmiana*) respecto al catálogo de `REFORESTATHON`, el archivo `poli31/registro_oficial31.csv` usa nombres explícitos en el mismo orden de `REFORESTATHON`, y **las tres especies de talla grande tienen exactamente los mismos índices `(7, 8, 9)` en ambos proyectos**: `7 = Opuntia streptacantha`, `8 = Prosopis laevigata`, `9 = Yucca filifera`.
   - Se documentó el plan maestro en [`trabajo/PLAN.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PLAN.md).

### Paso 2 — Subagente 1: Importación de `poli31/` y Adaptación de Entrada (`trabajo/subagente_1/`)
- **Conversación**: `53047da1-957b-4218-8475-faf1bb79c1c3` (Modelo: `flash`).
- **Trabajo realizado**:
  - Importó los 7 archivos de `modelo_dominica/poli31/` a `trabajo/subagente_1/data/poli31/`.
  - Implementó `load_poli31_datasets(poligonos_dir)` y adaptó `load_semiraw_datasets(poligonos_dir=None)` manteniendo retrocompatibilidad total cuando no se pasa `--poligonos-dir` (salvo que se invoque `--poligono-id 31`, en cuyo caso activa `poli31/` automáticamente).
  - En `load_poli31_datasets`, cruzó `poligonos_31.csv` (31 polígonos UTM 14N) con `registro_oficial31.csv` (30 filas), asignando al **Polígono 29 (`6.54 ha`, sin registro de plantas vivas)** vector de conteos `0` y bandera `sin_registro_vivas = True`.
  - Adaptó `run_monte_carlo_rtx3060` para excluir polígonos con `sin_registro_vivas == True` al muestrear densidades históricas por hectárea (`df_valid = df_wide[~df_wide["sin_registro_vivas"]]`), evitando sesgar a la baja la media empírica de los 30 polígonos censados.
  - Adaptó `build_real_preexisting_nodes_from_csv` para retornar inmediatamente `fixed_nodes = {}` y `E_i = np.zeros(n_sp, dtype=int)` cuando `total_est == 0.0` (caso del Polígono 29).
  - Añadió los argumentos CLI `--poligono-id 1..31` y `--poligonos-dir`.
  - Documentó resultados en [`trabajo/subagente_1/REPORTE_SUBAGENTE_1.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/subagente_1/REPORTE_SUBAGENTE_1.md).

### Paso 3A — Subagente 2: Restricción `big_index` en Malla, Heurísticas y MILP (`trabajo/subagente_2/`)
- **Conversaciones**: `2717e4d0-2fec-4a1c-a745-b4442c12ec26` (`flash`, Intento 1) y `8991aa01-5cd9-4110-9e23-272026052034` (`flash_lite`, Intento 2 para finalizar `main()` tras límite de tasa 429).
- **Trabajo realizado**:
  - Definió `BIG_SPECIES_IDS: Tuple[int, ...] = (7, 8, 9)` con comentario explícito de trazabilidad (`# origen: modelo_dominica, categoría b`).
  - Extendió `HexGridGraph` y `build_tres_bolillos_graph` con coordenadas reticulares `grid_i`, `grid_j`, `big_index: int = 0` y máscara booleana `big_mask = ((grid_i - grid_j) % big_index == 0)` cuando `big_index > 1` (o `np.ones(m, dtype=bool)` cuando `big_index <= 1`). En la malla `6x11` (`66` nodos), `big_index=3` habilita exactamente `22/66` nodos (1/3 de la retícula).
  - Sincronizó `build_real_preexisting_nodes_from_csv` para ubicar las plantas preexistentes de especies `(7, 8, 9)` dentro de `big_mask` cuando `big_index > 1`, reportando advertencia si el conteo preexistente excede la capacidad de la subred.
  - Sincronizó `gpu_parallel_annealing_warmstart` para inicializar las réplicas de especies grandes dentro de `big_mask` y rechazar swaps en GPU que muevan especies `(7, 8, 9)` a nodos con `big_mask == False`.
  - En `solve_reforestation_mip` (tanto en el bloque **Gurobi** como en el bloque **HiGHS**), fijó cota superior `UB = 0.0` (`x[i, p].UB = 0.0` / `ub_bounds[p * n_sp + i] = 0.0`) para `i in (7, 8, 9)` en todo nodo libre con `not graph.big_mask[p]`, respetando exenciones de factibilidad si alguna planta preexistente fija cayera fuera de `big_mask` o si la suma de cotas inferiores `lb_i` de especies grandes superara los nodos disponibles en la subred.
  - Añadió soporte en `SpatialTiler` y la bandera CLI `--big-index N` (`default=0`, apagada por defecto).
  - Documentó resultados en [`trabajo/subagente_2/REPORTE_SUBAGENTE_2.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/subagente_2/REPORTE_SUBAGENTE_2.md).

### Paso 3B — Subagente 3: Proyección de Gráficos sobre Relieve (`trabajo/subagente_3/`)
- **Conversación**: `ef8bf505-2b0b-4fb3-92ce-ed440d3b5569` (Modelo: `flash`).
- **Trabajo realizado**:
  - Copió `modelo_dominica/terreno.py` (sin modificaciones) a `trabajo/subagente_3/scripts/src/terreno.py` y `modelo_dominica/poli31/*` a `trabajo/subagente_3/data/poli31/`.
  - Implementó `build_relief_terrain(poligono_id, slope_deg, seed, poli31_dir)` que instancia `Terrain.from_poligonos(...)` conectado a `poligonos_31.csv`, `poligonos_utm.csv` y `dem_srtm_puntos.csv`, y calcula la zonificación `terrain.zonas(pend_pct=20.0, min_ha=0.10)`.
  - Implementó `fit_graph_coords_to_polygon(graph_coords, terrain)` para encajar las coordenadas de la malla en el interior del polígono real (`terrain.inside(pts)`).
  - Implementó `export_relief_visualization(...)` e integró su llamada opcional en `export_visualizations(...)` cuando se activa `--plot-relief` (con `--relief-poligono-id`, por defecto `12`).
  - Los mapas `mapa_tres_bolillos_relieve*.png` muestran sombreado topográfico (`LightSource`), curvas de nivel cada 1 m, contorno y sombreado rojo de zonas con pendiente $\ge 20\%$, recorte al polígono UTM, aristas/nodos por especie, cepas preexistentes $E_i$ y una leyenda inferior explícita que distingue la componente real (**SRTM 30 m de 5 puntos**) de la sintética (**lomerío fractal `_band_fractal`**).
  - Documentó resultados en [`trabajo/subagente_3/REPORTE_SUBAGENTE_3.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/subagente_3/REPORTE_SUBAGENTE_3.md).

### Paso 4 — Integración y Validación (Orquestador)
- Se unificaron los cambios de los 3 subagentes en [`trabajo/integracion/reforestacion_pipeline_integrado.py`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/reforestacion_pipeline_integrado.py) (y su espejo en `trabajo/integracion/scripts/src/reforestacion_pipeline.py`).
- Se ejecutaron las dos corridas completas de validación del solver (`--big-index 0` y `--big-index 3 --plot-relief`), la verificación sobre `poli31` (Polígono 29 y Polígono 12) y la suite de 21 pruebas unitarias (`tests/test_mathematical_ecological_adversarial.py`).

---

## 2. Archivos Creados en `trabajo/`

- **Planificación y Auditoría**:
  - [`trabajo/PLAN.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PLAN.md)
  - [`trabajo/PARAMETROS_DOMINICA.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PARAMETROS_DOMINICA.md)
  - [`trabajo/PENDIENTES.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PENDIENTES.md)
  - [`trabajo/RESUMEN.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/RESUMEN.md)
- **Línea Base (`trabajo/base/`)**:
  - [`trabajo/base/METRICAS_BASE.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/base/METRICAS_BASE.md)
  - `trabajo/base/scripts/src/reforestacion_pipeline.py`
  - `trabajo/base/scripts/outputs/*` (CSV, LP y PNG de referencia)
- **Subagente 1 (`trabajo/subagente_1/`)**:
  - [`trabajo/subagente_1/REPORTE_SUBAGENTE_1.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/subagente_1/REPORTE_SUBAGENTE_1.md)
  - [`trabajo/subagente_1/scripts/src/reforestacion_pipeline.py`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/subagente_1/scripts/src/reforestacion_pipeline.py)
  - `trabajo/subagente_1/data/poli31/*` (7 archivos importados de `modelo_dominica/poli31/`)
- **Subagente 2 (`trabajo/subagente_2/`)**:
  - [`trabajo/subagente_2/REPORTE_SUBAGENTE_2.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/subagente_2/REPORTE_SUBAGENTE_2.md)
  - [`trabajo/subagente_2/scripts/src/reforestacion_pipeline.py`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/subagente_2/scripts/src/reforestacion_pipeline.py)
- **Subagente 3 (`trabajo/subagente_3/`)**:
  - [`trabajo/subagente_3/REPORTE_SUBAGENTE_3.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/subagente_3/REPORTE_SUBAGENTE_3.md)
  - [`trabajo/subagente_3/scripts/src/reforestacion_pipeline.py`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/subagente_3/scripts/src/reforestacion_pipeline.py)
  - [`trabajo/subagente_3/scripts/src/terreno.py`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/subagente_3/scripts/src/terreno.py)
  - `trabajo/subagente_3/scripts/outputs/mapa_tres_bolillos_relieve*.png`
- **Integración (`trabajo/integracion/`)**:
  - [`trabajo/integracion/reforestacion_pipeline_integrado.py`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/reforestacion_pipeline_integrado.py)
  - [`trabajo/integracion/scripts/src/reforestacion_pipeline.py`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/scripts/src/reforestacion_pipeline.py)
  - [`trabajo/integracion/terreno.py`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/terreno.py) y `trabajo/integracion/scripts/src/terreno.py`
  - `trabajo/integracion/scripts/outputs/mapa_tres_bolillos_relieve.png` (y `_0pct.png`, `_5pct.png`, `_10pct.png`)
  - `trabajo/integracion/scripts/outputs/comparativa_holgura_0_5_10.csv`

---

## 3. Comparación de Métricas: Línea Base vs. Integrado (`--big-index 0` y `--big-index 3`)

Todas las corridas se ejecutaron con HiGHS Branch-and-Cut (`14 hilos`, `--time-limit 30`, malla `6x11`, pendiente `6.0%`, datos base `data/semiraw/`).

### 3.1 Tabla Comparativa de Optimización Exacta (`ObjVal Z`, `Phi`, `BestBound`, `MIPGap`)

| Escenario | Métrica | Línea Base (`trabajo/base`) | Integrado `--big-index 0` (Corrida a) | Integrado `--big-index 3` (Corrida b) | Diferencia (`--big-index 3` vs Base) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Benchmark 1D (`1x22`)** | `ObjVal (Z)` | `1.5998` | `1.5998` | `1.5998` | `0.0000` (Idéntico) |
| | `BestBound` | `1.5905` | `1.5905` | `1.5905` | `0.0000` |
| | `MIPGap (%)` | `0.58%` | `0.58%` | `0.58%` | `0.00 pp` |
| **2D `6x11` Holgura ±0%** | `ObjVal (Z)` | `12.4293` | `12.4293` | `11.4906` | **`-0.9387`** (Menor costo*) |
| | `Costo Phi` | `11.8883` | `11.8883` | `10.9496` | `-0.9387` |
| | `BestBound` | `12.1314` | `12.1314` | `11.2167` | `-0.9147` |
| | `MIPGap (%)` | `2.40%` | `2.40%` | `2.38%` | `-0.02 pp` |
| | `Contactos Intra` | `1` | `1` | `0` | `-1` |
| | `Nodrizas` | `46` | `46` | `45` | `-1` |
| **2D `6x11` Holgura ±5%** | `ObjVal (Z)` | `11.2935` | `11.2935` | `11.3327` | **`+0.0392`** (+0.35% por restricción) |
| | `Costo Phi` | `10.7532` | `10.7532` | `10.7924` | `+0.0392` |
| | `BestBound` | `10.9052` | `10.9052` | `10.9349` | `+0.0297` |
| | `MIPGap (%)` | `3.44%` | `3.44%` | `3.51%` | `+0.07 pp` |
| | `Nodrizas / Agave-Agave` | `42 / 26` | `42 / 26` | `48 / 25` | `+6 nodrizas / -1 Ag-Ag` |
| **2D `6x11` Holgura ±10%** | `ObjVal (Z)` | `11.1725` | `11.1725` | `11.2388` | **`+0.0663`** (+0.59% por restricción) |
| | `Costo Phi` | `10.6295` | `10.6295` | `10.6958` | `+0.0663` |
| | `BestBound` | `10.6935` | `10.6935` | `10.7201` | `+0.0266` |
| | `MIPGap (%)` | `4.29%` | `4.29%` | `4.62%` | `+0.33 pp` |
| | `Nodrizas / Agave-Agave` | `42 / 28` | `42 / 28` | `49 / 23` | `+7 nodrizas / -5 Ag-Ag` |

### 3.2 Interpretación Técnica de los Resultados
1. **Reproducción exacta con `--big-index 0` (Corrida a)**:
   - Con `--big-index 0`, el pipeline integrado reproduce **al 100% y hasta la cuarta cifra decimal** todos los valores de `METRICAS_BASE.md` (`ObjVal`, `BestBound`, `MIPGap`, `Surv_Base`, `Surv_Eff`, `Nodrizas`, `Gasto_Vivero_MXN` y simulación Monte Carlo).
2. **Impacto de `--big-index 3` (Corrida b)**:
   - En la malla `6x11` (`66` nodos), la subred `(i - j) % 3 == 0` tiene exactamente `22` nodos, donde dos nodos cualesquiera de la subred están separados por una distancia mínima de $\sqrt{3}\,d$ (nunca son vecinos inmediatos de primer anillo).
   - **En Holgura ±5% y ±10%** (con las mismas cepas preexistentes dentro de la subred), agregar la restricción `big_index=3` reduce el espacio factible y por tanto el valor objetivo óptimo aumenta ligeramente (`+0.0392` en ±5% y `+0.0663` en ±10%), mientras que la cota dual (`BestBound`) también sube (`10.9052 -> 10.9349` y `10.6935 -> 10.7201`) y el `MIPGap` se mantiene en el mismo rango (`3.51%` y `4.62%`). Además, al obligar a *Prosopis laevigata*, *Opuntia streptacantha* y *Yucca filifera* a distribuirse de forma uniforme en la subred $\sqrt{3}\,d$, **aumentan los contactos nodriza** (`42 -> 48` en ±5% y `42 -> 49` en ±10%) y **disminuyen los contactos Agave-Agave** (`28 -> 23` en ±10%).
   - **¿Por qué en Holgura ±0% `ObjVal` bajó de `12.4293` a `11.4906`?** Porque en `build_real_preexisting_nodes_from_csv`, al activar `big_index=3`, las 3 plantas preexistentes de especies grandes (`1 O. streptacantha` y `2 P. laevigata`) se fijan en nodos de la subred `big_mask` (separados al menos $\sqrt{3}\,d$), evitando un cuello de botella topológico local que en el caso irrestricto forzaba `1` contacto intraespecífico (`Intra = 1 -> 0`).

---

## 4. Resumen de `PARAMETROS_DOMINICA.md`

En [`trabajo/PARAMETROS_DOMINICA.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PARAMETROS_DOMINICA.md) se auditaron y clasificaron **22 parámetros, reglas y conjuntos de datos** de `modelo_dominica`:

- **Categoría `a` (Con fuente o respaldo explícito en archivos/datos — 10 ítems)**:
  1. Geometría UTM 14N y áreas oficiales de los 31 polígonos (`poli31/poligonos_31.csv`, `poligonos_utm.csv`).
  2. Conteos de plantas vivas por especie y polígono (`poli31/registro_oficial31.csv`) y ausencia de registro en el Polígono 29 (`6.54 ha`).
  3. Regla de densidad CONAFOR por pendiente (`658 pl/ha` si $<20\%$, `524 pl/ha` si $\ge 20\%$).
  4. Receta base proporcional del programa para 10 especies (`658 pl/ha`).
  5. Mapeo nominal de las 10 especies en `registro_oficial31.csv`.
  6. Plano regional de elevación SRTM 30 m de 5 puntos (`poli31/dem_srtm_puntos.csv`).
  7. Costos unitarios de vivero en `Costo_por_unidad.csv` (con discrepancias puntuales en 2 especies respecto a `REFORESTATHON`; se conservaron los de `REFORESTATHON`).
  8. Forma funcional del kernel de Epanechnikov $(1-u^2)_+$.
  9. Tasas de supervivencia empíricas 2021–2023 en `REFORESTATHON` (`monitoreo_supervivencia.csv`, conservadas íntegramente).
  10. Pesos de vulnerabilidad empíricos $w_i$ de `REFORESTATHON` (conservados íntegramente).
- **Categoría `b` (Declarados explícitamente como `HEURÍSTICO`, `PLACEHOLDER` o `[guessing]` en `modelo_dominica` — 11 ítems)**:
  1. Clasificación binaria de talla grande `LEVEL = 1` para `(7: O. streptacantha, 8: P. laevigata, 9: Yucca filifera)` (`parametros_modelo.md` §6: *"Criterio HEURÍSTICO fijado por inspección de las tallas adultas"*).
  2. Regla de subred `big_index = 3` (`(i - j) % 3 == 0`, 1 de cada 3 nodos, distancia $\sqrt{3}\,a \approx 7.25\text{ m}$) (`parametros_modelo.md` §1 y §19).
  3. Relieve local de lomerío fractal `_band_fractal` y pendientes sintéticas `slope_deg = 6° / 10°` (`parametros_modelo.md` §9, §19.5 y §19.11: *"El relieve dentro de cada polígono sigue siendo sintético (lomerío fractal reproducible)"*).
  4. Asignación por orden de lectura del mapa para polígonos con área empatada (`1.04`, `1.47`, `1.77`, `4.24 ha`) (`parametros_modelo.md` §19.1).
  5. Diámetros de copa adulta de 6 de las 10 especies marcados con `# [guessing]` en `hexgarden.py` (`parametros_modelo.md` §19.3).
  6. Escala temporal ontogenética de 3 edades $t \in \{0.2, 0.5, 1.0\}$ y pesos $(0.2, 0.3, 0.5)$ (`parametros_modelo.md` §3 y §19.9).
  7. Talla de cohorte preexistente (`size = 0.50` del adulto) (`parametros_modelo.md` §5 y §19.4).
  8. Pesos de estrés por edad `STRESS_W` (`parametros_modelo.md` §3 y §19.9).
  9. Proxy de supervivencia $g(F) = 1/(1 + 0.5\max(0, -F))$ (`parametros_modelo.md` §4 y §19.10: *"PLACEHOLDER FUNCIONAL — no calibrado con mortalidad observada"*).
  10. Radio de truncamiento de interacción `MAX_R = 10.0 m` (`parametros_modelo.md` §1 y §19.7).
  11. Matrices de interacción `B_SAME` y `B_DIFF` (`parametros_modelo.md` §2 y §19.8).
- **Categoría `c` (Sin fuente ni justificación indicada en los archivos — 1 ítem)**:
  1. Convención visual de formas y colores por género `SP_STYLE` en `pipeline.py`.

### Parámetros que requieren confirmación con tu amigo botánico:
1. **Lista de especies de talla grande (`LEVEL = 1`: *O. streptacantha*, *P. laevigata*, *Yucca filifera*) y exclusión de *Opuntia robusta* y *Agave salmiana***: confirmar si el criterio obedece a arquitectura radicular/dosel adulto documentada en campo o si *O. robusta* debería incluirse o mantenerse en `LEVEL = 0`.
2. **Factor de espaciamiento `big_index = 3` ($\sqrt{3}\,d \approx 7.25\text{ m}$ entre especies grandes)**: confirmar si la distancia mínima de $7.25\text{ m}$ proviene de recomendaciones silvícolas para mezquite/yucca/cardón en zonas áridas o si fue un supuesto geométrico.
3. **Diámetros de copa adulta marcados con `[guessing]` en `hexgarden.py`**: *A. lechuguilla* (`0.55 m`), *A. striata* (`0.60 m`), *O. cantabrigiensis* (`1.30 m`), *O. engelmannii* (`1.50 m`), *O. robusta* (`1.80 m`) y *O. streptacantha* (`2.20 m`).
4. **Orden de índices en `hexgarden.PLANTED` vs `registro_oficial31.csv`**: confirmar que en `hexgarden.py` el intercambio entre *A. striata* (índice 1) y *A. salmiana* (índice 3) fue involuntario, dado que `registro_oficial31.csv` mantiene el orden estándar de `REFORESTATHON`.

---

## 5. Problemas Encontrados y Resolución

1. **Límite de tasa (HTTP 429) en Subagente 2 (Intento 1)**:
   - Al lanzar en paralelo a los Subagentes 2 y 3 (ambos con modelo `flash`), el Subagente 2 alcanzó el límite de tokens por minuto de la API tras haber escrito el 90% de los cambios en `trabajo/subagente_2/scripts/src/reforestacion_pipeline.py`.
   - **Resolución**: Siguiendo la regla de control de costo (máximo 2 intentos por tarea), se lanzó un segundo subagente ligero (`flash_lite`, `8991aa01-5cd9-4110-9e23-272026052034`) que completó las ~50 líneas restantes en `SpatialTiler` y `main()` y verificó las corridas con `--big-index 0` y `--big-index 3`.
2. **Resolución de rutas relativas al ejecutar desde subcarpetas**:
   - El script original calculaba `ROOT_DIR = Path(__file__).resolve().parent.parent.parent`, lo cual asumía que el script siempre vive en `scripts/src/`. Para que tanto `trabajo/integracion/reforestacion_pipeline_integrado.py` como `trabajo/integracion/scripts/src/reforestacion_pipeline.py` encuentren `data/` y `scripts/outputs/` sin importar desde dónde se invoquen, se añadió detección automática de `ROOT_DIR` y `SRC_DIR`.

---

## 6. Contenido de `PENDIENTES.md`

No hubo comandos pendientes ni bloqueados por permisos:
> *"No se requirió ningún comando restringido (ni comandos de `git`, ni borrado de archivos `Remove-Item`/`del`/`rm`, ni comandos de red) durante la ejecución del plan, delegación a subagentes, integración ni validación."*

---

## 7. Lista de Revisión Manual antes de Integrar al Código Real

Antes de copiar [`trabajo/integracion/reforestacion_pipeline_integrado.py`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/reforestacion_pipeline_integrado.py), [`trabajo/integracion/terreno.py`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/terreno.py) y `trabajo/integracion/data/poli31/` a tu árbol principal de `REFORESTATHON`, te recomiendo revisar manualmente:

1. **Gráficos proyectados sobre relieve (`trabajo/integracion/scripts/outputs/mapa_tres_bolillos_relieve*.png`)**:
   - Revisa visualmente cómo luce el encaje (`fit_graph_coords_to_polygon`) de la malla de `6x11` dentro del contorno del Polígono 12 (o del polígono que elijas con `--poligono-id` / `--relief-poligono-id`) y verifica si prefieres mantener el encaje sin escalar (`scale=1.0`) o permitir reducción de escala cuando se simulen mallas más grandes.
2. **Polígono 29 (`sin_registro_vivas = True`)**:
   - Verifica que el comportamiento implementado ($E_i = 0$ al simular `--poligono-id 29` y exclusión del Polígono 29 del muestreo histórico en `run_monte_carlo_rtx3060`) coincide exactamente con el criterio de negocio esperado para ese polígono de `6.54 ha`.
3. **Ubicación de plantas preexistentes bajo `--big-index 3`**:
   - En `build_real_preexisting_nodes_from_csv`, cuando `--big-index 3` está activo, las plantas preexistentes de especies `(7, 8, 9)` se asignan prioritariamente a nodos con `big_mask == True` (dado que el CSV sólo reporta conteos por polígono y no coordenadas GPS por planta). Si en el futuro cuentas con coordenadas GPS exactas de plantas preexistentes, la salvaguarda en `solve_reforestation_mip` ya exime automáticamente cualquier nodo fijo que caiga fuera de `big_mask` para nunca volver infactible el MILP.
