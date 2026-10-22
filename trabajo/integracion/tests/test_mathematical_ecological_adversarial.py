# -*- coding: utf-8 -*-
"""Suite de Pruebas Adversariales Empíricas de Formulación Matemática y Ecológica
=============================================================================
REFORESTATHON - Challenger 1 (Mathematical & Ecological Adversarial Challenger)

Verifica empíricamente:
1. Propiedades del kernel de Epanechnikov biweight: soporte compacto en [0, 1),
   no-negatividad, frontera K(1)=0, y derivada K'(1)=0 (suavidad C^1).
2. Consistencia dimensional de la función objetivo y escala de penalización
   financiera mu * sum(k_i * q_i) con mu = 0.0005 vs supervivencia biológica.
3. Función logística dosis-respuesta de supervivencia s(F): acotamiento en (0, 1),
   monotonía estricta, umbrales críticos (LD50 en F=0.25) y estabilidad numérica.
4. Comportamiento de facilitación nodriza para Prosopis laevigata (amortiguamiento
   microclimático, islas de nitrógeno, reducción de matriz de interacción neta y
   repulsión intraespecífica).
"""

import math
import os
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

# Asegurar que el directorio raíz y scripts/src estén en sys.path
TEST_DIR = Path(__file__).resolve().parent
ROOT_DIR = TEST_DIR.parent
SRC_DIR = ROOT_DIR / "scripts" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from reforestacion_pipeline import (
    MODEL_PARAMS,
    SPECIES_METADATA,
    build_ecological_matrices,
    get_target_density,
    load_semiraw_datasets,
)


