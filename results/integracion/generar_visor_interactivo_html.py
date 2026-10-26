#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
REFORESTATHÓN 2026 — GENERADOR DE VISOR INTERACTIVO HTML5 (MALLAS COMPLETAS)
===============================================================================
Este script lee 'datos_mallas_completas_visor.json' y genera un visor web interactivo
100% autocontenido (offline, cero CDNs ni dependencias externas) en:
'visor_interactivo_malla_completa.html'

Características principales del visor:
1. Renderizado en HTML5 Canvas 2D de alto rendimiento (60 FPS, soporte Retina/DPI).
2. Selector de vista para alternar instantáneamente entre:
   - 1 ha — H1 (Valle con Ei, 658 pl)
   - 1 ha — H2 (Ladera >=20%, 524 pl)
   - 1 ha — H3 (Pol. 29 Ei=0, 658 pl)
   - Polígono Oficial 12 (967 pl, 1.47 ha)
   - Polígono Oficial 29 (4,287 pl, 6.54 ha)
   - Polígono Oficial 19 (3,237 pl, 4.92 ha)
   - Polígono Oficial 31 (4,781 pl, 7.34 ha)
3. Navegación fluida:
   - Zoom con rueda del ratón centrado en cursor + Pan arrastrando.
   - Botón "Ajustar Vista (Reset Zoom)".
   - Atajos de teclado (R, +, -, Flechas, 1-7, E, G, S).
4. Control de capas:
   - Aristas tresbolillo (grafo de contacto hexagonal).
   - Retícula modular de 1 ha (100 m x 100 m).
   - Resaltado de plantas vivas preexistentes (Ei, anillo dorado/halo brillante).
   - Plantas nuevas a comprar/plantar (Nz - Ei).
   - Subred big_index=3 (rombo central en especies grandes).
   - Zonas de pendiente >= 20% (sombreado rojo translúcido H2).
   - Radio de facilitación nodriza (Prosopis laevigata).
5. Filtro interactivo por especie con desglose de vivas, nuevas, totales y %.
6. Tooltip flotante al pasar el cursor (ID nodo, coordenadas (X, Y), especie,
   condición Ei vs nueva, zona topográfica, pertenencia a subred grande).
