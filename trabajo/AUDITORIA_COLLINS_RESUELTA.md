# Reporte de Auditoría Científica y Concordancia con Collins

**Destinatario**: Comité Técnico y de Orquestación REFORESTATHON  
**Autor**: Subagente A (Auditoría Científica y Corrección de Observaciones de Collins)  
**Fecha**: 23 de octubre de 2026  
**Documentos auditados**:
- `REFORESTATHON/collins/citas_resumen_orquestador.xlsx`
- `REFORESTATHON/collins/referencias_modelo.md`
- `modelo_dominica/modelo_dominica/parametros_modelo.md`
- `modelo_dominica/modelo_dominica/poli31/poligonos_oficiales_31.md`
- `modelo_dominica/modelo_dominica/terreno.py`
- `REFORESTATHON/trabajo/PARAMETROS_DOMINICA.md`
- `REFORESTATHON/trabajo/RESUMEN.md`
- `REFORESTATHON/trabajo/integracion/reforestacion_pipeline_integrado.py`

---

## 1. Resumen Ejecutivo

El presente reporte consolida y documenta la resolución integral y definitiva de las **12 observaciones científicas, matemáticas y bibliográficas** planteadas por Collins respecto al documento previo de resumen (`RESUMEN.md`) y la parametrización de `modelo_dominica` vs `REFORESTATHON`.

Se verificó cada punto contrastándolo directamente contra los archivos fundacionales del repositorio (`parametros_modelo.md` y `poligonos_oficiales_31.md`), actualizando quirúrgicamente [`trabajo/PARAMETROS_DOMINICA.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PARAMETROS_DOMINICA.md) y corrigiendo en el código integrado [`trabajo/integracion/reforestacion_pipeline_integrado.py`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/integracion/reforestacion_pipeline_integrado.py) la ambigüedad física entre la pendiente porcentual CONAFOR y la pendiente angular en grados del lomerío fractal (`slope_deg`), garantizando retrocompatibilidad total y el paso exitoso de toda la suite de pruebas unitarias (`21/21 passed`).

---

## 2. Resolución Punto por Punto de las 12 Observaciones de Collins

### Observación 1: Forma Funcional y Respaldo del Kernel de Vecindario
- **Lo que señalaba el resumen previo**: Clasificaba el kernel como "Epanechnikov $(1-u^2)_+$ como categoría (a)".
- **Hallazgo en auditoría**: En `parametros_modelo.md` §3, la fórmula implementada es $(1-u^2)^2$ (kernel biweight o cuadrático), no el kernel lineal de Epanechnikov. Asimismo, en `referencias_modelo.md` (nota final de Collins), se documenta que la fórmula del biweight se tomó de una fuente secundaria (Wikipedia) y que las referencias primarias clásicas (Epanechnikov, 1969; Silverman, 1986) no están verificadas en texto completo. En `REFORESTATHON`, la función evaluada en `reforestacion_pipeline` siempre fue `(1.0 - v**2)**2`.
- **Resolución**: Se corrigió la descripción matemática en [`PARAMETROS_DOMINICA.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PARAMETROS_DOMINICA.md). Se define rigurosamente como kernel biweight cuadrático con soporte compacto en $[0, 1)$, clasificado como híbrido **(a/b)**: categoría (a) por su estructura matemática estándar de soporte compacto y categoría (b) por la elección heurística de la potencia cuadrática sin calibración ecológica de campo.

### Observación 2: Cita Textual Apócrifa de Niveles Ontogenéticos en §6
- **Lo que señalaba el resumen previo**: Citaba textualmente entre comillas: *"Criterio HEURÍSTICO fijado por inspección de las tallas adultas"*, atribuido a §6.
- **Hallazgo en auditoría**: §6 de `parametros_modelo.md` únicamente indica en su tabla: `"Nivel (grande, mediano, pequeño): HEURÍSTICO"`. La frase entrecomillada atribuida a §6 no existe en los archivos originales. Además, §6 define tres niveles ontogenéticos/arquitecturales, no una partición binaria.
- **Resolución**: Se eliminó la cita textual apócrifa. Se aclaró que `modelo_dominica` establece tres niveles arquitecturales y que la reducción a una clasificación binaria para especies de talla grande `(7: O. streptacantha, 8: P. laevigata, 9: Y. filifera)` dentro de la subred `big_index` fue una decisión técnica de diseño de `REFORESTATHON`.