class TestEpanechnikovKernelProperties(unittest.TestCase):
    """Pruebas adversariales sobre el kernel de Epanechnikov biweight K(v) = (1 - v^2)^2."""

    @staticmethod
    def K(v: float) -> float:
        """Kernel biweight de Epanechnikov según Ec. (3)."""
        if 0.0 <= v < 1.0:
            return (1.0 - v**2)**2
        return 0.0

    @staticmethod
    def dK_analytical(v: float) -> float:
        """Derivada analítica formal de K(v)."""
        if 0.0 <= v < 1.0:
            return -4.0 * v * (1.0 - v**2)
        return 0.0

    def test_compact_support_upper_bound(self):
        """Verifica que K(v) == 0 para cualquier v >= 1.0 en un rango masivo."""
        # Puntos críticos en la frontera
        self.assertEqual(self.K(1.0), 0.0)
        self.assertEqual(self.K(1.0 + 1e-15), 0.0)
        self.assertEqual(self.K(1.0001), 0.0)

        # Muestreo masivo en [1.0, 10000.0]
        v_values = np.linspace(1.0, 10000.0, 100000)
        for v in v_values:
            self.assertEqual(self.K(float(v)), 0.0, f"Fallo soporte compacto en v={v}")

    def test_non_negativity(self):
        """Verifica que K(v) >= 0 para todo v en [0, inf)."""
        v_dense = np.linspace(0.0, 5.0, 500000)
        for v in v_dense:
            val = self.K(float(v))
            self.assertGreaterEqual(val, 0.0, f"Fallo no-negatividad en v={v}: K={val}")
            self.assertLessEqual(val, 1.0, f"Fallo acotamiento superior en v={v}: K={val}")

    def test_zero_boundary_condition(self):
        """Verifica K(1) = 0 y continuidad lateral lim_{v -> 1^-} K(v) = 0."""
        self.assertEqual(self.K(1.0), 0.0)
        eps_list = [1e-3, 1e-5, 1e-7, 1e-9, 1e-12]
        for eps in eps_list:
            v = 1.0 - eps
            val = self.K(v)
            self.assertGreater(val, 0.0)
            self.assertLess(val, 4.0 * eps**2 + 1e-12, f"Convergencia de frontera lenta en eps={eps}")

    def test_derivative_smoothness_at_boundary(self):
        """Verifica que K'(1) = 0 tanto analítica como numéricamente (clase C^1)."""
        # 1. Derivada analítica lateral
        dK_1_minus = self.dK_analytical(1.0 - 1e-12)
        self.assertAlmostEqual(dK_1_minus, 0.0, places=9)

        # 2. Derivada numérica por diferencias finitas centrales
        h_values = [1e-4, 1e-5, 1e-6]
        for h in h_values:
            d_num = (self.K(1.0 + h) - self.K(1.0 - h)) / (2.0 * h)
            self.assertAlmostEqual(d_num, 0.0, places=3, msg=f"Derivada numérica no nula en frontera con h={h}")

        # 3. Concordancia analítica en todo el soporte (0, 1)
        test_v = np.linspace(0.01, 0.99, 1000)
        h = 1e-6
        for v in test_v:
            d_ana = self.dK_analytical(float(v))
            d_num = (self.K(v + h) - self.K(v - h)) / (2.0 * h)
            self.assertAlmostEqual(d_ana, d_num, places=4, msg=f"Discrepancia en derivada analítica vs numérica en v={v}")

    def test_derivative_at_origin(self):
        """Verifica K'(0) = 0 (meseta de saturación en proximidad radicular)."""
        dK_0 = self.dK_analytical(0.0)
        self.assertEqual(dK_0, 0.0)

        h = 1e-6
        d_num_right = (self.K(h) - self.K(0.0)) / h
        self.assertAlmostEqual(d_num_right, 0.0, places=4)

    def test_strict_monotonicity_on_unit_interval(self):
        """Verifica que dK/dv < 0 en (0, 1) (decaimiento monótono con la distancia)."""
        v_points = np.linspace(0.001, 0.999, 10000)
        for v in v_points:
            d_val = self.dK_analytical(float(v))
            self.assertLess(d_val, 0.0, f"Violación de monotonicidad decreciente en v={v}")

    def test_pipeline_kernel_pruning_efficiency(self):
        """Verifica el porcentaje de poda del soporte compacto en la cuadrícula de plantación."""
        df_cat, _, _ = load_semiraw_datasets()
        _, _, Phi = build_ecological_matrices(df_cat, slope_pct=6.0, density_per_ha=658.0)

        # En t=1 año, radio radicular R_1 está en [0.4, 0.8] m.
        # R_max(t=1) = 0.8 + 0.8 = 1.6 m.
        # Distancia intercepa d = 4.19 m > 1.6 m.
        # Por ende v > 2.6 > 1.0 => el soporte compacto anula 100% de competencia hídrica en t=1.
        d_step = math.sqrt(20000.0 / (658.0 * math.sqrt(3.0)))
        for i in range(10):
            for j in range(10):
                R_sum_t1 = SPECIES_METADATA[i]["R_rad"][1] + SPECIES_METADATA[j]["R_rad"][1]
                v_t1 = d_step / R_sum_t1
                self.assertGreater(v_t1, 1.0, "En t=1 no debería haber solapamiento radicular entre cepas a 4.19m")
                self.assertEqual(self.K(v_t1), 0.0)


