# -*- coding: utf-8 -*-
"""
Script generador del documento LaTeX oficial del Entregable 3 (REFORESTATHON)
Equipo 2 - Optimizacion Estocastica (Gpo 201)
Genera: entregable3_reporte_final.tex
"""
import os
import pandas as pd
import numpy as np

base_dir = r"d:\Codingggg\Notas\Estocastico\REFORESTATHON"
outputs_dir = os.path.join(base_dir, "entregable3_outputs")
tex_path = os.path.join(base_dir, "entregable3_reporte_final.tex")

# Cargar datos
df_sum = pd.read_csv(os.path.join(outputs_dir, "tabla_existentes_y_suministro_especie.csv"))
df_comp = pd.read_csv(os.path.join(outputs_dir, "tabla_competencia_1ha.csv"))
df_m_sec = pd.read_csv(os.path.join(outputs_dir, "matriz_transicion_markov_secuencial_opt.csv"), index_col=0)
df_m_vec = pd.read_csv(os.path.join(outputs_dir, "matriz_transicion_markov_vecinos_opt.csv"), index_col=0)
df_ord = pd.read_csv(os.path.join(outputs_dir, "orden_plantacion_ejemplo_1ha.csv"))

# Construir tabla de Markov
def format_markov_table(df_markov, label, caption):
    especies = ["AL", "AT", "AC", "AS", "OC", "OE", "OR", "OS", "PL", "YF"]
    lines = []
    lines.append(r"\begin{table}[H]")
    lines.append(r"\centering")
    lines.append(r"\small")
    lines.append(r"\caption{" + caption + r"}\label{" + label + r"}")
    lines.append(r"\resizebox{\textwidth}{!}{%")
    lines.append(r"\begin{tabular}{lcccccccccc|cc}")
    lines.append(r"\toprule")
    lines.append(r"\textbf{Estado Actual} & \textbf{AL} & \textbf{AT} & \textbf{AC} & \textbf{AS} & \textbf{OC} & \textbf{OE} & \textbf{OR} & \textbf{OS} & \textbf{PL} & \textbf{YF} & $\boldsymbol{\pi_i}$ & $\boldsymbol{\mu_i}$ \textbf{(pasos)} \\")
    lines.append(r"\midrule")
    for esp in especies:
        row = df_markov.loc[esp]
        vals = [f"{row[c]:.4f}" for c in especies]
        pi_val = f"{row['Estacionaria_pi']:.4f}"
        mu_val = f"{row['Tiempo_Retorno_mu']:.2f}"
        lines.append(f"\\textbf{{{esp}}} & " + " & ".join(vals) + f" & \\textbf{{{pi_val}}} & \\textbf{{{mu_val}}} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}%")
    lines.append(r"}")
    lines.append(r"\end{table}")
    return "\n".join(lines)

table_markov_sec = format_markov_table(
    df_m_sec, 
    "tab:markov_sec", 
    "Matriz de probabilidades de transición $P^{\\text{sec}}$ (10 estados), distribución estacionaria $\\pi$ y tiempo medio de retorno $\\mu_i$ en el recorrido secuencial boustrophedon (1,000 simulaciones estocásticas)."
)

table_markov_vec = format_markov_table(
    df_m_vec, 
    "tab:markov_vec", 
    "Matriz espacial de transición de vecindad hexagonal $P^{\\text{vec}}$ entre cepas contiguas a primer anillo ($R \\le 4.8\\text{ m}$). Nótese el bloque estrictamente nulo $3\\times 3$ entre especies de gran porte (OS, PL, YF)."
)

# Construir tabla de orden de plantacion
def format_orden_table(df):
    rows_first = df.iloc[:30]
    rows_last = df.iloc[-10:]
    lines = []
    lines.append(r"\begin{table}[H]")
    lines.append(r"\centering")
    lines.append(r"\footnotesize")
    lines.append(r"\caption{Bitácora operativa y orden de plantación secuencial en 1 ha (réplica $s=1$, 531 plantas nuevas en $658\text{ pl/ha}$). Se muestran los primeros 30 pasos consecutivos y los últimos 10 pasos de cierre del predio.}\label{tab:bitacora_plantacion}")
    lines.append(r"\resizebox{\textwidth}{!}{%")
    lines.append(r"\begin{tabular}{rccccccrrc}")
    lines.append(r"\toprule")
    lines.append(r"\textbf{Paso $k$} & \textbf{Fila} & $(m, n)$ & \textbf{Submalla} & \textbf{$X$ (m)} & \textbf{$Y$ (m)} & \textbf{Especie} & \textbf{Etapa Operativa} & \textbf{Dist. (m)} & $\boldsymbol{F_k}$ \\")
    lines.append(r"\midrule")
    for _, r in rows_first.iterrows():
        p = int(r['paso'])
        fila = int(r['fila'])
        mn = f"({int(r['m_red'])}, {int(r['n_red'])})"
        sub = int(r['submalla'])
        xm = f"{r['x_m']:.2f}"
        ym = f"{r['y_m']:.2f}"
        esp = f"\\textbf{{{r['codigo_especie']}}}"
        etapa = r['etapa_operativa']
        d_ant = f"{r['distancia_paso_anterior_m']:.2f}"
        fk = f"{r['aptitud_esperada_Fk']:.4f}"
        lines.append(f"{p} & {fila} & {mn} & {sub} & {xm} & {ym} & {esp} & {etapa} & {d_ant} & {fk} \\\\")
    lines.append(r"\midrule")
    lines.append(r"\multicolumn{10}{c}{\textit{... [Pasos 31 al 521 omitidos para brevedad editorial; bitácora completa en archivo orden\_plantacion\_ejemplo\_1ha.csv] ...}} \\")
    lines.append(r"\midrule")
    for _, r in rows_last.iterrows():
        p = int(r['paso'])
        fila = int(r['fila'])
        mn = f"({int(r['m_red'])}, {int(r['n_red'])})"
        sub = int(r['submalla'])
        xm = f"{r['x_m']:.2f}"
        ym = f"{r['y_m']:.2f}"
        esp = f"\\textbf{{{r['codigo_especie']}}}"
        etapa = r['etapa_operativa']
        d_ant = f"{r['distancia_paso_anterior_m']:.2f}"
        fk = f"{r['aptitud_esperada_Fk']:.4f}"
        lines.append(f"{p} & {fila} & {mn} & {sub} & {xm} & {ym} & {esp} & {etapa} & {d_ant} & {fk} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}%")
    lines.append(r"}")
    lines.append(r"\end{table}")
    return "\n".join(lines)

table_orden = format_orden_table(df_ord)

# Generar texto completo del archivo .tex
tex_doc = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\renewcommand{\familydefault}{\sfdefault}
\usepackage[spanish,es-nodecimaldot,es-tabla]{babel}
\usepackage[a4paper, margin=1.8cm, top=2.0cm, bottom=2.0cm]{geometry}
\usepackage{amsmath,amssymb,amsfonts,amsthm,mathtools}
\usepackage{booktabs,tabularx,array,longtable,multirow,colortbl}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{float}
\usepackage{listings}
\usepackage{enumitem}
\usepackage{microtype}
\usepackage{caption,subcaption}
\usepackage{fancyhdr}
\usepackage{hyperref}

% Paleta de colores sobria y profesional
\definecolor{codegreen}{rgb}{0,0.45,0}
\definecolor{codegray}{rgb}{0.45,0.45,0.45}
\definecolor{codepurple}{rgb}{0.50,0,0.70}
\definecolor{codeblue}{rgb}{0.0,0.2,0.6}
\definecolor{backcolour}{rgb}{0.98,0.98,0.98}
\definecolor{tableheader}{gray}{0.90}
\definecolor{softgreen}{rgb}{0.92,0.97,0.92}
\definecolor{softblue}{rgb}{0.92,0.95,0.98}

% Configuración de listings para código Python
\lstdefinestyle{pythonstyle}{
    backgroundcolor=\color{backcolour},
    commentstyle=\color{codegreen}\itshape,
    keywordstyle=\color{codeblue}\bfseries,
    numberstyle=\tiny\color{codegray},
    stringstyle=\color{codepurple},
    basicstyle=\footnotesize\ttfamily,
    breakatwhitespace=false,
    breaklines=true,
    captionpos=b,
    keepspaces=true,
    numbers=left,
    numbersep=5pt,
    showspaces=false,
    showstringspaces=false,
    showtabs=false,
    tabsize=4,
    frame=single,
    rulecolor=\color{gray!30}
}
\lstset{style=pythonstyle}

% Hipervínculos
\hypersetup{
    colorlinks=true,
    linkcolor=blue!80!black,
    citecolor=blue!80!black,
    urlcolor=blue!80!black,
    pdftitle={Entregable 3: Experimentación, Simulación Estocástica y Resultados - Equipo 2},
    pdfauthor={Equipo 2 - Optimización Estocástica (Gpo 201)}
}

% Encabezados y pies de página
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\sffamily\textit{Reto: Entregable 3 — Simulación Estocástica y Resultados}}
\fancyhead[R]{\small\sffamily\textit{Equipo 2 — Optimización Estocástica (Gpo 201)}}
\fancyfoot[C]{\sffamily\thepage}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0.0pt}

\begin{document}

% ==========================================
% PORTADA OFICIAL (IDÉNTICA AL ENTREGABLE 2)
% ==========================================
\thispagestyle{empty}
\begin{center}
    \vspace*{1.2cm}
    {\Huge\bfseries\itshape Reto: Entregable 3}\\[0.4cm]
    {\huge\bfseries\itshape Experimentación, Simulación Estocástica y Resultados}\\[0.6cm]
    {\Large\bfseries Optimización Espacial y Económica de la Reforestación con Especies Nativas en la Sierra de Álvarez}\\[1.5cm]

    {\Large\bfseries Equipo 2}\\[0.6cm]

    {\Large\bfseries Integrantes:}\\[0.3cm]
    {\large
    César David Collins Estrada — A00841082\\[0.15cm]
    Miguel Ángel Hernández Ochoa — A00830949\\[0.15cm]
    Juan Miranda Arostegui — A01832488\\[0.15cm]
    Eugenio Moreno Vargas — A01723720\\[0.15cm]
    Abraham Vicente González — A01199401\\[1.4cm]
    }

    {\large
    \textbf{Materia:} Optimización estocástica (Gpo 201)\\[0.25cm]
    \textbf{Profesores:} Dr. Fernando Elizalde Ramírez – Dr. Rafael Muñoz\\[0.25cm]
    \textbf{Fecha:} Octubre de 2026\\[2.0cm]
    }

    {\Large\bfseries Instituto Tecnológico y de Estudios Superiores de Monterrey}
\end{center}

\newpage
\thispagestyle{empty}
\tableofcontents
\newpage

