# Reporte de Ejecución - Subagente 1
**Tarea 1**: Importar `poli31/` (31 polígonos oficiales en UTM 14N) y adaptar la entrada de datos del pipeline.

---

## 1. Copia de Archivos
Se copiaron exitosamente todos los archivos desde `d:\Codingggg\Notas\Estocastico\modelo_dominica\modelo_dominica\poli31\` hacia `d:\Codingggg\Notas\Estocastico\REFORESTATHON\trabajo\subagente_1\data\poli31\`:
- `poligonos_31.csv`
- `poligonos_utm.csv`
- `registro_oficial31.csv`
- `dem_srtm_puntos.csv`
- `poligonos_oficiales_31.md`
- `digitalizacion_poligonos.py`
- `mapa_digitalizado.png`

---

## 2. Modificaciones Realizadas en `reforestacion_pipeline.py`

1. **Constante y Argumentos CLI**:
   - Se incorporó la constante `POLI31_DIR = ROOT_DIR / "data" / "poli31"`.
   - Se añadió el argumento CLI `--poligonos-dir` (`str`, default `None`).
   - Se actualizó el parámetro `--poligono-id` para admitir `1..31` (o `0` para promedio).
   - Si `--poligonos-dir` es proporcionado o si `--poligono-id == 31`, el pipeline conmuta automáticamente la carga hacia la carpeta `poli31/`.

2. **Función Auxiliar `load_poli31_datasets(poli31_dir: Path)`**:
   - Contiene la firma y comentario obligatorio:
     `# origen: modelo_dominica, categoría a (geometría y conteos registro_oficial31.csv) / categoría b (orden de empates de área)`
   - Procesa `registro_oficial31.csv`, `poligonos_31.csv` y `poligonos_utm.csv` para generar un `df_wide` completamente compatible.
   - Columnas requeridas: `poligono_id` (1..31), `poligono` (`f"Polígono {pid}"`), `dimension_ha`, `area_ha_digitalizada`, `dx_m`, `dy_m`, y las 10 especies nativas (`Agave lechuguilla`, `Agave salmiana`, `Agave scabra`, `Agave striata`, `Opuntia cantabrigiensis`, `Opuntia engelmannii`, `Opuntia robusta`, `Opuntia streptacantha`, `Prosopis laevigata`, `Yucca filifera`), así como metadatos geométricos opcionales (`local_vertices`, `utm_vertices`, `utm_e_min`, `utm_n_min`).
   - **Polígono 29**: Se tratan sus campos vacíos como 0 plantas vivas ($E_i = 0$) y se inyecta la columna booleana `sin_registro_vivas` (`True` para el polígono 29, `False` para los demás).

3. **Compatibilidad en `load_semiraw_datasets(poligonos_dir: Optional[Union[Path, str]] = None)`**:
   - **Retrocompatibilidad estricta**: Si `poligonos_dir is None`, mantiene la carga idéntica previa desde `DATA_DIR / "poligonos_plantas_wide.csv"`.
   - Si `poligonos_dir` está definido, delega la carga a `load_poli31_datasets(Path(poligonos_dir))`.

4. **Filtrado en `run_monte_carlo_rtx3060`**:
   - Filtra los polígonos con plantas registradas (`~df_wide["sin_registro_vivas"]`), excluyendo el Polígono 29 al estimar la media y varianza muestral de densidad, evitando sesgos estadísticos. Incluye salvaguarda contra división por cero si no existieran polígonos válidos.

5. **Manejo en `build_real_preexisting_nodes_from_csv`**:
   - Si un polígono tiene 0 plantas vivas (como el Polígono 29), establece $E_i = \mathbf{0}$ y `fixed_nodes = {}` sin generar NaNs ni `ZeroDivisionError`.
   - Al promediar (`poligono_id == 0`), filtra utilizando `~df_wide["sin_registro_vivas"]`.

---

## 3. Pruebas y Verificación

1. **Polígono 29 (sin plantas vivas / sin_registro_vivas = True)**:
   - Comando: `python scripts\src\reforestacion_pipeline.py --poligonos-dir "data\poli31" --poligono-id 29 --time-limit 10`
   - Resultado: Carga desde `poli31/`, reconoce 31 polígonos, excluye el Polígono 29 en la estimación de densidad Monte Carlo, asigna `0/66 cepas fijas (0.0%) | E_i = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]` y completa los tres escenarios de holgura (0%, 5%, 10%) sin errores (código de salida 0).

2. **Polígono 12 (con registro de plantas vivas)**:
   - Comando: `python scripts\src\reforestacion_pipeline.py --poligonos-dir "data\poli31" --poligono-id 12 --time-limit 10`
   - Resultado: Detecta `14/66 cepas fijas (21.2%) | E_i = [1, 4, 1, 1, 1, 1, 1, 1, 3, 0]` y finaliza correctamente (código de salida 0).