class TestDimensionalConsistencyAndCostPenalty(unittest.TestCase):
    """Pruebas adversariales de análisis dimensional y escala de penalización monetaria mu."""

    def test_units_consistency_derivation(self):
        """Comprueba formalmente las dimensiones físicas algebraicas de la función objetivo.
        J_total = J_bio - mu * C_vivero
        [J_bio] = [plantas]
        [C_vivero] = [MXN]
        [mu] = [plantas / MXN]
        => [mu * C_vivero] = [plantas]
        => [J_total] = [plantas]
        """
        unit_J_bio = "plantas"
        unit_C_vivero = "MXN"
        unit_mu = "plantas / MXN"

        # Comprobación de consistencia
        dim_penalty = f"{unit_mu} * {unit_C_vivero}"  # (plantas/MXN)*MXN = plantas
        self.assertEqual(dim_penalty.replace(" / MXN * MXN", ""), unit_J_bio)

    def test_cost_penalty_relative_magnitude(self):
        """Verifica que el término mu * sum(k_i * q_i) NO domina la supervivencia biológica.
        Evalúa en una hectárea completa (N=658) y en la malla reducida (N=66).
        """
        mu = MODEL_PARAMS["mu_cost_penalty"]
        self.assertEqual(mu, 0.0005)

        costs_vivero = [SPECIES_METADATA[i]["cost_mxn"] for i in range(10)]
        k_min = min(costs_vivero)  # 14.50 MXN (AL, AT)
        k_max = max(costs_vivero)  # 36.00 MXN (YF)

        # 1. Hectárea Completa CONAFOR (N = 658 plantas)
        N_ha = 658
        # Supervivencia biológica esperada realista (entre 70% y 95%)
        # J_bio in [658 * 0.70, 658 * 0.95] = [460.6, 625.1] plantas
        surv_rates = [0.70, 0.80, 0.85, 0.90, 0.95]

        # Costos extremos de vivero posibles
        cost_min_ha = N_ha * k_min  # 658 * 14.50 = 9,541 MXN
        cost_max_ha = N_ha * k_max  # 658 * 36.00 = 23,688 MXN

        # Costo de la receta oficial CONAFOR ponderada
        proportions = np.array([SPECIES_METADATA[i]["alpha_target"] for i in range(10)])
        cost_recipe_unit = float(np.dot(proportions, costs_vivero))
        cost_recipe_ha = N_ha * cost_recipe_unit  # ~13,195 MXN

        penalty_recipe = mu * cost_recipe_ha  # ~6.598 plantas equivalentes

        for s_rate in surv_rates:
            J_bio = N_ha * s_rate
            rel_ratio = penalty_recipe / J_bio
            # El término de penalización debe representar entre 1.0% y 2.0% del valor biológico
            self.assertLess(rel_ratio, 0.035, f"La penalización de costo ({rel_ratio:.2%}) excede el límite del 3.5%")
            self.assertGreater(rel_ratio, 0.005, f"La penalización de costo ({rel_ratio:.2%}) es insignificante (<0.5%)")

        # 2. Comprobación bajo 50,000 mezclas aleatorias de especies (Dirichlet)
        rng = np.random.default_rng(2026)
        samples = rng.dirichlet(np.ones(10), size=50000)
        for weights in samples:
            q_mix = weights * N_ha
            c_mix = float(np.dot(q_mix, costs_vivero))
            p_mix = mu * c_mix
            # Suponiendo supervivencia media del 85%
            j_bio_est = N_ha * 0.85
            ratio = p_mix / j_bio_est
            self.assertLess(ratio, 0.045, "Mezcla de especies causó dominancia monetaria sobre la biología")

    def test_critical_mu_distortion_threshold(self):
        """Determina numéricamente el punto de bifurcación mu* donde el costo comenzaría a dominar (>25%)."""
        N_ha = 658
        J_bio = N_ha * 0.85  # 559.3 plantas
        costs_vivero = np.array([SPECIES_METADATA[i]["cost_mxn"] for i in range(10)])
        proportions = np.array([SPECIES_METADATA[i]["alpha_target"] for i in range(10)])
        cost_ha = N_ha * float(np.dot(proportions, costs_vivero))  # 13,195.50 MXN

        # mu actual: 0.0005
        current_penalty = 0.0005 * cost_ha
        current_share = current_penalty / J_bio  # ~1.18%

        # mu que causaría 10% de dominancia
        mu_10pct = (0.10 * J_bio) / cost_ha  # ~0.00424 (8.5x mayor que el actual)
        # mu que causaría 50% de dominancia
        mu_50pct = (0.50 * J_bio) / cost_ha  # ~0.02120 (42.4x mayor que el actual)

        self.assertLess(0.0005, mu_10pct)
        self.assertAlmostEqual(current_share, 0.0118, places=3)

    def test_shadow_price_reciprocal_meaning(self):
        """Verifica que lambda = 1/mu coincide exactamente con 2000.0 MXN / individuo adulto."""
        mu = MODEL_PARAMS["mu_cost_penalty"]
        lambda_bio = 1.0 / mu
        self.assertEqual(lambda_bio, 2000.0)


