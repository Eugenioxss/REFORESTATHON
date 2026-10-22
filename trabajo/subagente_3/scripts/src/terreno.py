#!/usr/bin/env python3
"""
terreno.py - Terreno para hexgarden: aleatorio (simulacion) o leido de archivos (mapeo).

Principio de diseno: las entradas NO son independientes.
  altitud -> temperatura (gradiente -6.5 C/km) y algo de lluvia (efecto orografico)
  lluvia / evapotranspiracion -> INDICE DE ARIDEZ (AI = P/PET)
  PET = evapotranspiracion de referencia FAO-56 Penman-Monteith (Allen et al., 1998) con radiacion solar ESTIMADA
        a partir del rango diario de temperatura (Hargreaves-Samani; kRs = 0.16 interior), viento por defecto 2 m/s,
        humedad relativa y altitud; la pendiente x orientacion modifican la radiacion (ver pet_fao56)
  AI local = AI * disponibilidad (profundidad de suelo, humedad topografica TWI, escurrimiento por pendiente)
Capas independientes: relieve, profundidad de suelo (si se mide), pastoreo, polígono.

Formato de carpeta (terreno_dir):
  terreno.json         escalares (ver TerrainSpec); "fila0_es_norte": true si las rejillas vienen con fila 0 al norte
  elevacion.csv|npy    rejilla (ny, nx) en metros s.n.m.            [opcional]
  lluvia.csv|npy       rejilla de lluvia anual en mm                 [opcional]
  temperatura.csv|npy  rejilla de temperatura media anual en C       [opcional]
  suelo_cm.csv|npy     rejilla de profundidad de suelo en cm         [opcional]
  pastoreo.csv|npy     rejilla de presion de pastoreo 0..1           [opcional]
  poligono.csv         vertices x,y (m) del limite del terreno       [opcional, si no hay: rectangulo]
  flora_existente.csv  x,y,tipo[,removible,radio_excl]               [opcional: es "el mapeo"]
Todo lo que falte se simula de forma consistente con los escalares dados.
Todas las rejillas deben tener la misma forma. Para GeoTIFF: exportar a CSV/NPY (no hay lector GeoTIFF).
Los parametros por defecto son PLACEHOLDERS razonables para Altiplano/Mesa Central, no datos medidos.
"""
import argparse
import csv
import json
import math
import os
from dataclasses import dataclass, asdict, fields

import numpy as np
from matplotlib.path import Path

UNITS = ["MDR primario", "MDR secundario", "Pastizal", "Sin vegetacion aparente"]
# flora existente por ha segun unidad ambiental (ver texto: MDR, vegetacion secundaria de MDR, pastizal, sin vegetacion)
DENS = {
    # larrea: sitio Dominica = matorral desertico microfilo (MDM) dominado por Larrea tridentata [guessing: 250/ha; la MIA da 67.8 % MDM en el sistema ambiental]
    0: dict(buffel=20, lenosa=6, arbusto=90, arbol=8, hierba=300, larrea=250),
    1: dict(buffel=200, lenosa=12, arbusto=40, arbol=3, hierba=250, larrea=250),
    2: dict(buffel=600, lenosa=4, arbusto=10, arbol=1, hierba=800, larrea=150),
    3: dict(buffel=20, lenosa=0, arbusto=5, arbol=0, hierba=30, larrea=60),
}
ALIAS = [
    (("buffel", "pennisetum", "cenchrus"), "buffel"),
    (("gobernadora", "larrea"), "larrea"),
    (("lenos", "invasor"), "lenosa"),
    (("mezquite", "prosopis", "arbol", "huizache", "acacia"), "arbol"),
    (("pasto", "zacate", "hierba", "gramin", "navajita", "borreguero"), "hierba"),
    (("arbusto", "matorral", "nopal", "opuntia", "agave", "maguey", "yucca", "palma", "sotol", "dasylirion",
      "cact"), "arbusto"),
]
LAYER_FILES = dict(elev=("elevacion",), rain=("lluvia",), temp=("temperatura",), soil=("suelo_cm",),
                   graze=("pastoreo",))


@dataclass
class TerrainSpec:
    width: float = 150.0          # m (dimension x)
    height: float = 150.0         # m (dimension y)
    cell: float = 3.0             # m (resolucion de rejilla simulada)
    elev_mean: float = 2430.0     # m s.n.m. SITIO DE LOS 31 POLIGONOS (SRTM 30 m, 5 puntos sobre los poligonos: 2410-2456 m, media 2432; poli31/dem_srtm_puntos.csv)
    slope_deg: float = 6.0       # pendiente media (gradiente a 3 m) del relieve local de lomerio, grados [guessing: no hay DEM fino; con 10 deg ~32 % del area de los 31 poligonos queda >= 20 %]
    tilt_deg: float = 1.0         # inclinacion regional (grados)
    rain_mm: float = 420.0        # lluvia anual a elev_mean [likely: isoyetas 400-500 mm, INEGI 2010 Charcas; falta normal SMN]
    rain_cv: float = 0.35         # variabilidad interanual de la lluvia
    orographic: float = 0.04      # fraccion de lluvia extra por cada 100 m de altitud
    temp_mean: float = 16.0       # C a elev_mean [likely: isoterma de 16 C, INEGI 2010]
    tmin_offset: float = -22.0    # minima extrema ~ T media + offset: 16 - 22 = -6 C [guessing; reportes locales -5 a -6.5 C]
    rh: float = 45.0              # humedad relativa media (%)
    pet_modo: str = "fao56"       # fao56 (Penman-Monteith con radiacion estimada) | heuristico (formula casera anterior)
    lat: float = 23.37            # latitud (grados N) del Parque Eolico Dominica, Charcas SLP
    dtr: float = 16.0             # rango diario medio de temperatura (Tmax-Tmin, C) [PLACEHOLDER: medir en el sitio]
    wind: float = 2.0             # viento a 2 m (m/s); 2 m/s es el valor por defecto que sugiere FAO-56 si no hay dato
    t_amp: float = 5.0            # amplitud estacional de la temperatura media mensual (+- C) [PLACEHOLDER]
    t_peak_doy: int = 160         # dia del anio con la temperatura media mas alta (~junio) [PLACEHOLDER]
    k_rs: float = 0.16            # coeficiente de Hargreaves-Samani para Rs (0.16 interior, 0.19 costa; FAO-56 ec. 50)
    pet_ref: float = 1800.0       # evapotranspiracion potencial de referencia (mm/anio) a 17 C, RH 50%
    soil_max_cm: float = 120.0    # profundidad de suelo maxima en fondos de valle
    grazing_mean: float = 0.0     # presion media de pastoreo 0..1 (Dominica: no se encontro pastoreo en la zona de los 31 poligonos)
    n_water_points: int = 2       # abrevaderos/corrales que concentran el pastoreo
    ar_modo: str = "unep-lineal"  # curva | unep | unep-lineal (ver ar_from_ai)
    ai_ref: float = 0.19          # AI "de referencia": aridez efectiva 0.7
    max_slope: float = 35.0       # grados; mas empinado no se planta
    rock_cm: float = 6.0          # suelo mas somero que esto + pendiente => afloramiento rocoso
    seed: int = 0


