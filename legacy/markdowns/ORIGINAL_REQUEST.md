# Original User Request

## Initial Request — 2026-10-22T01:55:40Z

Robustify and align the stochastic reforestation optimization pipeline (`REFORESTATHON`) with the mathematical report document (`miguel.pdf` / `scripts/entregable2_texto.txt`), directly addressing all 13 reviewer critiques to raise the project grade above 80.

Working directory: D:\Codingggg\Notas\Estocastico\REFORESTATHON
Integrity mode: development

## Context & Available Resources
- Document to revise: `D:\Codingggg\Notas\Estocastico\REFORESTATHON\miguel.pdf` (full text extracted in `scripts/entregable2_texto.txt`).
- Monitoring & field data: `data/semiraw/` (`monitoreo_supervivencia.csv`, `catalogo_especies_consolidado.csv`, `poligonos_plantas_wide.csv`, `orden_plantacion_100m.csv`).
- Existing codebase: `scripts/src/reforestacion_pipeline.py`.
- Hardware available: Windows 11, AMD Ryzen 7 6800H (16 threads), 32 GB RAM, NVIDIA RTX 3060 Laptop GPU (6 GB VRAM).

## Requirements

### R1. Formal Mathematical Revision & Rebuttal Document (Addressing the 13 Critiques)
Produce an exhaustive technical rebuttal and revised report (Markdown / LaTeX ready to recompile) that thoroughly answers each of the 13 reviewer comments:
1. **Eq. (1) $N_z$ separation by slope:** Justify the piecewise formula $N_z = \lfloor 658 \cdot A_z \rfloor$ (slope $< 20\%$) vs $\lceil 524 \cdot A_z \rceil$ (slope $\ge 20\%$) citing technical CONAFOR reforestation guidelines (e.g., erosion control, soil stability, and moisture retention reducing planting density on steep gradients).
2. **Notation collision:** Rename the parameter $E_z$ (existing plants in zone $z$) to $X_z$ across the document to eliminate ambiguity with $E_i$ (initial abundance of species $i$).
3. **Index definitions for $c^L_{ji,qp,t}$:** Fully specify indices: $q \in P$ (neighboring position of competitor $j$), $p \in P$ (target planting position of species $i$), and $t \in T$ (year within planning horizon $T$).
4. **Formal definition of $q$:** Explicitly state that $q \in P$ represents the spatial coordinate / node in the hexagonal grid where competitor $j$ is located.
5. **Formal definition of $t$:** Clarify that $t \in \{1, \dots, T_{\max}\}$ indexes the discrete planning years over which biological maturity and survival evolve.
6. **Derivation of root water competition Eq. (2):** Provide the ecological derivation based on the Zone of Influence (ZOI) root overlap model (Berger et al., 2008), explaining the ratio of water uptake $U_{jt} / (U_{jt} + U_{it})$ and root overlap.
7. **Justification of Kernel $K(v)$ Eq. (3):** Explain the Epanechnikov biweight kernel $K(v) = (1 - v^2)^2$ for $v \in [0, 1)$, its optimal MSE efficiency in distance decay, and bounded compact support avoiding infinite tails.
8. **Dimensional consistency in Objective Function Eq. (4):** Resolve the dimensional clash between dimensionless survival probability and nursery acquisition cost $k_i q_i$ (in MXN) by explaining $\mu$ as a shadow price / trade-off parameter (pesos per marginal unit of survival) or normalizing the objective.
9. **Interpretation & choice of $\mu = 0.0005$:** Explain what $\mu$ represents economically (marginal trade-off) and how its value was calibrated against the CONAFOR budget per hectare ($13,200 MXN / 658 pl = ~20.06 MXN/pl).
10. **Logistic Survival Eq. (5):** Document the origin and calibration of $s_{ipt} = 1 / (1 + \exp[-(F_{ipt} - 0.25)/0.05])$, citing logistic dose-response curves (Metcalf et al., 2015) where $0.25$ is the critical threshold of environmental fitness and $0.05$ controls steepness.
11. **Multiplicative Fitness $F_{ipt}$ Eq. (7):** Justify Liebig's Law of the Minimum / multiplicative stress degradation across water, nutrient, and light stresses.
12. **Stress Variables Calibration Eqs. (8)–(10):** Detail how constants (3, 0.9, 0.5, 0.6) and sensitivities $v_i, \ell_i$ were derived from empirical 2021–2023 survival data across the 10 species.
13. **Weighted Interaction Graph Eq. (17):** Justify weights (0.60 water, 0.25 light, 0.15 nurse facilitation) as reflecting primary limiting factors in semi-arid zones (Table 2).

### R2. Refactor Reforestation Optimization Pipeline
Upgrade `scripts/src/reforestacion_pipeline.py`:
1. Implement terrain slope-dependent target density $N_z \in \{524, 658\}$ pl/ha.
2. Implement the multi-component ecological competition kernel: water competition $c^W$ with Epanechnikov kernel $K(v)$, light competition $c^L$, and nurse facilitation $c^B$ (Prosopis laevigata).
3. Calibrate species parameters ($R_i, U_i, v_i, \ell_i$) empirically from `monitoreo_supervivencia.csv`.
4. Incorporate real species acquisition costs from catalogue rather than a single average cost.
5. Multi-objective or penalized formulation maximizing survival while bounding nursery cost.

### R3. Transparent MIP Solver & Scalability (Addressing "No corrieron el modelo matemático")
1. Solve the MILP with Gurobi (or HiGHS fallback) tracking genuine lower bounds, upper bounds, and real `MIPGap` (no hardcoded `0.0%`).
2. Provide a spatial tiling / domain decomposition strategy enabling scaling beyond the 66-node demonstration grid to multi-hectare polygons.
3. Save full solver execution logs and comparison tables in `scripts/logs/` and `scripts/outputs/` verifying that the exact mathematical optimization was solved.

## Acceptance Criteria

### Verification Commands & Tests
- [ ] Pipeline executes successfully: `python scripts/src/reforestacion_pipeline.py --rows 6 --cols 11` runs without errors.
- [ ] Output verification: `scripts/outputs/comparativa_holgura_0_5_10.csv` and `scripts/outputs/asignacion_optima_2d.csv` are generated and contain genuine mathematical metrics (non-trivial `MIPGap`, objective values, ecological audit).
- [ ] No hardcoded 0.0% gap: inspection of the solver wrapper confirms `gap` is computed from `(ObjVal - ObjBound) / ObjVal` or solver API.
- [ ] Deliverable report: A comprehensive markdown document `REVISION_ENTREGABLE2_REBUTTAL.md` (and/or updated report) is generated in the repository addressing all 13 points with formal mathematical formulas and citations.
