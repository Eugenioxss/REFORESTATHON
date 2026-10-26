# Reporte de Subagente 3: Proyección de Gráficos de Asignación sobre Relieve Topográfico

**Fecha:** 22 de Octubre, 2026  
**Subagente:** Subagente 3  
**Tarea:** Proyectar los gráficos de asignación óptima en malla 2D Tres Bolillos sobre el relieve topográfico (curvas de nivel, sombreado e inclinación de `terreno.py`).

---

## 1. Resumen Ejecutivo

Se implementó exitosamente la integración del módulo de terreno topográfico (`terreno.py`) en el pipeline de optimización estocástica de reforestación (`reforestacion_pipeline.py`). Las asignaciones óptimas resultantes del modelo MILP (y sus escenarios de holgura de 0%, 5% y 10%) ahora se pueden proyectar visualmente sobre el relieve realista recortado al polígono de interés.

Todos los requerimientos funcionales y de transparencia metodológica fueron satisfechos, conservando intacta la generación de las figuras originales.

---

## 2. Auditoría Metodológica y Transparencia del Relieve Topográfico

Siguiendo las directrices estrictas de auditoría de parámetros (`PARAMETROS_DOMINICA.md` §9, §19 y §19.5), en la reconstrucción del relieve en `terreno.py` (`SiteRelief` y `Terrain.from_poligonos`), la elevación $Z(x,y)$ combina dos componentes diferenciadas por su categoría de evidencia:

1. **Plano Regional SRTM 30 m (`Categoría a - DATO`):**
   - Ajustado por mínimos cuadrados a los 5 puntos georreferenciados reales de `data/poli31/dem_srtm_puntos.csv` (rango de elevación 2,410–2,456 m s.n.m., media de 2,432 m s.n.m.).
   - Modela la pendiente regional del sitio (~2.3% hacia el oeste-suroeste).

2. **Relieve Local de Lomerío (`Categoría b - HEURÍSTICO / [guessing]`):**
   - Campo aleatorio sintético gaussiano con espectro de potencia $f^{-\beta}$ (`_band_fractal` acotado a longitudes de onda de 40 m a 600 m).
   - Escalado para cumplir una pendiente media asumida (`slope_deg = 6.0°` por defecto, o `10.0°`).

> **Regla de Transparencia Cumplida:**  
> Tanto en los comentarios del código fuente (`# origen: modelo_dominica, categoría a (plano SRTM 30m) y categoría b (lomerío fractal sintético)`), como en el pie/leyenda de los gráficos generados y en este reporte, se establece explícitamente qué parte del relieve proviene del DEM real (plano regional SRTM 30m de 5 puntos) y cuál es el lomerío fractal simulado.

---

## 3. Modificaciones Implementadas en `reforestacion_pipeline.py`

Las modificaciones se realizaron **exclusivamente** dentro del directorio `trabajo/subagente_3/`:

1. **Configuración de Rutas:**
   - Se añadió la constante `POLI31_DIR = ROOT_DIR / "data" / "poli31"`.
   - Se aseguró que `SRC_DIR` se incluya en `sys.path` para permitir la importación limpia de `terreno.py`.

2. **Argumentos de Línea de Comandos (CLI):**
   - `--plot-relief`: Bandera (`action="store_true"`) para activar la generación de mapas proyectados sobre el relieve.
   - `--relief-poligono-id`: Entero (`default=12`) para especificar el polígono de `poligonos_31.csv` sobre el cual recortar el terreno cuando `--poligono-id` es 0.

3. **Construcción del Terreno (`build_relief_terrain`):**
   - Construye una instancia de `Terrain` cargando las coordenadas de `poligonos_31.csv`, `poligonos_utm.csv` y `dem_srtm_puntos.csv` mediante `Terrain.from_poligonos`.
   - Calcula las zonas de pendiente con `T.zonas(pend_pct=20.0, min_ha=0.10)`.

4. **Encaje Espacial (`fit_graph_coords_to_polygon`):**
   - Centra e interpola las coordenadas de la malla tresbolillo (`graph.coords`) dentro de la geometría del polígono `T.polygon`, ajustando escala y traslación para garantizar que los nodos caigan en el interior del predio.

5. **Visualización Científica del Relieve (`export_relief_visualization`):**
   - **Sombreado Topográfico:** Utiliza `matplotlib.colors.LightSource(azdeg=315, altdeg=40)` sobre `T.elev` con el mapa de color `terrain`.
   - **Curvas de Nivel:** Dibujadas cada 1 m con etiquetas explícitas de elevación (`linewidths=0.4`, `alpha=0.45`).
   - **Zonas Críticas de Pendiente $\ge 20\%$:** Resaltadas con sombreado translúcido rojo (`#d7301f`, `alpha=0.35`) y contorno punteado en `#b30000`, alineado con la regla de densidad CONAFOR.
   - **Recorte al Polígono:** Pinta el exterior en gris tenue (`#d0d0d0`) y dibuja el límite del polígono con trazo continuo negro.
   - **Malla de Asignación:** Dibuja las aristas, nodos coloreados por especie según `assignment` y resalta con anillos rojos las cepas preexistentes `fixed_nodes`.
   - **Anotación de Transparencia:** Incluye leyenda clara y pie de figura con el aviso de procedencia de datos (SRTM 30m real vs lomerío fractal sintético).

6. **Integración en `export_visualizations`:**
   - La función principal `export_visualizations` mantiene intacta la exportación de `matriz_competencia_phi.png` y `mapa_tres_bolillos_optimo{suffix}.png`.
   - Si `terrain is not None`, invoca en paralelo `export_relief_visualization` para generar los archivos `mapa_tres_bolillos_relieve{suffix}.png`.

---

## 4. Resultados de la Prueba de Ejecución

Se ejecutó la prueba de validación mediante la siguiente línea de comandos:

```powershell
& "d:\Codingggg\Notas\Estocastico\REFORESTATHON\.venv\Scripts\python.exe" "d:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\subagente_3\scripts\src\reforestacion_pipeline.py" --plot-relief --time-limit 15 --solver highs
```

### Archivos Generados en `scripts/outputs/`:

1. **Gráficos Originales Preservados:**
   - `matriz_competencia_phi.png` (250 KB)
   - `mapa_tres_bolillos_optimo.png` (244 KB)
   - `mapa_tres_bolillos_optimo_0pct.png` (243 KB)
   - `mapa_tres_bolillos_optimo_5pct.png` (239 KB)
   - `mapa_tres_bolillos_optimo_10pct.png` (243 KB)

2. **Nuevos Mapas Proyectados sobre Relieve:**
   - `mapa_tres_bolillos_relieve.png` (440 KB)
   - `mapa_tres_bolillos_relieve_0pct.png` (439 KB)
   - `mapa_tres_bolillos_relieve_5pct.png` (437 KB)
   - `mapa_tres_bolillos_relieve_10pct.png` (438 KB)

3. **Archivos de Datos y Reportes:**
   - `asignacion_optima_2d.csv`, `asignacion_optima_2d_holgura_0pct.csv`, `5pct.csv`, `10pct.csv`
   - `comparativa_holgura_0_5_10.csv`
   - `monte_carlo_compras.csv`

---

## 5. Conclusión

El Subagente 3 ha completado la Tarea 3 cumpliendo todas las restricciones:
- Trabajo exclusivo en `trabajo/subagente_3/`.
- Ningún archivo original modificado ni eliminado.
- Sin llamadas de red ni comandos git.
- Estricta transparencia entre datos DEM reales SRTM 30m y lomerío fractal simulado.