PRESETS = {
    "valle": dict(slope_deg=2.0, tilt_deg=0.5, soil_max_cm=150.0),
    "mixto": dict(),
    "ladera": dict(slope_deg=18.0, tilt_deg=4.0, soil_max_cm=60.0),
    "arido": dict(rain_mm=220.0, rh=35.0, temp_mean=19.0),
    "humedo": dict(rain_mm=550.0, rh=60.0, temp_mean=15.0, elev_mean=2250.0),
}


def spec_from(preset=None, **kw):
    d = dict(PRESETS.get(preset or "mixto", {}))
    d.update({k: v for k, v in kw.items() if v is not None})
    return TerrainSpec(**d)


def fractal(rng, ny, nx, beta):
    fy = np.fft.fftfreq(ny)[:, None]
    fx = np.fft.rfftfreq(nx)[None, :]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1.0
    amp = f ** (-beta / 2.0)
    amp[0, 0] = 0.0
    ph = rng.normal(size=(ny, nx // 2 + 1)) + 1j * rng.normal(size=(ny, nx // 2 + 1))
    z = np.fft.irfft2(amp * ph, s=(ny, nx))
    return (z - z.mean()) / (z.std() + 1e-12)


def flow_acc(z, cell):
    """Acumulacion de flujo D8 (celdas aportantes)."""
    ny, nx = z.shape
    zz = z.ravel()
    order = np.argsort(zz)[::-1]
    acc = np.ones(ny * nx)
    for idx in order:
        iy, ix = divmod(int(idx), nx)
        best, bs = -1, 0.0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                jy, jx = iy + dy, ix + dx
                if 0 <= jy < ny and 0 <= jx < nx:
                    d = cell * (1.4142 if (dx and dy) else 1.0)
                    s = (zz[idx] - zz[jy * nx + jx]) / d
                    if s > bs:
                        bs, best = s, jy * nx + jx
        if best >= 0:
            acc[best] += acc[idx]
    return acc.reshape(ny, nx)


# ------------------------------------------------------------------------------------------------------------
# CLASES UNEP DEL INDICE DE ARIDEZ  AI = P / PET  (P = lluvia media anual, PET = evapotranspiracion de referencia)
#   Fuente de las clases: UNEP (1997). World Atlas of Desertification (2nd ed.). United Nations Environment Programme.
#   Tabla tal como la reproducen Zomer, R. J., Xu, J., & Trabucco, A. (2022). Version 3 of the Global Aridity Index and
#   Potential Evapotranspiration Database. Scientific Data, 9, Article 409. https://doi.org/10.1038/s41597-022-01493-1
#       hiperarido      AI < 0.03
#       arido           0.03 <= AI < 0.2
#       semiarido       0.2  <= AI < 0.5
#       subhumedo seco  0.5  <= AI < 0.65
#       humedo          AI >= 0.65
#   (El atlas UNEP original no se leyo directamente; las fronteras vienen de la tabla de Zomer et al., 2022.)
#
# INTERPOLACION (modo 'unep-lineal', el que usa el modelo por defecto):
#   La UNEP define CLASES, no un estres de planta. Un valor fijo por clase (modo 'unep') produce escalones: el estres
#   cae de 1.10 a 0.54 al cruzar AI = 0.2, de modo que un cambio de 0.001 en AI cambia el modelo. Para evitarlo:
#     1. A cada clase se le asigna un valor de estres 'ar' en el CENTRO GEOMETRICO de la clase (UNEP_CENTROS).
#     2. Entre centros, ar se interpola linealmente en x = log10(AI) (las fronteras UNEP crecen de forma
#        aproximadamente geometrica: 0.03, 0.2, 0.5, 0.65), y fuera del primer o ultimo centro se mantiene constante.
#        Es decir:  ar(AI) = ar_k + (ar_(k+1) - ar_k) * (log10 AI - log10 c_k) / (log10 c_(k+1) - log10 c_k).
#   OJO: los cinco valores UNEP_AR son PLACEHOLDER. Salen de mi curva anterior 0.7*(0.19/AI)^0.5 evaluada en el
#   centro de cada clase, asi que NO agregan informacion biologica: ninguna fuente asigna un estres de planta a
#   cada clase UNEP. Calibrarlos contra mortalidad observada es lo que falta.
# ------------------------------------------------------------------------------------------------------------
UNEP_LIMITES = (0.03, 0.2, 0.5, 0.65)
UNEP_NOMBRES = ("hiperarido", "arido", "semiarido", "subhumedo seco", "humedo")
UNEP_AR = (1.6, 1.10, 0.54, 0.40, 0.31)                  # PLACEHOLDER (ver arriba)
UNEP_CENTROS = (0.015, 0.0775, 0.316, 0.570, 1.0)        # centros geometricos: sqrt(0.03*0.2)=0.0775, etc.


_DIAS_MES = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
_DOY_MES = np.cumsum(_DIAS_MES) - _DIAS_MES / 2.0         # dia del anio a mitad de cada mes


def _ra_mj(lat, J):
    """Radiacion extraterrestre diaria Ra (MJ m-2 dia-1), FAO-56 ecs. 21-25 (Allen et al., 1998)."""
    phi = math.radians(lat)
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * J / 365.0)
    dec = 0.409 * math.sin(2.0 * math.pi * J / 365.0 - 1.39)
    ws = math.acos(-math.tan(phi) * math.tan(dec))
    return 24.0 * 60.0 / math.pi * 0.0820 * dr * (ws * math.sin(phi) * math.sin(dec) +
                                                    math.cos(phi) * math.cos(dec) * math.sin(ws))


def pet_fao56(T, z, rad, spec):
    """PET anual (mm/anio) por celda con FAO-56 Penman-Monteith y radiacion ESTIMADA.
    Referencia: Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). Crop evapotranspiration: Guidelines for
    computing crop water requirements (FAO Irrigation and Drainage Paper 56). FAO.
    Entradas por celda: T (temperatura media anual, C), z (altitud, m), rad (factor de radiacion por pendiente y
    orientacion, ~0.7-1.4). Escalares del spec: lat, dtr, wind, rh, t_amp, t_peak_doy, k_rs.
    Procedimiento (12 meses, ET0 mensual x dias del mes):
      Tmes = T + t_amp*sin(2*pi*(J - t_peak_doy + 91)/365);  Tmax/Tmin = Tmes +- dtr/2
      Rs  = min(k_rs*sqrt(dtr)*Ra*rad, Rso)         [radiacion estimada, Hargreaves-Samani: FAO-56 ec. 50]
      Rn  = 0.77*Rs - Rnl                            [FAO-56 ecs. 38-40; G = 0]
      ET0 = (0.408*D*Rn + g*900/(T+273)*u2*(es-ea)) / (D + g*(1+0.34*u2))   [FAO-56 ec. 6]
    La pendiente/orientacion se aplican como factor sobre Rs (aproximacion mia: FAO-56 no corrige por pendiente).
    SUPUESTOS que no vienen de datos del sitio: dtr, wind, t_amp, t_peak_doy (ver TerrainSpec)."""
    T = np.asarray(T, float)
    z = np.asarray(z, float)
    e0 = lambda x: 0.6108 * np.exp(17.27 * x / (x + 237.3))
    P_atm = 101.3 * ((293.0 - 0.0065 * z) / 293.0) ** 5.26
    gam = 0.000665 * P_atm
    pet = np.zeros_like(T)
    for J, n in zip(_DOY_MES, _DIAS_MES):
        Tm = T + spec.t_amp * np.sin(2.0 * math.pi * (J - spec.t_peak_doy + 91.0) / 365.0)
        Tx, Tn = Tm + spec.dtr / 2.0, Tm - spec.dtr / 2.0
        Ra = _ra_mj(spec.lat, J)
        Rso = (0.75 + 2e-5 * z) * Ra
        Rs = np.minimum(spec.k_rs * math.sqrt(spec.dtr) * Ra * rad, Rso)
        es = 0.5 * (e0(Tx) + e0(Tn))
        ea = spec.rh / 100.0 * es
        Rnl = 4.903e-9 * 0.5 * ((Tx + 273.16) ** 4 + (Tn + 273.16) ** 4) * (0.34 - 0.14 * np.sqrt(ea)) * \
            (1.35 * np.minimum(Rs / Rso, 1.0) - 0.35)
        Rn = 0.77 * Rs - Rnl
        D = 4098.0 * e0(Tm) / (Tm + 237.3) ** 2
        et0 = (0.408 * D * Rn + gam * 900.0 / (Tm + 273.0) * spec.wind * (es - ea)) / (D + gam * (1.0 + 0.34 * spec.wind))
        pet += np.maximum(et0, 0.0) * n
    return pet


def ar_from_ai(ai, ref=0.19, modo="curva"):
    """Aridez efectiva (la perilla que usa el modelo); mayor = mas seco.
    modo 'curva'      : 0.7*(ref/AI)^0.5 recortada a [0.25, 1.6] (heuristica anterior; 0.7 en AI=ref)
    modo 'unep'       : valor fijo por clase UNEP (escalones: salta en cada limite de clase)
    modo 'unep-lineal': interpolacion lineal en log10(AI) entre los valores de cada clase (sin saltos)"""
    ai = np.maximum(np.asarray(ai, float), 1e-3)
    if modo == "curva":
        return np.clip(0.7 * (ref / ai) ** 0.5, 0.25, 1.6)
    if modo == "unep":
        return np.asarray(UNEP_AR)[np.searchsorted(UNEP_LIMITES, ai, side="right")]
    if modo == "unep-lineal":
        return np.interp(np.log10(ai), np.log10(UNEP_CENTROS), UNEP_AR)
    raise ValueError(f"modo de aridez desconocido: {modo}")


def ai_class(ai):
    return UNEP_NOMBRES[int(np.searchsorted(UNEP_LIMITES, float(ai), side="right"))]


def _poly_area(poly):
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _band_fractal(rng, ny, nx, cell, lmin, lmax, beta):
    """Campo aleatorio de media 0 y desviacion 1 con espectro de potencia ~ f^-beta SOLO entre las longitudes de onda lmin y lmax (m):
    sin energia mas fina que lmin (relieve suave a escala de lomerio) ni mas gruesa que lmax (esa escala la da el plano regional)."""
    fy = np.fft.fftfreq(ny, d=cell)[:, None]
    fx = np.fft.rfftfreq(nx, d=cell)[None, :]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1.0
    amp = f ** (-beta / 2.0)
    amp[(f > 1.0 / lmin) | (f < 1.0 / lmax)] = 0.0
    amp[0, 0] = 0.0
    ph = rng.normal(size=(ny, nx // 2 + 1)) + 1j * rng.normal(size=(ny, nx // 2 + 1))
    z = np.fft.irfft2(amp * ph, s=(ny, nx))
    return (z - z.mean()) / (z.std() + 1e-12)


_SITE_CACHE = {}


class SiteRelief:
    """DEM simulado UNICO del sitio, en el marco UTM 14N de poligonos_utm.csv. Todos los poligonos lo recortan, asi que vecinos comparten ladera.
    z = plano regional ajustado por minimos cuadrados a puntos SRTM 30 m (dem_srtm_puntos.csv; si no hay, plano horizontal a elev_mean)
        + relieve local de lomerio (espectro de potencia limitado a longitudes de onda lmin..lmax) escalado para que la pendiente media
          (gradiente a 3 m) sea slope_deg.
    El plano regional sale con 2.3 % de pendiente hacia el oeste-suroeste (bajada); las pendientes >= 20 % vienen solo del relieve local, cuya
    amplitud (slope_deg) es [guessing]: no hay DEM fino del sitio."""

    def __init__(self, utm_csv, pts_csv=None, slope_deg=8.0, seed=0, cell=3.0, margin=60.0, lmin=40.0, lmax=600.0, beta=2.0, elev_mean=2430.0):
        rows = [(float(r["E_utm14N"]), float(r["N_utm14N"])) for r in csv.DictReader(open(utm_csv, encoding="utf-8"))]
        E = np.array([r[0] for r in rows])
        N = np.array([r[1] for r in rows])
        self.e0, self.n0 = float(E.min()) - margin, float(N.min()) - margin
        self.cell = cell
        nx = int(math.ceil((E.max() + margin - self.e0) / cell))
        ny = int(math.ceil((N.max() + margin - self.n0) / cell))
        self.nx, self.ny = nx, ny
        plane = np.array([0.0, 0.0, elev_mean])           # gE, gN (m/m), z en el centro
        self.ec, self.nc = float(E.mean()), float(N.mean())
        if pts_csv and os.path.exists(pts_csv):
            pr = np.array([[float(r["E_utm14N"]), float(r["N_utm14N"]), float(r["elev_m_srtm30m"])] for r in csv.DictReader(open(pts_csv, encoding="utf-8"))])
            X = np.c_[pr[:, 0] - self.ec, pr[:, 1] - self.nc, np.ones(len(pr))]
            plane = np.linalg.lstsq(X, pr[:, 2], rcond=None)[0]
        self.plane = plane
        ee = self.e0 + (np.arange(nx) + 0.5) * cell
        nn = self.n0 + (np.arange(ny) + 0.5) * cell
        EE, NN = np.meshgrid(ee, nn)
        base = plane[0] * (EE - self.ec) + plane[1] * (NN - self.nc) + plane[2]
        rng = np.random.default_rng(1000 + seed)
        z0 = _band_fractal(rng, ny, nx, cell, lmin, lmax, beta)
        gy, gx = np.gradient(z0, cell, cell)
        k = math.tan(math.radians(slope_deg)) / max(float(np.mean(np.hypot(gx, gy))), 1e-9)
        self.z = base + k * z0
        self.slope_deg = slope_deg

    def sample(self, E, N):
        """Elevacion (bilineal) en coordenadas UTM; arreglos de la misma forma."""
        from scipy.ndimage import map_coordinates
        fx = (np.asarray(E) - self.e0) / self.cell - 0.5
        fy = (np.asarray(N) - self.n0) / self.cell - 0.5
        return map_coordinates(self.z, [fy.ravel(), fx.ravel()], order=1, mode="nearest").reshape(np.shape(E))

    @staticmethod
    def get(utm_csv, pts_csv, slope_deg, seed, elev_mean):
        key = (os.path.abspath(utm_csv), pts_csv, round(slope_deg, 3), seed)
        if key not in _SITE_CACHE:
            _SITE_CACHE[key] = SiteRelief(utm_csv, pts_csv, slope_deg=slope_deg, seed=seed, elev_mean=elev_mean)
        return _SITE_CACHE[key]


class Terrain:
    def __init__(self, spec, layers=None, polygon=None):
        self.spec = spec
        rng = np.random.default_rng(spec.seed)
        layers = dict(layers or {})
        W, H = spec.width, spec.height
        if layers:
            ny, nx = np.asarray(next(iter(layers.values()))).shape
        else:
            nx, ny = int(math.ceil(W / spec.cell)), int(math.ceil(H / spec.cell))
        self.nx, self.ny = nx, ny
        self.cx, self.cy = W / nx, H / ny
        self.layers_given = sorted(layers)
        self.polygon = None if polygon is None else np.asarray(polygon, float)
        xx = (np.arange(nx) + 0.5) * self.cx
        yy = (np.arange(ny) + 0.5) * self.cy
        XX, YY = np.meshgrid(xx, yy)

        # --- relieve
        if "elev" in layers:
            z = np.asarray(layers["elev"], float)
        else:
            z0 = fractal(rng, ny, nx, 3.2)
            g0y, g0x = np.gradient(z0, self.cy, self.cx)
            k = math.tan(math.radians(spec.slope_deg)) / max(float(np.mean(np.hypot(g0x, g0y))), 1e-9)
            z = spec.elev_mean + k * z0
            z = z + math.tan(math.radians(spec.tilt_deg)) * (XX - W / 2.0)
        self.elev = z
        gy, gx = np.gradient(z, self.cy, self.cx)
        srad = np.arctan(np.hypot(gx, gy))
        self.slope = np.degrees(srad)
        self.aspect = np.degrees(np.arctan2(-gx, -gy)) % 360.0     # direccion cuesta abajo desde el norte
        acc = flow_acc(z, 0.5 * (self.cx + self.cy))
        twi = np.log(acc * 0.5 * (self.cx + self.cy) / np.tan(np.maximum(srad, 0.01)))
        self.twi_n = np.clip((twi - twi.mean()) / (twi.std() + 1e-9) / 2.0, -1.0, 1.0)

        # --- clima derivado
        T = np.asarray(layers["temp"], float) if "temp" in layers else \
            spec.temp_mean - 0.0065 * (z - spec.elev_mean)
        P = np.asarray(layers["rain"], float) if "rain" in layers else \
            spec.rain_mm * (1.0 + spec.orographic * (z - spec.elev_mean) / 100.0)
        rad = np.clip(1.0 + 0.6 * np.tan(srad) * (-np.cos(np.radians(self.aspect))), 0.7, 1.4)
        rhf = float(np.clip(1.0 + 0.012 * (50.0 - spec.rh), 0.7, 1.4))
        self.temp, self.rain = T, P
        self.tmin = T + spec.tmin_offset
        if spec.pet_modo == "fao56":
            self.pet = pet_fao56(T, z, rad, spec)
        else:                                  # formula casera anterior (solo para reproducir corridas viejas)
            self.pet = spec.pet_ref * (1.0 + 0.04 * (T - 17.0)) * rhf * rad
        self.ai = np.maximum(P / self.pet, 0.01)

        # --- suelo
        if "soil" in layers:
            soil = np.asarray(layers["soil"], float)
        else:
            base = spec.soil_max_cm * np.exp(-self.slope / 10.0) * (0.5 + 0.25 * (1.0 + self.twi_n))
            soil = np.clip(base * np.exp(0.25 * fractal(rng, ny, nx, 2.0)), 0.0, spec.soil_max_cm)
        self.soil = soil
        self.rock = (soil < spec.rock_cm) & (self.slope > 12.0)

        # --- disponibilidad hidrica efectiva
        wf = (0.55 + 0.45 * np.minimum(1.0, soil / 60.0)) * (1.0 + 0.45 * self.twi_n) * \
             (1.0 - 0.35 * np.minimum(1.0, self.slope / 30.0))
        self.ai_eff = self.ai * np.clip(wf, 0.3, 2.0)
        self.ar = ar_from_ai(self.ai_eff, spec.ai_ref, spec.ar_modo)

        # --- pastoreo
        if "graze" in layers:
            g = np.clip(np.asarray(layers["graze"], float), 0, 1)
        else:
            wp = rng.uniform([0.0, 0.0], [W, H], size=(max(1, spec.n_water_points), 2))
            d = np.min([np.hypot(XX - p[0], YY - p[1]) for p in wp], axis=0)
            g = (0.5 + np.exp(-d / (0.35 * max(W, H)))) * (1.0 - np.minimum(1.0, self.slope / 40.0))
            g = np.clip(g * spec.grazing_mean / max(g.mean(), 1e-9), 0.0, 1.0)
        self.graze = g

        # --- unidad ambiental (del diagnostico del texto)
        bare = (soil < 8.0) | ((g > 0.8) & (self.slope > 10.0))
        pasto = (self.slope < 4.0) & (g > 0.55) & (soil > 40.0)
        sec = g > 0.45
        self.unit = np.select([bare, pasto, sec], [3, 2, 1], default=0)

        # --- poligono
        if self.polygon is not None:
            self._path = Path(self.polygon)
            self.area_ha = _poly_area(self.polygon) / 1e4
        else:
            self._path = None
            self.area_ha = W * H / 1e4
        self.flora = None  # se llena con load_flora()

    # ---------------- consultas
    @property
    def width(self):
        return self.spec.width

    @property
    def height(self):
        return self.spec.height

    def _ij(self, P):
        P = np.asarray(P, float).reshape(-1, 2)
        ix = np.clip((P[:, 0] / self.cx).astype(int), 0, self.nx - 1)
        iy = np.clip((P[:, 1] / self.cy).astype(int), 0, self.ny - 1)
        return iy, ix

    def inside(self, P):
        P = np.asarray(P, float).reshape(-1, 2)
        if self._path is not None:
            return self._path.contains_points(P)
        return (P[:, 0] >= 0) & (P[:, 0] <= self.width) & (P[:, 1] >= 0) & (P[:, 1] <= self.height)

    def ar_at(self, P, factor=1.0):
        iy, ix = self._ij(P)
        return ar_from_ai(self.ai_eff[iy, ix] * factor, self.spec.ai_ref, self.spec.ar_modo)

    def rock_at(self, P):
        """True donde hay roca (suelo < rock_cm en ladera): ahi no puede haber planta. Se usa al deformar nodos para no moverlos a una roca."""
        iy, ix = self._ij(P)
        return self.rock[iy, ix]

    def node_blocked(self, P):
        iy, ix = self._ij(P)
        return self.rock[iy, ix] | (self.slope[iy, ix] > self.spec.max_slope)

    def habitat(self, P, niche):
        """niche (N,3): profundidad de suelo requerida (cm), tolerancia de pendiente (grados), tolerancia a helada (C)."""
        iy, ix = self._ij(P)
        sd = self.soil[iy, ix][:, None]
        sl = self.slope[iy, ix][:, None]
        tm = self.tmin[iy, ix][:, None]
        f_soil = np.clip(sd / niche[None, :, 0], 0.1, 1.0) ** 0.7
        f_slope = 1.0 / (1.0 + np.exp((sl - (niche[None, :, 1] + 8.0)) / 4.0))
        f_frost = 1.0 / (1.0 + np.exp(-(tm - niche[None, :, 2]) / 2.0))
        return np.clip(f_soil * f_slope * f_frost, 0.02, 1.0)

    def grazing_hazard(self, P, vuln):
        iy, ix = self._ij(P)
        return self.graze[iy, ix][:, None] * np.asarray(vuln)[None, :]

    def unit_at(self, P):
        iy, ix = self._ij(P)
        return self.unit[iy, ix]

    def rain_factors(self, K, rng):
        s2 = math.log(1.0 + self.spec.rain_cv ** 2)
        return rng.lognormal(-s2 / 2.0, math.sqrt(s2), size=K)

    # ---------------- flora existente
    def sample_existing(self, rng, existing, n_plant, buf=15.0):
        W, H = self.width, self.height
        area_box = (W + 2 * buf) * (H + 2 * buf) / 1e4
        pos, typ = [], []
        for t, e in enumerate(existing):
            key = e[0].split()[0].lower()
            maxd = max(DENS[u].get(key, 0.0) for u in DENS)
            k = rng.poisson(maxd * area_box)
            if k == 0:
                continue
            p = rng.uniform([-buf, -buf], [W + buf, H + buf], size=(k, 2))
            u = self.unit_at(p)
            d = np.array([DENS[int(ui)].get(key, 0.0) for ui in u])
            if key in ("arbol", "lenosa"):                      # arboles solo en suelos profundos
                iy, ix = self._ij(p)
                d = d * np.minimum(1.0, self.soil[iy, ix] / 60.0)
            keep = rng.random(k) < d / max(maxd, 1e-9)
            pos.append(p[keep])
            typ.append(np.full(int(keep.sum()), n_plant + t))
        pos = np.vstack(pos) if pos else np.zeros((0, 2))
        typ = np.concatenate(typ) if typ else np.zeros(0, int)
        return self._pack(pos, typ, existing, n_plant, None, None)

    def place_cohort(self, rng, counts, existing, n_plant, first_t, min_sep=3.0):
        """Plantas VIVAS del campo (cohorte ya establecida): counts[s] plantas de la especie s (orden de PLANTED); posiciones desconocidas ->
        al azar dentro del poligono con separacion minima min_sep (m), como una plantacion. Tipos existentes first_t + s; no removibles."""
        N = int(np.sum(counts))
        W, H = self.width, self.height
        pts = []
        for _ in range(8):
            cs = min_sep
            grid, pts, tries = {}, [], 0
            while len(pts) < N and tries < 60 * N + 1000:
                batch = rng.uniform([0, 0], [W, H], size=(max(256, 2 * (N - len(pts))), 2))
                batch = batch[self.inside(batch)]
                for p in batch:
                    tries += 1
                    gx, gy = int(p[0] // cs), int(p[1] // cs)
                    if any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < min_sep ** 2
                           for dx in (-1, 0, 1) for dy in (-1, 0, 1) for q in grid.get((gx + dx, gy + dy), ())):
                        continue
                    grid.setdefault((gx, gy), []).append(p)
                    pts.append(p)
                    if len(pts) >= N:
                        break
            if len(pts) >= N:
                break
            min_sep *= 0.8
        pos = np.array(pts[:N]).reshape(-1, 2)
        lab = rng.permutation(np.repeat(np.arange(len(counts)), np.asarray(counts, int)))[:len(pos)]
        return self._pack(pos, n_plant + first_t + lab, existing, n_plant, None, None)

    @classmethod
    def from_poligonos(cls, path, pid, preset="mixto", utm=None, dem_pts=None, **kw):
        """Terreno de un poligono de un CSV unico (columnas poligono,x,y en metros locales: origen en la esquina suroeste de la caja envolvente).
        width/height = caja envolvente. Si existe poligonos_utm.csv junto al CSV (o se pasa `utm`), el relieve sale de UN DEM del sitio
        (SiteRelief) recortado en la posicion UTM real del poligono; si no, relieve simulado propio del poligono. El resto del sitio son los
        valores por defecto de TerrainSpec (Dominica) salvo lo que se pase en kw."""
        rows = [r for r in csv.DictReader(open(path, encoding="utf-8")) if int(r["poligono"]) == int(pid)]
        if not rows:
            raise ValueError(f"poligono {pid} no esta en {path}")
        poly = np.array([[float(r["x"]), float(r["y"])] for r in rows])
        kw = dict(kw, width=round(float(poly[:, 0].max()), 1), height=round(float(poly[:, 1].max()), 1))
        spec = spec_from(preset, **kw)
        d = os.path.dirname(os.path.abspath(path))
        utm = utm or os.path.join(d, "poligonos_utm.csv")
        dem_pts = dem_pts or os.path.join(d, "dem_srtm_puntos.csv")
        layers = {}
        if os.path.exists(utm):
            ur = [r for r in csv.DictReader(open(utm, encoding="utf-8")) if int(r["poligono"]) == int(pid)]
            e_min = min(float(r["E_utm14N"]) for r in ur)
            n_min = min(float(r["N_utm14N"]) for r in ur)
            site = SiteRelief.get(utm, dem_pts, spec.slope_deg, spec.seed, spec.elev_mean)
            nx, ny = int(math.ceil(spec.width / spec.cell)), int(math.ceil(spec.height / spec.cell))
            EE, NN = np.meshgrid(e_min + (np.arange(nx) + 0.5) * spec.width / nx, n_min + (np.arange(ny) + 0.5) * spec.height / ny)
            layers["elev"] = site.sample(EE, NN)
        return cls(spec, layers, poly)

    def _pack(self, pos, typ, existing, n_plant, removable_override, excl_override):
        ins = self.inside(pos) if len(pos) else np.zeros(0, bool)
        rem = np.array([existing[t - n_plant][10] for t in typ], bool) if len(typ) else np.zeros(0, bool)
        if removable_override is not None:
            rem = np.where(np.isnan(removable_override), rem, removable_override > 0)
        rm_cost = np.array([existing[t - n_plant][11] for t in typ], float) if len(typ) else np.zeros(0)
        excl = np.array([existing[t - n_plant][8] for t in typ], float) if len(typ) else np.zeros(0)
        if excl_override is not None:
            excl = np.where(np.isnan(excl_override), excl, excl_override)
        return dict(pos=pos, typ=typ.astype(int), removable=rem & ins, rm_cost=rm_cost, excl=excl)

    def load_flora(self, path, existing, n_plant):
        """Lee el mapeo de flora: columnas x,y,tipo[,removible,radio_excl]. Tipos libres -> grupo funcional."""
        keys = [e[0].split()[0].lower() for e in existing]
        pos, typ, rem, exc, unknown = [], [], [], [], 0
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                r = {k.strip().lower(): v for k, v in r.items()}
                name = (r.get("tipo") or "").lower()
                g = None
                for subs, grp in ALIAS:
                    if any(s in name for s in subs):
                        g = grp
                        break
                if g not in keys:
                    g, unknown = "arbusto", unknown + 1
                pos.append((float(r["x"]), float(r["y"])))
                typ.append(n_plant + keys.index(g))
                rem.append(float(r["removible"]) if r.get("removible") not in (None, "") else np.nan)
                exc.append(float(r["radio_excl"]) if r.get("radio_excl") not in (None, "") else np.nan)
        out = self._pack(np.array(pos).reshape(-1, 2), np.array(typ, int), existing, n_plant,
                         np.array(rem), np.array(exc))
        out["unknown_types"] = unknown
        self.flora = out
        return out

    def zonas(self, pend_pct=20.0, min_ha=0.10):
        """Zonas de pendiente. Zona 0 = suelo con pendiente < pend_pct (%); zonas 1..K = manchas conexas con pendiente >= pend_pct de al menos
        min_ha (las menores se reabsorben en la zona 0). Para cada mancha: pendiente media (%), y la direccion de sus curvas de nivel como orientacion
        de fila de la malla hexagonal (grados, modulo 60; media axial del aspecto ponderada por pendiente) con su coherencia (0..1).
        Guarda self.zone (rejilla) y self.zinfo; devuelve (zone, zinfo)."""
        from scipy import ndimage as ndi
        xs = (np.arange(self.nx)[None, :] * np.ones((self.ny, 1)) + .5) * self.cx
        ys = (np.arange(self.ny)[:, None] * np.ones((1, self.nx)) + .5) * self.cy
        m = self.inside(np.c_[xs.ravel(), ys.ravel()]).reshape(self.ny, self.nx)
        pct = 100.0 * np.tan(np.radians(self.slope))
        st = ndi.binary_opening(pct >= pend_pct, iterations=1)
        st = ndi.binary_closing(st, iterations=2) & m
        lab, k = ndi.label(st)
        cell_ha = self.cx * self.cy / 1e4
        zone = np.zeros((self.ny, self.nx), int)
        info = []
        for c in range(1, k + 1):
            mk = lab == c
            ha = float(mk.sum() * cell_ha)
            if ha < min_ha:
                continue
            zid = len(info) + 1
            zone[mk] = zid
            w = self.slope[mk] + 1e-9
            z = np.sum(w * np.exp(-2j * np.radians(self.aspect[mk]))) / np.sum(w)     # curva de nivel = aspecto + 90 deg (dato axial)
            info.append(dict(id=zid, area_ha=ha, pendiente_media_pct=float(pct[mk].mean()), theta_curva=float((math.degrees(np.angle(z)) / 2.0) % 60.0),
                             coherencia=float(abs(z))))
        self.zone, self.zinfo, self.pend_pct = zone, info, pend_pct
        self.zone_frac = {0: float(((zone == 0) & m).sum() / max(m.sum(), 1)), 1: float(((zone > 0) & m).sum() / max(m.sum(), 1))}
        self.zone_fracs = {z: float(((zone == z) & m).sum() / max(m.sum(), 1)) for z in range(len(info) + 1)}     # fraccion del poligono por zona (0 = plana)
        self.pend_media_pct = float(pct[m].mean())
        return zone, info

    def zone_at(self, P):
        iy, ix = self._ij(P)
        return self.zone[iy, ix]

    # ---------------- resumen / graficas / guardado
    def summary(self):
        s = self.spec
        m = self.inside(np.c_[(np.arange(self.nx)[None, :] * np.ones((self.ny, 1)) + .5).ravel() * self.cx,
                              (np.arange(self.ny)[:, None] * np.ones((1, self.nx)) + .5).ravel() * self.cy]
                        ).reshape(self.ny, self.nx)
        f = lambda a: float(np.mean(a[m]))
        un = {UNITS[u]: round(float(np.mean(self.unit[m] == u)), 3) for u in range(4)}
        return dict(area_ha=round(self.area_ha, 2), elev_m=round(f(self.elev)), slope_mean_deg=round(f(self.slope), 1),
                    slope_p90_deg=round(float(np.percentile(self.slope[m], 90)), 1),
                    rain_mm=round(f(self.rain)), temp_C=round(f(self.temp), 1), tmin_C=round(f(self.tmin), 1),
                    AI=round(f(self.ai), 3), clase=ai_class(f(self.ai)), AI_efectivo=round(f(self.ai_eff), 3),
                    aridez_efectiva_media=round(f(self.ar), 2),
                    aridez_efectiva_rango=[round(float(self.ar[m].min()), 2), round(float(self.ar[m].max()), 2)],
                    suelo_cm_medio=round(f(self.soil)), roca_frac=round(float(np.mean(self.rock[m])), 3),
                    pastoreo_medio=round(f(self.graze), 2), unidades=un, capas_dadas=self.layers_given)

    def plot(self, path, flora=None):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ext = [0, self.width, 0, self.height]
        fig, axs = plt.subplots(2, 4, figsize=(20, 9))
        items = [("Elevacion (m)", self.elev, "terrain"), ("Pendiente (grados)", self.slope, "magma_r"),
                 ("Suelo (cm)", self.soil, "YlOrBr"), ("Lluvia anual (mm)", self.rain, "Blues"),
                 ("Temperatura media (C)", self.temp, "coolwarm"),
                 ("Aridez efectiva (mayor = mas seco)", self.ar, "RdYlBu_r"),
                 ("Presion de pastoreo", self.graze, "Reds"),
                 ("Unidad ambiental (0 MDR prim., 1 MDR sec., 2 pastizal, 3 sin veg.)", self.unit, "Set2")]
        inmask = None
        if self.polygon is not None:      # fuera del polígono: gris, sin datos
            gx_, gy_ = np.meshgrid((np.arange(self.nx) + 0.5) * self.cx, (np.arange(self.ny) + 0.5) * self.cy)
            inmask = self.inside(np.c_[gx_.ravel(), gy_.ravel()]).reshape(self.ny, self.nx)
        for ax, (t, a, cm) in zip(axs.ravel(), items):
            if inmask is not None:
                ax.set_facecolor("#d0d0d0")
                a = np.ma.masked_where(~inmask, a)
            im = ax.imshow(a, origin="lower", extent=ext, cmap=cm)
            ax.set_title(t, fontsize=9)
            plt.colorbar(im, ax=ax, fraction=0.046)
            if self.polygon is not None:
                pp = np.vstack([self.polygon, self.polygon[:1]])
                ax.plot(pp[:, 0], pp[:, 1], "k-", lw=1.5)
            if flora is not None and t.startswith("Unidad"):
                p = flora["pos"]
                m = self.inside(p) if len(p) else np.zeros(0, bool)
                ax.plot(p[m, 0], p[m, 1], "k.", ms=1.5, alpha=0.6)
        fig.tight_layout()
        fig.savefig(path, dpi=110)
        plt.close(fig)

    def save_dir(self, path, flora=None, existing=None, n_plant=None):
        os.makedirs(path, exist_ok=True)
        d = asdict(self.spec)
        d["fila0_es_norte"] = False
        json.dump(d, open(os.path.join(path, "terreno.json"), "w"), indent=1)
        for key, arr in (("elevacion", self.elev), ("lluvia", self.rain), ("temperatura", self.temp),
                         ("suelo_cm", self.soil), ("pastoreo", self.graze)):
            np.savetxt(os.path.join(path, key + ".csv"), arr, delimiter=",", fmt="%.4f")
        if self.polygon is not None:
            np.savetxt(os.path.join(path, "poligono.csv"), self.polygon, delimiter=",", header="x,y", comments="")
        if flora is not None:
            with open(os.path.join(path, "flora_existente.csv"), "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["x", "y", "tipo", "removible", "radio_excl"])
                for p, t, r, ex_ in zip(flora["pos"], flora["typ"], flora["removable"], flora["excl"]):
                    if 0 <= p[0] <= self.width and 0 <= p[1] <= self.height:
                        w.writerow([round(p[0], 3), round(p[1], 3), existing[t - n_plant][0], int(r), round(ex_, 3)])

    @classmethod
    def from_dir(cls, path):
        d = json.load(open(os.path.join(path, "terreno.json")))
        flip = bool(d.pop("fila0_es_norte", False))
        names = {f.name for f in fields(TerrainSpec)}
        spec = TerrainSpec(**{k: v for k, v in d.items() if k in names})
        layers = {}
        for key, cands in LAYER_FILES.items():
            for c in cands:
                for ext in ("csv", "npy"):
                    fp = os.path.join(path, f"{c}.{ext}")
                    if os.path.exists(fp):
                        a = np.loadtxt(fp, delimiter=",") if ext == "csv" else np.load(fp)
                        layers[key] = np.flipud(a) if flip else a
        shapes = {a.shape for a in layers.values()}
        if len(shapes) > 1:
            raise ValueError(f"las rejillas deben tener la misma forma: {shapes}")
        poly = None
        fp = os.path.join(path, "poligono.csv")
        if os.path.exists(fp):
            rows = [r for r in csv.reader(open(fp)) if r]
            if not rows[0][0].replace(".", "").replace("-", "").isdigit():
                rows = rows[1:]
            poly = np.array(rows, float)
        return cls(spec, layers, poly)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Genera una carpeta de ejemplo con el formato de entrada.")
    ap.add_argument("--template", required=True)
    ap.add_argument("--preset", default="mixto", choices=list(PRESETS))
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    import hexgarden as hg
    T = Terrain(spec_from(a.preset, seed=a.seed))
    fl = T.sample_existing(np.random.default_rng(a.seed + 1), hg.EXISTING, hg.N_PLANT)
    T.save_dir(a.template, fl, hg.EXISTING, hg.N_PLANT)
    print("Carpeta de ejemplo en", a.template, "->", T.summary())