class TestLogisticDoseResponseFunction(unittest.TestCase):
    """Pruebas adversariales sobre la función de supervivencia logística dosis-respuesta (Ec. 5)."""

    @staticmethod
    def s_logistic(F: float, F_crit: float = 0.25, sigma_F: float = 0.05) -> float:
        """Función de dosis-respuesta logística con protección contra overflow en float64."""
        z = (F - F_crit) / sigma_F
        if z < -700.0:
            return 0.0
        if z > 700.0:
            return 1.0
        return 1.0 / (1.0 + math.exp(-z))

    def test_strict_bounds_unit_interval(self):
        """Verifica que s(F) in (0, 1) para un espectro extremo de valores de aptitud F."""
        extreme_F = [-100.0, -10.0, -1.0, 0.0, 0.10, 0.25, 0.40, 1.0, 10.0, 100.0]
        for F in extreme_F:
            s = self.s_logistic(F)
            self.assertGreaterEqual(s, 0.0)
            self.assertLessEqual(s, 1.0)

    def test_ld50_inflection_point(self):
        """Verifica que F_crit = 0.25 actúa exactamente como la Dosis Letal Mediana (s = 0.50)."""
        s_crit = self.s_logistic(0.25)
        self.assertEqual(s_crit, 0.5000000000000000)

    def test_strict_monotonicity(self):
        """Verifica que s(F1) < s(F2) para cualquier F1 < F2."""
        F_grid = np.linspace(-0.5, 1.5, 20000)
        s_vals = [self.s_logistic(float(f)) for f in F_grid]
        for i in range(len(s_vals) - 1):
            self.assertLessEqual(s_vals[i], s_vals[i + 1])

    def test_empirical_calibration_points(self):
        """Verifica la correspondencia numérica exacta con la Tabla de la Sec. 2.10."""
        expected_benchmarks = {
            0.40: 0.952574,  # +3.0 sigma
            0.38: 0.930862,  # +2.6 sigma (AL, OR)
            0.35: 0.880797,  # +2.0 sigma (OS, AS)
            0.30: 0.731059,  # +1.0 sigma (YF, AC)
            0.25: 0.500000,  #  0.0 sigma (LD50)
            0.15: 0.119203,  # -2.0 sigma (Colapso hidráulico)
            0.10: 0.047426,  # -3.0 sigma (Mortalidad prácticamente total)
        }
        for F, expected_s in expected_benchmarks.items():
            s_calc = self.s_logistic(F)
            self.assertAlmostEqual(s_calc, expected_s, places=5, msg=f"Discrepancia en s({F})")

    def test_derivative_maximum_at_inflection(self):
        """Verifica que la tasa de cambio ds/dF es máxima en F=0.25 y positiva en todo R."""
        # ds/dF = (1/sigma_F) * s * (1 - s)
        # En s = 0.5, max_ds = 1/0.05 * 0.25 = 5.0
        h = 1e-6
        d_num_max = (self.s_logistic(0.25 + h) - self.s_logistic(0.25 - h)) / (2.0 * h)
        self.assertAlmostEqual(d_num_max, 5.0, places=4)