7. Mini-mapa territorial interactivo con rectángulo de viewport en tiempo real.
8. Escala métrica gráfica dinámica y brújula cartográfica (Norte).
9. Exportación instantánea de captura de pantalla en PNG.
===============================================================================
"""

import sys
import json
import time
from pathlib import Path


def generate_html_viewer(json_data: dict) -> str:
    """Genera el código HTML5 completo con JS y CSS autocontenidos."""
    # Convertimos los datos a JSON string compacto para embeber directamente
    json_str = json.dumps(json_data, ensure_ascii=False, separators=(',', ':'))

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>REFORESTATHÓN 2026 — Visor Cartográfico Interactivo de Mallas Tresbolillo</title>
  <style>
    :root {{
      --bg-dark: #0a0e17;
      --bg-panel: #111827;
      --bg-card: #1f293d;
      --bg-card-hover: #28354f;
      --border-color: #2e3d5b;
      --border-focus: #38bdf8;
      --text-main: #f3f4f6;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --accent-green: #10b981;
      --accent-gold: #f59e0b;
      --accent-cyan: #06b6d4;
      --accent-red: #ef4444;
      --accent-purple: #a855f7;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
    }}

    body {{
      font-family: var(--font-family);
      background-color: var(--bg-dark);
      color: var(--text-main);
      overflow: hidden;
      height: 100vh;
      width: 100vw;
      display: flex;
      flex-direction: column;
    }}

    /* ==========================================================================
       HEADER & SELECTOR DE VISTA
       ========================================================================== */
    header {{
      background: linear-gradient(180deg, #131c2e 0%, #0d1320 100%);
      border-bottom: 1px solid var(--border-color);
      padding: 8px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      z-index: 50;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    }}

    .brand-section {{
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 280px;
    }}

    .brand-icon {{
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 12px rgba(16, 185, 129, 0.4);
    }}

    .brand-title {{
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.5px;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .brand-badge {{
      font-size: 10px;
      background: rgba(16, 185, 129, 0.2);
      border: 1px solid #10b981;
      color: #34d399;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
      text-transform: uppercase;
    }}

    .brand-sub {{
      font-size: 11px;
      color: var(--text-muted);
    }}

    /* Botones de Vista (Pills) */
    .view-selector {{
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(15, 23, 42, 0.6);
      padding: 4px;
      border-radius: 10px;
      border: 1px solid var(--border-color);
      overflow-x: auto;
      max-width: calc(100vw - 640px);
    }}

    .view-btn {{
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      padding: 6px 12px;
      border-radius: 7px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .view-btn:hover {{
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-main);
    }}

    .view-btn.active {{
      background: #1e293b;
      border-color: var(--accent-cyan);
      color: #38bdf8;
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.25);
    }}

    .view-pill-count {{
      font-size: 10px;
      background: rgba(255, 255, 255, 0.1);
      padding: 1px 5px;
      border-radius: 10px;
      color: var(--text-muted);
    }}

    .view-btn.active .view-pill-count {{
      background: rgba(56, 189, 248, 0.2);
      color: #bae6fd;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .btn-action {{
      background: #1e293b;
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 6px 12px;
      border-radius: 7px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }}

    .btn-action:hover {{
      background: #27354f;
      border-color: var(--border-focus);
      color: #fff;
    }}

    .btn-action.primary {{
      background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
      border-color: #38bdf8;
      color: #fff;
    }}

    .btn-action.primary:hover {{
      background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
      box-shadow: 0 0 12px rgba(56, 189, 248, 0.4);
    }}

    /* ==========================================================================
       CONTENEDOR PRINCIPAL
       ========================================================================== */
    .main-container {{
      flex: 1;
      display: flex;
      position: relative;
      overflow: hidden;
    }}

    /* SIDEBAR IZQUIERDA */
    .sidebar {{
      width: 360px;
      background: var(--bg-panel);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      z-index: 20;
      overflow-y: auto;
      box-shadow: 4px 0 16px rgba(0, 0, 0, 0.3);
      transition: transform 0.2s ease;
    }}

    .sidebar.collapsed {{
      transform: translateX(-100%);
      position: absolute;
      height: 100%;
    }}

    .sidebar-section {{
      padding: 14px 16px;
      border-bottom: 1px solid var(--border-color);
    }}

    .sidebar-title {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--text-muted);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    /* Tarjetas de Información */
    .view-info-header {{
      margin-bottom: 8px;
    }}

    .view-info-title {{
      font-size: 15px;
      font-weight: 700;
      color: #fff;
      line-height: 1.3;
    }}

    .view-info-sub {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
      line-height: 1.4;
    }}

    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      margin-top: 10px;
    }}

    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 8px 10px;
    }}

    .kpi-card.highlight-gold {{
      border-left: 3px solid var(--accent-gold);
    }}

    .kpi-card.highlight-green {{
      border-left: 3px solid var(--accent-green);
    }}

    .kpi-card.highlight-cyan {{
      border-left: 3px solid var(--accent-cyan);
    }}

    .kpi-card.highlight-red {{
      border-left: 3px solid var(--accent-red);
    }}

    .kpi-label {{
      font-size: 10px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }}

    .kpi-value {{
      font-size: 16px;
      font-weight: 700;
      color: #fff;
      margin-top: 2px;
    }}

    .kpi-subtext {{
      font-size: 9.5px;
      color: var(--text-dim);
      margin-top: 2px;
    }}

    /* Controles de Capas (Toggles) */
    .toggle-group {{
      display: flex;
      flex-direction: column;
      gap: 7px;
    }}

    .toggle-item {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 8px;
      border-radius: 6px;
      background: rgba(31, 41, 61, 0.4);
      cursor: pointer;
      transition: background 0.15s ease;
    }}

    .toggle-item:hover {{
      background: var(--bg-card);
    }}

    .toggle-label-wrap {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--text-main);
    }}

    .layer-icon {{
      width: 14px;
      height: 14px;
      display: inline-block;
      border-radius: 3px;
    }}

    /* Switch CSS */
    .switch {{
      position: relative;
      display: inline-block;
      width: 32px;
      height: 18px;
    }}

    .switch input {{
      opacity: 0;
      width: 0;
      height: 0;
    }}

    .slider {{
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #334155;
      transition: .2s;
      border-radius: 18px;
    }}

    .slider:before {{
      position: absolute;
      content: "";
      height: 12px;
      width: 12px;
      left: 3px;
      bottom: 3px;
      background-color: white;
      transition: .2s;
      border-radius: 50%;
    }}

    input:checked + .slider {{
      background-color: #0ea5e9;
    }}

    input:checked + .slider:before {{
      transform: translateX(14px);
    }}

    /* Filtro por Especies */
    .species-list {{
      display: flex;
      flex-direction: column;
      gap: 5px;
      max-height: 280px;
      overflow-y: auto;
      padding-right: 4px;
    }}

    .species-item {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 8px;
      border-radius: 6px;
      background: var(--bg-card);
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.12s ease;
    }}

    .species-item:hover {{
      background: var(--bg-card-hover);
      border-color: #3b82f6;
    }}

    .species-item.active {{
      background: #1e3a5f;
      border-color: #38bdf8;
      box-shadow: 0 0 8px rgba(56, 189, 248, 0.3);
    }}

    .species-item.dimmed {{
      opacity: 0.35;
    }}

    .species-left {{
      display: flex;
      align-items: center;
      gap: 8px;
      overflow: hidden;
    }}

    .species-color-dot {{
      width: 11px;
      height: 11px;
      border-radius: 50%;
      flex-shrink: 0;
      box-shadow: 0 0 4px rgba(0, 0, 0, 0.5);
    }}

    .species-name-wrap {{
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .species-sci-name {{
      font-size: 11px;
      font-weight: 600;
      font-style: italic;
      color: #fff;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }}

    .species-tag {{
      font-size: 9px;
      color: var(--text-muted);
    }}

    .species-right {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      flex-shrink: 0;
    }}

    .species-count {{
      font-size: 11px;
      font-weight: 700;
      color: #fff;
    }}

    .species-breakdown {{
      font-size: 9px;
      color: var(--text-muted);
    }}

    .filter-reset-btn {{
      font-size: 10px;
      color: var(--accent-cyan);
      background: none;
      border: none;
      cursor: pointer;
      font-weight: 600;
    }}

    .filter-reset-btn:hover {{
      text-decoration: underline;
    }}

    /* Deslizadores de Ajuste */
    .slider-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
      font-size: 11px;
    }}

    .slider-row span {{
      color: var(--text-muted);
      width: 110px;
    }}

    .slider-row input[type="range"] {{
      flex: 1;
      accent-color: #0ea5e9;
      cursor: pointer;
    }}

    .slider-row val {{
      font-size: 10px;
      color: var(--text-main);
      width: 32px;
      text-align: right;
    }}

    /* ==========================================================================
       CANVAS VIEWPORT Y OVERLAYS
       ========================================================================== */
    .canvas-viewport {{
      flex: 1;
      position: relative;
      background: radial-gradient(circle at center, #111827 0%, #080c14 100%);
      overflow: hidden;
    }}

    #mainCanvas {{
      display: block;
      width: 100%;
      height: 100%;
      cursor: grab;
    }}

    #mainCanvas:active {{
      cursor: grabbing;
    }}

    /* Mini-Mapa en esquina superior derecha */
    .minimap-panel {{
      position: absolute;
      top: 14px;
      right: 14px;
      background: rgba(17, 24, 39, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 8px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
      z-index: 10;
    }}

    .minimap-title {{
      font-size: 9px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: var(--text-muted);
      width: 100%;
      display: flex;
      justify-content: space-between;
    }}

    #miniCanvas {{
      background: #0a0e17;
      border-radius: 4px;
      border: 1px solid #1f293d;
      display: block;
    }}

    /* Brújula Cartográfica */
    .compass-rose {{
      position: absolute;
      top: 170px;
      right: 20px;
      width: 38px;
      height: 38px;
      background: rgba(17, 24, 39, 0.8);
      border: 1px solid var(--border-color);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      z-index: 10;
      pointer-events: none;
    }}

    .compass-arrow {{
      width: 0;
      height: 0;
      border-left: 6px solid transparent;
      border-right: 6px solid transparent;
      border-bottom: 16px solid #ef4444;
      position: relative;
    }}

    .compass-arrow:after {{
      content: "";
      position: absolute;
      top: 16px;
      left: -6px;
      width: 0;
      height: 0;
      border-left: 6px solid transparent;
      border-right: 6px solid transparent;
      border-top: 16px solid #94a3b8;
    }}

    .compass-label {{
      position: absolute;
      top: -12px;
      left: 50%;
      transform: translateX(-50%);
      font-size: 9px;
      font-weight: 800;
      color: #ef4444;
    }}

    /* HUD Inferior: Coordenadas y Escala */
    .hud-bottom-bar {{
      position: absolute;
      bottom: 14px;
      left: 14px;
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(17, 24, 39, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 6px 12px;
      z-index: 10;
      font-size: 11px;
      color: var(--text-muted);
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }}

    .coord-item {{
      display: flex;
      align-items: center;
      gap: 4px;
    }}

    .coord-item b {{
      color: var(--accent-cyan);
      font-family: monospace;
    }}

    .hud-divider {{
      width: 1px;
      height: 14px;
      background: var(--border-color);
    }}

    /* Barra de Escala Métrica Gráfica */
    .scale-bar-container {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
    }}

    .scale-bar-visual {{
      height: 4px;
      background: #fff;
      border-left: 2px solid #fff;
      border-right: 2px solid #fff;
      position: relative;
    }}

    .scale-bar-label {{
      font-size: 9.5px;
      font-weight: 600;
      color: #fff;
      font-family: monospace;
    }}

    /* Controles de Zoom Flotantes */
    .floating-zoom-controls {{
      position: absolute;
      bottom: 14px;
      right: 14px;
      display: flex;
      align-items: center;
      gap: 4px;
      background: rgba(17, 24, 39, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 4px;
      z-index: 10;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }}

    .zoom-btn {{
      background: #1f293d;
      border: 1px solid var(--border-color);
      color: var(--text-main);
      width: 28px;
      height: 28px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.12s ease;
    }}

    .zoom-btn:hover {{
      background: #28354f;
      border-color: var(--accent-cyan);
      color: #fff;
    }}

    .zoom-btn-label {{
      font-size: 11px;
      color: var(--text-muted);
      padding: 0 6px;
      font-family: monospace;
    }}

    /* ==========================================================================
       TOOLTIP FLOTANTE INTERACTIVO
       ========================================================================== */
    .node-tooltip {{
      position: absolute;
      pointer-events: none;
      background: rgba(15, 23, 42, 0.95);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-focus);
      border-radius: 10px;
      padding: 12px 14px;
      min-width: 260px;
      max-width: 320px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6), 0 0 12px rgba(56, 189, 248, 0.25);
      z-index: 100;
      display: none;
      transform: translate(14px, 14px);
      transition: opacity 0.1s ease;
    }}

    .tooltip-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 8px;
      margin-bottom: 8px;
    }}

    .tooltip-node-id {{
      font-size: 12px;
      font-weight: 700;
      color: #38bdf8;
      font-family: monospace;
    }}

    .tooltip-species-title {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }}

    .tooltip-color-swatch {{
      width: 14px;
      height: 14px;
      border-radius: 50%;
      border: 2px solid #fff;
      box-shadow: 0 0 6px rgba(0, 0, 0, 0.5);
    }}

    .tooltip-species-name {{
      font-size: 13px;
      font-weight: 700;
      font-style: italic;
      color: #fff;
    }}

    .tooltip-species-note {{
      font-size: 10px;
      color: var(--accent-gold);
      font-weight: 600;
      margin-left: 22px;
      margin-bottom: 8px;
    }}

    .tooltip-data-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 5px;
      font-size: 11px;
    }}

    .tooltip-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 2px 0;
    }}

    .tooltip-row-label {{
      color: var(--text-muted);
    }}

    .tooltip-row-val {{
      font-weight: 600;
      color: #fff;
    }}

    .badge-status {{
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 9.5px;
      font-weight: 700;
      text-transform: uppercase;
    }}

    .badge-status.viva {{
      background: rgba(245, 158, 11, 0.2);
      border: 1px solid #f59e0b;
      color: #fbbf24;
    }}

    .badge-status.nueva {{
      background: rgba(16, 185, 129, 0.2);
      border: 1px solid #10b981;
      color: #34d399;
    }}

    .badge-status.steep {{
      background: rgba(239, 68, 68, 0.2);
      border: 1px solid #ef4444;
      color: #f87171;
    }}

    .badge-status.flat {{
      background: rgba(56, 189, 248, 0.2);
      border: 1px solid #38bdf8;
      color: #7dd3fc;
    }}

    .badge-status.big {{
      background: rgba(168, 85, 247, 0.2);
      border: 1px solid #a855f7;
      color: #c084fc;
    }}

    /* Modal de Ayuda y Atajos */
    .modal-overlay {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      z-index: 200;
      display: none;
      align-items: center;
      justify-content: center;
    }}

    .modal-card {{
      background: var(--bg-panel);
      border: 1px solid var(--border-focus);
      border-radius: 12px;
      width: 480px;
      max-width: 90vw;
      padding: 20px;
      box-shadow: 0 12px 36px rgba(0, 0, 0, 0.8);
    }}

    .modal-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 10px;
      margin-bottom: 14px;
    }}

    .modal-title {{
      font-size: 15px;
      font-weight: 700;
      color: #fff;
    }}

    .modal-close {{
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 18px;
      cursor: pointer;
    }}

    .shortcut-list {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      font-size: 12px;
    }}

    .shortcut-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 4px 0;
    }}

    kbd {{
      background: #1e293b;
      border: 1px solid var(--border-color);
      border-radius: 4px;
      padding: 2px 7px;
      font-family: monospace;
      font-size: 11px;
      color: #38bdf8;
      box-shadow: 0 1px 2px rgba(0,0,0,0.4);
    }}

    /* Animación de pulso para nodo hovered */
    @keyframes pulse-ring {{
      0% {{ transform: scale(0.95); opacity: 0.8; }}
      50% {{ transform: scale(1.4); opacity: 0.4; }}
      100% {{ transform: scale(0.95); opacity: 0.8; }}
    }}
  </style>
</head>
<body>

  <!-- =========================================================================
       BARRA SUPERIOR DE NAVEGACIÓN Y SELECTOR DE VISTAS
       ========================================================================= -->
  <header>
    <div class="brand-section">
      <div class="brand-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/>
          <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
        </svg>
      </div>
      <div>
        <div class="brand-title">
          REFORESTATHÓN 2026
          <span class="brand-badge">Mallas 100% Reales</span>
        </div>
        <div class="brand-sub">Visor Cartográfico Interactivo de Tresbolillo Hexagonal</div>
      </div>
    </div>

    <!-- Selector de Vistas -->
    <div class="view-selector" id="viewSelector">
      <!-- Los botones de vista se generan dinámicamente con JS -->
    </div>

    <!-- Acciones Rápidas -->
    <div class="header-actions">
      <button class="btn-action primary" id="btnFitBounds" title="Ajustar y centrar la vista (Tecla R)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>
        </svg>
        Ajustar Vista
      </button>

      <button class="btn-action" id="btnExportPng" title="Exportar captura en PNG de alta resolución">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
          <circle cx="12" cy="13" r="4"/>
        </svg>
        Captura PNG
      </button>

      <button class="btn-action" id="btnHelp" title="Atajos de teclado y ayuda">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        Ayuda
      </button>
    </div>
  </header>

  <!-- =========================================================================
       CONTENIDO PRINCIPAL: SIDEBAR + CANVAS VIEWPORT
       ========================================================================= -->
  <div class="main-container">
    
    <!-- PANEL LATERAL DE CONTROL -->
    <aside class="sidebar" id="sidebar">
      
      <!-- Información del Polígono / Bloque Activo -->
      <div class="sidebar-section">
        <div class="view-info-header">
          <div class="view-info-title" id="lblViewTitle">Cargando vista...</div>
          <div class="view-info-sub" id="lblViewSubtitle">...</div>
        </div>

        <!-- Indicadores Clave (KPIs) -->
        <div class="kpi-grid">
          <div class="kpi-card highlight-cyan">
            <div class="kpi-label">Plantas Totales</div>
            <div class="kpi-value" id="kpiTotalNodes">0</div>
            <div class="kpi-subtext" id="kpiAreaHa">0.00 ha</div>
          </div>
          <div class="kpi-card highlight-gold">
            <div class="kpi-label">Vivas Ei (Dorado)</div>
            <div class="kpi-value" id="kpiFixedEi">0</div>
            <div class="kpi-subtext" id="kpiFixedPct">0.0% preexistentes</div>
          </div>
          <div class="kpi-card highlight-green">
            <div class="kpi-label">Nuevas a Plantar</div>
            <div class="kpi-value" id="kpiNewPlants">0</div>
            <div class="kpi-subtext" id="kpiNewPct">0.0% inversión</div>
          </div>
          <div class="kpi-card highlight-red">
            <div class="kpi-label">Ladera ≥ 20% (H2)</div>
            <div class="kpi-value" id="kpiSteepCount">0</div>
            <div class="kpi-subtext" id="kpiSteepStep">Paso d = 4.69 m</div>
          </div>
        </div>
      </div>

      <!-- Control de Capas de Visualización -->
      <div class="sidebar-section">
        <div class="sidebar-title">
          <span>Capas de Cartografía</span>
          <span style="font-size:9.5px;color:var(--text-dim);">En vivo</span>
        </div>

        <div class="toggle-group">
          <!-- Capa: Aristas Tresbolillo -->
          <label class="toggle-item">
            <div class="toggle-label-wrap">
              <span class="layer-icon" style="background:#38bdf8;"></span>
              <span>Aristas Tresbolillo (Red Hexagonal)</span>
            </div>
            <label class="switch">
              <input type="checkbox" id="chkEdges" checked>
              <span class="slider"></span>
            </label>
          </label>

          <!-- Capa: Retícula Modular 1 ha (100 m x 100 m) -->
          <label class="toggle-item">
            <div class="toggle-label-wrap">
              <span class="layer-icon" style="background:#94a3b8; border:1px dashed #fff;"></span>
              <span>Retícula Modular 1 ha (100m × 100m)</span>
            </div>
            <label class="switch">
              <input type="checkbox" id="chkGrid" checked>
              <span class="slider"></span>
            </label>
          </label>

          <!-- Capa: Resaltar Plantas Vivas Preexistentes (Ei) -->
          <label class="toggle-item">
            <div class="toggle-label-wrap">
              <span class="layer-icon" style="background:#f59e0b; box-shadow:0 0 6px #f59e0b;"></span>
              <span>Resaltar Vivas Preexistentes (Ei)</span>
            </div>
            <label class="switch">
              <input type="checkbox" id="chkEiHighlight" checked>
              <span class="slider"></span>
            </label>
          </label>

          <!-- Capa: Mostrar Plantas Nuevas -->
          <label class="toggle-item">
            <div class="toggle-label-wrap">
              <span class="layer-icon" style="background:#10b981;"></span>
              <span>Mostrar Plantas Nuevas (Nz - Ei)</span>
            </div>
            <label class="switch">
              <input type="checkbox" id="chkNewPlants" checked>
              <span class="slider"></span>
            </label>
          </label>

          <!-- Capa: Resaltar Subred Especies Grandes (big_index=3) -->
          <label class="toggle-item">
            <div class="toggle-label-wrap">
              <span class="layer-icon" style="background:#a855f7;"></span>
              <span>Resaltar Subred big_index=3 (Rombo)</span>
            </div>
            <label class="switch">
              <input type="checkbox" id="chkBigSublattice" checked>
              <span class="slider"></span>
            </label>
          </label>

          <!-- Capa: Zonas de Pendiente >= 20% (Mancha roja H2) -->
          <label class="toggle-item">
            <div class="toggle-label-wrap">
              <span class="layer-icon" style="background:rgba(239, 68, 68, 0.7);"></span>
              <span>Zonas de Ladera ≥ 20% (H2)</span>
            </div>
            <label class="switch">
              <input type="checkbox" id="chkSteepZones" checked>
              <span class="slider"></span>
            </label>
          </label>

          <!-- Capa: Halo de Facilitación Nodriza (Prosopis) -->
          <label class="toggle-item">
            <div class="toggle-label-wrap">
              <span class="layer-icon" style="background:#7f3b08; border-radius:50%;"></span>
              <span>Radio Facilitación Nodriza (P. laevigata)</span>
            </div>
            <label class="switch">
              <input type="checkbox" id="chkNurseHalo">
              <span class="slider"></span>
            </label>
          </label>

          <!-- Capa: Etiquetas P01-P31 en Parque Unido -->
          <label class="toggle-item">
            <div class="toggle-label-wrap">
              <span class="layer-icon" style="background:#0284c7; border:1px solid #38bdf8;"></span>
              <span>Etiquetas P01–P31 (Clic para abrir polígono)</span>
            </div>
            <label class="switch">
              <input type="checkbox" id="chkPolyLabels" checked>
              <span class="slider"></span>
            </label>
          </label>
        </div>
      </div>

      <!-- Filtro y Desglose por Especie -->
      <div class="sidebar-section" style="flex:1;">
        <div class="sidebar-title">
          <span>Especies Seleccionadas (10)</span>
          <button class="filter-reset-btn" id="btnResetFilter" title="Deseleccionar filtro">Mostrar Todas</button>
        </div>
        <div class="species-list" id="speciesListContainer">
          <!-- Inyectado dinámicamente -->
        </div>
      </div>

      <!-- Ajustes Finos de Renderizado -->
      <div class="sidebar-section">
        <div class="sidebar-title">
          <span>Ajustes de Renderizado</span>
        </div>
        <div class="slider-row">
          <span>Radio de Puntos:</span>
          <input type="range" id="rngPointSize" min="2" max="12" step="0.5" value="4.5">
          <val id="valPointSize">4.5px</val>
        </div>
        <div class="slider-row">
          <span>Opacidad Aristas:</span>
          <input type="range" id="rngEdgeOpacity" min="5" max="100" step="5" value="30">
          <val id="valEdgeOpacity">30%</val>
        </div>
        <div class="slider-row">
          <span>Opacidad Ladera:</span>
          <input type="range" id="rngSteepOpacity" min="5" max="80" step="5" value="35">
          <val id="valSteepOpacity">35%</val>
        </div>
      </div>

    </aside>

    <!-- AREA DEL CANVAS PRINCIPAL -->
    <main class="canvas-viewport" id="viewportContainer">
      <canvas id="mainCanvas"></canvas>

      <!-- Mini-Mapa Contextual -->
      <div class="minimap-panel">
        <div class="minimap-title">
          <span>Mini-Mapa</span>
          <span id="lblMinimapDim">100 × 100 m</span>
        </div>
        <canvas id="miniCanvas" width="130" height="130"></canvas>
      </div>

      <!-- Brújula Cartográfica (Norte) -->
      <div class="compass-rose" title="Orientación Norte Cartográfico">
        <div class="compass-arrow"></div>
        <span class="compass-label">N</span>
      </div>

      <!-- HUD Inferior Izquierdo: Coordenadas y Escala Gráfica -->
      <div class="hud-bottom-bar">
        <div class="coord-item">
          <span>Cursor:</span>
          <b id="hudCoords">X: 0.0 m | Y: 0.0 m</b>
        </div>
        <div class="hud-divider"></div>
        <div class="scale-bar-container">
          <div class="scale-bar-visual" id="hudScaleBarVisual" style="width: 60px;"></div>
          <span class="scale-bar-label" id="hudScaleBarLabel">25 m</span>
        </div>
        <div class="hud-divider"></div>
        <div class="coord-item">
          <span>Zoom:</span>
          <b id="hudZoom">100%</b>
        </div>
        <div class="hud-divider"></div>
        <div class="coord-item">
          <span>Visibles:</span>
          <b id="hudVisibleCount">0</b>
        </div>
      </div>

      <!-- Controles de Zoom Flotantes (Esquina inferior derecha) -->
      <div class="floating-zoom-controls">
        <button class="zoom-btn" id="btnZoomIn" title="Acercar (+)">+</button>
        <button class="zoom-btn" id="btnZoomOut" title="Alejar (-)">−</button>
        <button class="zoom-btn" id="btnZoomReset" title="Ajustar Vista (R)">⟲</button>
      </div>

      <!-- Tooltip Flotante de Planta -->
      <div class="node-tooltip" id="nodeTooltip">
        <div class="tooltip-header">
          <span class="tooltip-node-id" id="ttNodeId">#0000</span>
          <span class="badge-status flat" id="ttTopoBadge">Valle &lt;20%</span>
        </div>
        <div class="tooltip-species-title">
          <span class="tooltip-color-swatch" id="ttColorSwatch"></span>
          <span class="tooltip-species-name" id="ttSpeciesName">Especie</span>
        </div>
        <div class="tooltip-species-note" id="ttSpeciesNote"></div>
        
        <div class="tooltip-data-grid">
          <div class="tooltip-row">
            <span class="tooltip-row-label">Condición:</span>
            <span id="ttConditionBadge" class="badge-status viva">Viva Preexistente (Ei)</span>
          </div>
          <div class="tooltip-row">
            <span class="tooltip-row-label">Coordenadas Locales:</span>
            <span class="tooltip-row-val" id="ttCoords">X: 0.00 m, Y: 0.00 m</span>
          </div>
          <div class="tooltip-row">
            <span class="tooltip-row-label">Subred Especies Grandes:</span>
            <span id="ttBigBadge" class="badge-status big">big_index=3</span>
          </div>
          <div class="tooltip-row">
            <span class="tooltip-row-label">Paso Tresbolillo:</span>
            <span class="tooltip-row-val" id="ttStepD">d = 4.19 m</span>
          </div>
          <div class="tooltip-row">
            <span class="tooltip-row-label">Conexiones Tresbolillo:</span>
            <span class="tooltip-row-val" id="ttDegree" style="color:var(--accent-cyan);">6 vecinos</span>
          </div>
        </div>
      </div>

    </main>
  </div>

  <!-- Modal de Ayuda y Atajos de Teclado -->
  <div class="modal-overlay" id="helpModal">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">Atajos de Teclado y Controles</div>
        <button class="modal-close" id="btnHelpClose">&times;</button>
      </div>
      <div class="shortcut-list">
        <div class="shortcut-row"><span>Arrastrar con Clic Izquierdo</span> <kbd>Pan / Mover Malla</kbd></div>
        <div class="shortcut-row"><span>Rueda del Ratón</span> <kbd>Zoom Centrado en Cursor</kbd></div>
        <div class="shortcut-row"><span>Ajustar Vista / Centrar</span> <kbd>R</kbd></div>
        <div class="shortcut-row"><span>Acercar / Alejar</span> <kbd>+</kbd> / <kbd>−</kbd></div>
        <div class="shortcut-row"><span>Desplazamiento fino</span> <kbd>↑</kbd> <kbd>↓</kbd> <kbd>←</kbd> <kbd>→</kbd></div>
        <div class="shortcut-row"><span>Alternar Aristas Tresbolillo</span> <kbd>E</kbd></div>
        <div class="shortcut-row"><span>Alternar Retícula Modular 1 ha</span> <kbd>G</kbd></div>
        <div class="shortcut-row"><span>Alternar Zonas Pendiente ≥ 20%</span> <kbd>S</kbd></div>
        <div class="shortcut-row"><span>Limpiar Filtro de Especie</span> <kbd>Esc</kbd></div>
        <div class="shortcut-row"><span>Cambiar Vistas Rápidas</span> <kbd>1</kbd> a <kbd>7</kbd></div>
      </div>
    </div>
  </div>

  <!-- =========================================================================
       MOTOR JAVASCRIPT AUTOCONTENIDO (ZERO DEPENDENCIAS EXTERNAS)
       ========================================================================= -->
  <script>
    // --- DATOS EMBEBIDOS DIRECTAMENTE ---
    const VIEWER_DATA = {json_str};

    // --- ENSAMBLAJE DINÁMICO EN MEMORIA DEL MAPA MAESTRO UNIFICADO (31 POLÍGONOS UTM 14N) ---
    function buildUnifiedParkView() {{
      const pm = VIEWER_DATA.park_meta;
      if (!pm) return;
      const eMin = pm.utm_e_min;
      const nMin = pm.utm_n_min;
      const allNodes = [];
      const allEdges = [];
      const allSteepCells = [];
      const allPolygons = [];

      for (let pid = 1; pid <= 31; pid++) {{
        const key = `P${{String(pid).padStart(2, "0")}}`;
        const pv = VIEWER_DATA.views[key];
        if (!pv) continue;
        const dx = (pv.utm_e0 || eMin) - eMin;
        const dy = (pv.utm_n0 || nMin) - nMin;
        const nodeOffset = allNodes.length;

        // Polígono desplazado a marco UTM global relativo y centroide para etiqueta P01..P31
        let cx = 0, cy = 0;
        const shiftedPoly = pv.polygon.map(pt => {{
          const px = Math.round((pt[0] + dx) * 10) / 10;
          const py = Math.round((pt[1] + dy) * 10) / 10;
          cx += px;
          cy += py;
          return [px, py];
        }});
        if (shiftedPoly.length > 0) {{
          cx /= shiftedPoly.length;
          cy /= shiftedPoly.length;
        }}
        allPolygons.push({{
          pid: pid,
          key: key,
          points: shiftedPoly,
          cx: cx,
          cy: cy,
          area_ha: pv.area_ha || 0,
          n_nodes: pv.nodes.length
        }});

        if (pv.steep_cells) {{
          for (let i = 0; i < pv.steep_cells.length; i++) {{
            const c = pv.steep_cells[i];
            allSteepCells.push([c[0] + dx, c[1] + dy, c[2], c[3]]);
          }}
        }}

        for (let i = 0; i < pv.nodes.length; i++) {{
          const n = pv.nodes[i];
          // [x, y, sp_id, is_ei, is_big, is_steep, pid, local_id]
          allNodes.push([
            Math.round((n[0] + dx) * 10) / 10,
            Math.round((n[1] + dy) * 10) / 10,
            n[2],
            n[3],
            n[4],
            n[5],
            pid,
            i
          ]);
        }}

        if (pv.edges) {{
          for (let i = 0; i < pv.edges.length; i++) {{
            const ed = pv.edges[i];
            allEdges.push([ed[0] + nodeOffset, ed[1] + nodeOffset]);
          }}
        }}
      }}

      VIEWER_DATA.views["PARQUE_UNIDO"] = {{
        is_unified: true,
        title: `Mapa Maestro Unificado — 31 Polígonos Oficiales UTM 14N (${{pm.total_area_ha.toFixed(2)}} ha)`,
        subtitle: `Total: ${{allNodes.length.toLocaleString("es-MX")}} plantas (<20% H1 + >=20% H2) | Vivas Ei: ${{pm.total_vivas_Ei.toLocaleString("es-MX")}} (incl. 847 en P29) | Nuevas: ${{pm.total_nuevas.toLocaleString("es-MX")}} | Vivero: $${{pm.total_costo_mxn.toLocaleString("es-MX")}} MXN | Sobrev.: ${{pm.mean_sobrev_pct.toFixed(2)}}%`,
        area_ha: pm.total_area_ha,
        width: pm.width,
        height: pm.height,
        utm_e0: pm.utm_e_min,
        utm_n0: pm.utm_n_min,
        step_d: 4.19,
        polygon: [],
        polygons_list: allPolygons,
        steep_cells: allSteepCells,
        nodes: allNodes,
        edges: allEdges
      }};
    }}
    buildUnifiedParkView();

    // --- ESTADO GLOBAL DE LA APLICACIÓN ---
    const state = {{
      currentViewKey: VIEWER_DATA.views["PARQUE_UNIDO"] ? "PARQUE_UNIDO" : "1ha_H1",
      activeSpeciesFilter: null, // null = todas, o int (0..9)
      scale: 1.0,
      panX: 0,
      panY: 0,
      minScale: 0.1,
      maxScale: 45.0,
      isDragging: false,
      dragStartX: 0,
      dragStartY: 0,
      panStartX: 0,
      panStartY: 0,
      hoveredNode: null,
      mouseScreenX: -1000,
      mouseScreenY: -1000,
      cursorWorldX: 0,
      cursorWorldY: 0,
      // Toggles de capas
      showEdges: true,
      showGrid: true,
      highlightEi: true,
      showNewPlants: true,
      highlightBig: true,
      showSteep: true,
      showNurseHalo: false,
      showPolyLabels: true,
      // Sliders
      pointRadius: 4.5,
      edgeOpacity: 0.30,
      steepOpacity: 0.35,
      needsRender: true,
      dpr: window.devicePixelRatio || 1
    }};

    // Elementos DOM
    const canvas = document.getElementById("mainCanvas");
    const ctx = canvas.getContext("2d");
    const miniCanvas = document.getElementById("miniCanvas");
    const miniCtx = miniCanvas.getContext("2d");
    const container = document.getElementById("viewportContainer");
    const tooltip = document.getElementById("nodeTooltip");

    // Vista activa
    function getView() {{
      return VIEWER_DATA.views[state.currentViewKey];
    }}

    // Precomputar grados de los nodos para la vista activa
    let activeNodeDegrees = new Uint8Array(0);
    function computeNodeDegrees() {{
      const v = getView();
      if (!v) return;
      activeNodeDegrees = new Uint8Array(v.nodes.length);
      if (v.edges) {{
        for (let i = 0; i < v.edges.length; i++) {{
          const u = v.edges[i][0];
          const w = v.edges[i][1];
          if (u < activeNodeDegrees.length) activeNodeDegrees[u]++;
          if (w < activeNodeDegrees.length) activeNodeDegrees[w]++;
        }}
      }}
    }}

    // =========================================================================
    // INICIALIZACIÓN DE LA UI
    // =========================================================================
    function initUI() {{
      const selector = document.getElementById("viewSelector");
      selector.innerHTML = "";

      // 1. Botones principales: PARQUE UNIDO, 1ha_H1, 1ha_H2
      const mainButtons = [
        {{ key: "PARQUE_UNIDO", label: "🌍 PARQUE UNIDO (31 Polígonos — 124,514 pl)" }},
        {{ key: "1ha_H1", label: "📐 1 ha — H1 (Valle <20%, 658 pl)" }},
        {{ key: "1ha_H2", label: "⛰️ 1 ha — H2 (Ladera ≥20%, 524 pl)" }}
      ];
      mainButtons.forEach(item => {{
        if (!VIEWER_DATA.views[item.key]) return;
        const btn = document.createElement("button");
        btn.className = `view-btn ${{item.key === state.currentViewKey ? "active" : ""}}`;
        btn.dataset.key = item.key;
        btn.innerHTML = `<span>${{item.label}}</span>`;
        btn.addEventListener("click", () => switchView(item.key));
        selector.appendChild(btn);
      }});

      // 2. Selector desplegable para los 31 Polígonos Individuales (P01..P31) + Botones Anterior/Siguiente
      const polyWrap = document.createElement("div");
      polyWrap.style.display = "flex";
      polyWrap.style.alignItems = "center";
      polyWrap.style.gap = "4px";
      polyWrap.style.marginLeft = "4px";
      polyWrap.style.paddingLeft = "6px";
      polyWrap.style.borderLeft = "1px solid var(--border-color)";

      const btnPrevPoly = document.createElement("button");
      btnPrevPoly.className = "view-btn";
      btnPrevPoly.style.padding = "5px 8px";
      btnPrevPoly.title = "Polígono anterior ([)";
      btnPrevPoly.textContent = "◀";
      btnPrevPoly.addEventListener("click", () => stepPolygon(-1));

      const polySelect = document.createElement("select");
      polySelect.id = "polyDropdown";
      polySelect.style.background = "#1e293b";
      polySelect.style.color = "#f8fafc";
      polySelect.style.border = "1px solid #38bdf8";
      polySelect.style.borderRadius = "7px";
      polySelect.style.padding = "5px 10px";
      polySelect.style.fontSize = "12px";
      polySelect.style.fontWeight = "600";
      polySelect.style.cursor = "pointer";

      const optPlaceholder = document.createElement("option");
      optPlaceholder.value = "";
      optPlaceholder.textContent = "📍 Ir a Polígono Individual (P01 – P31)...";
      polySelect.appendChild(optPlaceholder);

      for (let pid = 1; pid <= 31; pid++) {{
        const k = `P${{String(pid).padStart(2, "0")}}`;
        const pv = VIEWER_DATA.views[k];
        if (!pv) continue;
        const opt = document.createElement("option");
        opt.value = k;
        const tag29 = pid === 29 ? " ★ Vecinos 28,30,22" : "";
        opt.textContent = `Polígono ${{String(pid).padStart(2, "0")}} (${{pv.area_ha.toFixed(2)}} ha — ${{pv.nodes.length.toLocaleString("es-MX")}} pl)${{tag29}}`;
        polySelect.appendChild(opt);
      }}

      polySelect.addEventListener("change", (e) => {{
        if (e.target.value) {{
          switchView(e.target.value);
        }}
      }});

      const btnNextPoly = document.createElement("button");
      btnNextPoly.className = "view-btn";
      btnNextPoly.style.padding = "5px 8px";
      btnNextPoly.title = "Polígono siguiente (])";
      btnNextPoly.textContent = "▶";
      btnNextPoly.addEventListener("click", () => stepPolygon(1));

      polyWrap.appendChild(btnPrevPoly);
      polyWrap.appendChild(polySelect);
      polyWrap.appendChild(btnNextPoly);
      selector.appendChild(polyWrap);

      // Configurar Sliders
      const rngPointSize = document.getElementById("rngPointSize");
      rngPointSize.addEventListener("input", (e) => {{
        state.pointRadius = parseFloat(e.target.value);
        document.getElementById("valPointSize").textContent = `${{state.pointRadius}}px`;
        requestRender();
      }});

      const rngEdgeOpacity = document.getElementById("rngEdgeOpacity");
      rngEdgeOpacity.addEventListener("input", (e) => {{
        state.edgeOpacity = parseInt(e.target.value) / 100;
        document.getElementById("valEdgeOpacity").textContent = `${{e.target.value}}%`;
        requestRender();
      }});

      const rngSteepOpacity = document.getElementById("rngSteepOpacity");
      rngSteepOpacity.addEventListener("input", (e) => {{
        state.steepOpacity = parseInt(e.target.value) / 100;
        document.getElementById("valSteepOpacity").textContent = `${{e.target.value}}%`;
        requestRender();
      }});

      // Configurar Toggles
      document.getElementById("chkEdges").addEventListener("change", (e) => {{
        state.showEdges = e.target.checked;
        requestRender();
      }});
      document.getElementById("chkGrid").addEventListener("change", (e) => {{
        state.showGrid = e.target.checked;
        requestRender();
      }});
      document.getElementById("chkEiHighlight").addEventListener("change", (e) => {{
        state.highlightEi = e.target.checked;
        requestRender();
      }});
      document.getElementById("chkNewPlants").addEventListener("change", (e) => {{
        state.showNewPlants = e.target.checked;
        requestRender();
      }});
      document.getElementById("chkBigSublattice").addEventListener("change", (e) => {{
        state.highlightBig = e.target.checked;
        requestRender();
      }});
      document.getElementById("chkSteepZones").addEventListener("change", (e) => {{
        state.showSteep = e.target.checked;
        requestRender();
      }});
      document.getElementById("chkNurseHalo").addEventListener("change", (e) => {{
        state.showNurseHalo = e.target.checked;
        requestRender();
      }});
      const chkPolyLabels = document.getElementById("chkPolyLabels");
      if (chkPolyLabels) {{
        chkPolyLabels.addEventListener("change", (e) => {{
          state.showPolyLabels = e.target.checked;
          requestRender();
        }});
      }}

      // Botones de Acción
      document.getElementById("btnFitBounds").addEventListener("click", fitBounds);
      document.getElementById("btnZoomIn").addEventListener("click", () => zoomStep(1.25));
      document.getElementById("btnZoomOut").addEventListener("click", () => zoomStep(0.8));
      document.getElementById("btnZoomReset").addEventListener("click", fitBounds);
      document.getElementById("btnResetFilter").addEventListener("click", () => setSpeciesFilter(null));
      document.getElementById("btnExportPng").addEventListener("click", exportScreenshot);

      // Modal de Ayuda
      const helpModal = document.getElementById("helpModal");
      document.getElementById("btnHelp").addEventListener("click", () => {{
        helpModal.style.display = "flex";
      }});
      document.getElementById("btnHelpClose").addEventListener("click", () => {{
        helpModal.style.display = "none";
      }});
      helpModal.addEventListener("click", (e) => {{
        if (e.target === helpModal) helpModal.style.display = "none";
      }});

      // Atajos de Teclado
      window.addEventListener("keydown", handleKeyDown);

      // Eventos de interacción Canvas
      window.addEventListener("resize", handleResize);
      setupCanvasInteractions();

      // Cargar vista inicial
      switchView(state.currentViewKey, true);
    }}

    function stepPolygon(delta) {{
      let currPid = 0;
      if (state.currentViewKey.startsWith("P") && state.currentViewKey.length === 3) {{
        currPid = parseInt(state.currentViewKey.slice(1)) || 0;
      }}
      let nextPid = currPid + delta;
      if (nextPid < 1) nextPid = 31;
      if (nextPid > 31) nextPid = 1;
      switchView(`P${{String(nextPid).padStart(2, "0")}}`);
    }}

    // =========================================================================
    // CAMBIO DE VISTA ACTIVA
    // =========================================================================
    function switchView(viewKey, isInitial = false) {{
      if (!VIEWER_DATA.views[viewKey]) return;
      state.currentViewKey = viewKey;
      state.activeSpeciesFilter = null;
      state.hoveredNode = null;
      hideTooltip();
      computeNodeDegrees();

      // Actualizar botones de vista y dropdown
      document.querySelectorAll(".view-btn").forEach(btn => {{
        if (btn.dataset.key) {{
          btn.classList.toggle("active", btn.dataset.key === viewKey);
        }}
      }});
      const polyDropdown = document.getElementById("polyDropdown");
      if (polyDropdown) {{
        polyDropdown.value = (viewKey.startsWith("P") && viewKey.length === 3) ? viewKey : "";
      }}

      if (!isInitial) {{
        fitBounds();
      }} else {{
        handleResize();
        fitBounds();
      }}

      updateSidebarInfo();
      buildSpeciesList();
      renderMinimap();
      requestRender();
    }}

    // =========================================================================
    // ACTUALIZACIÓN DE SIDEBAR Y KPIS
    // =========================================================================
    function updateSidebarInfo() {{
      const v = getView();
      document.getElementById("lblViewTitle").textContent = v.title;
      document.getElementById("lblViewSubtitle").textContent = v.subtitle;

      let fixedCount = 0;
      let newCount = 0;
      let steepCount = 0;

      for (let i = 0; i < v.nodes.length; i++) {{
        const n = v.nodes[i];
        if (n[3] === 1) fixedCount++;
        else newCount++;
        if (n[5] === 1) steepCount++;
      }}

      const totalNodes = v.nodes.length;
      const areaHa = v.area_ha ? v.area_ha : (v.width * v.height) / 10000;

      document.getElementById("kpiTotalNodes").textContent = totalNodes.toLocaleString("es-MX");
      document.getElementById("kpiAreaHa").textContent = `${{areaHa.toFixed(2)}} ha (${{v.width.toFixed(0)}}×${{v.height.toFixed(0)}}m)`;
      document.getElementById("kpiFixedEi").textContent = fixedCount.toLocaleString("es-MX");
      document.getElementById("kpiFixedPct").textContent = `${{((fixedCount / (totalNodes || 1)) * 100).toFixed(1)}}% preexistentes`;
      document.getElementById("kpiNewPlants").textContent = newCount.toLocaleString("es-MX");
      document.getElementById("kpiNewPct").textContent = `${{((newCount / (totalNodes || 1)) * 100).toFixed(1)}}% a plantar`;
      document.getElementById("kpiSteepCount").textContent = steepCount.toLocaleString("es-MX");
      document.getElementById("kpiSteepStep").textContent = `Paso d = ${{v.step_d.toFixed(2)}} m`;
    }}

    function buildSpeciesList() {{
      const v = getView();
      const container = document.getElementById("speciesListContainer");
      container.innerHTML = "";

      // Contar plantas por especie
      const totalBySp = new Array(10).fill(0);
      const fixedBySp = new Array(10).fill(0);
      const newBySp = new Array(10).fill(0);

      v.nodes.forEach(n => {{
        const sp = n[2];
        totalBySp[sp]++;
        if (n[3] === 1) fixedBySp[sp]++;
        else newBySp[sp]++;
      }});

      const grandTotal = v.nodes.length || 1;

      VIEWER_DATA.species_names.forEach((name, spId) => {{
        const item = document.createElement("div");
        const isActive = state.activeSpeciesFilter === spId;
        const isDimmed = state.activeSpeciesFilter !== null && !isActive;

        item.className = `species-item ${{isActive ? "active" : ""}} ${{isDimmed ? "dimmed" : ""}}`;
        item.dataset.sp = spId;

        const color = VIEWER_DATA.species_colors[spId];
        const shortName = VIEWER_DATA.species_short[spId];
        const isBig = VIEWER_DATA.big_species_ids.includes(spId);
        const count = totalBySp[spId];
        const pct = ((count / grandTotal) * 100).toFixed(1);

        let tagText = isBig ? "Subred Grande" : "Estándar";
        if (spId === 8) tagText = "Nodriza Catalizadora";

        item.innerHTML = `
          <div class="species-left">
            <span class="species-color-dot" style="background:${{color}};"></span>
            <div class="species-name-wrap">
              <span class="species-sci-name" title="${{name}}">${{shortName}}</span>
              <span class="species-tag">${{tagText}}</span>
            </div>
          </div>
          <div class="species-right">
            <span class="species-count">${{count.toLocaleString("es-MX")}} <small style="font-weight:400;color:var(--text-muted);">(${{pct}}%)</small></span>
            <span class="species-breakdown">Ei: ${{fixedBySp[spId]}} | Nz: ${{newBySp[spId]}}</span>
          </div>
        `;

        item.addEventListener("click", () => {{
          if (state.activeSpeciesFilter === spId) {{
            setSpeciesFilter(null);
          }} else {{
            setSpeciesFilter(spId);
          }}
        }});

        container.appendChild(item);
      }});
    }}

    function setSpeciesFilter(spId) {{
      state.activeSpeciesFilter = spId;
      document.querySelectorAll(".species-item").forEach(el => {{
        const elSp = parseInt(el.dataset.sp);
        const isActive = state.activeSpeciesFilter === elSp;
        const isDimmed = state.activeSpeciesFilter !== null && !isActive;
        el.classList.toggle("active", isActive);
        el.classList.toggle("dimmed", isDimmed);
      }});
      requestRender();
    }}

    // =========================================================================
    // NAVEGACIÓN: FIT BOUNDS, PAN Y ZOOM
    // =========================================================================
    function handleResize() {{
      const rect = container.getBoundingClientRect();
      state.dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(rect.width * state.dpr);
      canvas.height = Math.round(rect.height * state.dpr);
      canvas.style.width = `${{rect.width}}px`;
      canvas.style.height = `${{rect.height}}px`;
      requestRender();
    }}

    function fitBounds() {{
      const v = getView();
      const rect = container.getBoundingClientRect();
      const padding = 45;

      const availW = rect.width - padding * 2;
      const availH = rect.height - padding * 2;

      const scaleX = availW / v.width;
      const scaleY = availH / v.height;
      state.scale = Math.min(scaleX, scaleY);

      // Centrar
      const contentW = v.width * state.scale;
      const contentH = v.height * state.scale;

      state.panX = (rect.width - contentW) / 2;
      state.panY = (rect.height - contentH) / 2;

      requestRender();
    }}

    function zoomStep(factor) {{
      const rect = container.getBoundingClientRect();
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const worldX = (centerX - state.panX) / state.scale;
      const worldY = getView().height - (centerY - state.panY) / state.scale;

      const newScale = Math.min(Math.max(state.scale * factor, state.minScale), state.maxScale);

      state.panX = centerX - worldX * newScale;
      state.panY = centerY - (getView().height - worldY) * newScale;
      state.scale = newScale;

      requestRender();
    }}

    function setupCanvasInteractions() {{
      canvas.addEventListener("mousedown", (e) => {{
        if (e.button !== 0) return;
        state.isDragging = true;
        state.dragStartX = e.clientX;
        state.dragStartY = e.clientY;
        state.panStartX = state.panX;
        state.panStartY = state.panY;
      }});

      window.addEventListener("mousemove", (e) => {{
        const rect = canvas.getBoundingClientRect();
        state.mouseScreenX = e.clientX - rect.left;
        state.mouseScreenY = e.clientY - rect.top;

        if (state.isDragging) {{
          const dx = e.clientX - state.dragStartX;
          const dy = e.clientY - state.dragStartY;
          state.panX = state.panStartX + dx;
          state.panY = state.panStartY + dy;
          hideTooltip();
          requestRender();
          return;
        }}

        // Si el cursor está sobre el canvas, detectar nodo cercano
        if (
          state.mouseScreenX >= 0 && state.mouseScreenX <= rect.width &&
          state.mouseScreenY >= 0 && state.mouseScreenY <= rect.height
        ) {{
          updateCursorWorldCoords();
          checkHoverNode(state.mouseScreenX, state.mouseScreenY);
        }} else {{
          hideTooltip();
        }}
      }});

      window.addEventListener("mouseup", (e) => {{
        const wasDragging = state.isDragging;
        state.isDragging = false;
        if (wasDragging && Math.hypot(e.clientX - state.dragStartX, e.clientY - state.dragStartY) < 5) {{
          const v = getView();
          if (v && v.is_unified && v.polygons_list && state.showPolyLabels) {{
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            for (let p = 0; p < v.polygons_list.length; p++) {{
              const poly = v.polygons_list[p];
              const sx = state.panX + poly.cx * state.scale;
              const sy = state.panY + (v.height - poly.cy) * state.scale;
              if (Math.abs(mx - sx) <= 18 && Math.abs(my - sy) <= 10) {{
                switchView(poly.key);
                return;
              }}
            }}
          }}
        }}
      }});

      canvas.addEventListener("wheel", (e) => {{
        e.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const v = getView();
        const worldX = (mouseX - state.panX) / state.scale;
        const worldY = v.height - (mouseY - state.panY) / state.scale;

        const factor = e.deltaY < 0 ? 1.15 : (1 / 1.15);
        const newScale = Math.min(Math.max(state.scale * factor, state.minScale), state.maxScale);

        state.panX = mouseX - worldX * newScale;
        state.panY = mouseY - (v.height - worldY) * newScale;
        state.scale = newScale;

        hideTooltip();
        requestRender();
      }}, {{ passive: false }});

      canvas.addEventListener("dblclick", (e) => {{
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        const v = getView();

        const worldX = (mouseX - state.panX) / state.scale;
        const worldY = v.height - (mouseY - state.panY) / state.scale;

        const newScale = Math.min(state.scale * 1.8, state.maxScale);
        state.panX = mouseX - worldX * newScale;
        state.panY = mouseY - (v.height - worldY) * newScale;
        state.scale = newScale;

        requestRender();
      }});
    }}

    function updateCursorWorldCoords() {{
      const v = getView();
      state.cursorWorldX = (state.mouseScreenX - state.panX) / state.scale;
      state.cursorWorldY = v.height - (state.mouseScreenY - state.panY) / state.scale;

      const clampedX = Math.max(0, Math.min(v.width, state.cursorWorldX));
      const clampedY = Math.max(0, Math.min(v.height, state.cursorWorldY));

      document.getElementById("hudCoords").textContent = `X: ${{clampedX.toFixed(1)}} m | Y: ${{clampedY.toFixed(1)}} m`;
    }}

    // =========================================================================
    // DETECCIÓN DE HOVER Y TOOLTIP FLOTANTE
    // =========================================================================
    function checkHoverNode(mouseX, mouseY) {{
      const v = getView();
      const hitRadius = Math.max(state.pointRadius + 4, 10);
      let closestNode = null;
      let closestDistSq = hitRadius * hitRadius;

      // Iterar sobre los nodos (para mallas de 4.7k se evalúa en <0.5ms)
      for (let i = 0; i < v.nodes.length; i++) {{
        const n = v.nodes[i];
        // Si hay filtro de especie y este nodo no es de esa especie, ignorar
        if (state.activeSpeciesFilter !== null && n[2] !== state.activeSpeciesFilter) continue;
        if (!state.showNewPlants && n[3] === 0) continue;

        // Proyección pantalla
        const sx = state.panX + n[0] * state.scale;
        const sy = state.panY + (v.height - n[1]) * state.scale;

        const dx = sx - mouseX;
        const dy = sy - mouseY;
        const dsq = dx * dx + dy * dy;

        if (dsq < closestDistSq) {{
          closestDistSq = dsq;
          closestNode = {{ id: i, data: n, sx, sy }};
        }}
      }}

      if (closestNode !== state.hoveredNode) {{
        state.hoveredNode = closestNode;
        if (closestNode) {{
          showTooltip(closestNode);
        }} else {{
          hideTooltip();
        }}
        requestRender();
      }}
    }}

    function showTooltip(item) {{
      const n = item.data;
      const spId = n[2];
      const isEi = n[3] === 1;
      const isBig = n[4] === 1;
      const isSteep = n[5] === 1;
      const v = getView();

      const polyPid = n[6] ? n[6] : (v.pid || null);
      const localNodeId = (n[7] !== undefined) ? n[7] : item.id;
      if (polyPid) {{
        document.getElementById("ttNodeId").textContent = `Polígono P${{String(polyPid).padStart(2, "0")}} • Nodo #${{localNodeId}}`;
      }} else {{
        document.getElementById("ttNodeId").textContent = `Nodo #${{item.id}}`;
      }}
      document.getElementById("ttColorSwatch").style.background = VIEWER_DATA.species_colors[spId];
      document.getElementById("ttSpeciesName").textContent = VIEWER_DATA.species_names[spId];

      let note = VIEWER_DATA.species_short[spId];
      if (spId === 8) note += " — Especie Nodriza Clave";
      else if (isBig) note += " — Especie de Gran Porte";
      document.getElementById("ttSpeciesNote").textContent = note;

      // Badge Topografía
      const ttTopo = document.getElementById("ttTopoBadge");
      if (isSteep) {{
        ttTopo.className = "badge-status steep";
        ttTopo.textContent = "Ladera ≥ 20% (H2)";
      }} else {{
        ttTopo.className = "badge-status flat";
        ttTopo.textContent = "Valle < 20% (H1)";
      }}

      // Condición
      const ttCond = document.getElementById("ttConditionBadge");
      if (isEi) {{
        ttCond.className = "badge-status viva";
        ttCond.textContent = "🌟 Viva Preexistente (Ei)";
      }} else {{
        ttCond.className = "badge-status nueva";
        ttCond.textContent = "🌱 Nueva a Plantar (Nz - Ei)";
      }}

      // Coordenadas
      if (v.utm_e0) {{
        const utmE = (v.utm_e0 + n[0]).toFixed(1);
        const utmN = (v.utm_n0 + n[1]).toFixed(1);
        document.getElementById("ttCoords").textContent = `E:${{utmE}} N:${{utmN}}`;
      }} else {{
        document.getElementById("ttCoords").textContent = `X: ${{n[0].toFixed(2)}} m | Y: ${{n[1].toFixed(2)}} m`;
      }}

      // Subred Grande
      const ttBig = document.getElementById("ttBigBadge");
      if (isBig) {{
        ttBig.className = "badge-status big";
        ttBig.textContent = "💎 Subred big_index=3";
      }} else {{
        ttBig.className = "badge-status flat";
        ttBig.textContent = "⚪ Malla Estándar";
      }}

      document.getElementById("ttStepD").textContent = `d = ${{v.step_d.toFixed(2)}} m`;
      const deg = (activeNodeDegrees && item.id < activeNodeDegrees.length) ? activeNodeDegrees[item.id] : 0;
      document.getElementById("ttDegree").textContent = `${{deg}} vecinos directos`;

      // Posicionamiento inteligente del tooltip
      const rect = container.getBoundingClientRect();
      let left = item.sx + 16;
      let top = item.sy + 16;

      if (left + 300 > rect.width) left = item.sx - 300;
      if (top + 220 > rect.height) top = item.sy - 220;

      tooltip.style.left = `${{Math.max(10, left)}}px`;
      tooltip.style.top = `${{Math.max(10, top)}}px`;
      tooltip.style.display = "block";
    }}

    function hideTooltip() {{
      tooltip.style.display = "none";
      state.hoveredNode = null;
    }}

    // =========================================================================
    // ATAJOS DE TECLADO
    // =========================================================================
    function handleKeyDown(e) {{
      if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;

      const key = e.key.toLowerCase();
      if (key === "r") {{
        fitBounds();
      }} else if (key === "+" || key === "=") {{
        zoomStep(1.25);
      }} else if (key === "-" || key === "_") {{
        zoomStep(0.8);
      }} else if (key === "e") {{
        state.showEdges = !state.showEdges;
        document.getElementById("chkEdges").checked = state.showEdges;
        requestRender();
      }} else if (key === "g") {{
        state.showGrid = !state.showGrid;
        document.getElementById("chkGrid").checked = state.showGrid;
        requestRender();
      }} else if (key === "s") {{
        state.showSteep = !state.showSteep;
        document.getElementById("chkSteepZones").checked = state.showSteep;
        requestRender();
      }} else if (key === "[") {{
        stepPolygon(-1);
      }} else if (key === "]") {{
        stepPolygon(1);
      }} else if (key === "0" || key === "u") {{
        if (VIEWER_DATA.views["PARQUE_UNIDO"]) switchView("PARQUE_UNIDO");
      }} else if (key === "escape") {{
        setSpeciesFilter(null);
        document.getElementById("helpModal").style.display = "none";
      }} else if (key === "arrowleft") {{
        state.panX += 40; requestRender();
      }} else if (key === "arrowright") {{
        state.panX -= 40; requestRender();
      }} else if (key === "arrowup") {{
        state.panY += 40; requestRender();
      }} else if (key === "arrowdown") {{
        state.panY -= 40; requestRender();
      }}
    }}

    // =========================================================================
    // MOTOR DE RENDERIZADO EN CANVAS 2D DE ALTO RENDIMIENTO (60 FPS)
    // =========================================================================
    function requestRender() {{
      state.needsRender = true;
    }}

    function renderLoop() {{
      if (state.needsRender) {{
        state.needsRender = false;
        draw();
      }}
      requestAnimationFrame(renderLoop);
    }}
    requestAnimationFrame(renderLoop);

    function draw() {{
      const v = getView();
      if (!v) return;

      const rect = container.getBoundingClientRect();
      const dpr = state.dpr;

      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.scale(dpr, dpr);

      const w = rect.width;
      const h = rect.height;

      // 1. Fondo elegante oscuro
      ctx.fillStyle = "#0c121e";
      ctx.fillRect(0, 0, w, h);

      // Transformaciones de cámara
      const scale = state.scale;
      const panX = state.panX;
      const panY = state.panY;
      const viewH = v.height;

      // 2. Retícula modular de 1 ha (100 m x 100 m) y cuadrícula métrica
      if (state.showGrid) {{
        drawModularGrid(ctx, v, scale, panX, panY, viewH, w, h);
      }}

      // 3. Zonas con pendiente >= 20% (Mancha roja H2)
      if (state.showSteep && v.steep_cells && v.steep_cells.length > 0) {{
        drawSteepCells(ctx, v.steep_cells, scale, panX, panY, viewH);
      }}

      // 4. Polígono(s) delimitador(es) del terreno
      if (v.polygons_list && v.polygons_list.length > 0) {{
        drawUnifiedPolygons(ctx, v.polygons_list, scale, panX, panY, viewH, false);
      }} else if (v.polygon && v.polygon.length > 0) {{
        drawPolygonBoundary(ctx, v.polygon, scale, panX, panY, viewH);
      }}

      // 5. Aristas Tresbolillo (Grafo hexagonal)
      if (state.showEdges && v.edges && v.edges.length > 0) {{
        drawEdges(ctx, v, scale, panX, panY, viewH, w, h);
      }}

      // 6. Halos de Facilitación Nodriza (Prosopis laevigata)
      if (state.showNurseHalo) {{
        drawNurseHalos(ctx, v, scale, panX, panY, viewH, w, h);
      }}

      // 7. Nodos (Plantas) en capas agrupadas por especie para máxima velocidad
      drawNodes(ctx, v, scale, panX, panY, viewH, w, h);

      // 8. Etiquetas P01..P31 por encima de los nodos en la vista unificada
      if (v.polygons_list && v.polygons_list.length > 0 && state.showPolyLabels) {{
        drawUnifiedPolygons(ctx, v.polygons_list, scale, panX, panY, viewH, true);
      }}

      // 9. Resaltar nodo con Hover
      if (state.hoveredNode) {{
        drawHoverHighlight(ctx, state.hoveredNode);
      }}

      ctx.restore();

      // Actualizar HUD
      updateHudElements();
      renderMinimapViewport();
    }}

    // --- SUB-RUTINAS DE RENDERIZADO CANVAS ---

    function drawModularGrid(ctx, v, scale, panX, panY, viewH, w, h) {{
      ctx.save();
      ctx.strokeStyle = "rgba(71, 85, 105, 0.25)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);

      const stepGrid = (v.is_unified && scale < 0.7) ? 200 : 100;
      const maxX = Math.ceil(v.width / stepGrid) * stepGrid;
      const maxY = Math.ceil(v.height / stepGrid) * stepGrid;

      for (let x = 0; x <= maxX; x += stepGrid) {{
        const sx = panX + x * scale;
        if (sx < -20 || sx > w + 20) continue;
        ctx.beginPath();
        ctx.moveTo(sx, 0);
        ctx.lineTo(sx, h);
        ctx.stroke();

        ctx.fillStyle = "rgba(148, 163, 184, 0.4)";
        ctx.font = "10px monospace";
        ctx.fillText(`${{x}}m`, sx + 4, 14);
      }}

      for (let y = 0; y <= maxY; y += stepGrid) {{
        const sy = panY + (viewH - y) * scale;
        if (sy < -20 || sy > h + 20) continue;
        ctx.beginPath();
        ctx.moveTo(0, sy);
        ctx.lineTo(w, sy);
        ctx.stroke();

        ctx.fillStyle = "rgba(148, 163, 184, 0.4)";
        ctx.font = "10px monospace";
        ctx.fillText(`${{y}}m`, 4, sy - 4);
      }}

      ctx.restore();
    }}

    function drawSteepCells(ctx, cells, scale, panX, panY, viewH) {{
      ctx.save();
      ctx.fillStyle = `rgba(239, 68, 68, ${{state.steepOpacity}})`;
      ctx.strokeStyle = `rgba(239, 68, 68, ${{Math.min(1.0, state.steepOpacity * 1.6)}})`;
      ctx.lineWidth = 1;

      for (let i = 0; i < cells.length; i++) {{
        const c = cells[i];
        const sx = panX + c[0] * scale;
        const sy = panY + (viewH - (c[1] + c[3])) * scale;
        const sw = c[2] * scale;
        const sh = c[3] * scale;
        ctx.fillRect(sx, sy, sw, sh);
        if (scale > 0.8) ctx.strokeRect(sx, sy, sw, sh);
      }}

      ctx.restore();
    }}

    function drawPolygonBoundary(ctx, polygon, scale, panX, panY, viewH) {{
      ctx.save();
      ctx.strokeStyle = "rgba(56, 189, 248, 0.85)";
      ctx.lineWidth = 2;
      ctx.shadowColor = "rgba(56, 189, 248, 0.4)";
      ctx.shadowBlur = 6;

      ctx.beginPath();
      polygon.forEach((pt, i) => {{
        const sx = panX + pt[0] * scale;
        const sy = panY + (viewH - pt[1]) * scale;
        if (i === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      }});
      ctx.closePath();
      ctx.stroke();

      ctx.restore();
    }}

    function drawUnifiedPolygons(ctx, polyList, scale, panX, panY, viewH, labelsOnly) {{
      ctx.save();
      if (!labelsOnly) {{
        for (let p = 0; p < polyList.length; p++) {{
          const poly = polyList[p];
          const isP29 = poly.pid === 29;
          ctx.strokeStyle = isP29 ? "rgba(251, 191, 36, 0.92)" : "rgba(56, 189, 248, 0.80)";
          ctx.lineWidth = isP29 ? 2.4 : 1.7;
          ctx.beginPath();
          for (let i = 0; i < poly.points.length; i++) {{
            const pt = poly.points[i];
            const sx = panX + pt[0] * scale;
            const sy = panY + (viewH - pt[1]) * scale;
            if (i === 0) ctx.moveTo(sx, sy);
            else ctx.lineTo(sx, sy);
          }}
          ctx.closePath();
          ctx.stroke();
        }}
      }} else {{
        ctx.font = "bold 11px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        for (let p = 0; p < polyList.length; p++) {{
          const poly = polyList[p];
          const sx = panX + poly.cx * scale;
          const sy = panY + (viewH - poly.cy) * scale;
          const label = `P${{String(poly.pid).padStart(2, "0")}}`;
          const isP29 = poly.pid === 29;
          const bw = 32, bh = 17;
          ctx.fillStyle = isP29 ? "rgba(180, 83, 9, 0.90)" : "rgba(15, 23, 42, 0.86)";
          ctx.strokeStyle = isP29 ? "#fbbf24" : "#38bdf8";
          ctx.lineWidth = 1.2;
          ctx.fillRect(sx - bw / 2, sy - bh / 2, bw, bh);
          ctx.strokeRect(sx - bw / 2, sy - bh / 2, bw, bh);
          ctx.fillStyle = isP29 ? "#fef3c7" : "#e0f2fe";
          ctx.fillText(label, sx, sy + 0.5);
        }}
      }}
      ctx.restore();
    }}

    function drawEdges(ctx, v, scale, panX, panY, viewH, screenW, screenH) {{
      // En vista unificada muy alejada (scale < 0.65), el paso de 4.19 m mide < 2.7 px;
      // las 355k aristas se activan automáticamente al acercar el zoom para mantener nitidez y 60 FPS
      if (v.is_unified && scale < 0.65) return;

      ctx.save();
      ctx.strokeStyle = `rgba(148, 163, 184, ${{state.edgeOpacity}})`;
      ctx.lineWidth = Math.max(0.6, Math.min(1.5, 0.8 * (scale / 4)));

      const nodes = v.nodes;
      const edges = v.edges;

      ctx.beginPath();
      for (let i = 0; i < edges.length; i++) {{
        const u = edges[i][0];
        const w = edges[i][1];
        const nu = nodes[u];
        const nw = nodes[w];

        const sx1 = panX + nu[0] * scale;
        const sy1 = panY + (viewH - nu[1]) * scale;
        if (sx1 < -30 || sx1 > screenW + 30 || sy1 < -30 || sy1 > screenH + 30) continue;

        const sx2 = panX + nw[0] * scale;
        const sy2 = panY + (viewH - nw[1]) * scale;

        ctx.moveTo(sx1, sy1);
        ctx.lineTo(sx2, sy2);
      }}
      ctx.stroke();
      ctx.restore();
    }}

    function drawNurseHalos(ctx, v, scale, panX, panY, viewH, screenW, screenH) {{
      ctx.save();
      ctx.fillStyle = "rgba(16, 185, 129, 0.12)";
      ctx.strokeStyle = "rgba(16, 185, 129, 0.4)";
      ctx.lineWidth = 1.2;
      const nurseR = 5.0 * scale;

      for (let i = 0; i < v.nodes.length; i++) {{
        const n = v.nodes[i];
        if (n[2] === 8) {{
          const sx = panX + n[0] * scale;
          const sy = panY + (viewH - n[1]) * scale;
          if (sx < -30 || sx > screenW + 30 || sy < -30 || sy > screenH + 30) continue;
          ctx.beginPath();
          ctx.arc(sx, sy, nurseR, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        }}
      }}
      ctx.restore();
    }}

    function drawNodes(ctx, v, scale, panX, panY, viewH, screenW, screenH) {{
      const nodes = v.nodes;
      const baseR = state.pointRadius;
      // Escala adaptativa de radio en vista unificada para que los 124,514 nodos se distingan con nitidez a cualquier zoom
      const effBaseR = v.is_unified ? Math.max(1.35, Math.min(baseR, baseR * (scale / 2.1))) : baseR;
      const useFastRect = effBaseR < 2.25;
      let visibleCount = 0;

      for (let sp = 0; sp < 10; sp++) {{
        const isSpFiltered = state.activeSpeciesFilter !== null && state.activeSpeciesFilter !== sp;
        const color = isSpFiltered ? "rgba(100, 116, 139, 0.18)" : VIEWER_DATA.species_colors[sp];
        const isBigSpecies = VIEWER_DATA.big_species_ids.includes(sp);
        const r = (isBigSpecies ? effBaseR * 1.22 : effBaseR) * (isSpFiltered ? 0.8 : 1.0);

        ctx.fillStyle = color;
        ctx.beginPath();

        for (let i = 0; i < nodes.length; i++) {{
          const n = nodes[i];
          if (n[2] !== sp) continue;
          if (!state.showNewPlants && n[3] === 0) continue;

          const sx = panX + n[0] * scale;
          const sy = panY + (viewH - n[1]) * scale;

          if (sx < -15 || sx > screenW + 15 || sy < -15 || sy > screenH + 15) continue;
          if (!isSpFiltered) visibleCount++;

          if (useFastRect) {{
            ctx.rect(sx - r, sy - r, r * 2, r * 2);
          }} else {{
            ctx.moveTo(sx + r, sy);
            ctx.arc(sx, sy, r, 0, Math.PI * 2);
          }}
        }}
        ctx.fill();
      }}

      // Capa de resaltado de Vivas Preexistentes (Ei, anillo oscuro/dorado distintivo)
      if (state.highlightEi && (!v.is_unified || scale >= 0.85)) {{
        ctx.save();
        ctx.beginPath();
        const ringR = effBaseR * 1.6;
        for (let i = 0; i < nodes.length; i++) {{
          const n = nodes[i];
          if (n[3] !== 1) continue;
          if (state.activeSpeciesFilter !== null && n[2] !== state.activeSpeciesFilter) continue;

          const sx = panX + n[0] * scale;
          const sy = panY + (viewH - n[1]) * scale;
          if (sx < -15 || sx > screenW + 15 || sy < -15 || sy > screenH + 15) continue;

          ctx.moveTo(sx + ringR, sy);
          ctx.arc(sx, sy, ringR, 0, Math.PI * 2);
        }}
        ctx.strokeStyle = "#000000";
        ctx.lineWidth = Math.max(1.8, effBaseR * 0.55);
        ctx.stroke();

        ctx.strokeStyle = "#fbbf24";
        ctx.lineWidth = Math.max(1.1, effBaseR * 0.35);
        ctx.stroke();
        ctx.restore();
      }}

      // Capa de resaltado Subred big_index=3 (Rombo)
      if (state.highlightBig && (!v.is_unified || scale >= 1.15)) {{
        ctx.save();
        ctx.strokeStyle = "rgba(168, 85, 247, 0.85)";
        ctx.lineWidth = 1.3;
        const dSize = effBaseR * 1.8;
        ctx.beginPath();

        for (let i = 0; i < nodes.length; i++) {{
          const n = nodes[i];
          if (n[4] !== 1) continue;
          if (state.activeSpeciesFilter !== null && n[2] !== state.activeSpeciesFilter) continue;

          const sx = panX + n[0] * scale;
          const sy = panY + (viewH - n[1]) * scale;
          if (sx < -15 || sx > screenW + 15 || sy < -15 || sy > screenH + 15) continue;

          ctx.moveTo(sx, sy - dSize);
          ctx.lineTo(sx + dSize, sy);
          ctx.lineTo(sx, sy + dSize);
          ctx.lineTo(sx - dSize, sy);
          ctx.closePath();
        }}
        ctx.stroke();
        ctx.restore();
      }}

      document.getElementById("hudVisibleCount").textContent = visibleCount.toLocaleString("es-MX");
    }}

    function drawHoverHighlight(ctx, hovered) {{
      const sx = hovered.sx;
      const sy = hovered.sy;
      const r = state.pointRadius * 2.2;

      ctx.save();
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(sx - r * 1.6, sy);
      ctx.lineTo(sx + r * 1.6, sy);
      ctx.moveTo(sx, sy - r * 1.6);
      ctx.lineTo(sx, sy + r * 1.6);
      ctx.stroke();

      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 2;
      ctx.shadowColor = "#38bdf8";
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.stroke();

      ctx.restore();
    }}

    // =========================================================================
    // HUD: ESCALA MÉTRICA Y ZOOM
    // =========================================================================
    function updateHudElements() {{
      const zoomPct = Math.round((state.scale / 1.0) * 100);
      document.getElementById("hudZoom").textContent = `${{zoomPct}}%`;

      const targetPx = 80;
      const groundDistMeters = targetPx / state.scale;

      const niceSteps = [1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000];
      let chosenDist = niceSteps[0];
      for (let s of niceSteps) {{
        if (s >= groundDistMeters * 0.7) {{
          chosenDist = s;
          break;
        }}
      }}

      const actualPx = chosenDist * state.scale;
      document.getElementById("hudScaleBarVisual").style.width = `${{Math.round(actualPx)}}px`;
      document.getElementById("hudScaleBarLabel").textContent = `${{chosenDist}} m`;
    }}

    // =========================================================================
    // MINI-MAPA TERRITORIAL
    // =========================================================================
    function renderMinimap() {{
      const v = getView();
      if (!v) return;

      miniCtx.clearRect(0, 0, miniCanvas.width, miniCanvas.height);
      document.getElementById("lblMinimapDim").textContent = `${{v.width.toFixed(0)}} × ${{v.height.toFixed(0)}} m`;

      const mw = miniCanvas.width;
      const mh = miniCanvas.height;
      const pad = 8;

      const availW = mw - pad * 2;
      const availH = mh - pad * 2;
      const mScale = Math.min(availW / v.width, availH / v.height);

      const mPanX = (mw - v.width * mScale) / 2;
      const mPanY = (mh - v.height * mScale) / 2;

      if (v.polygons_list && v.polygons_list.length > 0) {{
        miniCtx.fillStyle = "#1e293b";
        miniCtx.strokeStyle = "#38bdf8";
        miniCtx.lineWidth = 0.8;
        for (let p = 0; p < v.polygons_list.length; p++) {{
          const pts = v.polygons_list[p].points;
          miniCtx.beginPath();
          for (let i = 0; i < pts.length; i++) {{
            const sx = mPanX + pts[i][0] * mScale;
            const sy = mPanY + (v.height - pts[i][1]) * mScale;
            if (i === 0) miniCtx.moveTo(sx, sy);
            else miniCtx.lineTo(sx, sy);
          }}
          miniCtx.closePath();
          miniCtx.fill();
          miniCtx.stroke();
        }}
      }} else if (v.polygon && v.polygon.length > 0) {{
        miniCtx.fillStyle = "#1e293b";
        miniCtx.strokeStyle = "#38bdf8";
        miniCtx.lineWidth = 1;

        miniCtx.beginPath();
        v.polygon.forEach((pt, i) => {{
          const sx = mPanX + pt[0] * mScale;
          const sy = mPanY + (v.height - pt[1]) * mScale;
          if (i === 0) miniCtx.moveTo(sx, sy);
          else miniCtx.lineTo(sx, sy);
        }});
        miniCtx.closePath();
        miniCtx.fill();
        miniCtx.stroke();
      }}

      miniCtx.fillStyle = "rgba(148, 163, 184, 0.55)";
      const stride = Math.max(1, Math.floor(v.nodes.length / 3500));
      for (let i = 0; i < v.nodes.length; i += stride) {{
        const n = v.nodes[i];
        const sx = mPanX + n[0] * mScale;
        const sy = mPanY + (v.height - n[1]) * mScale;
        miniCtx.fillRect(sx, sy, 1.2, 1.2);
      }}
    }}

    function renderMinimapViewport() {{
      // Redibujar rectángulo de vista sobre el mini-mapa
      renderMinimap();

      const v = getView();
      if (!v) return;

      const rect = container.getBoundingClientRect();
      const mw = miniCanvas.width;
      const mh = miniCanvas.height;
      const pad = 8;
      const mScale = Math.min((mw - pad * 2) / v.width, (mh - pad * 2) / v.height);
      const mPanX = (mw - v.width * mScale) / 2;
      const mPanY = (mh - v.height * mScale) / 2;

      // Límites de la cámara en coordenadas del mundo
      const worldX0 = Math.max(0, -state.panX / state.scale);
      const worldX1 = Math.min(v.width, (rect.width - state.panX) / state.scale);
      const worldY1 = Math.min(v.height, v.height - (-state.panY / state.scale));
      const worldY0 = Math.max(0, v.height - ((rect.height - state.panY) / state.scale));

      const vx = mPanX + worldX0 * mScale;
      const vy = mPanY + (v.height - worldY1) * mScale;
      const vw = (worldX1 - worldX0) * mScale;
      const vh = (worldY1 - worldY0) * mScale;

      miniCtx.save();
      miniCtx.strokeStyle = "#ef4444";
      miniCtx.lineWidth = 1.5;
      miniCtx.fillStyle = "rgba(239, 68, 68, 0.15)";
      miniCtx.fillRect(vx, vy, vw, vh);
      miniCtx.strokeRect(vx, vy, vw, vh);
      miniCtx.restore();
    }}

    // =========================================================================
    // EXPORTACIÓN DE CAPTURA PNG DE ALTA RESOLUCIÓN
    // =========================================================================
    function exportScreenshot() {{
      const v = getView();
      const tempLink = document.createElement("a");
      tempLink.download = `captura_malla_${{state.currentViewKey}}.png`;
      tempLink.href = canvas.toDataURL("image/png");
      tempLink.click();
    }}

    // INICIAR AL CARGAR EL DOM
    window.addEventListener("DOMContentLoaded", initUI);
  </script>
</body>
</html>
"""
    return html_content