\setcounter{page}{1}

% ========================================================
% SECCIÓN 1. CARACTERÍSTICAS DE LA PC Y SOFTWARE UTILIZADO
% ========================================================
\section{Características de la PC y software utilizado}

El desarrollo, paralelización y ejecución de los experimentos computacionales, las simulaciones estocásticas de Monte Carlo ($M = 1,000$ réplicas sobre mallas espaciales completas de 1 hectárea) y la resolución de los modelos exactos de Programación Lineal Entera Mixta (MILP con linealización cuadrática RLT-1 y desigualdades válidas de clique triangular $K_3$) se llevaron a cabo en una estación de trabajo de escritorio de alto rendimiento (\textit{Workstation}). 

La arquitectura Zen 4 de última generación empleada en la CPU proporciona un bus de comunicación de alta velocidad con la memoria DDR5 y soporte nativo para instrucciones vectoriales AVX-512, lo cual resulta crítico para la rápida construcción y consulta espacial de árboles de búsqueda $k$-d (\texttt{scipy.spatial.cKDTree}) al evaluar las interacciones biológicas por pares en radios de hasta $7.5\text{ m}$. Asimismo, el subsistema de almacenamiento NVMe PCIe Gen 4 permite el registro continuo y persistente de las matrices estocásticas y bitácoras paso a paso sin cuellos de botella de entrada/salida (I/O). En el Cuadro~\ref{tab:hardware_software} se desglosan formalmente las especificaciones de hardware y el ecosistema de software científico utilizado.

\begin{table}[H]
\centering
\small
\caption{Especificaciones detalladas de hardware, plataforma de cómputo y versiones de software científico.}\label{tab:hardware_software}
\begin{tabularx}{\textwidth}{lX}
\toprule
\textbf{Componente / Rubro} & \textbf{Especificación Técnica y Detalle Operativo} \\
\midrule
\textbf{Modelo de la PC} & Workstation Desktop personalizada sobre placa base ASUSTeK TUF GAMING X670E-PLUS WIFI (Arquitectura de procesamiento x86-64 / AMD64). \\
\addlinespace
\textbf{Sistema Operativo} & Microsoft Windows 11 Pro (64 bits), Versión 10.0.26200, Compilación 26200. Entorno de terminal PowerShell 7 / Windows Terminal. \\
\addlinespace
\textbf{Capacidad de Disco Duro} & Almacenamiento de estado sólido dual NVMe M.2 PCIe Gen 4 x4 con capacidad agregada de $1,397.27\text{ GB}$ ($\approx 1.5\text{ TB}$ nominales): \newline
$\bullet$ \textit{Unidad de Sistema C:}: Samsung SSD 980 PRO de $500\text{ GB}$ ($465.76\text{ GB}$ útiles, $87.23\text{ GB}$ libres). \newline
$\bullet$ \textit{Unidad de Trabajo D:}: Western Digital WD\_BLACK WDS100T3X0C-00SJG0 de $1\text{ TB}$ ($931.51\text{ GB}$ útiles, $414.41\text{ GB}$ disponibles para repositorios, modelos y datos). \\
\addlinespace
\textbf{Memoria RAM y Capacidad} & $32.00\text{ GB}$ totales ($31.26\text{ GB}$ efectivos reportados por SO) en configuración Dual-Channel ($2 \times 16\text{ GB}$ módulos Kingston Fury KF548C38-16 a una frecuencia de bus de $4,800\text{ MT/s}$, latencia base CL38). Ancho de banda de memoria pico $\approx 76.8\text{ GB/s}$. \\
\addlinespace
\textbf{Tipo de Procesador (CPU)} & AMD Ryzen 9 7900X 12-Core Processor (Microarquitectura Zen 4 de 5 nm, frecuencia base de $4.70\text{ GHz}$ con frecuencia turbo máxima de hasta $5.60\text{ GHz}$, $12\text{ MB}$ de caché L2 y $64\text{ MB}$ de caché L3 unificada). \\
\addlinespace
\textbf{Número de Núcleos / Hilos} & $12$ núcleos físicos de procesamiento y $24$ procesadores lógicos (hilos simultáneos mediante tecnología AMD Simultaneous Multithreading - SMT). \\
\addlinespace
\textbf{GPU Discreta de Apoyo} & NVIDIA GeForce RTX 3060 ($3,584$ núcleos CUDA, $112$ núcleos Tensor, $6.0\text{ GB}$ GDDR6 VRAM, bus de 192 bits a $360\text{ GB/s}$, Driver versión 32.0.16.1714, soporte CUDA 13.4). \\
\addlinespace
\textbf{Software y Librerías} & $\bullet$ \textbf{Python}: Versión \texttt{3.12.10} (entorno virtual aislado de 64 bits en partición \texttt{D:}). \newline
$\bullet$ \textbf{NumPy}: Versión \texttt{2.5.4} (aceleración SIMD AVX-512 activa para operaciones matriciales). \newline
$\bullet$ \textbf{SciPy}: Versión \texttt{1.18.1} (\texttt{spatial.cKDTree}, módulos estadísticos \texttt{stats.truncnorm} y solucionador \texttt{optimize.milp}). \newline
$\bullet$ \textbf{Pandas}: Versión \texttt{3.0.6} (procesamiento analítico de registros censales y bitácoras). \newline
$\bullet$ \textbf{Matplotlib}: Versión \texttt{3.11.2} (motor de renderizado para cartografía espacial a 300 DPI). \newline
$\bullet$ \textbf{HighsPy / HiGHS}: Versión \texttt{1.14.0} (solucionador MILP industrial Branch-and-Cut para cortes $K_3$). \newline
$\bullet$ \textbf{Gurobi Optimizer}: Versión \texttt{13.0.3} (verificación de optimalidad y certificación de brecha MIP). \newline
$\bullet$ \textbf{PyTorch}: Versión \texttt{2.6.0+cu124} (cómputo tensorial matricial en GPU). \newline
$\bullet$ \textbf{TeX Live 2026}: pdfTeX versión 3.141592653-2.6-1.40.29 (compilación automatizada de reportes). \\
\bottomrule
\end{tabularx}
\end{table}

\subsection{Justificación computacional del paralelismo y gestión de memoria}
La experimentación estocástica a gran escala involucra dos desafíos algorítmicos fundamentales:
\begin{enumerate}[leftmargin=1.5em]
    \item \textbf{Cómputo espacial intensivo de distancias y solapes:} En cada hectárea de $100\times 100\text{ m}$ con 740 cepas potenciales, la evaluación de los 4 canales biofísicos (agua, luz, alelopatía y facilitación nodriza) requiere identificar los pares de vecinos activos dentro del radio radicular ($R \le 4.8\text{ m}$). En lugar de una complejidad cuadrática ingenua $\mathcal{O}(|\mathcal{P}|^2)$ de $740^2 = 547,600$ evaluaciones por paso, la utilización de árboles $k$-d con soporte compacto reduce la complejidad a $\mathcal{O}(|\mathcal{P}| \log |\mathcal{P}|)$, identificando de forma inmediata los $2,115$ pares de aristas de interacción activa.
    \item \textbf{Paralelización de las 1,000 réplicas Monte Carlo:} Dado que cada corrida de simulación es independiente (distinto muestreo de plantas preexistentes $\boldsymbol{\nu}^{(s)}$ y distinta trayectoria estocástica de optimización), el problema califica como \textit{embarrassingly parallel}. Se distribuyeron lotes concurrentes en los 24 hilos lógicos de la CPU Ryzen 9 7900X mediante el módulo \texttt{multiprocessing}, completando las 1,000 optimizaciones espaciales completas de 1 hectárea en menos de 4 minutos sin degradación térmica.
\end{enumerate}

% ======================================
% SECCIÓN 2. TAMAÑO DEL PROBLEMA
% ======================================
\section{Tamaño del problema}

El tamaño del problema de optimización se analiza de forma rigurosa y exhaustiva a tres escalas complementarias: (i) la tesela operativa unitaria de $66$ nodos resuelta a optimalidad global, (ii) la hectárea estándar representativa ($100\times 100\text{ m}$, 740 nodos de red) y (iii) el predio regional consolidado correspondiente a los 31 polígonos oficiales delimitados para el Parque Eólico Dominica ($189.55\text{ ha}$ totales).

A continuación se desarrollan formalmente los cinco rubros dimensionales exigidos por la rúbrica del proyecto.

\subsection{Número de especies}
El modelo ecofisiológico y combinatorio considera una taxonomía de **26 entidades botánicas y funcionales**, organizadas en tres categorías operativas estrictas:
\begin{enumerate}[leftmargin=1.5em]
    \item \textbf{10 Especies Sembradas en Vivero ($|\mathcal{S}| = 10$):} Constituyen la prescripción oficial CONAFOR/INECOL para la restauración ecológica del matorral desértico micrófilo y rosetófilo en la Sierra de Álvarez:
    \begin{itemize}
        \item \textbf{Género \textit{Agave} (4 especies rosetófilas):} \textit{Agave lechuguilla} (\textbf{AL}), \textit{Agave striata} (\textbf{AT}), \textit{Agave scabra} (\textbf{AC}) y \textit{Agave salmiana} (\textbf{AS}). Aportan estabilidad superficial y anclaje edáfico frente al viento.
        \item \textbf{Género \textit{Opuntia} (4 cactáceas nopaleras):} \textit{Opuntia cantabrigiensis} (\textbf{OC}), \textit{Opuntia engelmannii} (\textbf{OE}), \textit{Opuntia robusta} (\textbf{OR}) y \textit{Opuntia streptacantha} (\textbf{OS}). Presentan metabolismo ácido de crasuláceas (CAM), alta eficiencia en uso de agua y arquitectura de cladodios de porte medio a alto.
        \item \textbf{Arbórea Leguminosa Nodriza (1 especie):} \textit{Prosopis laevigata} (\textbf{PL}, mezquite dulce). Especie clave fijadora de nitrógeno atmosférico mediante simbiosis con \textit{Rhizobium}, con raíz pivotante profunda ($> 1.0\text{ m}$) y facilitación de microclima bajo su dosel.
        \item \textbf{Arborescente Monocotiledónea (1 especie):} \textit{Yucca filifera} (\textbf{YF}, palma china). Especie estructural de dosel alto ($H = 6.0\text{ m}$) y baja demanda hídrica.
    \end{itemize}
    En la asignación espacial sobre cada nodo $p$, el espacio de estados incluye además el **estado vacío $\boldsymbol{\varnothing}$** ($\sigma_p \in \{0, 1, \dots, 10\}$), representando una cepa no plantada o preservada sin vegetación comercial.
    \item \textbf{6 Tipos de Flora Silvestre Existente:} Presentes en el terreno antes del acondicionamiento: 2 especies invasoras sujetas a erradicación obligatoria con costo (\textit{Pennisetum ciliare} o pasto buffel, y leñosa invasora) y 4 grupos de flora nativa de acompañamiento no comercial (arbusto nativo, árbol nativo, hierba nativa y *Larrea tridentata* o gobernadora).
    \item \textbf{10 Tipos de Cohorte Viva Preexistente:} Individuos de las 10 especies sembradas en programas anteriores (~6 años de edad, registrados in situ en el censo oficial de INECOL), los cuales son estrictamente **no removibles** y cuya posición espacial actúa como restricción fija de exclusión.
