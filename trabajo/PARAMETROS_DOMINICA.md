# Auditoría Científica, Clasificación de Parámetros y Resolución de Observaciones (Collins)

**Proyecto**: REFORESTATHON & Modelo Dominica  
**Documento**: `trabajo/PARAMETROS_DOMINICA.md`  
**Fecha de actualización**: 23 de octubre de 2026  
**Auditoría y Concordancia**: Subagente A (Auditoría Científica y Concordancia con Collins)  
**Fuentes primarias auditadas**:
- `modelo_dominica/modelo_dominica/parametros_modelo.md` (Versión 18 oct 2026, §§ 1–19.16)
- `modelo_dominica/modelo_dominica/poli31/poligonos_oficiales_31.md`
- `modelo_dominica/modelo_dominica/terreno.py` y `hexgarden.py`
- `REFORESTATHON/collins/referencias_modelo.md` (Entradas #1 a #42, Sección A–H)
- `REFORESTATHON/collins/citas_resumen_orquestador.xlsx` (Hojas: Contradicciones, Citable, Sin cita)
- `REFORESTATHON/trabajo/RESUMEN.md` y `trabajo/integracion/reforestacion_pipeline_integrado.py`

---

## 1. Criterios Epistemológicos de Clasificación

Para garantizar absoluta integridad académica frente a evaluadores, inversionistas y comités de restauración ecológica, cada parámetro, regla geométrica, coeficiente ecofisiológico y fuente topográfica se clasifica bajo tres categorías ontológicas:

- **Categoría (a) — Respaldado empírica o bibliográficamente**: Mediciones directas en campo de INECOL, cartografía oficial (plano SRTM 30 m de 5 puntos, digitalización UTM 14N del cerco ganadero), normas silvícolas oficiales (Ficha CONAFOR 2010), literatura científica indexada con DOI verificado o datos empíricos de monitoreo trianual 2021–2023.
- **Categoría (b) — Declarado explícitamente como Heurístico, Placeholder o Supuesto (`[guessing]`)**: Parámetros operativos, coeficientes matemáticos o hipótesis cualitativas introducidos sin calibración empírica ni bibliografía primaria para permitir la convergencia de los algoritmos.
- **Categoría (c) — Convención de implementación sin cita externa**: Decisiones estéticas o de ingeniería de software (p. ej. paletas de visualización Okabe-Ito, orden de capas gráficas) que no afectan la formulación biológica ni la optimización.

> [!IMPORTANT]
> **Aviso de Integridad Científica (de `referencias_modelo.md` de Collins)**:
> La literatura científica respalda rigurosamente la **estructura conceptual y matemática** del modelo (optimización estocástica, recocido simulado, asimetría de competencia por luz, facilitación por nodrizas, evapotranspiración FAO-56 Penman-Monteith, aridez UNEP). **No respalda los parámetros cuantitativos finos que más pesan en los resultados numéricos**: la matriz `NICHE`, el umbral de muerte `dead_thr`, los exponentes de aptitud $F$, los coeficientes de estrés por aridez, `juv_vuln`, `nurse_gain`, las 6 copas adultas marcadas `[guessing]`, $\tau$, la pendiente media del lomerío simulado ($6.0^\circ$), las densidades de flora nativa y los costos unitarios de remoción/reubicación. Esos valores son supuestos de trabajo.

---

## 2. Resolución Quirúrgica de las 12 Observaciones de Collins

A continuación se detalla la resolución de cada una de las 12 observaciones registradas en la hoja `Contradicciones` de `citas_resumen_orquestador.xlsx`, contrastando lo afirmado previamente, la evidencia en los archivos fuente y el estado técnico corregido.

### Resumen de Discrepancias y Correcciones

| # | Parámetro / Afirmación | Afirmación Previa en `RESUMEN.md` | Lo que dicen los Archivos Originales | Confianza | Resolución y Corrección Técnica |
|:---:|---|---|---|:---:|---|
| **1** | **Kernel espacial de vecindario** | Epanechnikov $(1-u^2)_+$ como categoría (a) | `modelo_dominica` §3 usa $(1-u^2)^2$ (biweight), no Epanechnikov. Fórmula respaldada solo secundariamente (Wikipedia); Epanechnikov (1969) y Silverman (1986) no verificados | `[certain]` | **Corregido**: La formulación es kernel biweight cuadrático $K(u) = \frac{15}{16}(1-u^2)^2$ para $|u| \le 1$. En `parametros_modelo.md` §3 es `ESTÁNDAR` (forma compacta) / `HEURÍSTICO` (potencia 2). En `REFORESTATHON`, `reforestacion_pipeline` evalúa `(1-v^2)^2`. Clasificado como **(a/b)** (concepto estándar / elección funcional heurística). |
| **2** | **Cita textual de niveles ontogenéticos** | Cita textual de §6: *"Criterio HEURÍSTICO fijado por inspección de las tallas adultas"* | §6 solo dice textualmente *"Nivel (grande, mediano, pequeño): HEURÍSTICO"*. La frase citada no existe; define 3 niveles, no una división binaria | `[certain]` | **Corregido**: Se elimina la cita apócrifa. Se aclara que §6 define 3 niveles ontogenéticos (`grande, mediano, pequeño`) de forma heurística. La clasificación operativa binaria `(7, 8, 9)` en subred fue una adaptación de `REFORESTATHON` para las 3 especies de nivel 1. |
| **3** | **Copas adultas `[guessing]`** | Copas supuestas: lechuguilla 0.55, striata 0.60, cantabr. 1.30, engelm. 1.50, robusta 1.80, strept. 2.20 m | En §19.3, lechuguilla (0.6 m) y striata (1.2 m) son derivadas. Las 6 copas supuestas reales son: cantabr. 2.0, engelm. 2.5, robusta 3.0, strept. 3.5, Prosopis 6.0, Yucca 3.0 m | `[certain]` | **Corregido**: Se actualiza la tabla con los valores oficiales de §19.3. Los valores de 0.55–2.20 m venían de un borrador preliminar. Se documentan con precisión las 2 botánicas derivadas (0.6, 1.2 m), las 2 de Wikipedia (1.75, 3.6 m) y las 6 reales `[guessing]` (2.0, 2.5, 3.0, 3.5, 6.0, 3.0 m). |
| **4** | **Edades ontogenéticas y ponderaciones** | Edades $t \in \{0.2, 0.5, 1.0\}$, pesos $(0.2, 0.3, 0.5)$, citando "§3 y §19.9" | En §2: edades 1, 6 y 20 años con pesos 0.3, 0.3 y 0.4. §19.9 trata sobre la sensibilidad a la pendiente del relieve simulado | `[certain]` | **Corregido**: Se rectifican los valores a `ages = (1, 6, 20)` años y `age_w = (0.3, 0.3, 0.4)` de §2. Se corrige el número de sección: §19.9 corresponde al análisis de pendiente del relieve, no a crecimiento ontogenético. |
| **5** | **Tamaño de la cohorte viva preexistente** | Cohorte preexistente `size = 0.50`, citando "§5 y §19.4" | En §18.2 y §19: cohorte de edad estimada 6 años; tamaño dinámico $f(t+6)$ con $\tau$ por especie. §19.4 es tresbolillo y §5 es objetivo | `[certain]` | **Corregido**: La cohorte no tiene un tamaño arbitrario fijo de 0.50, sino una edad estimada de 6 años evaluada dinámicamente según la curva de crecimiento monomolecular $f(t+6) = f_0 + (1-f_0)(1-e^{-(t+6)/\tau})$. Se rectifica que §19.4 es tresbolillo y §5 es función objetivo. |
| **6** | **Función dosis-respuesta de supervivencia** | $g(F) = 1/(1+0.5\max(0,-F))$ con cita *"PLACEHOLDER FUNCIONAL…"*, citando "§19.10" | En §4: logística formal con `dead_thr = 0.25` y pendiente `0.05`. §19.10 es nodos deformados. La cita entrecomillada no existe | `[certain]` | **Corregido**: Se sustituye por la logística real de §4: $g(F) = 1 / (1 + \exp(-(F - 0.25)/0.05))$. Se rectifica que §19.10 es deformación de nodos. Se enfatiza que en `modelo_dominica` $F$ no está calibrada contra mortalidad real (proxy comparativo), mientras que en `REFORESTATHON` se usan datos reales 2021–2023. |
| **7** | **Radio máximo de interacción de vecindario** | `MAX_R = 10 m`, citando "§19.7" | En §1: `range_m = 14 m` (`HEURÍSTICO`). §19.7 son pruebas empíricas del Polígono 12 | `[certain]` | **Corregido**: Se fija `range_m = 14 m` de §1. Se aclara que en §12 el análisis de sensibilidad demostró que `range_m` es inerte frente a perturbaciones de $\pm 30\%$ debido al soporte compacto menor de los kernels individuales. §19.7 son pruebas del P12. |
| **8** | **Origen de matrices `B_SAME`, `B_DIFF`, `STRESS_W`** | Matrices y penalizaciones atribuidas a "§19.8" de `modelo_dominica` | No están en el inventario de `modelo_dominica`. Vienen de la formulación propia de `REFORESTATHON`. §19.8 son los 31 terrenos simulados | `[certain]` | **Corregido**: Separación quirúrgica de procedencia: `B_SAME`, `B_DIFF` y `STRESS_W` pertenecen a la modelación matricial de `REFORESTATHON`, no a `modelo_dominica`. Se rectifica que §19.8 describe la simulación de los 31 terrenos. |
| **9** | **Empates reales de área oficial entre polígonos** | Empates de área reportados en 1.04, 1.47, 1.77 y 4.24 ha | Empates reales en §19.1 y `poligonos_oficiales_31.md`: 8.0 ha (5 polígonos), 5.64 ha (2 polígonos) y 5.4 ha (2 polígonos). 1.47 ha es área única del P12 | `[certain]` | **Corregido**: Se corrigen los empates de área a los valores reales: `8.0 ha` (P21, P9, P10, P3, P4), `5.64 ha` (P24, P16) y `5.4 ha` (P15, P1). Se aclara que `1.47 ha` es única del Polígono 12 y que los valores 1.04, 1.77, 4.24 ha eran erróneos. |
| **10** | **Unidades de pendiente: grados vs porcentaje** | Corridas reportadas con "pendiente 6.0 %" | En `terreno.py`, `slope_deg` está en grados ($6.0^\circ \approx 10.51\%$). En el pipeline `--slope` está en porcentaje para CONAFOR ($20\%$). Si se pasaba directo, se confundían unidades | `[likely]` | **Corregido en código**: Se desacopló `--slope-pct` / `--slope` (porcentaje para CONAFOR, default 6.0%) de `--relief-slope-deg` (grados para el lomerío de `terreno.py`, default 6.0° $\approx 10.51\%$). Se documentó la equivalencia trigonométrica $\tan(6.0^\circ) = 0.1051$. |
| **11** | **Intercambio *A. striata* / *A. salmiana* en `PLANTED`** | Intercambio calificado como "involuntario" o descuido | `poligonos_oficiales_31.md` (L44–45) documenta explícitamente y a propósito que los conteos siguen el orden deliberado de `hexgarden.PLANTED` | `[certain]` | **Corregido**: No fue un error involuntario sino una convención deliberada documentada en `poligonos_oficiales_31.md`. Se explica cómo `REFORESTATHON` mapea las especies por nombre científico en `df_wide[sp_names]` garantizando indexación unívoca. |
| **12** | **Estado por defecto de `big_index`** | `big_index = 0` por defecto atribuido como estándar general | En `modelo_dominica` §19, `big_index = 3` es el valor activo por diseño. `big_index = 0` es decisión técnica de `REFORESTATHON` | `[certain]` | **Corregido**: En `modelo_dominica` la subred activa de especies grandes es `big_index = 3` (restringe a $1/3$ de los nodos, distancia $\sqrt{3}a$). En `REFORESTATHON`, `big_index = 0` se fijó por defecto únicamente para mantener retrocompatibilidad estricta con la línea base preexistente. |

---

## 3. Verificación de Especies, Índices y Mapeo entre Proyectos

A continuación se presenta la correspondencia formal de las 10 especies del programa de restauración en Charcas, SLP.

| ID en `REFORESTATHON` | Especie | Nombre Común | ID en `hexgarden.PLANTED` | Nivel en §6 / §18.4 | Copa Adulta §19.3 (m) | Origen de Copa | Altura Adulta §18.4 (m) | Fuente de Altura |
|:---:|---|---|:---:|:---:|:---:|---|:---:|---|
| **0** | *Agave lechuguilla* | Lechuguilla | **0** | 3 (pequeña) | **0.60** | Derivado de roseta (FEIS) | 0.45 | FEIS (roseta 20–60 cm) |
| **1** | *Agave salmiana* | Maguey verde | **3** | 2 (mediana) | **3.60** | Wikipedia (sin cita primaria) | 1.80 | Wikipedia |
| **2** | *Agave scabra* | Maguey azul | **2** | 2 (mediana) | **1.75** | Wikipedia (1.5–2 m) | 0.85 | Wikipedia (0.7–1 m) |
| **3** | *Agave striata* | Espadín | **1** | 3 (pequeña) | **1.20** | Derivado de hoja 60 cm | 0.60 | Derivado botánico |
| **4** | *Opuntia cantabrigiensis* | Cuijo | **4** | 2 (mediana) | **2.00** | `[guessing]` | 1.50 | `[guessing]` |
| **5** | *Opuntia engelmannii* | Nopal rastrero | **5** | 2 (mediana) | **2.50** | `[guessing]` | 1.50 | theferns (1–3.5 m) |
| **6** | *Opuntia robusta* | Nopal tapón | **6** | 2 (mediana) | **3.00** | `[guessing]` | 1.50 | LLIFLE (1–2 m, a veces 4–6) |
| **7** | *Opuntia streptacantha* | Cardón | **7** | **1 (grande)** | **3.50** | `[guessing]` | 3.50 | Scheinvar & Rodríguez (hasta 5 m) |
| **8** | *Prosopis laevigata* | Mezquite | **8** | **1 (grande)** | **6.00** | `[guessing]` | 5.00 | Pennington & Sarukhán (hasta 13 m) |
| **9** | *Yucca filifera* | Palma china | **9** | **1 (grande)** | **3.00** | `[guessing]` | 6.00 | LLIFLE (6–10 m) |

### Puntos clave del mapeo:
1. **Especies grandes (Nivel 1)**: Los índices `(7: O. streptacantha, 8: P. laevigata, 9: Y. filifera)` son **idénticos** en ambos modelos. Representan el 26.7% de la receta comunitaria (176 de 658 plantas/ha).
2. **Intercambio *A. striata* / *A. salmiana***: En `hexgarden.PLANTED` se ordenaron deliberadamente como `0: lechuguilla, 1: striata, 2: scabra, 3: salmiana...`, mientras que el catálogo de `REFORESTATHON` y las columnas de `registro_oficial31.csv` emplean `0: lechuguilla, 1: salmiana, 2: scabra, 3: striata...`. Al indexar por nombre científico en `df_wide[sp_names]`, la correspondencia de conteos es perfecta.
3. **Copas adultas**: Se constata que de las 10 especies, solo 2 copas son derivadas de literatura botánica (lechuguilla, striata), 2 provienen de fuentes secundarias sin cita (scabra, salmiana), y exactamente **6 copas son supuestos `[guessing]`** (cantabrigiensis, engelmannii, robusta, streptacantha, Prosopis, Yucca).

---

## 4. Tabla Maestra de Parámetros (`modelo_dominica` vs `REFORESTATHON`)

| # | Parámetro / Componente | Valor en `modelo_dominica` | Valor en `REFORESTATHON` | Cat. | Sección Oficial de Respaldo | Respaldo Bibliográfico / Documental | Decisión de Integración |
|:---:|---|---|---|:---:|---|---|---|
| **1** | **Geometría de 31 polígonos UTM 14N** | 31 polígonos (189.55 ha totales; P29 = 6.54 ha sin registro). Escalados a áreas oficiales (error $\pm 5$ m) | 30 polígonos base en `poligonos_plantas_wide.csv` (183.01 ha); adaptado a 31 polígonos en `poli31/` | **a** | §19.1 y `poligonos_oficiales_31.md` | Sección D: Mapa oficial cerco ganadero Parque Eólico Dominica | **Integrado** (soporte completo de 31 polígonos; P29 con $E_i=0$ y excluido del muestreo de vivas) |
| **2** | **Mapeo de filas INECOL a polígono** | Asignación 1→27, 2→28, ..., 30→1 por área; empates en 8.0, 5.64 y 5.4 ha por orden de lectura | `poligono_id` 1..30 usa fila directa de tabla original | **a/b** | §19.1 y `poligonos_oficiales_31.md` | DATO para áreas únicas; `[likely]` orden de lectura en empates | **Integrado** (`load_poli31_datasets` mapea polígonos oficiales 1..31) |
| **3** | **Censo de plantas vivas por polígono** | 23,569 plantas vivas censadas en 30 polígonos (128.8 pl/ha medio), no removibles | Idénticos conteos (23,569 plantas preexistentes $E_i$) | **a** | §18.2 y §19 | Sección D: `datos_inecol.xlsx` Hoja 2 (`DATO` de campo) | **Conservado** (conteos idénticos en ambos proyectos) |
| **4** | **Cohorte viva: edad y posicionamiento** | Edad 6.0 años (`[likely]`), colocación al azar con separación mín 3 m y radio exclusión `clip(0.35*copa, 0.6, 1.5)` m | Asignadas a nodos de la malla evitando auto-adyacencia (`build_real_preexisting_nodes_from_csv`) | **b** | §18.2, §19 y §19.10 | HEURÍSTICO / PLACEHOLDER (edad y exclusión) | **Conservada lógica de nodos** de `REFORESTATHON` |
| **5** | **Clasificación de talla grande (`LEVEL = 1`)** | Especies 7 (*O. streptacantha*), 8 (*P. laevigata*), 9 (*Y. filifera*) como nivel 1 | Mismas especies `(7, 8, 9)` en `BIG_SPECIES_IDS` | **b** | §6 ("Nivel (grande, mediano, pequeño): HEURÍSTICO") | Scheinvar 2003 (#30), Pennington (#31), LLIFLE (#32) respaldan altura, no el corte | **Integrado** como heurística estructural para especies de porte arbóreo/arborescente |
| **6** | **Subred `big_index = 3` ($\sqrt{3}a$)** | Submáscara `(i - j) % 3 == 0` (1/3 de los nodos admiten especies grandes, dist $\sqrt{3}a \approx 7.25$ m) | CLI `--big-index 3` (default 0 para compatibilidad histórica) | **b** | §1 y §19 (`HEURÍSTICO`) | Geometría hexagonal (Hales 2001 #37 no verificada; tresbolillo CONAFOR 2010) | **Integrado como opción CLI** `--big-index` (activa en solver HiGHS, warmstart GPU y graficación) |
| **7** | **Densidad por pendiente CONAFOR** | 658 pl/ha en plano ($< 20\%$, `floor`), 524 pl/ha en pendiente ($\ge 20\%$, `ceil`), ratio $a_{pend} = 1.121 \cdot a_{plan}$ | Exactamente igual en `get_target_density`: 658 vs 524 pl/ha | **a** | §19.4 | Sección D: Ficha diapositiva INECOL/CONAFOR 2010 | **Consenso total** (ambos códigos implementan la misma regla) |
| **8** | **Receta de plantación y bandas** | 658 pl/ha: 42, 196, 42, 42, 49, 38, 73, 64, 86, 26 con bandas relativas $\pm 10\%$ (o $\pm 5\%$) | Mismo vector en `SPECIES_METADATA["quota_recipe"]` | **a** | §10 y §18.1 | Sección D: `datos_inecol.xlsx` (`DATO` oficial del programa) | **Consenso total** |
| **9** | **Plano regional SRTM 30 m** | Ajuste por mínimos cuadrados a 5 puntos SRTM 30 m (2,410–2,456 m, media 2,432 m, pendiente regional 2.3% ENE) | Sin modelo de elevación regional en la línea base | **a** | §19 y §19.5 | #28 OpenTopoData SRTM 30 m (18 oct 2026) | **Integrado** (`terreno.py` proyecta el plano regional en Tarea 3) |
| **10** | **Lomerío sintético fractal y pendientes** | Espectro fractal $\lambda \in [40, 600]$ m, $\beta=2.0$, pendiente media `slope_deg = 6.0°` ($\approx 10.51\%$) | Argumentos CLI desacoplados: `--slope-pct 6.0` (CONAFOR) y `--relief-slope-deg 6.0` (Lomerío) | **b** | §9, §19.5, §19.9, §19.11 | `[guessing]`: No hay DEM continuo de alta resolución del predio | **Corregido y desacoplado** (se aclara en leyendas que el lomerío es sintético sobre plano SRTM real) |
| **11** | **Climatología y PET Penman-Monteith** | 2,430 m s.n.m., 420 mm lluvia, 16 °C, lat 23.37° N, sin pastoreo (0), PET FAO-56 Penman-Monteith | No modela clima dinámico; usa matrices de interacción ecológica calibradas | **a/b** | §9, §18.5 y §19 | #13 Zomer et al. 2022; #20 Allen et al. 1998; #25 INEGI 2010 Charcas | **Conservado en `terreno.py`** sin alterar la formulación de optimización |
| **12** | **Edades ontogenéticas y pesos** | `ages = (1.0, 6.0, 20.0)` años, `age_w = (0.30, 0.30, 0.40)` | Mismo esquema temporal: `planning_years = [1, 6, 20]`, $\omega = (0.30, 0.30, 0.40)$ | **b** | §2 (`HEURÍSTICO`) | #19 Paine et al. 2012 respalda no-linealidad ontogenética | **Consenso total** |
| **13** | **Pesos de recursos en competencia** | $\beta_W = 0.60$ (agua), $\beta_L = 0.25$ (luz), $\beta_N = 0.15$ (nitrógeno/nodriza) | Idénticos pesos: $\beta_W=0.60, \beta_L=0.25, \beta_N=0.15$ | **b** | §4 (`HEURÍSTICO`) | #3 Weiner 1990 (asimetría de luz); #4 Padilla & Pugnaire 2006 (facilitación) | **Consenso total** |
| **14** | **Kernel biweight compacto** | $K(u) = (1-u^2)^2$ para $|u| < 1$ (biweight cuadrático) | $K(v) = (1-v^2)^2$ para $v \in [0, 1)$ | **a/b** | §3 | Silverman 1986 y Epanechnikov 1969; nota final referencias | **Consenso total** (forma analítica compartida) |
| **15** | **Alturas adultas de especies** | 0.45, 0.60, 0.85, 1.80, 1.50, 1.50, 1.50, 3.50, 5.00, 6.00 m | 0.60, 2.00, 1.00, 0.80, 1.50, 1.20, 2.50, 4.00, 6.00, 8.00 m | **a/b** | §18.4 | Literatura botánica variada (#29, #30, #31, #32, #33) | **Conservados valores de `REFORESTATHON`** |
| **16** | **Diámetros de copa adulta y radios** | Copas: 0.6, 1.2, 1.75, 3.6, 2.0, 2.5, 3.0, 3.5, 6.0, 3.0 m; $f_0 = 0.042–0.889$ | Radios radiculares calibrados por edad ontogenética $R_{rad}(t)$ | **a/b** | §18.4 y §19.3 | 2 copas derivadas (#29 FEIS), 2 Wikipedia (#33), 6 copas `[guessing]` | **Conservados valores de `REFORESTATHON`** |
| **17** | **Sensibilidad ecofisiológica ($WU$, sens.)** | Rasgos específicos: $WU \in [0.2, 1.0]$, profundidad radicular, $\tau \in [5, 40]$ años | Sensibilidad hídrica $v_i \in [0.2, 0.8]$, lumínica $l_i$, captación $U_i(t)$ | **b** | §6, §13, §18.4 | #15 Escamilla-Treviño 2012 y #16 Stewart 2015 respaldan dirección CAM vs C3 | **Conservados valores de `REFORESTATHON`** |
| **18** | **Matriz de nicho ecológico (`NICHE`)** | 40 coeficientes (suelo 5–60 cm, pend 12–40°, helada, pastoreo) | No usa `NICHE`; calibrado con matriz empírica $\Phi$ y supervivencia observada | **b** | §7 y §18.4 | 38 valores `PLACEHOLDER`; 2 datos de helada (#32, #36) | **Conservada formulación de `REFORESTATHON`** |
| **19** | **Supervivencia por especie vs Proxy $g(F)$** | Proxy logística no calibrada: $g(F) = 1/(1+e^{-(F-0.25)/0.05})$ | Supervivencia observada trianual 2021–2023 en campo: 72.63% a 92.65% | **a (REFORESTATHON)** vs **b (Dominica)** | §4 ("Nota clave: F no está calibrada contra mortalidad real") | `monitoreo_supervivencia.csv` (DATO empírico real en `REFORESTATHON`) | **PROHIBIDO sobrescribir**: Se mantiene la supervivencia empírica real de `REFORESTATHON` |
| **20** | **Costos de vivero por planta** | \$26.0 (Agaves, Yucca), \$18.0 (Opuntias medianas), \$21.0 (*O. engelmannii*), \$26.5 (*P. laevigata*) | Costos diferenciados: \$14.50 a \$36.00 MXN (`SPECIES_METADATA["cost_mxn"]`) | **a** | §6 y §18.3 | DATO oficial en `Costo_por_unidad.csv` | **Conservados costos de `REFORESTATHON`** |
| **21** | **Penalización presupuestal ($\mu$)** | $\mu = 0.0005$ MXN$^{-1}$ (precio sombra: 2,000 MXN / sobreviviente) | Idéntico: `mu_cost_penalty = 0.0005` | **b** | §5 (`HEURÍSTICO`) | Decisión de balance multiobjetivo | **Consenso total** |
| **22** | **Estilo visual de especies (`SP_STYLE`)** | Colores Okabe-Ito, formas por género: `^` Agave, `o` Opuntia, `*` Prosopis, `D` Yucca | Paleta cualitativa estándar `tab10` | **c** | `pipeline.py` L377–381 | Convención de diseño gráfico accesible | **Opcional en visualizaciones** |

---

## 5. Compendio Bibliográfico Verificado (Collins)

Las referencias bibliográficas verificadas que sustentan la arquitectura del modelo se detallan a continuación, organizadas por componente del proyecto:

### A. Algoritmos de Optimización y Geometría Espacial
1. **Recocido Simulado**: Kirkpatrick, S., Gelatt, C. D., & Vecchi, M. P. (1983). *Optimization by simulated annealing*. Science, 220(4598), 671–680. DOI: [10.1126/science.220.4598.671](https://doi.org/10.1126/science.220.4598.671).
   - *Uso*: Algoritmo estocástico de optimización de especies en nodos (`Plan.optimize_fixed` y `gpu_parallel_annealing_warmstart`).
2. **Criterio de Metrópolis**: Metropolis, N., Rosenbluth, A. W., Rosenbluth, M. N., Teller, A. H., & Teller, E. (1953). *Equation of state calculations by fast computing machines*. J. Chem. Phys., 21(6), 1087–1092. DOI: [10.1063/1.1699114](https://doi.org/10.1063/1.1699114).
   - *Uso*: Regla probabilística de aceptación de transiciones $\exp(-\Delta E / T)$.
3. **Mapeo Geodésico Transverso de Mercator (UTM)**: Karney, C. F. F. (2011). *Transverse Mercator with an accuracy of a few nanometers*. Journal of Geodesy, 85(8), 475–485. DOI: [10.1007/s00190-011-0445-3](https://doi.org/10.1007/s00190-011-0445-3).
   - *Uso*: Proyección y verificación de coordenadas WGS84 $\to$ UTM 14N para los 31 polígonos.

### B. Interacciones Ecológicas: Competencia y Facilitación
4. **Asimetría de Competencia por Luz**: Weiner, J. (1990). *Asymmetric competition in plant populations*. Trends in Ecology & Evolution, 5(11), 360–364. DOI: [10.1016/0169-5347(90)90095-U](https://doi.org/10.1016/0169-5347(90)90095-U).
   - *Uso*: Fundamento conceptual de que los individuos más altos sombrean a los más bajos unidireccionalmente.
5. **Efecto Nodriza en Restauración de Zonas Áridas**: Padilla, F. M., & Pugnaire, F. I. (2006). *The role of nurse plants in the restoration of degraded environments*. Frontiers in Ecology and the Environment, 4(4), 196–202. DOI: [10.1890/1540-9295(2006)004[0196:TRONPI]2.0.CO;2](https://doi.org/10.1890/1540-9295(2006)004[0196:TRONPI]2.0.CO;2).
   - *Uso*: Modelación de la facilitación radicular y microclimática provista por *Prosopis laevigata* sobre juveniles.
6. **Facilitación en la Mesa Central Mexicana**: Flores, J., & Jurado, E. (2003). *Are nurse-protégé interactions more common among plants from arid environments?* Journal of Vegetation Science, 14(6), 911–916. DOI: [10.1111/j.1654-1103.2003.tb02225.x](https://doi.org/10.1111/j.1654-1103.2003.tb02225.x).
   - *Uso*: Evidencia empírica de asociaciones nodriza-protegido en cactáceas del Altiplano mexicano.
7. **Simetría Subterránea Radicular**: Weiner, J., Wright, D. B., & Castro, S. (1997). *Symmetry of below-ground competition between Kochia scoparia individuals*. Oikos, 79(1), 85–91.
   - *Uso*: Demuestra que la competencia por agua es predominantemente simétrica según el área radicular, justificando el balance hídrico $U / (U + U')$.
8. **Competencia con Pastos Invasores (Buffel)**: Rinella, M. J., Hammond, D. H., Bryant, A.-E. M., & Kozar, B. J. (2015). *High precipitation and seeded species competition reduce seeded shrub establishment during dryland restoration*. Ecological Applications, 25(4), 1044–1053. DOI: [10.1890/14-1110.1](https://doi.org/10.1890/14-1110.1).
   - *Uso*: Respaldo cualitativo de la agresividad competitiva de gramíneas introducidas (*Cenchrus ciliaris*) sobre el establecimiento de leñosas.

### C. Ecofisiología de Especies de Zonas Áridas
9. **Eficiencia en Uso de Agua de Agaváceas (CAM)**: Escamilla-Treviño, L. L. (2012). *Potential of plants from the genus Agave as bioenergy crops*. BioEnergy Research, 5, 1–9. DOI: [10.1007/s12155-011-9159-x](https://doi.org/10.1007/s12155-011-9159-x).
   - *Uso*: Fundamenta que plantas CAM requieren solo 16% del agua de una C3 para la misma biomasa (10–40 g CO$_2$/kg H$_2$O vs 1–3 en C3).
10. **Tolerancia a Sequía Extrema en Agaves**: Stewart, J. R. (2015). *Agave as a model CAM crop system for a warming and drying world*. Frontiers in Plant Science, 6, 684. DOI: [10.3389/fpls.2015.00684](https://doi.org/10.3389/fpls.2015.00684).
   - *Uso*: Justificación de las bajas demandas hídricas relativas de *A. salmiana*, *A. scabra*, *A. striata* y *A. lechuguilla*.
11. **Morfología y Requerimientos de *Agave lechuguilla***: USDA Forest Service, FEIS. *Agave lechuguilla*. URL: [fs.usda.gov](https://www.fs.usda.gov/database/feis/plants/shrub/agalec/all.html).
   - *Uso*: Altura de roseta (20–60 cm), raíz corta (~10 cm), tolerancia a suelos someros ($\le 30$ cm).
12. **Morfología de *Opuntia streptacantha***: Scheinvar, L., & Rodríguez Fuentes, A. (2003). *Nueva subespecie de Opuntia streptacantha...* Anales del Instituto de Biología, UNAM, Serie Botánica, 74(2), 303–311.
   - *Uso*: Altura de hasta 5 m en ejemplares adultos (respaldo de especie de porte grande `LEVEL = 1`).
13. **Sistema Radicular de *Prosopis laevigata***: CONABIO/INIFAP. *Monografía de Prosopis laevigata* (citando a Pennington & Sarukhán, 1998; Conaza e INE, 1994).
   - *Uso*: Altura de hasta 13 m, raíces pivotantes $> 50$ m y raíces laterales de hasta 15 m.

### D. Climatología, Evapotranspiración y Topografía
14. **Evapotranspiración de Referencia FAO-56 Penman-Monteith**: Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements*. FAO Irrigation and Drainage Paper 56. FAO, Roma.
   - *Uso*: Estándar internacional para el cálculo de PET en `terreno.py` acoplado con la estimación de radiación de Hargreaves-Samani.
15. **Índice Global de Aridez y Clases UNEP**: Zomer, R. J., Xu, J., & Trabucco, A. (2022). *Version 3 of the Global Aridity Index and Potential Evapotranspiration Database*. Scientific Data, 9, 409. DOI: [10.1038/s41597-022-01493-1](https://doi.org/10.1038/s41597-022-01493-1).
   - *Uso*: Clases climáticas UNEP (hiperárido $< 0.03$, árido $0.03–0.2$, semiárido $0.2–0.5$).
16. **Información Geográfica y Topoformas de Charcas, SLP**: INEGI (2010). *Compendio de información geográfica municipal: Charcas, SLP* (clave 24015).
   - *Uso*: Clima BS1kw, precipitación media 300–600 mm, temperatura 14–20 °C, bajada (32%), bajada con lomeríos (36%).
17. **Manifestación de Impacto Ambiental Parque Dominica**: Dominica Energía Limpia (2011). *MIA particular Línea de Transmisión Dominica–Charcas* (24SL2011E0012). SEMARNAT.
   - *Uso*: Vegetación dominante Matorral Desértico Micrófilo (MDM 67.8%), ausencia de pastoreo activo en el área de exclusión.
18. **Elevación SRTM 30 m de 5 Puntos sobre Polígonos**: OpenTopoData SRTM 30 m (18 oct 2026).
   - *Uso*: Plano regional de elevación (2,410–2,456 m, media 2,432 m s.n.m., pendiente 2.3% ENE).

---

## 6. Lista de Verificación y Recomendaciones para la Presentación

1. **Declarar explícitamente qué es real y qué es sintético en los mapas**:
   - El contorno perimetral, las áreas de los 31 polígonos y el plano regional de 2,432 m son **reales** (digitalización oficial y SRTM 30 m).
   - Las ondulaciones finas de lomerío son **sintéticas** (campo fractal espectral $\beta=2.0$ con pendiente media $6.0^\circ$).
2. **Presentar las dos densidades CONAFOR como política pública**:
   - La regla $658\text{ pl/ha}$ en plano y $524\text{ pl/ha}$ en pendiente $\ge 20\%$ proviene de la Ficha Técnica INECOL/CONAFOR 2010.
3. **Resaltar el valor de la subred `big_index = 3`**:
   - Demostrar que al separar espacialmente los mezquites, cardones y palmas chinas al menos $\sqrt{3}a \approx 7.25\text{ m}$, se incrementan los contactos de facilitación nodriza (+6 a +7 contactos) y se minimiza la competencia intraespecífica severa.
4. **Reconocer con total transparencia los parámetros sin calibrar**:
   - Exponer ante los evaluadores que las 6 copas adultas marcadas `[guessing]`, los 40 coeficientes de `NICHE` y el proxy logístico de $F$ son hipótesis de trabajo, resaltando que la gran ventaja competitiva de `REFORESTATHON` es contar con **supervivencia trianual real en campo (2021–2023)** para calibrar la toma de decisiones.
