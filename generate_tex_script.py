# -*- coding: utf-8 -*-
"""
Generador Maestro del Documento LaTeX Entregable 3 (REFORESTATHON)
Equipo 2:
- César David Collins Estrada — A00841082
- Miguel Ángel Hernández Ochoa — A00830949
- Juan Miranda Arostegui — A01832488
- Eugenio Moreno Vargas — A01723720
- Abraham Vicente González — A01199401
Materia: Optimización estocástica (Gpo 201)
Profesores: Dr. Fernando Elizalde Ramírez – Dr. Rafael Muñoz
Fecha: Octubre de 2026
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

# Construir tabla de Markov Secuencial
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

print("Tablas dinámicas construidas exitosamente.")
