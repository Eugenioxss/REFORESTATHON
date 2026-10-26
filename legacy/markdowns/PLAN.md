# Plan de Orquestación e Integración (`REFORESTATHON\trabajo\`)

## Objetivo General
Integrar en copias aisladas dentro de `d:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\` las tres mejoras provenientes de `modelo_dominica`:
1. **Tarea 1 (`trabajo\subagente_1\`)**: Importación de `poli31/` (31 polígonos oficiales en UTM 14N y coordenadas locales) y adaptación de la entrada de datos del pipeline (`--poligono-id 1..31`, `--poligonos-dir`), tratando el Polígono 29 (6.54 ha sin registro de plantas vivas) con $E_i = 0$ y manteniendo retrocompatibilidad total cuando no se pasan los nuevos argumentos.
2. **Tarea 2 (`trabajo\subagente_2\`)**: Incorporación de la restricción `big_index` (`(i - j) % big_index == 0`) al grafo `HexGridGraph`, al colocador de plantas preexistentes, al warm-start en GPU y al modelo MILP (`solve_reforestation_mip` en Gurobi y HiGHS) para las especies grandes (`7: Opuntia streptacantha`, `8: Prosopis laevigata`, `9: Yucca filifera`), controlada por `--big-index N` (por defecto `0` = desactivada).
3. **Tarea 3 (`trabajo\subagente_3\`)**: Integración de `terreno.py` y actualización de `export_visualizations` para proyectar de forma opcional la asignación óptima sobre el relieve sombreado (`SiteRelief` / `Terrain`), con curvas de nivel, contorno de zonas con pendiente $\ge 20\%$ y recorte al polígono, distinguiendo explícitamente el plano SRTM real del relieve fractal sintético.
4. **Paso 4 (`trabajo\integracion\`)**: Unificación de las tres ramas en `trabajo\integracion\reforestacion_pipeline_integrado.py` y validación empírica contra `trabajo\base\METRICAS_BASE.md` (con `--big-index 0` y `--big-index 3`) más ejecución de tests.

---

## Secuencia de Ejecución

### Paso 0: Línea Base (`trabajo\base\`)
1. Copiar `reforestacion_pipeline.py` y `data/semiraw/*` a `trabajo\base\`.
2. Ejecutar el solver exacto (`--time-limit 30 --solver highs`) y registrar en `trabajo\base\METRICAS_BASE.md` el valor objetivo (`ObjVal`), `BestBound`, `MIPGap`, tiempo de ejecución y argumentos empleados para el benchmark 1D y los escenarios 2D (0%, 5%, 10% de holgura).

### Paso 1: Auditoría de Parámetros y Planificación
1. Generar `trabajo\PARAMETROS_DOMINICA.md` con la clasificación (a/b/c) basada en evidencia y el mapeo de índices de especies.
2. Generar este archivo `trabajo\PLAN.md`.

### Paso 2: Subagente 1 (`trabajo\subagente_1\`) — Ejecución Secuencial Primero
- **Modelo**: `flash`
- **Aislamiento**: `d:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\subagente_1`
- **Entregables**:
  - Copia de `poli31/*` en `trabajo\subagente_1\data\poli31\`.
  - Adaptación de `load_semiraw_datasets`, `run_monte_carlo_rtx3060`, `build_real_preexisting_nodes_from_csv` y CLI (`--poligono-id` 1..31, `--poligonos-dir`) en `trabajo\subagente_1\scripts\src\reforestacion_pipeline.py`.
  - Manejo del Polígono 29 con $E_i = 0$ (sin plantas vivas registradas) y preservación de las columnas por nombre de especie (evitando el desfase `salmiana`/`striata` de `hexgarden.PLANTED`).
  - Reporte en `trabajo\subagente_1\REPORTE_SUBAGENTE_1.md`.

### Paso 3: Subagentes 2 y 3 (en paralelo tras finalizar Subagente 1)
- **Subagente 2 (`trabajo\subagente_2\`, Modelo `flash`)**:
  - Añadir `grid_i`, `grid_j` y `big_mask` a `HexGridGraph` y `build_tres_bolillos_graph` con comentario `# origen: modelo_dominica, categoría b`.
  - Añadir `--big-index` (default `0` = apagado) al CLI.
  - Cuando `big_index > 0`, restringir especies `BIG_SPECIES_IDS = (7, 8, 9)` a nodos con `big_mask[p] == True` en `build_real_preexisting_nodes_from_csv`, `gpu_parallel_annealing_warmstart`, `solve_reforestation_mip` (Gurobi y HiGHS) y `SpatialTiler`.
  - Si alguna planta preexistente de especie grande no cabe en la subred (o viene fuera de ella), emitir advertencia clara y relajar/manejar la excepción para ese nodo fijo sin volver infactible el MILP.
  - Documentar en `trabajo\subagente_2\REPORTE_SUBAGENTE_2.md`.
- **Subagente 3 (`trabajo\subagente_3\`, Modelo `flash`)**:
  - Copiar `terreno.py` a `trabajo\subagente_3\scripts\src\terreno.py` y los datos `poli31/` a `trabajo\subagente_3\data\poli31\`.
  - Actualizar `export_visualizations` y añadir opciones CLI (`--plot-relief` / integración con `--poligono-id`) para generar mapas proyectados sobre el relieve (`mapa_tres_bolillos_relieve*.png`) con sombreado topográfico (`LightSource`), curvas de nivel (`ax.contour`), zonas de pendiente $\ge 20\%$ y recorte al polígono (`MplPolygon`), sin romper los gráficos originales.
  - Indicar claramente en el título/leyenda del gráfico y en `trabajo\subagente_3\REPORTE_SUBAGENTE_3.md` qué parte del relieve proviene del DEM SRTM 30 m real (plano regional de 5 puntos) y qué parte es sintética (lomerío fractal `_band_fractal`).

### Paso 4: Integración y Validación (`trabajo\integracion\`)
1. Unificar los cambios verificados de los 3 subagentes en `trabajo\integracion\scripts\src\reforestacion_pipeline_integrado.py` (y su copia en `trabajo\integracion\reforestacion_pipeline_integrado.py`).
2. Ejecutar corrida (a): `--big-index 0` con entrada original y verificar que reproduce `METRICAS_BASE.md`.
3. Ejecutar corrida (b): `--big-index 3` y comparar `ObjVal`, `BestBound` y `MIPGap` contra la línea base, además de probar la carga de `poli31` (incluyendo Polígono 12 y Polígono 29) y la generación de gráficos sobre relieve.
4. Ejecutar tests existentes sobre la versión integrada.
5. Redactar `trabajo\RESUMEN.md` y finalizar.