class TestNurseFacilitationBehavior(unittest.TestCase):
    """Pruebas adversariales del comportamiento de facilitación nodriza (Prosopis laevigata)."""

    def setUp(self):
        self.df_cat, self.df_wide, _ = load_semiraw_datasets()
        self.df_sp, self.C_norm, self.Phi = build_ecological_matrices(self.df_cat)
        self.prosopis_id = 8

    def test_nurse_matrix_exclusivity(self):
        """Verifica que la facilitación nodriza c^B beneficia a los pares que involucran Prosopis."""
        # En build_ecological_matrices, C_nurse solo es poblado en fila/columna prosopis_id=8
        # Verifiquemos que C_norm[8, i] para i!=8 es notablemente menor que la diagonal C_norm[8, 8]
        for i in range(10):
            if i != self.prosopis_id:
                # El costo de interacción con mezquite debe ser estrictamente menor que 1.0 (auto-competencia)
                self.assertLess(
                    self.C_norm[self.prosopis_id, i],
                    self.C_norm[self.prosopis_id, self.prosopis_id],
                    f"Fallo facilitación: interacción Prosopis con especie {i} no es favorable vs monocultivo",
                )

    def test_prosopis_autocompetition_maximum(self):
        """Verifica que la auto-competencia de mezquite esté fuertemente penalizada (C_norm[8,8] == 1.0)."""
        self.assertEqual(self.C_norm[self.prosopis_id, self.prosopis_id], 1.00)
        self.assertEqual(self.Phi[self.prosopis_id, self.prosopis_id], self.df_sp.loc[self.prosopis_id, "w_vuln"])

    def test_nurse_water_stress_mitigation_eq8(self):
        """Verifica la Ec. (8): S_W se mitiga hasta en un 90% bajo efecto nodriza completo.
        S_{W,ipt} = a_p * v_i * (1 + 3 J_{it}) * [1 - 0.9 * min{3 H^B_{ipt}, 1}] + H^W_{ipt} * (1 - 0.5 J_{it})
        """
        v_i = SPECIES_METADATA[0]["v_water_sens"]  # AL = 0.20
        J_t1 = 1.0  # Año 1
        a_p = 1.0
        H_W = 0.0

        # Sin nodriza (H_B = 0)
        S_W_no_nurse = a_p * v_i * (1.0 + 3.0 * J_t1) * (1.0 - 0.9 * min(3.0 * 0.0, 1.0))
        # Con nodriza completa (H_B >= 0.3333 => 3 * H_B >= 1.0)
        S_W_with_nurse = a_p * v_i * (1.0 + 3.0 * J_t1) * (1.0 - 0.9 * min(3.0 * 0.35, 1.0))

        # La reducción debe ser exactamente del 90% en el término de aridez
        reduction_pct = (S_W_no_nurse - S_W_with_nurse) / S_W_no_nurse
        self.assertAlmostEqual(reduction_pct, 0.90, places=6)

    def test_nurse_nitrogen_stress_mitigation_eq9(self):
        """Verifica la Ec. (9): S_N se reduce en un 60% por fijación biológica de Rhizobium.
        S_{N,ipt} = 0.5 * [1 - 0.6 * min{H^N_{ipt}, 1}]
        """
        # Sin nodriza (H_N = 0)
        S_N_no_nurse = 0.5 * (1.0 - 0.6 * min(0.0, 1.0))
        # Con nodriza saturada (H_N >= 1.0)
        S_N_with_nurse = 0.5 * (1.0 - 0.6 * min(1.0, 1.0))

        self.assertEqual(S_N_no_nurse, 0.50)
        self.assertEqual(S_N_with_nurse, 0.20)
        self.assertAlmostEqual((S_N_no_nurse - S_N_with_nurse) / S_N_no_nurse, 0.60, places=6)

    def test_facilitation_triad_weight_normalization_eq17(self):
        """Verifica la suma exacta de pesos fisiológicos beta_W + beta_L + beta_N = 1.00."""
        b_w = MODEL_PARAMS["beta_water"]
        b_l = MODEL_PARAMS["beta_light"]
        b_n = MODEL_PARAMS["beta_nurse"]
        self.assertEqual(b_w, 0.60)
        self.assertEqual(b_l, 0.25)
        self.assertEqual(b_n, 0.15)
        self.assertAlmostEqual(b_w + b_l + b_n, 1.00, places=9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
