# -*- coding: utf-8 -*-
"""
generar_figuras_entregable3.py
==============================
Generación de las 4 Figuras Científicas de Nivel Publicación (300 DPI) para el Entregable 3:
1. fig1_existentes_y_suministro_1000sim.png
2. fig2_competencia_y_supervivencia_1000sim.png
3. fig3_markov_transicion_heatmaps.png
4. fig4_orden_plantacion_mapa_1ha.png

Estilo sobrio académico idéntico al Entregable 2:
- Paleta Okabe-Ito (accesible para daltónicos) y Viridis
- Tipografía limpia con Computer Modern math
- 300 DPI, layout balanceado, sin textos encimados ni recortados
"""

import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.gridspec import GridSpec
from matplotlib.colors import LinearSegmentedColormap

# Configuración de rutas
REFOREST_DIR = Path(r"d:\Codingggg\Notas\Estocastico\REFORESTATHON")
OUT_DIR = REFOREST_DIR / "entregable3_outputs"
FIG_DIR = OUT_DIR / "figuras"
FIG_DIR.mkdir(parents=True, exist_ok=True)
MODELO_DIR = REFOREST_DIR.parent / "modelo_dominica" / "modelo_dominica"
sys.path.insert(0, str(MODELO_DIR))
sys.path.insert(0, str(REFOREST_DIR / "scripts" / "src"))

import hexgarden as hg
import terreno as tr
import pipeline as pl
import experimento_1000_simulaciones_ha as exp

# Parámetros de estilo científico
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans", "Helvetica"],
    "mathtext.fontset": "cm",
    "axes.edgecolor": "#222222",
    "axes.linewidth": 0.8,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.size": 4,
    "ytick.major.size": 4,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight"
})

# Paleta Okabe-Ito
COLOR_BLACK = "#000000"
COLOR_ORANGE = "#E69F00"
COLOR_SKY_BLUE = "#56B4E9"
COLOR_BLUISH_GREEN = "#009E73"
COLOR_YELLOW = "#F0E442"
COLOR_BLUE = "#0072B2"
COLOR_VERMILION = "#D55E00"
COLOR_REDDISH_PURPLE = "#CC79A7"
COLOR_GREY = "#7F7F7F"
COLOR_DARK_SLATE = "#2F4F4F"

SPECIES_CODES = ["AL", "AT", "AC", "AS", "OC", "OE", "OR", "OS", "PL", "YF"]
SPECIES_FULL_NAMES = [
    "Agave lechuguilla", "Agave striata", "Agave scabra", "Agave salmiana",
    "Opuntia cantabrigiensis", "Opuntia engelmannii", "Opuntia robusta",
    "Opuntia streptacantha", "Prosopis laevigata", "Yucca filifera"
]
SPECIES_LABELS = [f"{c} - {n}" for c, n in zip(SPECIES_CODES, SPECIES_FULL_NAMES)]