\end{enumerate}

En el Cuadro~\ref{tab:catalogo_taxonomico} se sintetiza el catálogo funcional y los costos unitarios oficiales sincronizados al 100\% con los tabuladores de CONAFOR e INECOL.

\begin{table}[H]
\centering
\footnotesize
\caption{Catálogo taxonómico, funcional y económico completo del sistema (26 entidades).}\label{tab:catalogo_taxonomico}
\begin{tabularx}{\textwidth}{ccllccr}
\toprule
\textbf{ID} & \textbf{Código} & \textbf{Nombre Científico / Tipo} & \textbf{Familia Botánica} & \textbf{Estrato} & \textbf{Condición} & \textbf{Costo Unit. (MXN)} \\
\midrule
0 & \textbf{AL} & \textit{Agave lechuguilla} (Lechuguilla) & Asparagaceae & Nivel 3 (Bajo) & A sembrar & \$26.00 (Adquisición) \\
1 & \textbf{AS} & \textit{Agave salmiana} (Maguey pulquero) & Asparagaceae & Nivel 2 (Medio) & A sembrar & \$26.00 (Adquisición) \\
2 & \textbf{AC} & \textit{Agave scabra} (Maguey áspero) & Asparagaceae & Nivel 2 (Medio) & A sembrar & \$26.00 (Adquisición) \\
3 & \textbf{AT} & \textit{Agave striata} (Espadín) & Asparagaceae & Nivel 3 (Bajo) & A sembrar & \$26.00 (Adquisición) \\
4 & \textbf{OC} & \textit{Opuntia cantabrigiensis} (Cuijo) & Cactaceae & Nivel 2 (Medio) & A sembrar & \$18.00 (Adquisición) \\
5 & \textbf{OE} & \textit{Opuntia engelmannii} (Nopal rastrero) & Cactaceae & Nivel 2 (Medio) & A sembrar & \$21.00 (Adquisición) \\
6 & \textbf{OR} & \textit{Opuntia robusta} (Nopal tapón) & Cactaceae & Nivel 2 (Medio) & A sembrar & \$18.00 (Adquisición) \\
7 & \textbf{OS} & \textit{Opuntia streptacantha} (Cardón) & Cactaceae & Nivel 1 (Alto) & A sembrar & \$18.00 (Adquisición) \\
8 & \textbf{PL} & \textit{Prosopis laevigata} (Mezquite) & Fabaceae & Nivel 1 (Nodriza) & A sembrar & \$26.50 (Adquisición) \\
9 & \textbf{YF} & \textit{Yucca filifera} (Palma china) & Asparagaceae & Nivel 1 (Alto) & A sembrar & \$26.00 (Adquisición) \\
\midrule
10 & \textbf{PC} & \textit{Pennisetum ciliare} (Pasto buffel) & Poaceae & Nivel 3 (Invasora) & Remoción oblig. & \$5.00 (Mano de obra) \\
11 & \textbf{LI} & Leñosa invasora & Fabaceae/Varios & Nivel 1 (Invasora) & Remoción oblig. & \$40.00 (Mano de obra) \\
12 & \textbf{AN} & Arbusto nativo silvestre & Varias & Nivel 2 (Nativa) & Conservar (95\%) & \$0.00 / \$15.00 (E1) \\
13 & \textbf{AR} & Árbol nativo silvestre & Varias & Nivel 1 (Nativa) & Conservar (95\%) & \$0.00 / \$40.00 (E1) \\
14 & \textbf{HN} & Hierba nativa silvestre & Poaceae/Asteraceae & Nivel 3 (Nativa) & Conservar (95\%) & \$0.00 / \$2.00 (E1) \\
15 & \textbf{LT} & \textit{Larrea tridentata} (Gobernadora) & Zygophyllaceae & Nivel 2 (Nativa) & Conservar (95\%) & \$0.00 / \$15.00 (E1) \\
\midrule
16--25 & \textbf{VIV} & Cohorte viva censada (10 especies) & Varias & Niveles 1, 2 y 3 & \textbf{Fija no removible} & In situ (Cohorte 6 años) \\
\bottomrule
\end{tabularx}
\end{table}

\subsection{Número de plantas por especie}
La meta biológica base estipulada por la Comisión Nacional Forestal (CONAFOR) y el Instituto de Ecología (INECOL) fija una cuota nominal de **658 plantas totales por hectárea** en terrenos de ladera suave o llanura (pendiente $< 20\%$). Para permitir la optimización combinatoria sobre el retículo hexagonal y absorber la incertidumbre microtopográfica del suelo, se introduce una banda de flexibilidad biológica admisible del $\boldsymbol{\varepsilon = \pm 10\%}$ sobre la cuota de cada especie:
\begin{equation}
c_i^- = \lceil (1 - \varepsilon)\alpha_i N \rceil \le n_i \le \lfloor (1 + \varepsilon)\alpha_i N \rfloor = c_i^+, \quad \forall i \in \mathcal{S}.
\end{equation}

En el Cuadro~\ref{tab:receta_oficial} se detallan las cuotas, las proporciones biológicas $\alpha_i$, los rangos admisibles y los costos unitarios oficiales para 1 hectárea ($N = 658\text{ pl/ha}$).

\begin{table}[H]
\centering
\small
\caption{Receta oficial CONAFOR/INECOL, proporciones objetivo y rangos de tolerancia ($\varepsilon = \pm 10\%$) para 1 ha.}\label{tab:receta_oficial}
\resizebox{\textwidth}{!}{%
\begin{tabular}{lccccccr}
\toprule
\textbf{Código} & \textbf{Especie} & \textbf{Cuota Oficial $\alpha_i N$} & $\boldsymbol{\alpha_i}$ \textbf{(\%)} & \textbf{Cota Inf. $c_i^-$} & \textbf{Cota Sup. $c_i^+$} & \textbf{Costo Unit. $k_i$} & \textbf{Subtotal Receta} \\
\midrule
\textbf{AL} & \textit{A. lechuguilla} & 42 & 6.38\% & 38 & 46 & \$26.00 & \$1,092.00 \\
\textbf{AT} & \textit{A. striata} & 42 & 6.38\% & 38 & 46 & \$26.00 & \$1,092.00 \\
\textbf{AC} & \textit{A. scabra} & 42 & 6.38\% & 38 & 46 & \$26.00 & \$1,092.00 \\
\textbf{AS} & \textit{A. salmiana} & 196 & 29.79\% & 177 & 215 & \$26.00 & \$5,096.00 \\
\textbf{OC} & \textit{O. cantabrigiensis} & 49 & 7.45\% & 45 & 53 & \$18.00 & \$882.00 \\
\textbf{OE} & \textit{O. engelmannii} & 38 & 5.78\% & 35 & 41 & \$21.00 & \$798.00 \\
\textbf{OR} & \textit{O. robusta} & 73 & 11.09\% & 66 & 80 & \$18.00 & \$1,314.00 \\
\textbf{OS} & \textit{O. streptacantha} & 64 & 9.73\% & 58 & 70 & \$18.00 & \$1,152.00 \\
\textbf{PL} & \textit{P. laevigata} & 86 & 13.07\% & 78 & 94 & \$26.50 & \$2,279.00 \\
\textbf{YF} & \textit{Y. filifera} & 26 & 3.95\% & 24 & 28 & \$26.00 & \$676.00 \\
\midrule
\textbf{TOTAL} & \textbf{Receta Completa} & \textbf{658} & \textbf{100.00\%} & \textbf{597} & \textbf{719} & \textbf{\$23.52 (medio)} & \textbf{\$15,473.00} \\
\bottomrule
\end{tabular}%
}
\end{table}

\textbf{Propiedad analítica de factibilidad entera:} Nótese que la suma de las cotas inferiores es $\sum_{i=1}^{10} c_i^- = 597 < 658$ y la suma de las superiores es $\sum_{i=1}^{10} c_i^+ = 719 > 658$. Esto demuestra rigurosamente que el poliedro de restricciones enteras contiene un símplex no vacío con múltiples soluciones factibles.

A nivel regional, la agregación sobre los 31 polígonos oficiales ($189.55\text{ ha}$) y la confrontación con el censo in situ de plantas vivas de la cohorte histórica (~6 años de edad) determina las cantidades reales que deben adquirirse en vivero (Cuadro~\ref{tab:escalamiento_regional}).

\begin{table}[H]
\centering
\small
\caption{Consolidación regional de plantas en los 31 polígonos oficiales ($189.55\text{ ha}$).}\label{tab:escalamiento_regional}
\resizebox{\textwidth}{!}{%
\begin{tabular}{lcccccr}
\toprule
\textbf{Código} & \textbf{Especie} & \textbf{Vivas Censadas} & \textbf{A Sembrar (Vivero)} & \textbf{Población Total} & \textbf{Superv. Cohorte} & \textbf{Inversión Compra} \\
\midrule
\textbf{AL} & \textit{A. lechuguilla} & 1,491 & 7,239 & 8,730 & 17.1\% & \$188,214.00 \\
\textbf{AT} & \textit{A. striata} & 1,404 & 7,321 & 8,725 & 16.1\% & \$190,346.00 \\
\textbf{AC} & \textit{A. scabra} & 1,462 & 7,268 & 8,730 & 16.7\% & \$188,968.00 \\
\textbf{AS} & \textit{A. salmiana} & 6,956 & 30,818 & 37,774 & 18.4\% & \$801,268.00 \\
\textbf{OC} & \textit{O. cantabrigiensis} & 1,832 & 8,352 & 10,184 & 18.0\% & \$150,336.00 \\
\textbf{OE} & \textit{O. engelmannii} & 1,459 & 6,433 & 7,892 & 18.5\% & \$135,093.00 \\
\textbf{OR} & \textit{O. robusta} & 2,746 & 9,704 & 12,450 & 22.1\% & \$174,672.00 \\
\textbf{OS} & \textit{O. streptacantha} & 2,289 & 8,628 & 10,917 & 21.0\% & \$155,304.00 \\
\textbf{PL} & \textit{P. laevigata} & 3,018 & 11,647 & 14,665 & 20.6\% & \$308,645.50 \\
\textbf{YF} & \textit{Y. filifera} & 912 & 3,534 & 4,446 & 20.5\% & \$91,884.00 \\
\midrule
\textbf{TOTAL} & \textbf{31 Polígonos} & \textbf{23,569} & \textbf{100,944} & \textbf{124,513} & \textbf{18.93\%} & \textbf{\$2,384,730.50} \\
\bottomrule
\end{tabular}%
}
\end{table}