### Observación 3: Copas Adultas `[guessing]` Reales vs Valores Obsoletos
- **Lo que señalaba el resumen previo**: Listaba como copas `[guessing]`: *A. lechuguilla* (0.55 m), *A. striata* (0.60 m), *O. cantabrigiensis* (1.30 m), *O. engelmannii* (1.50 m), *O. robusta* (1.80 m) y *O. streptacantha* (2.20 m).
- **Hallazgo en auditoría**: En `parametros_modelo.md` §19.3, los diámetros de copa de *A. lechuguilla* (0.60 m) y *A. striata* (1.20 m) son derivados botánicos a partir del diámetro de roseta (FEIS) y longitud de hoja (60 cm). Las 6 copas supuestas marcadas formalmente con `[guessing]` en la sección §19.3 son:
  1. *Opuntia cantabrigiensis*: **2.0 m**
  2. *Opuntia engelmannii*: **2.5 m**
  3. *Opuntia robusta*: **3.0 m**
  4. *Opuntia streptacantha*: **3.5 m**
  5. *Prosopis laevigata*: **6.0 m**
  6. *Yucca filifera*: **3.0 m**
  Los valores citados previamente correspondían a un script preliminar obsoleto.
- **Resolución**: Se actualizó la tabla oficial en [`PARAMETROS_DOMINICA.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PARAMETROS_DOMINICA.md), diferenciando con precisión quirúrgica las 2 copas derivadas (0.6 y 1.2 m), las 2 de fuentes secundarias (scabra 1.75 m, salmiana 3.6 m) y las 6 verdaderas copas `[guessing]` de §19.3.

### Observación 4: Edades Ontogenéticas y Ponderaciones Temporales
- **Lo que señalaba el resumen previo**: Atribuía las edades $t \in \{0.2, 0.5, 1.0\}$ y pesos $(0.2, 0.3, 0.5)$ a "§3 y §19.9".
- **Hallazgo en auditoría**: En `parametros_modelo.md` §2, las edades ontogenéticas son exactamente `ages = (1, 6, 20)` años y los pesos son `age_w = (0.3, 0.3, 0.4)` (`HEURÍSTICO`). Además, §19.9 trata sobre la "Sensibilidad a la pendiente media del relieve simulado" y no sobre crecimiento biológico.
- **Resolución**: Se corrigieron los valores oficiales a 1, 6 y 20 años con pesos $0.3, 0.3, 0.4$, rectificando que su procedencia es §2.

### Observación 5: Tamaño y Dinámica de la Cohorte Viva Preexistente
- **Lo que señalaba el resumen previo**: Describía la cohorte preexistente como `size = 0.50` citando "§5 y §19.4".
- **Hallazgo en auditoría**: En `parametros_modelo.md` §18.2 y §19, la cohorte viva censada (23,569 plantas en 30 polígonos) tiene una edad estimada de 6 años (`COHORT_AGE = 6`, `[likely]`). Su tamaño ontogenético no es una constante arbitraria de 0.50, sino una función monomolecular dinámica $f(t+6) = f_0 + (1 - f_0)(1 - e^{-(t+6)/\tau})$ con constante de crecimiento $\tau$ específica para cada especie. Además, §19.4 trata sobre el tresbolillo y zonas de pendiente CONAFOR, mientras que §5 trata sobre la función objetivo.
- **Resolución**: Se corrigió la descripción del crecimiento de la cohorte viva a la ecuación monomolecular dinámica con edad base de 6 años, corrigiendo los números de sección (§18.2 y §19).

### Observación 6: Función Dosis-Respuesta de Supervivencia $g(F)$
- **Lo que señalaba el resumen previo**: Reportaba $g(F) = 1/(1+0.5\max(0,-F))$ con una cita entrecomillada *"PLACEHOLDER FUNCIONAL…"*, atribuida a "§19.10".
- **Hallazgo en auditoría**: En `parametros_modelo.md` §4, el vínculo de aptitud $F$ a probabilidad de supervivencia es una función logística formal:
  $$g(F) = \frac{1}{1 + e^{-(F - \text{dead\_thr}) / \text{slope}}}$$
  con `dead_thr = 0.25` y pendiente = `0.05` (`PLACEHOLDER`). §19.10 trata sobre "Nodos deformados", y la cita textual no existe. Además, §4 subraya explícitamente: *"Nota clave: F no está calibrada contra mortalidad real. Por eso la 'mortalidad esperada' de los reportes es solo un proxy para comparar planes"*.
- **Resolución**: Se sustituyó la ecuación por la logística de §4 con umbral 0.25 y escala 0.05. Se resaltó que mientras `modelo_dominica` utiliza un proxy logístico no calibrado, `REFORESTATHON` cuenta con datos de supervivencia real observada en campo (2021–2023).

### Observación 7: Radio Máximo de Truncamiento Espacial
- **Lo que señalaba el resumen previo**: Reportaba `MAX_R = 10 m` citando "§19.7".
- **Hallazgo en auditoría**: En `parametros_modelo.md` §1, el parámetro es `range_m = 14 m` (`HEURÍSTICO`). §19.7 contiene las pruebas del Polígono 12. En el análisis de sensibilidad (§12), `range_m` demostró ser completamente inerte frente a variaciones de $\pm 30\%$ porque los radios de los kernels individuales no superan ese umbral.
- **Resolución**: Se corrigió el valor a `range_m = 14 m` referenciado a §1 y §12.

### Observación 8: Origen de Matrices Matriciales `B_SAME`, `B_DIFF`, `STRESS_W`
- **Lo que señalaba el resumen previo**: Atribuía las matrices `B_SAME`, `B_DIFF` y `STRESS_W` a "§19.8" de `modelo_dominica`.
- **Hallazgo en auditoría**: Dichos identificadores no forman parte del inventario ni del código de `modelo_dominica`. Pertenecen exclusivamente a la formulación matemática matricial de `REFORESTATHON`. Además, §19.8 describe la simulación de los 31 terrenos.
- **Resolución**: Se separó con rigor el origen: `B_SAME`, `B_DIFF` y `STRESS_W` son formulaciones originales de `REFORESTATHON`, mientras que §19.8 trata sobre los 31 terrenos simulados.

### Observación 9: Empates Reales de Área Oficial entre Polígonos
- **Lo que señalaba el resumen previo**: Mencionaba empates de área oficial en "1.04, 1.47, 1.77 y 4.24 ha".
- **Hallazgo en auditoría**: En `parametros_modelo.md` §19.1 y `poligonos_oficiales_31.md`, los únicos empates de área oficial en los 31 polígonos son:
  - **8.0 ha**: 5 polígonos (Polígonos 21, 9, 10, 3 y 4).
  - **5.64 ha**: 2 polígonos (Polígonos 24 y 16).
  - **5.4 ha**: 2 polígonos (Polígonos 15 y 1).
  El área de `1.47 ha` es única y corresponde exclusivamente al Polígono 12. Las áreas 1.04, 1.77 y 4.24 ha no corresponden a empates del registro.
- **Resolución**: Se corrigió la lista de empates en [`PARAMETROS_DOMINICA.md`](file:///d:/Codingggg/Notas/Estocastico/REFORESTATHON/trabajo/PARAMETROS_DOMINICA.md), documentando que los empates de área se resolvieron por orden de lectura del mapa `[likely]`.

### Observación 10: Unidades de Pendiente (Grados vs Porcentaje) y Desacoplamiento en Código
- **Lo que señalaba el resumen previo**: Mencionaba corridas con "pendiente 6.0 %" sin distinguir unidades entre la norma silvícola y el relieve.
- **Hallazgo en auditoría**:
  - En `terreno.py` (L65, L294), `slope_deg` es un ángulo geométrico en **grados**: `slope_deg = 6.0°`, lo que produce una pendiente media del gradiente fractal de $\tan(6.0^\circ) = 0.1051 \approx 10.51\%$. En §19.11 se explica que $6.0^\circ$ se adoptó como default porque con $10.0^\circ$ el 32% del terreno superaba el 20%, mientras que con $6.0^\circ$ solo el 0.8% del área queda con pendiente $\ge 20\%$.
  - En `reforestacion_pipeline_integrado.py`, el argumento `--slope-pct` / `--slope` representa la pendiente del predio en **porcentaje** para la regla CONAFOR (umbral del 20.0%). Al invocar `build_relief_terrain(poligono_id, slope_deg=args.slope_pct, ...)`, se le estaba pasando directamente el valor numérico 6.0 como grados. Si un usuario corría `--slope 20.0` (pensando en 20% para la regla CONAFOR), el lomerío sintético recibía $20.0^\circ$, equivalente a una pendiente física extrema de $\tan(20^\circ) \approx 36.4\%$.
- **Resolución en código**:
  - Se introdujo en `reforestacion_pipeline_integrado.py` (y sus espejos) el argumento dedicado:
    `--relief-slope-deg` (tipo `float`, default `6.0°`).
  - Se desacopló `--slope-pct` / `--slope` (que rige exclusivamente la norma CONAFOR y la matriz $\Phi$) de `--relief-slope-deg` (que controla la amplitud del relieve fractal en `terreno.py`).
  - Al invocar `build_relief_terrain`, se pasa `slope_deg=args.relief_slope_deg`, logueando con claridad la conversión: `slope_deg=6.0° ≈ 10.5% pendiente media`.
  - La suite de 21 pruebas unitarias sigue pasando al 100%.

### Observación 11: Intercambio *A. striata* / *A. salmiana* en `PLANTED`
- **Lo que señalaba el resumen previo**: Calificaba el intercambio de posiciones entre *A. striata* y *A. salmiana* como "involuntario".
- **Hallazgo en auditoría**: En `poligonos_oficiales_31.md` (L44–45), se señala expresamente: *"Los conteos están en el orden de `hexgarden.PLANTED` (lechuguilla, striata, scabra, salmiana, …), distinto del orden de las columnas del CSV original (lechuguilla, salmiana, scabra, striata, …)"*. Fue una ordenación deliberada y consciente en la tupla `PLANTED`.
- **Resolución**: Se eliminó la etiqueta de "involuntario". Se documentó que al indexar por nombre científico en `df_wide[sp_names]` dentro de `REFORESTATHON`, no existe ningún riesgo de desfase biológico.

### Observación 12: Estado por Defecto de `big_index`
- **Lo que señalaba el resumen previo**: Afirmaba que `big_index = 0` era la configuración por defecto general.
- **Hallazgo en auditoría**: En `modelo_dominica` §19, la subred `big_index = 3` está activada por diseño (restringe especies de nivel 1 a 1 de cada 3 nodos). El valor `big_index = 0` (desactivado) fue una decisión deliberada de `REFORESTATHON` para mantener retrocompatibilidad exacta con la línea base histórica preexistente.
- **Resolución**: Se aclaró en la documentación que `big_index = 3` es la heurística nativa de `modelo_dominica`, mientras que `big_index = 0` es una guarda de compatibilidad de `REFORESTATHON` que se activa a discreción mediante la bandera `--big-index 3`.

---

## 3. Matriz de Citas de `referencias_modelo.md` que Respaldan el Proyecto

Para la presentación técnica y defensa del proyecto ante el jurado evaluador, se estructuran las citas verificadas que proporcionan respaldo epistemológico a cada bloque del modelo:

### Bloque I: Optimización Combinatoria y Métodos Estocásticos
- **Kirkpatrick, Gelatt & Vecchi (1983)** (*Science*, DOI: [10.1126/science.220.4598.671](https://doi.org/10.1126/science.220.4598.671)) y **Metropolis et al. (1953)** (*J. Chem. Phys.*, DOI: [10.1063/1.1699114](https://doi.org/10.1063/1.1699114)):
  - *Qué respalda*: El algoritmo de recocido simulado (*simulated annealing*) y el criterio de aceptación probabilística para optimizar configuraciones espaciales multiespecíficas de $N$ fijo (`Plan.optimize_fixed` y warmstart GPU).
- **Kleywegt, Shapiro & Homem-de-Mello (2002)** (*SIAM J. Optim.*, DOI: [10.1137/S1052623499363220](https://doi.org/10.1137/S1052623499363220)):
  - *Qué respalda*: El método de aproximación por promedio muestral (*Sample Average Approximation*, SAA) para evaluar escenarios de incertidumbre y convergencia en optimización estocástica.

### Bloque II: Dinámica Ecológica, Facilitación y Asimetría de Competencia
- **Padilla & Pugnaire (2006)** (*Frontiers in Ecology and the Environment*, DOI: [10.1890/1540-9295(2006)004[0196:TRONPI]2.0.CO;2](https://doi.org/10.1890/1540-9295(2006)004[0196:TRONPI]2.0.CO;2)) y **Flores & Jurado (2003)** (*J. Veg. Sci.*, DOI: [10.1111/j.1654-1103.2003.tb02225.x](https://doi.org/10.1111/j.1654-1103.2003.tb02225.x)):
  - *Qué respalda*: La inclusión de interacciones de facilitación (*nurse plants*) en ambientes áridos y semiáridos (Mesa Central mexicana), justificando el papel nodriza de *Prosopis laevigata* sobre cactáceas y agaves juveniles.
- **Weiner (1990)** (*Trends in Ecology & Evolution*, DOI: [10.1016/0169-5347(90)90095-U](https://doi.org/10.1016/0169-5347(90)90095-U)):
  - *Qué respalda*: La asimetría de la competencia por **luz** (un individuo de mayor altura proyecta sombra sobre uno menor sin reciprocidad). *Nota de rigor*: No respalda la competencia asimétrica por agua.
- **Weiner, Wright & Castro (1997)** (*Oikos*, JSTOR: 3546093):
  - *Qué respalda*: La simetría de la competencia subterránea por recursos hídricos en función del área y volumen radicular, sustentando la formulación $U / (U + U')$.
- **Rinella et al. (2015)** (*Ecological Applications*, DOI: [10.1890/14-1110.1](https://doi.org/10.1890/14-1110.1)):
  - *Qué respalda*: La justificación ecológica de la remoción de pastos introducidos agresivos (*Cenchrus ciliaris* / buffel), cuya competencia reduce significativamente el prendimiento de plántulas arbustivas.

### Bloque III: Ecofisiología de Especies de Zonas Áridas y Uso de Agua
- **Escamilla-Treviño (2012)** (*BioEnergy Research*, DOI: [10.1007/s12155-011-9159-x](https://doi.org/10.1007/s12155-011-9159-x)) y **Stewart (2015)** (*Frontiers in Plant Science*, DOI: [10.3389/fpls.2015.00684](https://doi.org/10.3389/fpls.2015.00684)):
  - *Qué respalda*: La jerarquía de eficiencia en el uso de agua del metabolismo CAM de los agaves frente a especies C3 y C4 (fijación de 10–40 g CO$_2$/kg H$_2$O en CAM vs 1–3 en C3), validando las demandas relativas reducidas de las 4 agaváceas.
- **USDA Forest Service, FEIS** (*Agave lechuguilla*):
  - *Qué respalda*: Talla de roseta (20–60 cm), sistema radicular superficial (~10 cm) y tolerancia a litosoles someros ($\le 30$ cm).
- **Scheinvar & Rodríguez Fuentes (2003)** (*Anales IB-UNAM*, Ser. Bot.):
  - *Qué respalda*: Porte adulto de *Opuntia streptacantha* de hasta 5 m, justificando su inclusión como especie grande (`LEVEL = 1`).
- **CONABIO/INIFAP** (*Monografía de Prosopis laevigata*):
  - *Qué respalda*: Porte arbóreo (hasta 13 m), enraizamiento profundo ($> 50$ m) y desarrollo lateral de raíces (hasta 15 m).

### Bloque IV: Climatología, Evapotranspiración y Datos Geográficos
- **Allen, Pereira, Raes & Smith (1998)** (*FAO Irrigation and Drainage Paper 56*):
  - *Qué respalda*: El método estándar de cálculo de evapotranspiración de referencia (ETo / PET) mediante FAO-56 Penman-Monteith con aproximación de radiación de Hargreaves-Samani.
- **Zomer, Xu & Trabucco (2022)** (*Scientific Data*, DOI: [10.1038/s41597-022-01493-1](https://doi.org/10.1038/s41597-022-01493-1)):
  - *Qué respalda*: La zonificación bioclimática según el Índice de Aridez (AI = P/PET) y los límites oficiales UNEP (árido 0.03–0.2, semiárido 0.2–0.5).
- **INEGI (2010)** (*Compendio Municipal de Charcas, SLP*) y **MIA Parque Eólica Dominica (2011)**:
  - *Qué respalda*: Contexto geográfico del altiplano potosino (elevación base, régimen térmico y pluvial BS1kw, dominancia de matorral desértico micrófilo y ausencia de pastoreo activo en el polígono protegido).
- **OpenTopoData SRTM 30 m (2026)**:
  - *Qué respalda*: El plano regional de elevación real del sitio (2,432 m s.n.m. medio con inclinación de 2.3% ENE) ajustado sobre 5 puntos satelitales en los polígonos.
- **Ficha Técnica INECOL/CONAFOR (2010)**:
  - *Qué respalda*: La densidad normativa de 658 pl/ha en terrenos llanos, la reducción a 524 pl/ha en pendientes $\ge 20\%$ y el diseño silvícola en tresbolillo para control de erosión e infiltración hídrica.

---

## 4. Guía Estratégica para la Presentación Técnica

1. **Destacar la Complementariedad de Ambos Modelos**:
   - `modelo_dominica` aporta la infraestructura geométrica (malla hexagonal tresbolillo, zonificación CONAFOR, plano regional SRTM 30 m de 5 puntos y restricción de subred `big_index = 3`).
   - `REFORESTATHON` aporta la potencia analítica de formulación MIP dual exacta con HiGHS/Gurobi, paralelización en GPU RTX 3060 y lo más valioso: **calibración con supervivencia real de campo trianual 2021–2023** (`72.6% a 92.6%`).
2. **Claridad Absoluta entre Datos Reales y Sintéticos**:
   - Resaltar que el plano regional (2,432 m) y los perímetros de los 31 polígonos (189.55 ha) son datos geodésicos reales.
   - Declarar con total transparencia científica que el micro-relieve de lomerío fractal (`slope_deg = 6.0°`) es un generador sintético espectral plausible utilizado para sombreado topográfico ante la ausencia de un DEM continuo de alta resolución LIDAR.
3. **Defensa de la Subred `big_index = 3`**:
   - Demostrar cómo la dispersión espacial de los mezquites, cardones y palmas chinas a una distancia mínima de $\sqrt{3}a \approx 7.25\text{ m}$ optimiza los microclimas de nodriza (+6 a +7 contactos de facilitación) y evita solapes de copa competitivos.
4. **Honestidad Científica en las Copas Adultas**:
   - Si el panel pregunta por los diámetros de copa de las especies de nopal y mezquite, señalar que se tomaron los supuestos de trabajo de §19.3 (`[guessing]`), destacando que en el análisis de sensibilidad §19.3 la reducción o aumento de copas no altera la factibilidad de la receta del programa silvícola.

---

## 5. Estado de la Suite de Pruebas

Tras las correcciones de unidades y la sincronización de archivos:
- **Pruebas unitarias**: `tests/test_mathematical_ecological_adversarial.py`
- **Resultado**: `21 passed in 17.51s`
- **CLI y Argumentos**: `--help` verificado y funcional en entornos Windows cp1252 sin errores de codificación.