# ==============================================================================
# FIGURA 1: EXISTENTES Y SUMINISTRO EN 1,000 SIMULACIONES
# ==============================================================================
def generar_figura_1():
    print("-> Generando Figura 1: Existentes y Suministro en 1,000 Simulaciones...")
    df_species = pd.read_csv(OUT_DIR / "tabla_existentes_y_suministro_especie.csv")
    df_summary = pd.read_csv(OUT_DIR / "sim_1000_corridas_resumen.csv")

    # Excluir la fila TOTAL para el panel de especies
    df_sp = df_species[df_species["especie_codigo"] != "TOTAL"].copy()

    fig = plt.figure(figsize=(15.5, 7.8), dpi=300)
    gs = GridSpec(2, 2, width_ratios=[1.35, 1.0], hspace=0.32, wspace=0.28)

    # -------------------------------------------------------------
    # Panel (a): Barras agrupadas por especie (Preexistentes vs Suministro)
    # -------------------------------------------------------------
    ax_a = fig.add_subplot(gs[:, 0])
    y_pos = np.arange(len(df_sp))
    bar_height = 0.26

    # Datos
    nu_mean = df_sp["existentes_nu_mean"].values
    nu_se = df_sp["existentes_nu_se"].values
    strict_mean = df_sp["suministro_strict_eps0_mean"].values
    strict_std = df_sp["suministro_strict_eps0_std"].values
    opt_mean = df_sp["suministro_opt_eps10_mean"].values
    opt_se = df_sp["suministro_opt_eps10_se"].values

    # Dibujar barras horizontales
    b1 = ax_a.barh(y_pos + bar_height, nu_mean, height=bar_height,
                   xerr=nu_se * 1.96, color=COLOR_BLUE, alpha=0.90,
                   edgecolor="#1b3a6b", linewidth=0.7, label=r"Preexistentes observadas $\mathbb{E}[\nu_i]$",
                   capsize=3, zorder=3)
    b2 = ax_a.barh(y_pos, strict_mean, height=bar_height,
                   color=COLOR_ORANGE, alpha=0.90,
                   edgecolor="#a65d00", linewidth=0.7, label=r"Suministro estricto ($\varepsilon = 0$)",
                   zorder=3)
    b3 = ax_a.barh(y_pos - bar_height, opt_mean, height=bar_height,
                   xerr=opt_se * 1.96, color=COLOR_BLUISH_GREEN, alpha=0.90,
                   edgecolor="#005a3e", linewidth=0.7, label=r"Suministro optimizado ($\varepsilon = 0.10$)",
                   capsize=3, zorder=3)

    # Anotaciones de valores al extremo de las barras
    for idx, y in enumerate(y_pos):
        # Preexistentes
        ax_a.text(nu_mean[idx] + (nu_se[idx]*1.96) + 1.2, y + bar_height,
                  f"{nu_mean[idx]:.1f}", va="center", ha="left", fontsize=7.5, color="#1b3a6b", fontweight="bold")
        # Estricto
        ax_a.text(strict_mean[idx] + 1.2, y,
                  f"{strict_mean[idx]:.1f}", va="center", ha="left", fontsize=7.5, color="#a65d00", fontweight="bold")
        # Optimizado
        ax_a.text(opt_mean[idx] + (opt_se[idx]*1.96) + 1.2, y - bar_height,
                  f"{opt_mean[idx]:.1f}", va="center", ha="left", fontsize=7.5, color="#005a3e", fontweight="bold")

    ax_a.set_yticks(y_pos)
    ax_a.set_yticklabels(SPECIES_LABELS, fontsize=9.0, fontweight="medium")
    ax_a.invert_yaxis()  # Primera especie arriba
    ax_a.set_xlabel("Número esperado de individuos por hectárea (plantas/ha)", fontsize=10, labelpad=8)
    ax_a.set_xlim(0, 185)
    ax_a.grid(True, axis="x", linestyle="--", alpha=0.45, linewidth=0.6, zorder=0)
    ax_a.set_axisbelow(True)
    ax_a.legend(loc="upper right", frameon=True, framealpha=0.95, facecolor="white", edgecolor="#cccccc", fontsize=8.5)
    ax_a.set_title("(a) Distribución Taxonómica: Vegetación Preexistente vs Demanda de Vivero",
                   fontsize=10.5, fontweight="bold", pad=10, loc="left")

    # -------------------------------------------------------------
    # Panel (b1): Histograma + KDE de Vegetación Preexistente Total
    # -------------------------------------------------------------
    ax_b1 = fig.add_subplot(gs[0, 1])
    nu_total = df_summary["nu_total"].values
    mu_nu = float(np.mean(nu_total))
    std_nu = float(np.std(nu_total, ddof=1))
    ci_nu_low, ci_nu_high = np.percentile(nu_total, 2.5), np.percentile(nu_total, 97.5)

    n_bins_nu = np.arange(nu_total.min() - 0.5, nu_total.max() + 1.5, 1)
    counts, bins, _ = ax_b1.hist(nu_total, bins=n_bins_nu, density=True,
                                 color=COLOR_BLUE, alpha=0.45, edgecolor="#1b3a6b", linewidth=0.6, zorder=2)
    # KDE
    kde_nu = stats.gaussian_kde(nu_total)
    x_grid_nu = np.linspace(nu_total.min() - 2, nu_total.max() + 2, 300)
    ax_b1.plot(x_grid_nu, kde_nu(x_grid_nu), color="#003d73", linewidth=1.8, label="Densidad empírica KDE", zorder=3)

    # Intervalo de confianza y media
    ax_b1.axvline(mu_nu, color="#b71c1c", linestyle="--", linewidth=1.6, zorder=4,
                  label=f"Media $\\mathbb{{E}}[\\nu] = {mu_nu:.2f}$ pl/ha")
    ax_b1.axvspan(ci_nu_low, ci_nu_high, color=COLOR_BLUE, alpha=0.15, zorder=1,
                  label=f"IC 95%: [{ci_nu_low:.1f}, {ci_nu_high:.1f}] pl/ha")

    ax_b1.set_xlabel(r"Total de plantas preexistentes conservadas ($\nu$, pl/ha)", fontsize=9.2, labelpad=6)
    ax_b1.set_ylabel("Densidad de probabilidad", fontsize=9.2, labelpad=6)
    ax_b1.grid(True, linestyle="--", alpha=0.4, linewidth=0.5, zorder=0)
    ax_b1.legend(loc="upper right", frameon=True, framealpha=0.92, facecolor="white", fontsize=8.0)
    ax_b1.set_title(r"(b) Distribución Estocástica del Censo de Vegetación Preexistente",
                    fontsize=10.0, fontweight="bold", pad=8, loc="left")

    # -------------------------------------------------------------
    # Panel (b2): Histograma + KDE de Demanda de Suministro Nuevo
    # -------------------------------------------------------------
    ax_b2 = fig.add_subplot(gs[1, 1])
    n_sembrar = df_summary["N_sembrar"].values
    mu_sem = float(np.mean(n_sembrar))
    std_sem = float(np.std(n_sembrar, ddof=1))
    ci_sem_low, ci_sem_high = np.percentile(n_sembrar, 2.5), np.percentile(n_sembrar, 97.5)

    n_bins_sem = np.arange(n_sembrar.min() - 0.5, n_sembrar.max() + 1.5, 1)
    ax_b2.hist(n_sembrar, bins=n_bins_sem, density=True,
               color=COLOR_BLUISH_GREEN, alpha=0.45, edgecolor="#005a3e", linewidth=0.6, zorder=2)
    kde_sem = stats.gaussian_kde(n_sembrar)
    x_grid_sem = np.linspace(n_sembrar.min() - 2, n_sembrar.max() + 2, 300)
    ax_b2.plot(x_grid_sem, kde_sem(x_grid_sem), color="#004d40", linewidth=1.8, label="Densidad empírica KDE", zorder=3)

    ax_b2.axvline(mu_sem, color="#b71c1c", linestyle="--", linewidth=1.6, zorder=4,
                  label=f"Media $\\mathbb{{E}}[N_{{\\text{{sembrar}}}}] = {mu_sem:.2f}$ pl/ha")
    ax_b2.axvspan(ci_sem_low, ci_sem_high, color=COLOR_BLUISH_GREEN, alpha=0.15, zorder=1,
                  label=f"IC 95%: [{ci_sem_low:.1f}, {ci_sem_high:.1f}] pl/ha")

    ax_b2.set_xlabel(r"Total de plantas a sembrar de vivero ($N_{\text{sembrar}} = 658 - \nu$, pl/ha)", fontsize=9.2, labelpad=6)
    ax_b2.set_ylabel("Densidad de probabilidad", fontsize=9.2, labelpad=6)
    ax_b2.grid(True, linestyle="--", alpha=0.4, linewidth=0.5, zorder=0)
    ax_b2.legend(loc="upper right", frameon=True, framealpha=0.92, facecolor="white", fontsize=8.0)
    ax_b2.set_title(r"(c) Demanda Neta de Adquisición en Vivero para $N = 658$ pl/ha",
                    fontsize=10.0, fontweight="bold", pad=8, loc="left")

    out_file = FIG_DIR / "fig1_existentes_y_suministro_1000sim.png"
    plt.savefig(out_file)
    plt.close()
    print(f"  [OK] Guardada: {out_file}")