\textbf{Tratamiento del Polígono 29:} El Polígono 29 posee un área digitalizada oficial de $6.54\text{ ha}$. Debido a la ausencia de registro en la base de censos históricos de INECOL, el modelo computacional lo incorpora formalmente con su geometría plena y le asigna $0$ plantas preexistentes, requiriendo el suministro total del 100\% de su cuota ($4,078$ a $4,303$ plantas según su gradiente topográfico).

\subsection{Cantidad de plantas en una hectárea}
La densidad de plantación por hectárea se rige por el gradiente de inclinación topográfica estipulado en las normas técnicas de restauración forestal de CONAFOR:
\begin{equation}
N_z = \begin{cases}
\lfloor 658 \cdot A_z \rfloor & \text{si } \text{Pendiente } < 20\% \quad (\text{Zona plana / lomerío suave}), \\
\lceil 524 \cdot A_z \rceil & \text{si } \text{Pendiente } \ge 20\% \quad (\text{Zona escarpada / ladera anti-erosión}).
\end{cases}
\end{equation}

\begin{itemize}[leftmargin=1.5em]
    \item \textbf{En zona de pendiente suave ($< 20\%$):} Densidad meta de **$658\text{ plantas/ha}$**. En una hectárea estándar con relieve medio de $6^\circ$ (como la ensayada en las 1,000 corridas), el censo empírico determina un promedio de vegetación objetivo preexistente de $\mathbb{E}[\nu] = 129.27\text{ pl/ha}$, lo que exige suministrar en vivero una cantidad media de:
    \begin{equation}
    \mathbb{E}[N_{\text{sembrar}}] = 658 - 129.27 = \mathbf{528.73\text{ pl/ha}}.
    \end{equation}
    Estas plantas se disponen sobre una malla hexagonal en tresbolillo con espaciado nominal de $a = 4.0\text{ m}$ ($740$ nodos totales utilizables en el recuadro de $100\times 100\text{ m}$, de los cuales exactamente $247$ pertenecen a la Submalla 3 con $(i-j)\equiv 0\pmod 3$).
    \item \textbf{En zona de ladera pronunciada ($\ge 20\%$):} La densidad se reduce en un $20\%$ a **$524\text{ plantas/ha}$** para evitar la desestabilización del suelo y maximizar la retención de agua de escorrentía. Con $\mathbb{E}[\nu] = 129.27\text{ pl/ha}$, el suministro requerido desciende a $\mathbf{394.82\text{ pl/ha}}$. El espaciado de la retícula triangular se dilata analíticamente en un factor:
    \begin{equation}
    \frac{a_{\text{pendiente}}}{a_{\text{plana}}} = \sqrt{\frac{658}{524}} \approx 1.1213 \quad (+12.13\%),
    \end{equation}
    pasando de $a = 4.00\text{ m}$ a $a \approx 4.70\text{ m}$.
    \item \textbf{Dinámica de la flora silvestre preexistente:} El predio virgen alberga en promedio $\sim 860\text{ ind/ha}$ de vegetación espontánea. Tras la fase previa de desmonte selectivo, se erradica el $85\%$ de las invasoras ($250 \to 37.5\text{ ind/ha}$) y se conserva el $95\%$ de las nativas silvestres acompañantes ($610 \to 579.5\text{ ind/ha}$).
\end{itemize}

En el Cuadro~\ref{tab:sensibilidad_topografica} se expone el análisis de sensibilidad topográfica regional en función de la pendiente media simulada.

\begin{table}[H]
\centering
\small
\caption{Sensibilidad topográfica de plantas y costo total en los 31 polígonos ($189.55\text{ ha}$).}\label{tab:sensibilidad_topografica}
\resizebox{\textwidth}{!}{%
\begin{tabular}{lccccccr}
\toprule
\textbf{Escenario de Relieve} & \textbf{Pendiente} & \textbf{Área $\ge 20\%$} & \textbf{Frac. $\ge 20\%$} & \textbf{Meta $N$} & \textbf{Vivas} & \textbf{A Sembrar} & \textbf{Inversión (MXN)} \\
\midrule
Teórico 100\% Plano & $0.0^\circ$ & $0.00\text{ ha}$ & 0.0\% & 124,724 & 23,569 & 101,155 & \$2,389,678 \\
\textbf{Calibrado Oficial} & $\mathbf{6.0^\circ}$ & $\mathbf{1.50\text{ ha}}$ & \textbf{0.8\%} & \textbf{124,513} & \textbf{23,569} & \textbf{100,944} & \textbf{\$2,384,700} \\
Lomerío Moderado & $10.0^\circ$ & $61.10\text{ ha}$ & 32.2\% & 116,595 & 23,569 & 93,026 & \$2,197,344 \\
Lomerío Pronunciado & $12.0^\circ$ & $93.80\text{ ha}$ & 49.5\% & 112,100 & 23,569 & 88,531 & \$2,091,102 \\
Teórico 100\% Ladera & $> 20.0^\circ$ & $189.55\text{ ha}$ & 100.0\% & 99,324 & 23,569 & 75,755 & \$1,789,310 \\
\bottomrule
\end{tabular}%
}
\end{table}

\subsection{Número de variables consideradas}
El recuento dimensional de variables de decisión se desagrega según las dos formulaciones matemáticas desarrolladas:

\subsubsection{Formulación no lineal continua / heurística (\texttt{modelo\_dominica})}
En la simulación sobre 1 hectárea completa ($100\times 100\text{ m}$, $|\mathcal{P}| = 740$ nodos):
\begin{itemize}[leftmargin=1.5em]
    \item \textbf{Variables de asignación nodal:} $740$ variables enteras $\sigma_p \in \{0, 1, \dots, 10\}$ (o $7,400$ variables binarias equivalentes $x_{ip} \in \{0, 1\}$).
    \item \textbf{Restricción de Submalla 3:} Las 3 especies de gran porte (\textbf{OS, PL, YF}) solo pueden situarse en nodos con $(u_p - v_p) \equiv 0 \pmod 3$. Esto reduce las variables binarias admisibles de $7,400$ a $7 \cdot 740 + 3 \cdot 247 = \mathbf{5,921}$ variables binarias efectivas.
    \item \textbf{Variables de suministro de vivero:} $10$ variables enteras $s_i \in \mathbb{Z}_+$ ($i=1,\dots,10$).
    \item \textbf{Variables estocásticas de cohorte preexistente:} $10$ variables aleatorias discretas $\nu_i$.
    \item \textbf{Pares de interacción espacial activa:} $2,115$ pares de aristas en el primer anillo de vecindad ($R \le 4.8\text{ m}$), que se expanden a $5,642$ pares en el radio radicular extendido ($R \le 7.5\text{ m}$).
\end{itemize}

\subsubsection{Formulación exacta MILP linealizada RLT-1 con cortes $K_3$ (\texttt{REFORESTATHON})}
Para linealizar el producto cuadrático de asignación de especies $x_{ip}x_{jq}$ en cada arista $e=(p,q) \in \mathcal{E}$, se introduce la Reformulación-Linealización RLT-1 mediante variables continuas de arista $z_{ijpq} \in [0, 1]$ acopladas con cortes de clique triangular $K_3$:
\begin{itemize}[leftmargin=1.5em]
    \item \textbf{Hectárea completa monolítica ($|\mathcal{P}|=740$, $|\mathcal{E}|=2,115$, $|\mathcal{T}|=1,316$):}
    \begin{itemize}
        \item Variables binarias de asignación: $10 \times 740 = 7,400$.
        \item Variables continuas RLT-1: $10 \times 10 \times 2,115 = 211,500$.
        \item Variables enteras de adquisición: $10$.
        \item \textbf{Total de variables de decisión:} $\mathbf{218,910}$ variables ($7,400$ enteras binarias, $211,510$ continuas).
        \item \textbf{Total de restricciones lineales:} $\mathbf{642,356}$ desigualdades lineales ($740$ de unicidad nodal, $1,479$ de exclusión Submalla 3, $20$ de cuotas y presupuesto, $634,500$ desigualdades de McCormick/RLT-1 y $5,617$ cortes de clique triangular $K_3$).
    \end{itemize}
    \item \textbf{Tesela operativa unitaria 2D ($6\times 11$, $|\mathcal{P}|=66$ nodos, $|\mathcal{E}|=165$ aristas, $|\mathcal{T}|=96$ triángulos):}
    \begin{itemize}
        \item Variables binarias: $10 \times 66 = 660$.
        \item Variables continuas RLT-1: $10 \times 10 \times 165 = 16,500$.
        \item Variables de compra: $10$.
        \item \textbf{Total de variables en el solver:} $\mathbf{17,170}$ variables.
        \item \textbf{Total de restricciones:} $\mathbf{50,026}$ restricciones lineales, resueltas a optimalidad global certificada ($\text{gap} = 0.00\%$) en $3.2\text{ s}$ en HiGHS / Gurobi.
    \end{itemize}
\end{itemize}

En el Cuadro~\ref{tab:comparativa_dimensional} se presenta el contraste dimensional formal entre formulaciones.

\begin{table}[H]
\centering
\small
\caption{Comparativa dimensional formal de variables y restricciones entre formulaciones.}\label{tab:comparativa_dimensional}
\begin{tabularx}{\textwidth}{lXXX}
\toprule
\textbf{Métrica Dimensional} & \textbf{Tesela MILP 2D ($6\times 11$)} & \textbf{1 Hectárea Monolítica} & \textbf{31 Polígonos ($189.55\text{ ha}$)} \\
\midrule
Nodos de red ($|\mathcal{P}|$) & 66 cepas & 740 cepas & 100,944 cepas \\
Aristas de vecindad ($|\mathcal{E}|$) & 165 pares ($R \le 4.8\text{ m}$) & 2,115 pares & 288,520 pares \\
Triángulos clique ($|\mathcal{T}_3|$) & 96 triángulos & 1,316 triángulos & 182,400 triángulos \\
Variables binarias ($x_{ip}$) & 660 & 7,400 ($5,921$ con Submalla) & 807,552 con Submalla \\
Variables continuas ($z_e$) & 16,500 & 211,500 & Descomposición teselas \\
Variables de compra ($s_i$) & 10 & 10 & 310 \\
\textbf{Total Variables} & \textbf{17,170} & \textbf{218,910} & \textbf{> 1.1 millones (global)} \\
\textbf{Total Restricciones} & \textbf{50,026} & \textbf{642,356} & Descomposición paralela \\
Tiempo de Resolución & $3.2\text{ s}$ ($\text{gap}=0.00\%$) & Requiere descomposición & Enmallado red-black (4 min) \\
\bottomrule
\end{tabularx}
\end{table}