def main():
    print("=" * 80)
    print("REFORESTATHÓN 2026 — GENERADOR DE VISOR INTERACTIVO HTML5")
    print("=" * 80)

    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / "outputs_presentacion"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "datos_mallas_completas_visor.json"
    html_path = out_dir / "visor_interactivo_malla_completa.html"

    print(f"Ruta esperada del JSON: {json_path}")
    print(f"Ruta objetivo del HTML: {html_path}")

    # Esperar si el proceso GPU todavía está escribiendo el JSON
    max_wait = 240  # hasta 4 minutos
    t_start = time.time()
    while not json_path.exists() or json_path.stat().st_size < 1000:
        elapsed = time.time() - t_start
        if elapsed > max_wait:
            print(f"[ERROR] Tiempo límite agotado esperando '{json_path}'.")
            sys.exit(1)
        print(f"... Esperando generación de JSON ({elapsed:.0f}s transcurridos)...")
        time.sleep(3)

    # Asegurar que el archivo no esté siendo escrito activamente
    time.sleep(1)

    print(f"[OK] Archivo JSON encontrado! Tamaño: {json_path.stat().st_size:,d} bytes ({json_path.stat().st_size / 1024 / 1024:.2f} MB)")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Falló la lectura del archivo JSON: {e}")
        sys.exit(1)

    # Validar campos clave
    assert "species_names" in data, "Falta 'species_names' en JSON"
    assert "views" in data, "Falta 'views' en JSON"
    views = data["views"]
    print(f"Vistas encontradas en el payload ({len(views)}): {list(views.keys())}")

    for k, v in views.items():
        n_nodes = len(v.get("nodes", []))
        n_edges = len(v.get("edges", []))
        print(f"  - Vista '{k}': {n_nodes:,d} plantas | {n_edges:,d} aristas | {v.get('title')}")

    # Generar HTML
    print("\nGenerando documento HTML5 100% autocontenido y optimizado...")
    html_code = generate_html_viewer(data)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_code)

    file_size_kb = html_path.stat().st_size / 1024
    print(f"\n[ÉXITO] Visor interactivo generado correctamente:")
    print(f"  -> Archivo: {html_path}")
    print(f"  -> Tamaño: {file_size_kb:,.1f} KB ({file_size_kb / 1024:.2f} MB)")
    print(f"  -> Offline y cero dependencias CDN externas.")
    print("=" * 80)


if __name__ == "__main__":
    main()