# ==============================================================================
# FIGURA 2: COMPETENCIA MULTICANAL Y SUPERVIVENCIA EN 1,000 SIMULACIONES
# ==============================================================================
def generar_figura_2():
    print("-> Generando Figura 2: Competencia Multicanal y Supervivencia...")
    df_summary = pd.read_csv(OUT_DIR / "sim_1000_corridas_resumen.csv")
    df_comp = pd.read_csv(OUT_DIR / "tabla_competencia_1ha.csv")

    fig = plt.figure(figsize=(15.5, 9.2), dpi=300)
    gs = GridSpec(2, 2, hspace=0.32, wspace=0.25)

    # -------------------------------------------------------------
    # Panel (a): Distribución Pareada de Aptitud Biológica Media (F_bar)
    # -------------------------------------------------------------
    ax_a = fig.add_subplot(gs[0, 0])
    f_rand = df_summary["F_media_init"].values
    f_opt = df_summary["F_media_opt"].values
    f_iso = df_summary["F_aislada"].values

    parts = ax_a.violinplot([f_rand, f_opt, f_iso], positions=[1, 2, 3],
                            showmeans=False, showmedians=False, showextrema=False, widths=0.62)
    colors = [COLOR_VERMILION, COLOR_BLUISH_GREEN, COLOR_BLUE]
    for pc, col in zip(parts["bodies"], colors):
        pc.set_facecolor(col)
        pc.set_edgecolor("#333333")
        pc.set_alpha(0.65)
        pc.set_linewidth(0.8)

    # Boxplots empotrados
    ax_a.boxplot([f_rand, f_opt, f_iso], positions=[1, 2, 3], widths=0.18,
                 patch_artist=True, boxprops=dict(facecolor="white", edgecolor="#222222", linewidth=0.8),
                 medianprops=dict(color="#b71c1c", linewidth=1.6),
                 whiskerprops=dict(color="#222222", linewidth=0.8),
                 capprops=dict(color="#222222", linewidth=0.8),
                 showfliers=False)

    # Anotaciones numéricas de medias
    ax_a.plot([1, 2, 3], [f_rand.mean(), f_opt.mean(), f_iso.mean()], "D", color="#b71c1c", markersize=4.5, zorder=5)
    ax_a.text(1, f_rand.mean() + 0.0035, f"{f_rand.mean():.4f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#900C3F")
    ax_a.text(2, f_opt.mean() + 0.0035, f"{f_opt.mean():.4f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#005a3e")
    ax_a.text(3, f_iso.mean() + 0.0035, f"{f_iso.mean():.4f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#003d73")

    # Flecha de ganancia porcentual en zona despejada
    ax_a.annotate(
        r"$\mathbf{+4.76\%}$" + " mejora\n" + r"$(p < 0.001)$",
        xy=(2.0, f_opt.mean()),
        xytext=(1.45, 0.582),
        ha="center", va="center", fontsize=8.5, fontweight="bold", color="#005a3e",
        arrowprops=dict(arrowstyle="->", color="#005a3e", lw=1.3),
        bbox=dict(boxstyle="round,pad=0.25", facecolor="#e8f5e9", edgecolor="#2e7d32", lw=0.7)
    )

    ax_a.set_xticks([1, 2, 3])
    ax_a.set_xticklabels(["Siembra\nAleatoria", "Optimizada\n(Recocido)", "Planta\nAislada (Ref.)"], fontsize=9.2)
    ax_a.set_ylabel(r"Aptitud Biológica Ponderada Media ($\bar{F}$)", fontsize=9.5, labelpad=6)
    ax_a.set_ylim(0.530, 0.612)
    ax_a.grid(True, axis="y", linestyle="--", alpha=0.45, linewidth=0.6)
    ax_a.set_title("(a) Desempeño Biológico Global $(\\bar{F})$ en 1,000 Corridas", fontsize=10.5, fontweight="bold", pad=10, loc="left")

    # -------------------------------------------------------------
    # Panel (b): Pérdida de Aptitud por Competencia Espacial (%)
    # -------------------------------------------------------------
    ax_b = fig.add_subplot(gs[0, 1])
    loss_rand = df_summary["loss_comp_init"].values * 100.0
    loss_opt = df_summary["loss_comp_opt"].values * 100.0

    ax_b.hist(loss_rand, bins=35, density=True, color=COLOR_VERMILION, alpha=0.40,
              edgecolor="#a63600", linewidth=0.5, label="Aleatorio")
    ax_b.hist(loss_opt, bins=35, density=True, color=COLOR_BLUISH_GREEN, alpha=0.40,
              edgecolor="#005a3e", linewidth=0.5, label="Optimizado")

    kde_lr = stats.gaussian_kde(loss_rand)
    kde_lo = stats.gaussian_kde(loss_opt)
    x_grid_l = np.linspace(2.5, 10.5, 400)
    ax_b.plot(x_grid_l, kde_lr(x_grid_l), color="#a63600", linewidth=1.8, label="KDE Aleatorio")
    ax_b.plot(x_grid_l, kde_lo(x_grid_l), color="#004d40", linewidth=1.8, label="KDE Optimizado")

    # Medias verticales
    ax_b.axvline(loss_rand.mean(), color="#a63600", linestyle="--", linewidth=1.5)
    ax_b.axvline(loss_opt.mean(), color="#004d40", linestyle="--", linewidth=1.5)

    ax_b.text(loss_rand.mean() - 0.15, 1.50, f"{loss_rand.mean():.2f}%", color="#a63600", fontweight="bold", fontsize=8.5, ha="right")
    ax_b.text(loss_opt.mean() - 0.15, 1.50, f"{loss_opt.mean():.2f}%", color="#004d40", fontweight="bold", fontsize=8.5, ha="right")

    # Flecha de reducción relativa del 50.8%
    ax_b.annotate(
        r"$\mathbf{-50.8\%}$" + " reducción relativa\n" + r"$(\Delta = -4.36\text{ puntos})$",
        xy=((loss_rand.mean() + loss_opt.mean()) / 2.0, 0.70),
        xytext=(6.35, 1.15),
        ha="center", va="center", fontsize=8.5, fontweight="bold", color="#b71c1c",
        arrowprops=dict(arrowstyle="->", color="#b71c1c", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#ffebee", edgecolor="#c62828", lw=0.7)
    )

    ax_b.set_xlabel(r"Pérdida por competencia $1 - \bar{F}/\bar{F}_{\text{aislada}}$ (%)", fontsize=9.5, labelpad=6)
    ax_b.set_ylabel("Densidad de probabilidad", fontsize=9.5, labelpad=6)
    ax_b.set_xlim(2.5, 11.2)
    ax_b.grid(True, linestyle="--", alpha=0.45, linewidth=0.6)
    ax_b.legend(loc="upper right", frameon=True, framealpha=0.95, facecolor="white", fontsize=8.0)
    ax_b.set_title("(b) Atenuación del Estrés Competitivo", fontsize=10.5, fontweight="bold", pad=10, loc="left")

    # -------------------------------------------------------------
    # Panel (c): Comparativa por Canal Fisiológico y Presión de Interferencia
    # -------------------------------------------------------------
    ax_c = fig.add_subplot(gs[1, 0])

    channels = [
        r"$H^W$" + "\n(Hídrico)",
        r"$H^L$" + "\n(Luz)",
        r"$H^B$" + "\n(Nodriza)",
        r"$H^N$" + "\n(Nutrientes)",
        r"$\Phi_{\text{Eq17}}$" + "\n(Interf. $\\times 10^{-3}$)"
    ]

    v_init_ch = [
        float(df_comp.loc[5, "inicial_aleatorio_mean"]),
        float(df_comp.loc[6, "inicial_aleatorio_mean"]),
        float(df_comp.loc[7, "inicial_aleatorio_mean"]),
        float(df_comp.loc[8, "inicial_aleatorio_mean"]),
        float(df_comp.loc[9, "inicial_aleatorio_mean"]) / 1000.0
    ]
    v_opt_ch = [
        float(df_comp.loc[5, "optimizado_recocido_mean"]),
        float(df_comp.loc[6, "optimizado_recocido_mean"]),
        float(df_comp.loc[7, "optimizado_recocido_mean"]),
        float(df_comp.loc[8, "optimizado_recocido_mean"]),
        float(df_comp.loc[9, "optimizado_recocido_mean"]) / 1000.0
    ]
    pct_ch = [
        float(df_comp.loc[5, "cambio_relativo_pct"]),
        float(df_comp.loc[6, "cambio_relativo_pct"]),
        float(df_comp.loc[7, "cambio_relativo_pct"]),
        float(df_comp.loc[8, "cambio_relativo_pct"]),
        float(df_comp.loc[9, "cambio_relativo_pct"])
    ]

    x_c = np.arange(len(channels))
    width_c = 0.35

    ax_c.bar(x_c - width_c/2, v_init_ch, width_c, label="Aleatorio", color=COLOR_VERMILION, alpha=0.85, edgecolor="#a63600", linewidth=0.7)
    ax_c.bar(x_c + width_c/2, v_opt_ch, width_c, label="Optimizado", color=COLOR_BLUISH_GREEN, alpha=0.85, edgecolor="#005a3e", linewidth=0.7)

    for idx, (p, v1, v2) in enumerate(zip(pct_ch, v_init_ch, v_opt_ch)):
        y_top = max(v1, v2)
        sign = "+" if p > 0 else ""
        ax_c.text(idx, y_top + 0.006, f"{sign}{p:.1f}%", ha="center", va="bottom", fontsize=8.0, fontweight="bold",
                  color="#b71c1c" if p < 0 else "#005a3e")

    ax_c.set_xticks(x_c)
    ax_c.set_xticklabels(channels, fontsize=8.8)
    ax_c.set_ylabel("Presión media agregada por canal", fontsize=9.5, labelpad=6)
    ax_c.set_ylim(0, 0.225)
    ax_c.grid(True, axis="y", linestyle="--", alpha=0.45, linewidth=0.6)
    ax_c.legend(loc="upper right", frameon=True, framealpha=0.92, facecolor="white", fontsize=8.2)
    ax_c.set_title("(c) Canales de Presión Fisiológica y Reducción de Interferencia", fontsize=10.5, fontweight="bold", pad=10, loc="left")

    # -------------------------------------------------------------
    # Panel (d): Supervivencia Real Esperada (Plantas Vivas Adicionales)
    # -------------------------------------------------------------
    ax_d = fig.add_subplot(gs[1, 1])
    s_init_arr = df_summary["sobrev_init"].values
    s_opt_arr = df_summary["sobrev_opt"].values
    delta_arr = df_summary["delta_sobrevivientes"].values

    s_init_m = float(df_comp.loc[3, "inicial_aleatorio_mean"])
    s_opt_m = float(df_comp.loc[3, "optimizado_recocido_mean"])
    delta_m = s_opt_m - s_init_m

    # Gráfico de barras comparativo de sobrevivientes
    b_s1 = ax_d.bar(1, s_init_m, width=0.52, color=COLOR_VERMILION, alpha=0.88, edgecolor="#a63600", linewidth=0.8, label="Siembra Aleatoria")
    b_s2 = ax_d.bar(2, s_opt_m, width=0.52, color=COLOR_BLUISH_GREEN, alpha=0.88, edgecolor="#005a3e", linewidth=0.8, label="Siembra Optimizada")

    ax_d.text(1, s_init_m + 1.8, f"{s_init_m:.1f} pl/ha\n({s_init_m/6.58:.1f}%)", ha="center", va="bottom", fontsize=8.8, fontweight="bold", color="#a63600")
    ax_d.text(2, s_opt_m + 1.8, f"{s_opt_m:.1f} pl/ha\n({s_opt_m/6.58:.1f}%)", ha="center", va="bottom", fontsize=8.8, fontweight="bold", color="#005a3e")

    # Corchete anotador de ganancia neta
    ax_d.plot([1.0, 1.0, 2.0, 2.0], [517.0, 521.0, 521.0, 517.0], color="#111111", linewidth=1.1)
    ax_d.text(1.5, 522.5, f"+{delta_m:.2f} plantas vivas adicionales por hectárea\n(+4.42% supervivencia neta, p < 0.001)",
              ha="center", va="bottom", fontsize=8.6, fontweight="bold", color="#005a3e",
              bbox=dict(boxstyle="round,pad=0.35", facecolor="#e8f5e9", edgecolor="#2e7d32", lw=0.8))

    ax_d.set_xticks([1, 2])
    ax_d.set_xticklabels(["Siembra Aleatoria\nConvencional", "Siembra Optimizada\n(Recocido Simulado)"], fontsize=9.2)
    ax_d.set_ylabel("Sobrevivientes esperados por hectárea (plantas/ha)", fontsize=9.5, labelpad=6)
    ax_d.set_ylim(460, 538)
    ax_d.grid(True, axis="y", linestyle="--", alpha=0.45, linewidth=0.6)
    ax_d.legend(loc="lower left", frameon=True, framealpha=0.92, facecolor="white", fontsize=8.2)
    ax_d.set_title("(d) Ganancia Neta de Supervivencia en Campo (1 Hectárea)", fontsize=10.5, fontweight="bold", pad=10, loc="left")

    out_file = FIG_DIR / "fig2_competencia_y_supervivencia_1000sim.png"
    plt.savefig(out_file)
    plt.close()
    print(f"  [OK] Guardada: {out_file}")


# ==============================================================================
# FIGURA 3: MAPAS DE CALOR DE LAS CADENAS DE MARKOV (SECUENCIAL Y ESPACIAL)
# ==============================================================================
def generar_figura_3():
    print("-> Generando Figura 3: Mapas de Calor de Cadenas de Markov...")
    df_seq = pd.read_csv(OUT_DIR / "matriz_transicion_markov_secuencial_opt.csv", index_col=0)
    df_vec = pd.read_csv(OUT_DIR / "matriz_transicion_markov_vecinos_opt.csv", index_col=0)

    P_seq = df_seq[SPECIES_CODES].values
    P_vec = df_vec[SPECIES_CODES].values
    pi_vec = df_vec["Estacionaria_pi"].values

    with open(OUT_DIR / "resumen_estadistico_entregable3.json", "r", encoding="utf-8") as f:
        resumen_json = json.load(f)
    h_seq = resumen_json["cadenas_de_markov"]["entropia_secuencial_opt_bits"]
    h_vec = resumen_json["cadenas_de_markov"]["entropia_adyacencia_espacial_bits"]

    fig = plt.figure(figsize=(16.8, 7.8), dpi=300)
    gs = GridSpec(1, 2, width_ratios=[1.0, 1.0], wspace=0.25)

    # -------------------------------------------------------------
    # Panel (a): Transición Secuencial Boustrophedon Optimizada P^sec
    # -------------------------------------------------------------
    ax_a = fig.add_subplot(gs[0, 0])
    cmap_seq = plt.cm.YlGnBu
    im_a = ax_a.imshow(P_seq, cmap=cmap_seq, vmin=0.0, vmax=0.45, aspect="auto")

    # Anotar valores en cada celda
    for i in range(10):
        for j in range(10):
            val = P_seq[i, j]
            text_col = "white" if val > 0.22 else "#111111"
            ax_a.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7.8,
                      color=text_col, fontweight="bold" if val > 0.20 else "normal")

    ax_a.set_xticks(range(10))
    ax_a.set_yticks(range(10))
    ax_a.set_xticklabels(SPECIES_CODES, fontsize=8.8, fontweight="bold")
    ax_a.set_yticklabels(SPECIES_CODES, fontsize=8.8, fontweight="bold")
    ax_a.set_xlabel(r"Especie receptora en el paso consecutivo $k+1$ ($j$)", fontsize=9.5, labelpad=8)
    ax_a.set_ylabel(r"Especie sembrada en el paso actual $k$ ($i$)", fontsize=9.5, labelpad=8)
    ax_a.set_title(f"(a) Cadena de Markov Secuencial de Plantación Boustrophedon\nTasa de Entropía: $H(\\mathcal{{X}})_{{\\text{{opt}}}}^{{\\text{{sec}}}} = {h_seq:.4f}$ bits/transición",
                   fontsize=10.2, fontweight="bold", pad=12, loc="left")

    cbar_a = fig.colorbar(im_a, ax=ax_a, fraction=0.046, pad=0.04)
    cbar_a.set_label("Probabilidad de transición secuencial $p_{ij}^{\\text{sec}}$", fontsize=8.8)

    # -------------------------------------------------------------
    # Panel (b): Transición Espacial en Red de Vecinos P^vec
    # -------------------------------------------------------------
    ax_b = fig.add_subplot(gs[0, 1])
    cmap_vec = plt.cm.YlGnBu
    im_b = ax_b.imshow(P_vec, cmap=cmap_vec, vmin=0.0, vmax=0.45, aspect="auto")

    for i in range(10):
        for j in range(10):
            val = P_vec[i, j]
            text_col = "white" if val > 0.22 else "#111111"
            ax_b.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7.8,
                      color=text_col, fontweight="bold" if val > 0.20 else "normal")

    # RECUADRO ROJO/DORADO resaltando el bloque 0.00 entre especies grandes (OS, PL, YF)
    # Índices en SPECIES_CODES: OS=7, PL=8, YF=9
    rect = patches.Rectangle((6.5, 6.5), 3.0, 3.0, linewidth=2.6, edgecolor="#d50000",
                             facecolor="none", linestyle="-", zorder=5)
    ax_b.add_patch(rect)
    ax_b.text(8.0, 6.38, "Bloque 0.00 (Submalla 3: OS, PL, YF)",
              ha="center", va="bottom", fontsize=7.6, fontweight="bold", color="#b71c1c",
              bbox=dict(boxstyle="round,pad=0.18", facecolor="#ffebee", edgecolor="#c62828", lw=0.8),
              zorder=6)

    ax_b.set_xticks(range(10))
    ax_b.set_yticks(range(10))
    ax_b.set_xticklabels(SPECIES_CODES, fontsize=8.8, fontweight="bold")
    ax_b.set_yticklabels(SPECIES_CODES, fontsize=8.8, fontweight="bold")
    ax_b.set_xlabel(r"Especie adyacente en el retículo hexagonal ($j$)", fontsize=9.5, labelpad=8)
    ax_b.set_ylabel(r"Especie en el nodo central focal ($i$)", fontsize=9.5, labelpad=8)
    ax_b.set_title(f"(b) Cadena Espacial de Markov: Transición entre Vecinos Inmediatos\nTasa de Entropía: $H(\\mathcal{{X}})_{{\\text{{opt}}}}^{{\\text{{vec}}}} = {h_vec:.4f}$ bits/transición",
                   fontsize=10.2, fontweight="bold", pad=12, loc="left")

    cbar_b = fig.colorbar(im_b, ax=ax_b, fraction=0.046, pad=0.04)
    cbar_b.set_label("Probabilidad de adyacencia espacial $p_{ij}^{\\text{vec}}$", fontsize=8.8)

    # Anotación al pie de la distribución estacionaria pi
    pi_text = "Vector Estacionario Izquierdo $\\pi$:  " + "  |  ".join(
        [f"{code}: {pi_vec[k]:.3f}" for k, code in enumerate(SPECIES_CODES)]
    )
    fig.text(0.50, 0.02, pi_text, ha="center", fontsize=8.3, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#f5f5f5", edgecolor="#cccccc", lw=0.7))

    out_file = FIG_DIR / "fig3_markov_transicion_heatmaps.png"
    plt.savefig(out_file)
    plt.close()
    print(f"  [OK] Guardada: {out_file}")


# ==============================================================================
# FIGURA 4: MAPA ESPACIAL 2D Y ORDEN DE PLANTACIÓN BOUSTROPHEDON (1 HA)
# ==============================================================================
def generar_figura_4():
    print("-> Generando Figura 4: Mapa Espacial 2D y Orden de Plantación en 1 Hectárea...")
    df_orden = pd.read_csv(OUT_DIR / "orden_plantacion_ejemplo_1ha.csv")

    # Obtener preexistentes de simulación s=1
    means, cov, vars_, stds, mu_tot, std_tot = exp.compute_empirical_parameters()
    rng = np.random.default_rng(1)
    args = exp.SimConfigArgs()
    args.seed = 1
    nu_s = exp.sample_existing_plants(rng, means, cov, vars_)
    spec = tr.spec_from("mixto", width=100.0, height=100.0, slope_deg=6.0, seed=1)
    T = tr.Terrain(spec)
    zone, zinfo = T.zonas(20.0, 0.10)
    ex = T.sample_existing(rng, hg.EXISTING, hg.N_PLANT)
    ex_coh = T.place_cohort(rng, nu_s, hg.EXISTING, hg.N_PLANT, hg.N_BASE_EX, min_sep=3.0)
    ex_nc, _ = pl.apply_removals(T, ex, args)
    ex_o = {k: np.concatenate([ex_nc[k], ex_coh[k]]) for k in ex_nc}

    # Preexistentes estrictamente dentro del predio [0, 100] x [0, 100]
    pos_ex = ex_o["pos"]
    in_bounds = (pos_ex[:, 0] >= 0.0) & (pos_ex[:, 0] <= 100.0) & (pos_ex[:, 1] >= 0.0) & (pos_ex[:, 1] <= 100.0)
    pos_ex_in = pos_ex[in_bounds]

    fig = plt.figure(figsize=(17.5, 8.5), dpi=300)
    gs = GridSpec(1, 2, width_ratios=[1.0, 1.05], wspace=0.22)

    # Mapeo de colores por Etapa Operativa
    color_etapas = {
        "Etapa 1 (Estructural / Nodriza)": COLOR_VERMILION,
        "Etapa 2 (Maguey / Nopal)": COLOR_BLUISH_GREEN,
        "Etapa 3 (Rosetófila Menor)": COLOR_SKY_BLUE
    }

    # -------------------------------------------------------------
    # Panel (a): Hectárea Completa 100m x 100m
    # -------------------------------------------------------------
    ax_a = fig.add_subplot(gs[0, 0])

    # 1. Trayectoria boustrophedon completa conectando los 531 pasos
    x_steps = df_orden["x_m"].values
    y_steps = df_orden["y_m"].values
    ax_a.plot(x_steps, y_steps, color="#666666", linewidth=0.75, linestyle="-", alpha=0.45, zorder=1,
              label="Trayectoria boustrophedon")

    # 2. Plantas preexistentes conservadas in situ
    ax_a.scatter(pos_ex_in[:, 0], pos_ex_in[:, 1], marker="^", s=45, color=COLOR_BLACK,
                 edgecolor="white", linewidth=0.6, zorder=4,
                 label=f"Preexistentes conservadas ($n={len(pos_ex_in)}$)")

    # 3. Nuevas plantas por etapa
    for etapa, color in color_etapas.items():
        subset = df_orden[df_orden["etapa_operativa"] == etapa]
        ax_a.scatter(subset["x_m"], subset["y_m"], s=38, color=color,
                     edgecolor="#222222", linewidth=0.5, alpha=0.90, zorder=3,
                     label=f"{etapa} ($n={len(subset)}$)")

    # 4. Recuadro destacando el área de zoom del panel (b)
    # Sub-parcela [65, 100] x [0, 35] m
    zoom_rect = patches.Rectangle((66.0, 0.5), 33.5, 33.5, linewidth=1.8, edgecolor="#b71c1c",
                                  facecolor="none", linestyle="--", zorder=5)
    ax_a.add_patch(zoom_rect)
    ax_a.text(67.5, 32.0, "Detalle Sub-parcela (b)", color="#b71c1c", fontsize=8.5, fontweight="bold",
              bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#b71c1c", lw=0.6), zorder=6)

    # Elementos cartográficos: escala métrica y norte
    ax_a.plot([10, 30], [6, 6], color=COLOR_BLACK, linewidth=3.0, zorder=6)
    ax_a.text(20, 8.5, "20 m", ha="center", fontsize=8.0, fontweight="bold")
    ax_a.annotate("N", xy=(92, 92), xytext=(92, 85),
                  arrowprops=dict(facecolor=COLOR_BLACK, width=1.8, headwidth=6),
                  ha="center", va="center", fontsize=10, fontweight="bold")

    ax_a.set_xlim(0, 100)
    ax_a.set_ylim(0, 100)
    ax_a.set_aspect("equal")
    ax_a.set_xlabel("Coordenada Este X (metros)", fontsize=9.5, labelpad=6)
    ax_a.set_ylabel("Coordenada Norte Y (metros)", fontsize=9.5, labelpad=6)
    ax_a.grid(True, linestyle=":", alpha=0.40, linewidth=0.6)
    ax_a.legend(loc="upper left", frameon=True, framealpha=0.92, facecolor="white", fontsize=7.8)
    ax_a.set_title("(a) Distribución Espacial en 1 Hectárea Completa ($100\\times 100\\text{ m}$, Pendiente $6^\\circ$)\n531 Plantas Nuevas en Malla Triangular Regular ($d = 4.19\\text{ m}$)",
                   fontsize=10.0, fontweight="bold", pad=10, loc="left")

    # -------------------------------------------------------------
    # Panel (b): Zoom Detallado de Sub-parcela (Primeros 35 pasos de plantación)
    # -------------------------------------------------------------
    ax_b = fig.add_subplot(gs[0, 1])
    first35 = df_orden[df_orden["paso"] <= 35].copy()

    # Preexistentes dentro del zoom
    zoom_in_ex = (pos_ex[:, 0] >= 66.0) & (pos_ex[:, 0] <= 100.0) & (pos_ex[:, 1] >= 0.5) & (pos_ex[:, 1] <= 34.0)
    pos_zoom_ex = pos_ex[zoom_in_ex]
    ax_b.scatter(pos_zoom_ex[:, 0], pos_zoom_ex[:, 1], marker="^", s=80, color=COLOR_BLACK,
                 edgecolor="white", linewidth=0.8, zorder=4, label="Nativa preexistente in situ")

    # Flechas dirigidas conectando los pasos 1 -> 2 -> ... -> 35
    for k in range(len(first35) - 1):
        x1, y1 = first35.iloc[k]["x_m"], first35.iloc[k]["y_m"]
        x2, y2 = first35.iloc[k + 1]["x_m"], first35.iloc[k + 1]["y_m"]
        dx, dy = x2 - x1, y2 - y1
        dist = np.hypot(dx, dy)
        if dist > 0.1:
            # Acortar la flecha para que no tape los círculos de nodo
            frac_start = 1.1 / dist
            frac_end = 1.1 / dist
            xs = x1 + dx * frac_start
            ys = y1 + dy * frac_start
            xe = x2 - dx * frac_end
            ye = y2 - dy * frac_end
            ax_b.annotate("", xy=(xe, ye), xytext=(xs, ys),
                          arrowprops=dict(arrowstyle="->,head_length=0.4,head_width=0.25",
                                          color="#444444", lw=1.1, linestyle="-"),
                          zorder=2)

    # Nodos y etiquetas con ubicación óptima de clearance para evitar encimados
    all_xy_first35 = first35[["x_m", "y_m"]].values
    angles_cand = np.radians([90, 270, 0, 180, 45, 135, 225, 315])

    for idx, row in first35.iterrows():
        p_num = int(row["paso"])
        sp_code = row["codigo_especie"]
        etapa = row["etapa_operativa"]
        col = color_etapas[etapa]
        x, y = row["x_m"], row["y_m"]

        # Círculo del nodo
        ax_b.scatter(x, y, s=170, color=col, edgecolor="#111111", linewidth=0.9, zorder=3)

        # Buscar el ángulo que maximice la distancia a todos los demás nodos
        best_ang = angles_cand[0]
        max_min_d = -1.0
        offset_dist = 1.45
        for ang in angles_cand:
            cx = x + offset_dist * np.cos(ang)
            cy = y + offset_dist * np.sin(ang)
            mask = np.ones(len(all_xy_first35), dtype=bool)
            mask[idx] = False
            min_d = np.min(np.hypot(all_xy_first35[mask, 0] - cx, all_xy_first35[mask, 1] - cy))
            if min_d > max_min_d:
                max_min_d = min_d
                best_ang = ang

        lx = x + offset_dist * np.cos(best_ang)
        ly = y + offset_dist * np.sin(best_ang)

        ax_b.text(lx, ly, f"{p_num}: {sp_code}", ha="center", va="center", fontsize=6.8,
                  fontweight="bold", color="#111111",
                  bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="#888888", lw=0.45, alpha=0.92),
                  zorder=5)

    ax_b.set_xlim(65.0, 100.5)
    ax_b.set_ylim(0.0, 35.0)
    ax_b.set_aspect("equal")
    ax_b.set_xlabel("Coordenada Este X (metros)", fontsize=9.5, labelpad=6)
    ax_b.set_ylabel("Coordenada Norte Y (metros)", fontsize=9.5, labelpad=6)
    ax_b.grid(True, linestyle=":", alpha=0.40, linewidth=0.6)

    # Leyenda personalizada con etapas
    custom_handles = [
        patches.Patch(facecolor=COLOR_VERMILION, edgecolor="#111111", label="Etapa 1: Dosel / Submalla 3 (PL, YF, OS)"),
        patches.Patch(facecolor=COLOR_BLUISH_GREEN, edgecolor="#111111", label="Etapa 2: Nodrizas / Intermedias (OR, OC, OE, AS)"),
        patches.Patch(facecolor=COLOR_SKY_BLUE, edgecolor="#111111", label="Etapa 3: Rosetófilas litológicas (AL, AC, AT)"),
        plt.Line2D([0], [0], marker="^", color="w", markerfacecolor=COLOR_BLACK, markeredgecolor="w", markersize=9, label="Preexistente conservada in situ"),
        plt.Line2D([0], [0], color="#444444", lw=1.2, label=r"Dirección de siembra $k \to k+1$")
    ]
    ax_b.legend(handles=custom_handles, loc="upper left", frameon=True, framealpha=0.92, facecolor="white", fontsize=7.8)
    ax_b.set_title("(b) Detalle Ampliado de Sub-parcela ($35\\times 35\\text{ m}$)\nOrden Secuencial Exacto en Campo: Pasos 1 a 35",
                   fontsize=10.0, fontweight="bold", pad=10, loc="left")

    out_file = FIG_DIR / "fig4_orden_plantacion_mapa_1ha.png"
    plt.savefig(out_file)
    plt.close()
    print(f"  [OK] Guardada: {out_file}")


def main():
    print("=" * 85)
    print("GENERANDO LAS 4 FIGURAS CIENTÍFICAS DE NIVEL PUBLICACIÓN (300 DPI)")
    print("=" * 85)
    generar_figura_1()
    generar_figura_2()
    generar_figura_3()
    generar_figura_4()
    print("\n" + "=" * 85)
    print("TODAS LAS FIGURAS GENERADAS EXITOSAMENTE EN:")
    print(f"  {FIG_DIR}")
    print("=" * 85)


if __name__ == "__main__":
    main()