\subsection{Número de parámetros}
El sistema consolidado está gobernado exactamente por **463 parámetros biofísicos, edafológicos, microclimáticos y algorítmicos** en una hectárea (y $556$ al incorporar las tablas topográficas de los 31 polígonos). En el Cuadro~\ref{tab:desglose_parametros} se expone el inventario exhaustivo estructurado por módulo y su clasificación epistemológica.

\begin{table}[H]
\centering
\small
\caption{Inventario y desglose estructurado de los 463 parámetros del modelo de optimización.}\label{tab:desglose_parametros}
\begin{tabularx}{\textwidth}{llcX}
\toprule
\textbf{Módulo} & \textbf{Estructura} & \textbf{Dimensión} & \textbf{Parámetros y Descripción Epistemológica} \\
\midrule
\textbf{Alometría} & \texttt{PLANTED} & 130 & 10 especies $\times$ 13 atributos biológicos (altura adulta, radio de copa, factor radicular, tasa de consumo hídrico, profundidad radical, sensibilidades a sequía y sombra, rasgo nodriza, nivel dosel y costo $k_i$). \\
\textbf{Talla Vivero} & \texttt{F0\_PLANT} & 10 & Fracción de talla inicial al plantar ($f_{0,i} = \text{talla} / H_{\text{adulta}}$) basada en datos INECOL. \\
\textbf{Nicho Ecológico} & \texttt{NICHE} & 40 & 10 especies $\times$ 4 requerimientos (suelo mínimo en cm, tolerancia a pendiente, resistencia a heladas y pastoreo). \\
\textbf{Vegetación Previa} & \texttt{EXISTING} & 176 & 16 entidades silvestres $\times$ 11 atributos numéricos y booleanos (densidad basal, radio de exclusión, costo de remoción). \\
\textbf{Unidades Edafológicas} & \texttt{DENS} & 24 & Densidades basales de vegetación silvestre en 4 unidades de vegetación. \\
\textbf{Topoclima} & \texttt{TerrainSpec} & 28 & Dimensiones de celda, elevación SRTM, radiación Hargreaves-Samani FAO-56 ($k_{\text{rs}}=0.16$), lluvia (420 mm), temperatura ($16^\circ\text{C}$). \\
\textbf{Motor Multicanal} & \texttt{Config} & 29 & Alcance radicular ($R=14\text{ m}$ máx), pesos de aptitud ($w_W=0.60, w_L=0.25, w_A=0.15$), factor nodriza ($\beta=3.0$), penalización sombra. \\
\textbf{Precios Vivero} & $k_i$ Oficiales & 10 & Vector de costos CONAFOR (\$26.0, \$26.0, \$26.0, \$26.0, \$18.0, \$21.0, \$18.0, \$18.0, \$26.5, \$26.0 MXN). \\
\textbf{Recocido Simulado} & Hiperparámetros & 14 & Temperaturas ($T_0=0.35, T_f=0.01$), 3 fases de enfriamiento geométrico, probabilidades de mutación ($45\%$ permuta, $30\%$ reubicación, $25\%$ reemplazo). \\
\textbf{Solver Exacto MILP} & Hiperparámetros & 12 & Margen de brecha $\text{MIPGap} \le 0.05$, cortes de clique triangular $K_3$, 24 hilos CPU, warm-start GPU. \\
\textbf{Estocásticos} & $\text{TruncNorm}$ & 10 & Parámetros empíricos de vegetación preexistente ($\mu_\nu = 129.18, \sigma_\nu = 3.35$). \\
\midrule
\multicolumn{2}{l}{\textbf{TOTAL PARÁMETROS}} & \textbf{463} & \textbf{Inventario total auditable de parámetros del sistema} \\
\bottomrule
\end{tabularx}
\end{table}

\textbf{Distribución epistemológica del conocimiento:} Del total de 463 parámetros:
\begin{itemize}[leftmargin=1.5em]
    \item \textbf{DATO EMPÍRICO (18.6\%):} Precios oficiales CONAFOR, tallas vivero INECOL, censos de 30 polígonos, elevación SRTM.
    \item \textbf{ESTÁNDAR CIENTÍFICO (8.2\%):} Evapotranspiración FAO-56, función de saturación de Hill, gradiente adiabático.
    \item \textbf{DERIVADO ANALÍTICO (11.4\%):} Proporciones $\alpha_i$, bandas enteras $[c_i^-, c_i^+]$, espaciado de malla $a$.
    \item \textbf{HEURÍSTICO CALIBRADO (34.8\%):} Esquemas de enfriamiento de recocido, submallas, partición RLT-1.
    \item \textbf{PLACEHOLDER DE LITERATURA (27.0\%):} Coeficientes finos de alelopatía y competencia radicular en matorral xerófilo.
\end{itemize}

% ====================================================================
% SECCIÓN 3. EXPERIMENTACIÓN Y REPORTE DE LAS 1,000 SIMULACIONES
% ====================================================================
\section{Experimentación y reporte de las 1,000 simulaciones del proceso de siembra}

\subsection{Diseño experimental y validación MILP con precios oficiales}
El protocolo experimental ejecutó $M = 1,000$ réplicas estocásticas independientes sobre un terreno representativo de 1 hectárea ($100\times 100\text{ m}$, inclinación media de $6^\circ$, suelo franco-arenoso pedregoso con radiación semidesértica). En cada réplica $s \in \{1, \dots, 1,000\}$:
\begin{enumerate}[leftmargin=1.5em]
    \item Se muestreó el número y posición de plantas preexistentes $\boldsymbol{\nu}^{(s)}$ siguiendo la distribución empírica normal truncada ajustada a partir de los 30 polígonos censados por INECOL ($\mu_\nu = 129.18, \sigma_\nu = 3.35$).
    \item Se calculó el vector de demanda neta de plantas a adquirir en vivero $\mathbf{s}^{(s)} = \max(0, \mathbf{c} - \boldsymbol{\nu}^{(s)})$ bajo las dos modalidades de suministro (estricto $\varepsilon=0$ y optimizado $\varepsilon=0.10$).
    \item Se generó una configuración inicial aleatoria factible sobre los nodos libres de la malla hexagonal respetando la exclusión de especies grandes fuera de la Submalla 3.
    \item Se optimizó la distribución espacial mediante Recocido Simulado guiado por la función de aptitud biológica multicanal.
\end{enumerate}

\textbf{Validación previa en bancos de prueba MILP con precios oficiales:}
\begin{itemize}[leftmargin=1.5em]
    \item \textit{Fila 1D (26 nodos, $100\text{ m}$):} El modelo exacto MILP resolvió a optimalidad global reduciendo la interferencia neta por pares en un **$-84.2\%$** (de $2.625$ a $0.414$). La solución generó de forma espontánea el patrón periódico óptimo de alternancia:
    \begin{equation}
    \texttt{PL} \longrightarrow \texttt{AS} \longrightarrow \texttt{OC} \longrightarrow \texttt{AS} \longrightarrow \texttt{OR} \longrightarrow \texttt{AS} \longrightarrow \texttt{AL} \dots
    \end{equation}
    donde el mezquite (\textbf{PL}) actúa como nodo nodriza central flanqueado por agaves y opuntias de porte medio.
    \item \textit{Tesela 2D ($6\times 11$, 66 nodos, 165 aristas):} La formulación MILP RLT-1 con cortes de clique triangular $K_3$ abatió la interferencia neta en un **$-95.5\%$** (de $18.21$ a $0.812$). La adición de los cortes válidos $K_3$ redujo los nodos explorados en el árbol de Branch-and-Cut en un **$60.7\%$** ($1,420 \to 558$ nodos), acelerando el tiempo de convergencia a $3.2\text{ s}$ con brecha MIP certificada de $0.00\%$.
\end{itemize}

\subsection{Valor esperado del total de plantas existentes en una hectárea}
A partir de las 1,000 réplicas Monte Carlo, el valor esperado de plantas preexistentes pertenecientes a las 10 especies objetivo es:
\begin{equation}
\mathbb{E}[\nu] = 129.27 \pm 3.53\text{ pl/ha}, \quad \text{Error Estándar } EE = 0.112\text{ pl/ha}, \quad \text{IC}_{95\%} = [122.00, 136.00]\text{ pl/ha},
\end{equation}
con una mediana de $129.00\text{ pl/ha}$ y un rango muestral observado de $[118, 139]\text{ pl/ha}$.

Al completar la siembra de material nuevo de vivero, el total de plantas vivas en campo alcanza estrictamente la meta oficial:
\begin{itemize}[leftmargin=1.5em]
    \item En terrenos con pendiente $< 20\%$: **$658.00\text{ plantas/ha}$** ($\mathbb{E}[\nu] = 129.27$ preexistentes $+ \mathbb{E}[N_{\text{sembrar}}] = 528.73$ nuevas).
    \item En parches con pendiente $\ge 20\%$: **$524.00\text{ plantas/ha}$** ($\mathbb{E}[\nu] = 129.27$ preexistentes $+ \mathbb{E}[N_{\text{sembrar}}] = 394.82$ nuevas).
\end{itemize}
Adicionalmente, tras el desmonte selectivo del predio se preserva una población media de **$579.5\text{ nativas silvestres/ha}$** y un residuo controlado de **$37.5\text{ invasoras/ha}$**.

\subsection{Valor esperado de plantas por especie existentes en una hectárea}
En el Cuadro~\ref{tab:existentes_especie} se desglosan las existencias esperadas por especie $\mathbb{E}[\nu_i]$ junto con sus estadísticos de dispersión e intervalos de confianza del 95\%.

