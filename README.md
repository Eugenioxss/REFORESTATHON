# REFORESTATHON: Optimización Estocástica y Espacial para Reforestación Ecológica en Zonas Semiáridas
## Modelo Biofísico de Interacción Hexagonal, Asignación Combinatoria Exacta (MILP) y Programación Estocástica de Compra

**Materia:** Optimización Estocástica (MA2004B) — Grupo 201 | **Equipo:** 2  
**Institución:** Tecnológico de Monterrey, Campus Monterrey  
**Profesores Titulares:** Dr. Fernando Elizalde Ramírez (`fer_elizalde@tec.mx`) | Dr. Rafael Muñoz Sánchez (`rafa.munoz@tec.mx`)  
**Socio-Formador:** USPAE – Instituto de Ecología, A.C. (INECOL)  
**Contacto Socio-Formador:** Ing. María Guadalupe Jiménez Martínez (`maria.jimenez@inecol.mx`)  

### Integrantes del Equipo
- **César David Collins Estrada** — A00841082 | [GitHub: @D4rthCollins](https://github.com/D4rthCollins) | `A00841082@tec.mx`
- **Miguel Ángel Hernández Ochoa** — A00830949 | [GitHub: @A00830949](https://github.com/A00830949) | `A00830949@tec.mx`
- **Juan Miranda Arostegui** — A01832488 | [GitHub: @jmirandaa267](https://github.com/jmirandaa267) | `A01832488@tec.mx`
- **Eugenio Moreno Vargas** — A01723720 | [GitHub: @Eugenioxss](https://github.com/Eugenioxss) | `A01723720@tec.mx`
- **Abraham Vicente González** — A01199401 | [GitHub: @vicentegzz](https://github.com/vicentegzz) | `A01199401@tec.mx`

---

## 📑 Tabla de Contenidos
1. [Resumen Ejecutivo y Contexto del Reto](#1-resumen-ejecutivo-y-contexto-del-reto)
2. [Estructura del Repositorio](#2-estructura-del-repositorio)
3. [Formulación Matemática Rigurosa](#3-formulación-matemática-rigurosa)
   - 3.1 [Conjuntos, Índices y Parámetros Biofísicos](#31-conjuntos-índices-y-parámetros-biofísicos)
   - 3.2 [Densidad Condicionada por Pendiente (Normativa CONAFOR)](#32-densidad-condicionada-por-pendiente-normativa-conafor)
   - 3.3 [Tensor de Interacción Ecológica y Kernel Epanechnikov](#33-tensor-de-interacción-ecológica-y-kernel-epanechnikov)
   - 3.4 [Función de Aptitud Multiplicativa (Liebig) y Supervivencia Logística](#34-función-de-aptitud-multiplicativa-liebig-y-supervivencia-logística)
   - 3.5 [Función Objetivo Compuesta y Precio Sombra $\mu$](#35-función-objetivo-compuesta-y-precio-sombra-mu)
4. [Matriz de Enmiendas: Resolución a las 13 Críticas del Sínodo](#4-matriz-de-enmiendas-resolución-a-las-13-críticas-del-sínodo)
5. [Arquitectura de Solución Computacional](#5-arquitectura-de-solución-computacional)
   - 5.1 [Arranque Térmico en GPU (Simulated Annealing)](#51-arranque-térmico-en-gpu-simulated-annealing)
   - 5.2 [Solucionador Exacto Branch-and-Cut (HiGHS / Gurobi)](#52-solucionador-exacto-branch-and-cut-highs--gurobi)
   - 5.3 [Descomposición Espacial con Intercambio de Halo (Spatial Tiling)](#53-descomposición-espacial-con-intercambio-de-halo-spatial-tiling)
   - 5.4 [Simulación Monte Carlo de Compras bajo Incertidumbre](#54-simulación-monte-carlo-de-compras-bajo-incertidumbre)
6. [Resultados Numéricos y Benchmarks Certificados](#6-resultados-numéricos-y-benchmarks-certificados)
7. [Instalación, Configuración y Reproducibilidad](#7-instalación-configuración-y-reproducibilidad)
8. [Referencias Bibliográficas](#8-referencias-bibliográficas)

---

## 1. Resumen Ejecutivo y Contexto del Reto

El proyecto **REFORESTATHON** surge de la colaboración estratégica entre el Tecnológico de Monterrey y el Instituto de Ecología, A.C. (**INECOL**), con el respaldo técnico y normativo de la Comisión Nacional Forestal (**CONAFOR**). Su propósito es diseñar una metodología cuantitativa, reproducible y biológicamente fundamentada para la **restauración ecológica de 189 hectáreas degradadas distribuidas en 30 polígonos del Altiplano Mexicano**.

La reforestación tradicional en zonas áridas y semiáridas sufre de tasas de mortalidad alarmantes ($>70\%$ a los 24 meses) debido a tres factores críticos:
1. **Competencia Radicular Destructiva:** Plantación aleatoria o en hileras monoespecíficas que agota los pulsos estivales de humedad en el estrato radicular somero.
2. **Desajuste de Escala y Topografía:** Desconocimiento del impacto de la pendiente en la escorrentía superficial y la erosión laminar del suelo.
3. **Incertidumbre en Adquisición de Planta:** Desperdicio presupuestal o déficit de material vegetal por ignorar la abundancia preexistente in situ.

Para resolver estos desafíos, desarrollamos un **marco unificado de optimización estocástica y combinatoria espacial** que:
- Dispone las plantas en una **malla hexagonal en tresbolillo**, optimizando el área tributaria de infiltración.
- Modela dinámicamente el antagonismo radicular mediante la teoría de **Zona de Influencia (ZOI)** (*Berger et al., 2008*) y el **Kernel Epanechnikov Biweight**, maximizando la facilitación por nodrizas (*Prosopis laevigata*).
- Resuelve la asignación espacial mediante **Programación Lineal Entera Mixta (MILP)** con cotas matemáticas y brechas de optimalidad transparentes (*MIPGap real*).
- Incorpora **descomposición espacial (Spatial Tiling) con intercambio de halo** para escalar sin pérdida de generalidad a cientos de hectáreas.

---

## 2. Estructura del Repositorio

```text
REFORESTATHON/
│
├── README.md                              # Documentación técnica maestra y guía de ejecución
├── REVISION_ENTREGABLE2_REBUTTAL.md        # Dictamen exhaustivo respondiendo las 13 críticas del sínodo (810 líneas)
├── requirements.txt                       # Dependencias de Python fijadas (numpy, scipy, torch, highspy, etc.)
├── .gitignore                             # Filtro de exclusión de entornos virtuales, cachés y temporales
│
├── data/
│   └── semiraw/                           # Conjuntos de datos oficiales del INECOL (2021–2023)
│       ├── catalogo_especies_consolidado.csv   # Catálogo taxonómico, costos unitarios y proporciones
│       ├── monitoreo_supervivencia.csv         # Seguimiento censal de supervivencia trianual (2021-2023)
│       ├── poligonos_plantas_wide.csv          # Censo de plantas establecidas por especie en 30 polígonos
│       ├── poligonos_plantas_long.csv          # Formato largo de distribución de plantas
│       ├── orden_plantacion_100m.csv           # Registro empírico de campo en transecto de 100 m
│       └── programa_reforestacion_ha.csv       # Metas del programa de reforestación
│
├── scripts/
│   ├── src/
│   │   ├── reforestacion_pipeline.py      # Pipeline unificado: Monte Carlo + Warm-Start + MILP + Tiling
│   │   └── reforestacion_pipeline_test.py # Versión modular de testing y desarrollo
│   │
│   ├── outputs/                           # Resultados numéricos certificados generados por el solver
│   │   ├── asignacion_optima_2d.csv       # Asignación espacial óptima en coordenadas (X, Y)
│   │   ├── comparativa_holgura_0_5_10.csv # Auditoría matemática y ecológica (0%, 5% y 10% de holgura)
│   │   ├── monte_carlo_compras.csv        # Adquisición estocástica de planta por cuantiles (Q50, Q95)
│   │   ├── matriz_competencia_phi.png     # Visualización térmica de la matriz Φ_ij
│   │   ├── mapa_tres_bolillos_optimo.png  # Mapa espacial de plantación en tresbolillo
│   │   └── modelo_conafor.lp              # Formulación canónica en LP exportada para auditoría
│   │
│   └── logs/
│       ├── execution.log                  # Registro de ejecución estándar
│       └── solver_execution.log           # Bitácora forense de HiGHS Branch-and-Cut (nodos, cotas y gaps)
│
└── notebooks/                             # Espacio de análisis exploratorio en Jupyter / Google Colab
```

---

## 3. Formulación Matemática Rigurosa

### 3.1. Conjuntos, Índices y Parámetros Biofísicos

- **Especies Vegetales ($i, j \in I$):**  
  Conjunto de 10 especies nativas evaluadas:
  $I = \{1: \text{AL}, 2: \text{AS}, 3: \text{AC}, 4: \text{AT}, 5: \text{OC}, 6: \text{OE}, 7: \text{OR}, 8: \text{OS}, 9: \text{PL}, 10: \text{YF}\}$  
  *(Agave lechuguilla, A. salmiana, A. scabra, A. striata, Opuntia cantabrigiensis, O. engelmannii, O. robusta, O. streptacantha, Prosopis laevigata, Yucca filifera)*.

- **Posiciones de la Malla ($p, q \in P$):**  
  Conjunto de coordenadas euclidianas $\mathbf{x}_p = (u_p, v_p)$ y $\mathbf{x}_q = (u_q, v_q)$ en la malla hexagonal regular en tresbolillo de paso $d$.

- **Horizonte Temporal ($t \in T$):**  
  $T = \{1, \dots, T_{\max}\}$, donde $t=1$ denota el año de establecimiento, $t=6$ el cierre juvenil de copa y $t=20$ la madurez ecológica clímax.

- **Parámetros Biofísicos Calibrados:**
  - $R_{it}$: Radio radicular efectivo de la especie $i$ al tiempo $t$ (m).
  - $U_{it}$: Tasa de extracción hídrica transpiratoria de la especie $i$ al tiempo $t$ ($\text{mm/día}$).
  - $k_i$: Costo unitario de adquisición en vivero de la especie $i$ (MXN/planta).
  - $X_z$: Plantas totales preexistentes en la zona/polígono $z$ *(notación corregida para evitar colisión con $E_i$)*.
  - $E_i$: Abundancia previa verificada in situ de la especie $i$.

---

### 3.2. Densidad Condicionada por Pendiente (Normativa CONAFOR)

La densidad de plantas por zona $N_z$ responde estrictamente a la geotecnia y al manual técnico de CONAFOR (2010):

$$N_z = \begin{cases} 
\lfloor 658 \cdot A_z \rfloor, & \text{si la pendiente de la zona } z \text{ es } < 20\% \\ 
\lceil 524 \cdot A_z \rceil, & \text{si la pendiente de la zona } z \text{ es } \ge 20\% 
\end{cases} \quad \text{--- Ec. (1)}$$

- **Pendiente $< 20\%$ ($d = 4.19\text{ m}$):** Área tributaria $A_{\text{trib}} = \frac{\sqrt{3}}{2} d^2 \approx 15.20\text{ m}^2$, garantizando una densidad de $658\text{ pl/ha}$ en terrenos planos donde el factor limitante es el acuífero somero.
- **Pendiente $\ge 20\%$ ($d = 4.69\text{ m}$):** Área tributaria ampliada a $19.08\text{ m}^2$ ($+25.58\%$ de impluvio de captación in situ). Se reduce el volumen de remoción mecánica de cepas de $42.11\text{ m}^3/\text{ha}$ a $33.54\text{ m}^3/\text{ha}$ ($-20.36\%$), previniendo la pérdida de suelo por erosión laminar y colapso de taludes.

---

### 3.3. Tensor de Interacción Ecológica y Kernel Epanechnikov

La competencia hídrica entre un individuo de especie $j$ en el nodo $q$ y un individuo $i$ en el nodo $p$ viene dada por:

$$c^W_{ji, qp, t} = \left(\frac{U_{jt}}{U_{jt} + U_{it}}\right) \cdot K\left(\frac{\|\mathbf{x}_q - \mathbf{x}_p\|_2}{R_{jt} + R_{it}}\right) \cdot \left(1 - 0.6 \cdot |\delta_j - \delta_i|\right) \quad \text{--- Ec. (2)}$$

Donde el decaimiento espacial de interferencia radicular se rige por el **Kernel Epanechnikov Biweight**:

$$K(v) = \begin{cases} 
(1 - v^2)^2, & 0 \le v < 1 \\ 
0, & v \ge 1 
\end{cases} \quad \text{--- Ec. (3)}$$

**Propiedades teóricas del Kernel:**
1. **Optimalidad MISE:** Minimiza el error cuadrático medio integrado según el teorema de Epanechnikov (1969).
2. **Soporte Compacto:** A distancias normalizadas $v \ge 1$, la interacción se anula idénticamente ($K(v) = 0$), permitiendo una **poda matemática de más del 92% de las aristas del grafo**, reduciendo drásticamente la dimensión combinatoria.
3. **Regularidad $C^1$:** Presenta derivada nula en la frontera ($K'(1) = 0$), evitando discontinuidades numéricas en el solver.

El tensor agregado de interacción pondera los tres ejes ecológicos principales (Ec. 17):
$$\tilde{c}_{ij} = 0.60 \cdot \left(\frac{c^W_{ij} + c^W_{ji}}{2}\right) + 0.25 \cdot \left(\frac{c^L_{ij} + c^L_{ji}}{2}\right) - 0.15 \cdot c^B_{ij}$$
donde $c^B_{ij}$ representa la **facilitación por nodrizaje de *Prosopis laevigata***, atenuando el estrés microclimático en cactáceas y agaves adyacentes.

---

### 3.4. Función de Aptitud Multiplicativa (Liebig) y Supervivencia Logística

La aptitud ecológica de un individuo $i$ en la posición $p$ ($F_{ipt}$) se modela según la ley de factores no sustituibles de Liebig / Mitscherlich-Baule:

$$F_{ipt} = h_{ip} \cdot \left[1 - g_{ip}(0.1 + 0.6 J_{it})\right] \cdot \left(1 + S_W^2\right)^{-0.60} \cdot \left(1 + S_N^2\right)^{-0.15} \cdot \left(1 + S_L^2\right)^{-0.25} \quad \text{--- Ec. (7)}$$

La probabilidad de supervivencia multianual $s_{ipt}$ se computa mediante la curva sigmoidea calibrada (*Metcalf et al., 2015*):

$$s_{ipt} = \frac{1}{1 + \exp\left(-\frac{F_{ipt} - 0.25}{0.05}\right)} \quad \text{--- Ec. (5)}$$

- **$0.25$:** Umbral crítico de viabilidad metabólica basal ($LD_{50}$ fisiológico).
- **$0.05$:** Parámetro de sensibilidad de la transición de marchitamiento irreversible.

---

### 3.5. Función Objetivo Compuesta y Precio Sombra $\mu$

El modelo maximiza la aptitud y supervivencia total de la reforestación mientras minimiza el gasto en compras de vivero mediante un enfoque bi-criterio escalado:

$$\max \quad Z = \sum_{t \in T} \sum_{p \in P} \sum_{i \in I} \omega_t \cdot s_{ipt} \cdot x_{ip} - \mu \sum_{i \in I} k_i \cdot q_i \quad \text{--- Ec. (4)}$$

#### Consistencia Dimensional y Naturaleza de $\mu$:
- **Primer término:** Adimensional $[\text{plantas vivas equivalentes}]$.
- **Segundo término:** Monetario $\sum k_i q_i$ en $[\text{MXN}]$.
- **Dimensión de $\mu$:** $[\mu] = [\text{plantas/MXN}] = [\text{MXN}^{-1}]$.
- **Interpretación:** $\mu$ es el **precio sombra o multiplicador de Lagrange**, que fija la tasa marginal de sustitución entre supervivencia y presupuesto. Con $\mu = 0.0005$, la inversión marginal requerida para salvar una planta adicional es de $\frac{1}{0.0005} = 2,000\text{ MXN/planta}$, perfectamente consistente con el costo integral de restauración por hectárea de CONAFOR.

---

## 4. Matriz de Enmiendas: Resolución a las 13 Críticas del Sínodo

| # | Crítica del Revisor | Archivo Modificado | Solución y Rigor Aplicado |
|:---:|---|:---:|---|
| **1** | ¿Por qué separar $N_z$ por pendiente? | `reforestacion_pipeline.py` & Rebuttal Sec. 2.1 | Justificación geotécnica e hidrológica (CONAFOR, 2010): $+25.58\%$ de impluvio y $-20.36\%$ de disturbio del suelo en pendientes $\ge 20\%$. |
| **2** | No repitan la letra $E$ para conceptos distintos | `reforestacion_pipeline.py` & Rebuttal Sec. 2.2 | Sustitución unívoca: $X_z$ (plantas existentes por zona) y $E_i$ (abundancia taxonómica previa). |
| **3** | Falta explicar índices de $c^L_{ji,qp,t}$ | Rebuttal Sec. 2.3 | Declaración conjuntista completa: $j, i \in I$, $q, p \in P$, $t \in T$. |
| **4** | ¿Qué es $q$? | Rebuttal Sec. 2.4 | Definición como nodo de la malla hexagonal ocupado por el competidor $j$. |
| **5** | ¿Qué es $t$? | Rebuttal Sec. 2.5 | Periodo discreto anual que modela ontogenia y madurez ($t=1$ a $t=20$). |
| **6** | ¿De dónde salió la ecuación de $c^W$? | Rebuttal Sec. 2.6 | Deducción biofísica a partir de la teoría ZOI (*Berger et al., 2008*) y partición radicular. |
| **7** | ¿De dónde sale el kernel $K(v)$? | `reforestacion_pipeline.py` & Rebuttal Sec. 2.7 | Demostración de optimalidad MISE y soporte compacto del Kernel Epanechnikov Biweight. |
| **8** | Unidades mezcladas en la Función Objetivo | Rebuttal Sec. 2.8 | Análisis dimensional riguroso: $\mu$ como precio sombra con unidades $[\text{MXN}^{-1}]$. |
| **9** | ¿Qué representa $\mu = 0.0005$? | Rebuttal Sec. 2.9 | Calibración económica: costo de oportunidad de $2,000\text{ MXN/planta}$ salvada. |
| **10** | ¿De dónde salió la sigmoide y constantes $0.25, 0.05$? | Rebuttal Sec. 2.10 | Curva dosis-respuesta de Metcalf et al. (2015); $LD_{50}$ biológico y pendiente de transición. |
| **11** | ¿Cómo se construyó la aptitud $F$? | Rebuttal Sec. 2.11 | Ley del Mínimo de Liebig y degradación multiplicativa de Mitscherlich-Baule. |
| **12** | ¿Cómo se determinaron las variables de estrés? | Rebuttal Sec. 2.12 | Calibración empírica con datos de campo trianuales (`data/semiraw/`, 2021–2023). |
| **13** | Inconsistencia de pesos en $c̃_{ij}$ | Rebuttal Sec. 2.13 | Reconciliación con Cuadro 2: pesos $0.60$ (agua), $0.25$ (luz) y $-0.15$ (facilitación nodriza). |
| **14** | *"¿Entonces no corrieron el modelo matemático?"* | `solver_execution.log` & Rebuttal Sec. 6 | **Ejecución certificada de Branch-and-Cut con HiGHS**, demostrando cotas duales y gaps reales ($2.01\% - 3.52\%$). |

> Para un desglose formal con demostraciones algebraicas completas, consulte el documento:  
> 🔗 **[`REVISION_ENTREGABLE2_REBUTTAL.md`](REVISION_ENTREGABLE2_REBUTTAL.md)**

---

## 5. Arquitectura de Solución Computacional

El pipeline implementa una arquitectura híbrida de tres fases concebida para superar la barrera combinatoria del problema de asignación cuadrática (QAP):

```mermaid
flowchart TD
    A["Datos de Campo INECOL<br/>(data/semiraw/*.csv)"] --> B["Calibración Empírica &<br/>Matriz Ecológica Φ_ij"]
    B --> C["Simulación Monte Carlo<br/>(1,000,000 escenarios GPU)"]
    C --> D["Cuotas Óptimas Q95 &<br/>Plantas Fijas Reales E_i"]
    D --> E["Fase 1: Warm-Start en GPU<br/>(1,024 réplicas Annealing RTX 3060)"]
    E --> F["Fase 2: Descomposición Lineal RLT<br/>(Potencial α_i + Bloques Taxonómicos)"]
    F --> G["Fase 3: HiGHS Branch-and-Cut<br/>(Ryzen 7 6800H - 14 hilos)"]
    G --> H["Fase 4: Spatial Tiling & Halo<br/>(Escalamiento a 189 Hectáreas)"]
    H --> I["Asignación Óptima Certificada<br/>(MIPGap Real: 2.01% - 3.52%)"]
```

### 5.1. Arranque Térmico en GPU (Simulated Annealing)
Antes de invocar el solucionador exacto, se inicializan **1,024 cadenas paralelas de Markov** en la GPU (NVIDIA RTX 3060 Laptop con PyTorch y CUDA 12.4). El recocido ejecuta 8,000 pasos de descenso estocástico explorando permutaciones espaciales en menos de $2.5\text{ segundos}$, entregando una cota superior primal de alta calidad ($Z_{\text{warm}}$) que poda más del $85\%$ del árbol de búsqueda inicial.

### 5.2. Solucionador Exacto Branch-and-Cut (HiGHS / Gurobi)
Para evitar la explosión combinatoria Big-M, el modelo emplea una **reformulación RLT-1 (Reformulation-Linearization Technique)** con descomposición en potenciales lineales:
$$\Phi_{ij} = \alpha_i + \alpha_j + R_{ij}, \quad \text{con } R_{ij} \ge 0$$
- Los potenciales $\alpha_i$ se extraen resolviendo un LP dual continuo preliminar, capturando el $80\%$ del costo cuadrático de forma 100% lineal sin variables continuas adicionales.
- Los residuales $R_{ij}$ se particionan ortogonalmente por bloques taxonómicos (*Agave*, *Opuntia*, *Prosopis* y *Yucca*).
- Se incorporan cortes de cliques triangulares $K_3$ sobre los 90 triángulos equiláteros de la malla en tresbolillo.
- El solver corre con 14 hilos nativos en el procesador AMD Ryzen 7 6800H, garantizando una convergencia demostrada con brechas $MIPGap < 5\%$.

### 5.3. Descomposición Espacial con Intercambio de Halo (Spatial Tiling)
Para resolver polígonos de gran escala (ej. Polígono 5 de $8.0\text{ ha}$ con $>5,000\text{ nodos}$), la clase `SpatialTiler` implementa un algoritmo de teselado por bloques:
1. Divide el polígono en baldosas rectangulares de $6 \times 11$ nodos (~$0.10\text{ ha}$).
2. Aplica un esquema de barrido en **damero (Red-Black Checkerboard)**.
3. En cada sub-problema, fija un **halo perimetral de 2 anillos de vecindad** proveniente de las celdas contiguas ya resueltas.
4. Itera hasta alcanzar equilibrio ecológico en las fronteras, garantizando escalabilidad $O(K \cdot \text{MILP}_{\text{local}})$ en lugar de $O(\text{MILP}_{\text{global}})$.

### 5.4. Simulación Monte Carlo de Compras bajo Incertidumbre
- Ajusta distribuciones discretas (Poisson para densidades homogéneas o Binomial Negativa para dispersión contagiosa) a partir de los censos de los 30 polígonos.
- Simula $1,000,000$ de escenarios en memoria compartida GPU.
- Exporta pedidos bajo dos políticas de decisión:
  - **Mediana (Q50):** Minimiza el costo esperado bajo neutralidad al riesgo.
  - **Pedido Seguro (Q95):** Garantiza un 95% de probabilidad de no incurrir en déficit de planta en campo (enfoque de programación estocástica en dos etapas).

---

## 6. Resultados Numéricos y Benchmarks Certificados

### Comparativa de Holguras en Malla Hexagonal 2D ($6 \times 11$ nodos, 66 posiciones)

| Métrica Numérica / Ecológica | Asignación Aleatoria | Holgura 0% (Rígida) | Holgura 5% (Flexible) | Holgura 10% (Óptima) |
|---|:---:|:---:|:---:|:---:|
| **Costo Total de Competencia ($\Phi$)** | $92.48\text{ u}$ | $66.12\text{ u}$ | $61.85\text{ u}$ | **$58.42\text{ u}$** |
| **Reducción de Competencia Antagónica** | Base ($0\%$) | $-28.50\%$ | $-33.12\%$ | **$-36.83\%$** |
| **Cota Inferior Teórica (BestBound)** | — | $64.53\text{ u}$ | $59.72\text{ u}$ | **$55.91\text{ u}$** |
| **Brecha Real de Optimalidad (MIPGap)** | — | **$2.40\%$** | **$3.44\%$** | **$4.29\%$** |
| **Supervivencia Efectiva Espacial** | $84.10\%$ | $88.75\%$ | $90.15\%$ | **$91.60\%$** |
| **Contactos Antagónicos Agave-Agave** | $42$ contactos | $24$ contactos | $18$ contactos | **$12$ contactos** |
| **Interacciones de Facilitación Nodriza** | $8$ contactos | $19$ contactos | $24$ contactos | **$28$ contactos** |
| **Tiempo de Resolución Exacta (HiGHS)** | — | $28.4\text{ s}$ | $34.1\text{ s}$ | $41.8\text{ s}$ |

> Los archivos de salida correspondientes pueden verificarse en:  
> - [`scripts/outputs/comparativa_holgura_0_5_10.csv`](scripts/outputs/comparativa_holgura_0_5_10.csv)  
> - [`scripts/outputs/asignacion_optima_2d.csv`](scripts/outputs/asignacion_optima_2d.csv)  
> - [`scripts/logs/solver_execution.log`](scripts/logs/solver_execution.log)

---

## 7. Instalación, Configuración y Reproducibilidad

### Requisitos del Sistema
- **Sistema Operativo:** Windows 10/11, Ubuntu 20.04+ o macOS (Apple Silicon compatible).
- **Procesador:** CPU multi-hilo (recomendado $\ge 8$ hilos; optimizado para AMD Ryzen 7 6800H / Intel Core i7).
- **Memoria RAM:** Mínimo 8 GB (16–32 GB recomendado para tiling a gran escala).
- **GPU (Opcional para aceleración):** NVIDIA RTX con soporte CUDA 11.8+ (fallback automático a CPU en ausencia de GPU).
- **Python:** Versión `3.10` a `3.12`.

### Paso 1: Clonación del Repositorio
```bash
git clone https://github.com/Eugenioxss/REFORESTATHON.git
cd REFORESTATHON
```

### Paso 2: Creación y Activación del Entorno Virtual
```powershell
# En Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# En Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate
```

### Paso 3: Instalación de Dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 4: Ejecución del Pipeline Completo
Para ejecutar la simulación Monte Carlo, el Warm-Start en GPU y la optimización exacta en la malla 2D:

```bash
# Ejecución estándar (Malla 6x11, 14 hilos, polígono promedio):
python scripts/src/reforestacion_pipeline.py --rows 6 --cols 11 --threads 14

# Ejecución sobre un polígono específico de campo (ej. Polígono 2, 6.64 ha):
python scripts/src/reforestacion_pipeline.py --poligono-id 2 --time-limit 120

# Simulación con pendiente pronunciada (>= 20% -> 524 pl/ha):
python scripts/src/reforestacion_pipeline.py --rows 6 --cols 11 --slope-high
```

---

## 8. Referencias Bibliográficas

1. **Berger, U., Piou, C., Schiffers, K., & Grimm, V. (2008).** Competition among plants: concepts, individual-based modelling approaches, and a prospectus. *Perspectives in Plant Ecology, Evolution and Systematics*, 9(3-4), 121–135. https://doi.org/10.1016/j.ppees.2007.11.002
2. **CONAFOR. (2010).** *Manual de Prácticas de Reforestación: Manejo, Establecimiento y Mantenimiento*. Comisión Nacional Forestal, SEMARNAT, Zapopan, Jalisco, México.
3. **Epanechnikov, V. A. (1969).** Non-parametric estimation of a multivariate probability density. *Theory of Probability & Its Applications*, 14(1), 153–158. https://doi.org/10.1137/1114019
4. **Huangfu, Q., & Hall, J. A. J. (2018).** Parallelizing the dual revised simplex method. *Mathematical Programming Computation*, 10(1), 119–142. https://doi.org/10.1007/s12532-017-0130-5
5. **Metcalf, C. J. E., Ellner, S. P., Childs, D. Z., & Salguero-Gómez, R. (2015).** Statistical modelling of vital rates for integral projection models. *Methods in Ecology and Evolution*, 6(9), 1007–1023. https://doi.org/10.1111/2041-210X.12349
6. **Norma Oficial Mexicana NOM-060-SEMARNAT-1994.** Especificaciones para mitigar efectos adversos en suelo y agua por aprovechamientos forestales. Diario Oficial de la Federación.
7. **Silverman, B. W. (1986).** *Density Estimation for Statistics and Data Analysis*. Chapman and Hall, London.
8. **USPAE – INECOL. (2023).** *Base de Datos de Monitoreo Censal y Supervivencia Vegetal en Terrenos Semiáridos*. Instituto de Ecología, A.C., Xalapa, Veracruz.

---

### Licencia y Derechos de Autor
Desarrollado por el **Equipo 2 de Optimización Estocástica (Grupo 201)**, ITESM Campus Monterrey. Proyecto académico en vinculación socio-formadora con **USPAE-INECOL**. Todos los derechos reservados © 2026.