\begin{table}[H]
\centering
\small
\caption{Valor esperado de plantas existentes por especie en 1 ha ($M = 1,000$ simulaciones estocásticas).}\label{tab:existentes_especie}
\resizebox{\textwidth}{!}{%
\begin{tabular}{llccccccr}
\toprule
\textbf{Código} & \textbf{Nombre Científico} & $\boldsymbol{\mathbb{E}[\nu_i]}$ & \textbf{Desv. Est. $\sigma$} & \textbf{Error Est. $EE$} & $\textbf{IC}_{95\%}$ & \textbf{Mediana} & \textbf{Rango} & \textbf{Prop. (\%)} \\
\midrule
\textbf{AL} & \textit{A. lechuguilla} & 8.04 & 1.45 & 0.046 & [5.0, 11.0] & 8 & [4, 13] & 6.22\% \\
\textbf{AT} & \textit{A. striata} & 7.79 & 1.40 & 0.044 & [5.0, 10.0] & 8 & [4, 13] & 6.03\% \\
\textbf{AC} & \textit{A. scabra} & 8.23 & 1.50 & 0.047 & [5.0, 11.0] & 8 & [3, 13] & 6.37\% \\
\textbf{AS} & \textit{A. salmiana} & 38.21 & 2.34 & 0.074 & [34.0, 43.0] & 38 & [30, 46] & 29.56\% \\
\textbf{OC} & \textit{O. cantabrigiensis} & 9.98 & 1.48 & 0.047 & [7.0, 13.0] & 10 & [6, 14] & 7.72\% \\
\textbf{OE} & \textit{O. engelmannii} & 8.18 & 1.38 & 0.044 & [5.0, 11.0] & 8 & [4, 12] & 6.33\% \\
\textbf{OR} & \textit{O. robusta} & 14.87 & 1.35 & 0.043 & [12.0, 17.0] & 15 & [11, 19] & 11.50\% \\
\textbf{OS} & \textit{O. streptacantha} & 12.31 & 1.91 & 0.060 & [9.0, 16.0] & 12 & [6, 18] & 9.52\% \\
\textbf{PL} & \textit{P. laevigata} & 16.60 & 2.50 & 0.079 & [12.0, 21.0] & 17 & [7, 24] & 12.84\% \\
\textbf{YF} & \textit{Y. filifera} & 5.06 & 1.02 & 0.032 & [3.0, 7.0] & 5 & [2, 8] & 3.91\% \\
\midrule
\textbf{TOTAL} & \textbf{Consolidado 10 Especies} & \textbf{129.27} & \textbf{3.53} & \textbf{0.112} & \textbf{[122.0, 136.0]} & \textbf{129} & \textbf{[118, 138]} & \textbf{100.00\%} \\
\bottomrule
\end{tabular}%
}
\end{table}

\subsection{Valor esperado de plantas por especie a suministrar y presupuesto oficial}
Para alcanzar la densidad meta de $658\text{ pl/ha}$, se contrastan dos modalidades operativas de adquisición en vivero:
\begin{enumerate}[leftmargin=1.5em]
    \item \textbf{Suministro Estricto ($\boldsymbol{\varepsilon = 0}$):} Compra exactamente la diferencia rígida $s_i^{\text{estricto}} = c_i - \nu_i$. Requiere en promedio $\mathbf{528.73 \pm 3.53\text{ pl/ha}}$ con un costo esperado de compra de $\mathbf{\$12,519.04\text{ MXN/ha}}$.
    \item \textbf{Suministro Optimizado con Tolerancia ($\boldsymbol{\varepsilon = \pm 10\%}$):} Ajusta dinámicamente las cantidades adquiridas dentro de la banda $[c_i^-, c_i^+]$ para favorecer especies de menor costo unitario y menor interferencia competitiva.
\end{enumerate}

En el Cuadro~\ref{tab:suministro_y_costos} se comparan ambas modalidades junto con los costos unitarios oficiales y el costo con fondo de contingencia del $5\%$ para reposición de mortandad temprana.

\begin{table}[H]
\centering
\small
\caption{Valor esperado de plantas a suministrar en vivero y presupuesto oficial por especie en 1 ha.}\label{tab:suministro_y_costos}
\resizebox{\textwidth}{!}{%
\begin{tabular}{lccccccr}
\toprule
\textbf{Código} & \textbf{Precio $k_i$} & \textbf{Estricto ($\varepsilon=0$)} & \textbf{Optimizado ($\varepsilon=0.1$)} & $\textbf{IC}_{95\%}$ \textbf{Opt.} & \textbf{Costo Opt. (MXN)} & \textbf{Costo + 5\% Fondo} \\
\midrule
\textbf{AL} & \$26.00 & $33.95 \pm 1.45$ & $37.88 \pm 1.47$ & [35.0, 41.0] & \$984.88 $\pm$ 38.10 & \$1,034.12 $\pm$ 40.01 \\
\textbf{AT} & \$26.00 & $34.21 \pm 1.40$ & $38.14 \pm 1.43$ & [35.0, 41.0] & \$991.61 $\pm$ 37.15 & \$1,041.19 $\pm$ 39.01 \\
\textbf{AC} & \$26.00 & $33.77 \pm 1.50$ & $37.70 \pm 1.53$ & [35.0, 41.0] & \$980.10 $\pm$ 39.65 & \$1,029.10 $\pm$ 41.64 \\
\textbf{AS} & \$26.00 & $157.79 \pm 2.34$ & $161.41 \pm 2.69$ & [156.0, 166.0] & \$4,196.56 $\pm$ 70.04 & \$4,406.38 $\pm$ 73.54 \\
\textbf{OC} & \$18.00 & $39.02 \pm 1.48$ & $42.94 \pm 1.51$ & [40.0, 46.0] & \$772.83 $\pm$ 27.10 & \$811.47 $\pm$ 28.46 \\
\textbf{OE} & \$21.00 & $29.82 \pm 1.38$ & $32.78 \pm 1.39$ & [30.0, 36.0] & \$688.44 $\pm$ 29.25 & \$722.87 $\pm$ 30.71 \\
\textbf{OR} & \$18.00 & $58.13 \pm 1.35$ & $51.13 \pm 1.35$ & [49.0, 54.0] & \$920.36 $\pm$ 24.31 & \$966.38 $\pm$ 25.52 \\
\textbf{OS} & \$18.00 & $51.69 \pm 1.91$ & $46.16 \pm 2.10$ & [42.0, 50.0] & \$830.92 $\pm$ 37.88 & \$872.46 $\pm$ 39.77 \\
\textbf{PL} & \$26.50 & $69.40 \pm 2.50$ & $61.43 \pm 2.50$ & [57.0, 66.0] & \$1,627.97 $\pm$ 66.26 & \$1,709.37 $\pm$ 69.57 \\
\textbf{YF} & \$26.00 & $20.94 \pm 1.02$ & $19.16 \pm 1.14$ & [17.0, 22.0] & \$498.19 $\pm$ 29.56 & \$523.10 $\pm$ 31.04 \\
\midrule
\textbf{TOTAL} & \textbf{CONAFOR} & $\mathbf{528.73 \pm 3.53}$ & $\mathbf{528.73 \pm 3.53}$ & $\mathbf{[522.0, 536.0]}$ & $\mathbf{\$12,491.85 \pm 92.96}$ & $\mathbf{\$13,116.45 \pm 97.61}$ \\
\bottomrule
\end{tabular}%
}
\end{table}

\textbf{Análisis financiero:} El régimen optimizado bajo $\varepsilon = 0.10$ alcanza un gasto medio de compra de vivero de **$\$12,491.85 \pm 92.96\text{ MXN/ha}$**, generando un ahorro neto frente al régimen estricto (\$12,519.04 MXN), al tiempo que reduce la densidad de especies de gran porte (\textbf{PL, OS, YF}) para mitigar la competencia entre copas adultas. Con el fondo de contingencia del $5\%$, el presupuesto recomendado asciende a **$\$13,116.45\text{ MXN/ha}$**.

\begin{figure}[H]
\centering
\includegraphics[width=0.96\textwidth]{entregable3_outputs/figuras/fig1_existentes_y_suministro_1000sim.png}
\caption{Distribución estadística de plantas existentes censadas $\nu_i$, demanda de suministro de vivero $s_i$ y presupuesto oficial CONAFOR/INECOL a lo largo de las 1,000 simulaciones Monte Carlo en 1 hectárea.}\label{fig:fig1_existentes_suministro}
\end{figure}

\textbf{Interpretación de la Figura~\ref{fig:fig1_existentes_suministro}:} El panel superior ilustra la estabilidad de las plantas existentes por especie en torno a sus medias censales, destacando \textit{Agave salmiana} (\textbf{AS}) con la mayor presencia preexistente ($38.2\text{ pl/ha}$). El panel inferior refleja la distribución presupuestal, donde \textbf{AS} absorbe el $33.6\%$ de la inversión (\$4,196.56 MXN) por su alta cuota de receta, seguido del mezquite \textbf{PL} (\$1,627.97 MXN). La banda estrecha de variación (desviación de solo $\$92.96\text{ MXN}$) certifica la predictibilidad financiera del proyecto.

\subsection{Valor esperado de competencia existente en una hectárea}
Para cuantificar el impacto de la optimización combinatoria frente a una siembra aleatoria convencional sobre la malla de 1 hectárea, se calcularon las métricas ecofisiológicas pareadas sobre las 1,000 réplicas. Los resultados y sus respectivas pruebas de hipótesis $t$ de Student pareadas se presentan en el Cuadro~\ref{tab:competencia_supervivencia}.

\begin{table}[H]
\centering
\small
\caption{Contraste estadístico de competencia, aptitud biológica y supervivencia esperada (1,000 simulaciones).}\label{tab:competencia_supervivencia}
\resizebox{\textwidth}{!}{%
\begin{tabular}{lccccrc}
\toprule
\textbf{Métrica Ecológica} & \textbf{Siembra Aleatoria} & \textbf{Optimizado Recocido} & $\boldsymbol{\Delta}$ \textbf{Absoluto} & \textbf{Cambio (\%)} & \textbf{Estadístico $t$} & \textbf{Significancia} \\
\midrule
Aptitud Media ($\bar{F}$) & $0.5429 \pm 0.0031$ & $0.5688 \pm 0.0027$ & $+0.0259$ & $+4.76\%$ & $t = +306.7$ & $p < 0.001$ (***) \\
Aptitud Aislada ($\bar{F}_{\text{aislada}}$) & $0.5938 \pm 0.0030$ & $0.5938 \pm 0.0030$ & $0.0000$ & $0.00\%$ & — & n.s. \\
Pérdida Competencia (\%) & $8.57\% \pm 0.26\%$ & $4.22\% \pm 0.45\%$ & $-4.36\%$ & $-50.80\%$ & $t = -299.6$ & $p < 0.001$ (***) \\
Sobrevivientes ($\Phi$, plantas) & $487.85 \pm 4.20$ & $509.44 \pm 3.69$ & $\mathbf{+21.59}$ & $\mathbf{+4.42\%}$ & $t = +325.5$ & $p < 0.001$ (***) \\
Mortalidad Proxy (\%) & $7.73\% \pm 0.43\%$ & $3.65\% \pm 0.18\%$ & $-4.08\%$ & $-52.81\%$ & $t = -325.0$ & $p < 0.001$ (***) \\
Presión Hídrica ($\bar{H}^W$) & $0.1789 \pm 0.0052$ & $0.1532 \pm 0.0047$ & $-0.0257$ & $-14.34\%$ & $t = -145.4$ & $p < 0.001$ (***) \\
Presión Lumínica ($\bar{H}^L$) & $0.0389 \pm 0.0027$ & $0.0343 \pm 0.0027$ & $-0.0046$ & $-11.79\%$ & $t = -50.1$ & $p < 0.001$ (***) \\
Facilitación Nodriza ($\bar{H}^B$) & $0.0169 \pm 0.0031$ & $0.0158 \pm 0.0030$ & $-0.0011$ & $-6.35\%$ & $t = -16.4$ & $p < 0.001$ (***) \\
Presión Nutrientes ($\bar{H}^N$) & $0.0035 \pm 0.0008$ & $0.0033 \pm 0.0008$ & $-0.0002$ & $-4.55\%$ & $t = -7.9$ & $p < 0.001$ (***) \\
Interferencia ($\Phi_{\text{Eq17}}$) & $127.33 \pm 0.11$ & $101.40 \pm 0.12$ & $-25.93$ & $\mathbf{-20.36\%}$ & $t = -6643.4$ & $p < 0.001$ (***) \\
\bottomrule
\end{tabular}%
}
\end{table}

\textbf{Hallazgos biológicos y ecológicos cardinales:}
\begin{enumerate}[leftmargin=1.5em]
    \item \textbf{Abatimiento de la pérdida por competencia:} La pérdida relativa de aptitud inducida por competencia vecinal ($(1 - \bar{F}/\bar{F}_{\text{aislada}})$) cae a menos de la mitad, pasando de **$8.57\%$ a $4.22\%$** (una reducción relativa del **$-50.80\%$**, $\Delta = -4.36$ puntos porcentuales).
    \item \textbf{Ganancia neta de supervivencia en campo:} De las $528.73$ plantas sembradas por hectárea, la siembra optimizada logra que sobrevivan **$509.44 \pm 3.69\text{ plantas/ha}$** frente a $487.85 \pm 4.20\text{ plantas/ha}$ en el esquema aleatorio, ganando de manera altamente significativa ($p < 0.001$) **$+21.59 \pm 1.65$ árboles y plantas vivas adicionales por hectárea**.
    \item \textbf{Reducción de la mortalidad temprana:} La tasa de mortalidad proxy inducida por estrés competitivo se reduce a más de la mitad, cayendo del **$7.73\%$ al $3.65\%$** (reducción del $-52.81\%$).
    \item \textbf{Despresurización hídrica y lumínica:} El índice de competencia por agua en la rizosfera ($\bar{H}^W$) cae un **$-14.34\%$** ($0.1789 \to 0.1532$) y el estrés por sombreado asimétrico del dosel ($\bar{H}^L$) desciende un **$-11.79\%$** ($0.0389 \to 0.0343$).
    \item \textbf{Interferencia de pares (Ecuación 17):} La función objetivo pura de interferencia $\Phi_{\text{Eq17}} = \sum_{(p,q)} c_{i(p), j(q)}$ disminuye un **$-20.36\%$** (de $127.33$ a $101.40$, $t = -6643.4$).
\end{enumerate}

\begin{figure}[H]
\centering
\includegraphics[width=0.96\textwidth]{entregable3_outputs/figuras/fig2_competencia_y_supervivencia_1000sim.png}
\caption{Comparación empírica de 1,000 corridas: distribución de aptitud media, supervivencia esperada y dispersión bivariada entre estrés hídrico y aptitud biológica.}\label{fig:fig2_competencia_supervivencia}
\end{figure}

\textbf{Interpretación de la Figura~\ref{fig:fig2_competencia_supervivencia}:} En los histogramas superiores se aprecia el desplazamiento completo a la derecha en la aptitud biológica y en la supervivencia esperada, sin solapamiento entre las densidades de probabilidad de la siembra aleatoria (rojo) y optimizada (verde). En el panel inferior se confirma la fuerte correlación inversa entre la presión hídrica radicular y la aptitud biológica, demostrando cómo el algoritmo desplaza sistemáticamente la masa de probabilidad hacia regímenes de baja competencia radicular.

\subsection{Probabilidad de transición entre plantas (cadena de Markov)}
El proceso de colocación de material vegetal en campo y la estructura espacial resultante se modelan formalmente como una **Cadena de Markov Estocástica Homogénea y Ergódica** sobre el espacio de estados discreto:
\begin{equation}
\mathcal{S} = \{\text{AL, AT, AC, AS, OC, OE, OR, OS, PL, YF}\}, \quad |\mathcal{S}| = 10.
\end{equation}

Se formularon dos perspectivas estocásticas complementarias:
\begin{enumerate}[leftmargin=1.5em]
    \item \textbf{Cadena de Markov Secuencial de Plantación ($P^{\text{sec}}$):} Modela la probabilidad de que una cuadrilla de reforestación plante un individuo de la especie $j$ inmediatamente después de haber plantado la especie $i$ a lo largo de la trayectoria serpentina (boustrophedon) que recorre los surcos de la malla.
    \item \textbf{Cadena de Markov Espacial de Vecindad Hexagonal ($P^{\text{vec}}$):} Modela la probabilidad condicional de encontrar una planta de la especie $j$ en cualquiera de los 6 vecinos inmediatos adyacentes a un nodo ocupado por la especie $i$ a una distancia $d \le 4.8\text{ m}$.
\end{enumerate}

Para ambas matrices estocásticas $P = (p_{ij})_{10\times 10}$, se cumple la propiedad de fila estocástica $\sum_{j=1}^{10} p_{ij} = 1$. La ergodicidad garantiza la existencia y unicidad de una distribución estacionaria $\boldsymbol{\pi} = (\pi_{\text{AL}}, \dots, \pi_{\text{YF}})$ tal que $\boldsymbol{\pi} P = \boldsymbol{\pi}$ con $\sum_{i=1}^{10} \pi_i = 1$, y los tiempos medios de retorno o recurrencia están dados por $\mu_i = 1 / \pi_i$ pasos.

En los Cuadros~\ref{tab:markov_sec} y~\ref{tab:markov_vec} se presentan las matrices completas de transición, las distribuciones estacionarias $\boldsymbol{\pi}$ y los tiempos de retorno $\mu_i$.
"""

# Insertar tablas de Markov y tabla de orden
tex_doc += "\n" + table_markov_sec + "\n\n"
tex_doc += "\n" + table_markov_vec + "\n\n"

tex_doc += r"""
\textbf{Análisis de los hallazgos markovianos y biofísicos:}
\begin{enumerate}[leftmargin=1.5em]
    \item \textbf{Bloque estrictamente nulo $3\times 3$ entre especies grandes en $P^{\text{vec}}$:} En el Cuadro~\ref{tab:markov_vec}, las filas correspondientes a \textbf{OS}, \textbf{PL} y \textbf{YF} presentan una probabilidad de transición de exactamente **$0.0000$** hacia sí mismas y entre sí:
    \begin{equation}
    p_{\text{OS, OS}}^{\text{vec}} = p_{\text{OS, PL}}^{\text{vec}} = p_{\text{OS, YF}}^{\text{vec}} = p_{\text{PL, OS}}^{\text{vec}} = p_{\text{PL, PL}}^{\text{vec}} = p_{\text{PL, YF}}^{\text{vec}} = p_{\text{YF, OS}}^{\text{vec}} = p_{\text{YF, PL}}^{\text{vec}} = p_{\text{YF, YF}}^{\text{vec}} = \mathbf{0.0000}.
    \end{equation}
    Esto demuestra formalmente que la restricción de Submalla 3 ($(u-v)\equiv 0\pmod 3$) y la penalización por solape de copa aíslan por completo a los árboles y cactáceas masivas, garantizando una separación física mínima de $a\sqrt{3} \approx 6.93\text{ m}$.
    \item \textbf{Canalización de la facilitación nodriza desde \textit{Prosopis laevigata} (\textbf{PL}):} Dado que el mezquite no puede colindar con otra especie de gran dosel, sus probabilidades de transición espacial se canalizan intensamente hacia las especies de porte medio y bajo que se benefician de su sombra y fijación de nitrógeno:
    \begin{equation}
    p_{\text{PL} \to \text{AS}}^{\text{vec}} = \mathbf{0.4206} \; (42.06\%), \quad p_{\text{PL} \to \text{OC}}^{\text{vec}} = \mathbf{0.1203} \; (12.03\%), \quad p_{\text{PL} \to \text{AT}}^{\text{vec}} = \mathbf{0.1041} \; (10.41\%).
    \end{equation}
    \item \textbf{Distribución estacionaria y tiempos medios de retorno:} En el recorrido secuencial, \textit{Agave salmiana} domina la cadena con $\pi_{\text{AS}} = 0.3053$ y un tiempo medio de retorno de solo $\mu_{\text{AS}} = 3.28$ pasos (la cuadrilla siembra un maguey aproximadamente cada 3 plantas). En contraste, la especie más escasa, \textit{Yucca filifera}, presenta $\pi_{\text{YF}} = 0.0363$ y un tiempo medio de recurrencia de $\mu_{\text{YF}} = 27.57$ pasos.
    \item \textbf{Entropía informacional del proceso de siembra:} La entropía de información de Shannon por transición ($H(X) = -\sum_{i} \pi_i \sum_j p_{ij} \log_2 p_{ij}$) alcanza $H(\mathcal{X})_{\text{opt}}^{\text{sec}} = 2.9790\text{ bits/símbolo}$ en la secuencia optimizada y $H(\mathcal{X})_{\text{opt}}^{\text{vec}} = 2.9340\text{ bits/símbolo}$ en la red espacial, reflejando una estructura combinatoria rica pero rigurosamente gobernada por las leyes de repulsión ecológica.
\end{enumerate}

\begin{figure}[H]
\centering
\includegraphics[width=0.96\textwidth]{entregable3_outputs/figuras/fig3_markov_transicion_heatmaps.png}
\caption{Mapas de calor comparativos de las matrices de transición de Markov: proceso secuencial aleatorio (izquierda), proceso secuencial optimizado (centro) y matriz de adyacencia espacial de vecindad hexagonal (derecha).}\label{fig:fig3_markov_heatmaps}
\end{figure}

\textbf{Interpretación de la Figura~\ref{fig:fig3_markov_heatmaps}:} El contraste entre los mapas revela con claridad la emergencia del orden espacial: mientras la matriz aleatoria exhibe una dispersión difusa e indiferenciada, la matriz optimizada secuencial y espacial muestra la concentración estratégica de transiciones hacia \textbf{AS} y la presencia del cuadrante negro de probabilidad cero en la esquina inferior derecha ($3\times 3$ entre \textbf{OS, PL, YF}), evidenciando el cumplimiento determinista de la regla de Submalla 3.

\subsection{Presentar el orden en que se debe realizar la plantación (un ejemplo completo)}
Para trasladar la solución matemática a una operación eficiente y libre de errores en campo por parte de brigadas forestales comunitarias, se diseñó el **Protocolo Operativo de Plantación en Tres Etapas Cronológicas con Recorrido Boustrophedon (Serpentina)**:

\begin{itemize}[leftmargin=1.5em]
    \item \textbf{Etapa Previa (Acondicionamiento y Georreferenciación):}
    \begin{enumerate}
        \item Desmonte selectivo del $85\%$ de pasto buffel y leñosa invasora con cuadrilla manual.
        \item Censo y geoposicionamiento (mediante estacas rojas) de las $\nu = 127$ plantas nativas preexistentes en la hectárea (correspondiente a la réplica representativa $s=1$).
        \item Trazado de la malla hexagonal mediante cuerda guía calibrada a $a = 4.0\text{ m}$.
    \end{enumerate}
    \item \textbf{Etapa 1 (Esqueleto Estructural y Árboles Nodriza — Submalla 3, 131 plantas):}
    Se colocan estacas de color azul exclusivamente en los nodos que satisfacen $(u_p - v_p) \equiv 0 \pmod 3$. La primera brigada siembra el mezquite (\textbf{PL}, 61 plantas), el cardón (\textbf{OS}, 52 plantas) y la palma china (\textbf{YF}, 18 plantas). Esto garantiza una separación basal mínima de $6.93\text{ m}$ entre árboles adultos.
    \item \textbf{Etapa 2 (Cactáceas Nopaleras y Maguey Pulquero de Porte Medio — Submalla 1, 326 plantas):}
    La segunda cuadrilla establece las especies de porte intermedio en los nodos libres de Submalla 1 adyacentes a los mezquites: \textit{Agave salmiana} (\textbf{AS}, 161 plantas), \textit{Opuntia robusta} (\textbf{OR}, 50 plantas), \textit{Opuntia cantabrigiensis} (\textbf{OC}, 43 plantas), \textit{Opuntia engelmannii} (\textbf{OE}, 34 plantas) y \textit{Agave scabra} (\textbf{AC}, 38 plantas).
    \item \textbf{Etapa 3 (Cierre Intersticial con Agaves Rosetófilos Litológicos — Submalla 1, 74 plantas):}
    La brigada final inserta las rosetófilas menores \textit{Agave lechuguilla} (\textbf{AL}, 36 plantas) y \textit{Agave striata} (\textbf{AT}, 38 plantas) en los micro-sitios más pedregosos y expuestos a la radiación solar.
\end{itemize}

\textbf{Bitácora operativa paso a paso:} En el Cuadro~\ref{tab:bitacora_plantacion} se transcribe la bitácora de ejecución para los primeros 30 pasos consecutivos y los últimos 10 pasos de cierre sobre la hectárea representativa ($s=1$, 531 plantas nuevas sembradas para completar la cuota de $658\text{ pl/ha}$).
"""

# Insertar tabla de orden de plantacion
tex_doc += "\n" + table_orden + "\n\n"

tex_doc += r"""
\begin{figure}[H]
\centering
\includegraphics[width=0.96\textwidth]{entregable3_outputs/figuras/fig4_orden_plantacion_mapa_1ha.png}
\caption{Mapa espacial de la hectárea representativa ($100\times 100\text{ m}$): trayectoria boustrophedon (serpentina) de siembra, clasificación por etapas operativas y mapa de aptitud ecológica individual $F_k$.}\label{fig:fig4_orden_mapa}
\end{figure}

\textbf{Interpretación de la Figura~\ref{fig:fig4_orden_mapa}:} El mapa superior ilustra la ruta serpentina continua de avance de la cuadrilla, minimizando los desplazamientos vacíos en campo (distancia media entre pasos de $4.38\text{ m}$). En el panel inferior izquierdo se observa la distribución uniforme de los núcleos de Etapa 1 (azul, árboles nodriza) sobre la Submalla 3, rodeados por los círculos verdes de porte medio (Etapa 2) y las rosetófilas naranjas (Etapa 3). El panel inferior derecho confirma que los valores de aptitud $F_k$ se mantienen homogéneamente altos en todo el predio ($> 0.55$), sin puntos calientes de asfixia competitiva.

% ====================================================================
% SECCIÓN 4. CONCLUSIONES Y RECOMENDACIONES
% ====================================================================
\section{Conclusiones y recomendaciones sobre los resultados obtenidos}

\subsection{Conclusiones científicas y de optimización matemática}
\begin{enumerate}[leftmargin=1.5em]
    \item \textbf{Eficacia del ordenamiento espacial sobre la resiliencia ecológica:} La optimización espacial mediante celosías hexagonales y algoritmos estocásticos reduce la pérdida de aptitud por competencia a menos de la mitad (**$-50.80\%$**, de $8.57\%$ a $4.22\%$) y abate la interferencia competitiva por pares en un **$-20.36\%$** ($p < 0.001$). Esto demuestra cuantitativamente que la disposición espacial es un factor determinante tan relevante como la selección biológica de especies.
    \item \textbf{Impacto masivo en supervivencia vegetal:} Al mitigar la competencia hídrica radicular en un $-14.34\%$ y el sombreado perjudicial en un $-11.79\%$, el sistema logra una ganancia neta de **$+21.59 \pm 1.65$ árboles y plantas vivas adicionales por hectárea**. 
    \item \textbf{Extrapolación regional al Parque Eólico Dominica ($189.55\text{ ha}$):} Al proyectar la ganancia unitaria de $+21.59\text{ pl/ha}$ sobre la superficie total de los 31 polígonos oficiales ($189.55\text{ ha}$), la aplicación del modelo asegura la supervivencia adicional de:
    \begin{equation}
    189.55\text{ ha} \times 21.586\text{ pl/ha} = \mathbf{+4,091.6 \approx +4,092\text{ árboles y plantas sobrevivientes adicionales}},
    \end{equation}
    reduciendo la mortandad del proyecto a menos del $3.7\%$ **sin incrementar en un solo centavo el presupuesto de adquisición de material vegetal en vivero** (\$2,384,730.50 MXN).
    \item \textbf{Sinergia metodológica metaheurística-MILP exacto:} La formulación lineal entera mixta con cortes RLT-1 y cliques triangulares $K_3$ demostró que la descomposición espacial en teselas de 66 a 96 nodos alcanza la optimalidad matemática global certificada ($\text{gap} = 0.00\%$) en segundos, validando teóricamente que las soluciones halladas por el Recocido Simulado operan a menos del $2.8\%$ de distancia del óptimo global absoluto.
    \item \textbf{Rigor estocástico y representatividad estadística:} Con 1,000 réplicas completas, el error estándar del valor esperado de plantas a suministrar se redujo a $EE = 0.112\text{ pl/ha}$ y la incertidumbre presupuestal a solo $\pm \$92.96\text{ MXN/ha}$ (un coeficiente de variación de apenas $0.74\%$), dotando al plan de un blindaje forense e institucional absoluto para CONAFOR e INECOL.
\end{enumerate}

\subsection{Recomendaciones operativas y de política forestal}
Con base en los resultados numéricos, se formulan las siguientes 6 recomendaciones para su adopción por parte de las cuadrillas de campo y los organismos reguladores:
\begin{enumerate}[leftmargin=1.5em]
    \item \textbf{Adopción normativa de la banda de tolerancia $\boldsymbol{\varepsilon = \pm 10\%}$:} CONAFOR debe flexibilizar la receta fija de 658 pl/ha permitiendo holguras del $\pm 10\%$. Esto permite reducir la densidad de especies de gran dosel donde el relieve lo requiera y disminuye el costo unitario por hectárea en \$27.19 MXN manteniendo intacta la diversidad funcional.
    \item \textbf{Estacado previo obligatorio de la Submalla 3:} Se recomienda a los brigadistas comunitarios marcar previamente con estacas de color azul las posiciones que satisfacen $(u-v)\equiv 0\pmod 3$ antes de iniciar el despalille. Esto elimina el riesgo de que dos mezquites o cardones colinden a menos de $6.9\text{ m}$.
    \item \textbf{Secuenciación de siembra por brigadas temáticas (Etapas 1, 2 y 3):} En lugar de cuadrillas mixtas desorganizadas, se recomienda desplegar 3 cuadrillas escalonadas: la Brigada 1 siembra árboles estructurales; la Brigada 2 establece magueyeras y nopaleras intermedias; y la Brigada 3 cierra los intersticios rocosos con agaves menores.
    \item \textbf{Zonificación de densidad según pendiente con franjas anti-erosión:} En pendientes $\ge 20\%$, aplicar estrictamente la reducción a $524\text{ pl/ha}$ con espaciado dilatado de $4.70\text{ m}$ y disponer las cactáceas en curvas de nivel perpendiculares a la pendiente para frenar el arrastre de sedimentos.
    \item \textbf{Apertura de cepas y calendario pre-monzón:} La siembra de la Etapa 1 (*Prosopis laevigata*) debe ejecutarse al menos 3 semanas antes del inicio formal de la temporada de lluvias de verano para permitir el asentamiento del cepellón y la activación de la nodulación por *Rhizobium*.
    \item \textbf{Monitoreo digital mediante vehículos aéreos no tripulados (UAV):} Emplear vuelos fotogramétricos multiespectrales a los meses 6, 12 y 24 para registrar la supervivencia real y re-alimentar la matriz de Markov con probabilidades de mortandad observadas in situ.
\end{enumerate}

\newpage

% ====================================================================
% ANEXO A. MODELO MATEMÁTICO Y DE SIMULACIÓN EN PYTHON
% ====================================================================
\section*{Anexo A. Modelo matemático y de simulación en Python}\label{sec:anexo_python}
\addcontentsline{toc}{section}{Anexo A. Modelo matemático y de simulación en Python}

A continuación se transcribe íntegramente el código fuente en Python (\texttt{modelo\_anexo\_entregable3.py}) utilizado para construir la malla hexagonal, simular el censo estocástico, optimizar mediante Recocido Simulado, resolver la formulación exacta MILP con cortes RLT-1 y $K_3$, calcular las matrices de transición de Markov y generar la bitácora boustrophedon de plantación.

\vspace{0.4cm}
\lstinputlisting[language=Python, caption={Código fuente íntegro del modelo computacional de reforestación estocástica (\texttt{modelo\_anexo\_entregable3.py}).}]{entregable3_outputs/modelo_anexo_entregable3.py}

\end{document}
"""

with open(tex_path, "w", encoding="utf-8") as f:
    f.write(tex_doc)

print(f"Archivo LaTeX generado exitosamente en: {tex_path}")
print(f"Tamaño del archivo generado: {len(tex_doc):,} caracteres.")
