#modelo_anexo_entregable3.py - modelo matematico y estocastico de reforestacion en 1 ha
#incluye evaluacion multicanal, recocido simulado, milp rlt-1 k3 y cadenas de markov
import math
import numpy as np
from scipy import stats
from scipy.spatial import cKDTree
from scipy.optimize import milp, LinearConstraint

#catalogo oficial de las 10 especies de la sierra de alvarez
especies = ["AL", "AT", "AC", "AS", "OC", "OE", "OR", "OS", "PL", "YF"]
n_especies = len(especies)
#precios oficiales de vivero en pesos mexicanos (conafor/inecol)
precios_vivero = np.array([26.0, 26.0, 26.0, 26.0, 18.0, 21.0, 18.0, 18.0, 26.5, 26.0])
#cuotas nominales de la receta conafor para 1 ha (658 plantas)
cuotas_receta = np.array([42, 42, 42, 196, 49, 38, 73, 64, 86, 26])
#parametros alometricos: altura adulta, copa, factor raiz, uso agua, profundidad
alturas = np.array([0.45, 0.60, 0.85, 1.80, 1.50, 1.50, 1.50, 3.50, 5.00, 6.00])
copas = np.array([0.60, 1.20, 1.75, 3.60, 2.00, 2.50, 3.00, 3.50, 6.00, 3.00])
factores_raiz = np.array([1.5, 1.5, 1.4, 1.3, 1.5, 1.5, 1.5, 1.5, 2.5, 1.2])
consumo_agua = np.array([0.20, 0.25, 0.30, 0.50, 0.40, 0.40, 0.40, 0.45, 1.00, 0.40])
profundidades = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.3])
#sensibilidades a sequia y sombra, rasgos nodriza y nivel de submalla
sens_agua = np.array([0.5, 0.6, 0.6, 0.7, 0.6, 0.6, 0.6, 0.6, 0.5, 0.6])
sens_sombra = np.array([1.0, 1.0, 0.9, 0.7, 0.8, 0.8, 0.8, 0.8, 0.5, 0.7])
es_nodriza = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0])
submallas = np.array([1, 1, 1, 1, 1, 1, 1, 3, 3, 3])

#construccion de la malla hexagonal de 1 ha en tresbolillo
def construir_malla_hexagonal(ancho=100.0, alto=100.0, a=4.0):
    #calcula coordenadas de los nodos y asigna submallas 1 y 3
    dy = a * math.sqrt(3.0) / 2.0
    n_filas, n_cols = int(alto / dy) + 1, int(ancho / a) + 1
    coords, indices_red = [], []
    for j in range(n_filas):
        y, off_x = j * dy, (a / 2.0) if (j % 2 == 1) else 0.0
        for i in range(n_cols):
            x = i * a + off_x
            if x <= ancho and y <= alto:
                coords.append([x, y]); indices_red.append((i, j))
    coords = np.array(coords)
    es_submalla3 = np.array([(i - j) % 3 == 0 for i, j in indices_red])
    return coords, indices_red, es_submalla3

#muestreo de plantas preexistentes y calculo de cuotas con tolerancia
def muestrear_suministros(semilla=None, tol=0.10):
    #muestreo truncado de densidad preexistente con media 129.18 y desv 3.35
    rng = np.random.default_rng(semilla)
    a_tr = (0.0 - 129.18) / 3.35
    nu_tot = int(round(stats.truncnorm.rvs(a_tr, np.inf, loc=129.18, scale=3.35, random_state=rng)))
    nu = rng.multinomial(nu_tot, cuotas_receta / cuotas_receta.sum())
    dem = np.maximum(0, cuotas_receta - nu)
    c_inf = np.ceil((1.0 - tol) * cuotas_receta).astype(int)
    c_sup = np.floor((1.0 + tol) * cuotas_receta).astype(int)
    return nu, dem, c_inf, c_sup

#evaluacion de los 4 canales biologicos y la funcion de aptitud f
def evaluar_canales(coords, especies_asignadas, pares=None, pendiente_deg=6.0):
    #canales: agua h_w, sombra h_l, alelopatia h_a y facilitacion nodriza h_n
    n = len(coords)
    hw, hl, ha, hn = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    k_sombra = math.tan(math.radians(pendiente_deg))
    if pares is None:
        pares = cKDTree(coords).query_pairs(4.8, output_type="ndarray")
    for p, q in pares:
        sp_p, sp_q = especies_asignadas[p], especies_asignadas[q]
        if sp_p < 0 or sp_q < 0:
            continue
        v = coords[q] - coords[p]
        dist = math.hypot(v[0], v[1])
        #1. competencia hidrica radicular con kernel biweight y solape vertical
        r_sum = factores_raiz[sp_p] * (copas[sp_p] / 2.0) + factores_raiz[sp_q] * (copas[sp_q] / 2.0)
        if dist < r_sum:
            k_bw = (1.0 - (dist / r_sum)**2)**2
            dov = max(0.0, 1.0 - 0.6 * abs(profundidades[sp_p] - profundidades[sp_q]))
            hw[p] += (consumo_agua[sp_q] / (consumo_agua[sp_p] + consumo_agua[sp_q] + 1e-9)) * k_bw * dov
            hw[q] += (consumo_agua[sp_p] / (consumo_agua[sp_p] + consumo_agua[sp_q] + 1e-9)) * k_bw * dov
        #2. sombreo asimetrico por dosel y pendiente hacia el norte
        cr_sum = (copas[sp_p] + copas[sp_q]) / 2.0
        sy_p, sy_q = v[1] - k_sombra * alturas[sp_q], -v[1] - k_sombra * alturas[sp_p]
        ds_p, ds_q = math.hypot(v[0], sy_p), math.hypot(-v[0], sy_q)
        if alturas[sp_q] > alturas[sp_p] and ds_p < cr_sum:
            hl[p] += sens_sombra[sp_p] * ((alturas[sp_q] - alturas[sp_p]) / alturas[sp_q]) * (1.0 - ds_p / cr_sum)
        if alturas[sp_p] > alturas[sp_q] and ds_q < cr_sum:
            hl[q] += sens_sombra[sp_q] * ((alturas[sp_p] - alturas[sp_q]) / alturas[sp_p]) * (1.0 - ds_q / cr_sum)
        #3. alelopatia quimica y 4. facilitacion nodriza de prosopis laevigata (especie 8)
        if sp_q == 8:
            if dist < copas[8]: ha[p] += 0.35 * (1.0 - dist / copas[8])
            if dist < 0.8 * copas[8]: hn[p] += es_nodriza[8] * math.exp(-(dist**2) / 12.5)
        if sp_p == 8:
            if dist < copas[8]: ha[q] += 0.35 * (1.0 - dist / copas[8])
            if dist < 0.8 * copas[8]: hn[q] += es_nodriza[8] * math.exp(-(dist**2) / 12.5)
    #calculo de aptitud multi-recurso no lineal tipo hill
    estres_w = sens_agua[especies_asignadas] * (1.0 + hw - 0.7 * np.minimum(hn, 1.0))
    rw = 1.0 / (1.0 + np.maximum(0.0, estres_w)**2)
    rl, ra = 1.0 / (1.0 + hl**2), 1.0 / (1.0 + ha**2)
    f_aptitud = (rw**0.60) * (rl**0.25) * (ra**0.15)
    f_aptitud[especies_asignadas < 0] = 0.0
    return hw, hl, ha, hn, f_aptitud

#optimizacion espacial mediante recocido simulado
def optimizar_recocido(coords, asignacion_inicial, es_submalla3, pasos=200, t_ini=5.0, t_fin=0.01, semilla=42):
    #recocido simulado para maximizar aptitud y respetar restricciones de submalla
    rng, pares = np.random.default_rng(semilla), cKDTree(coords).query_pairs(4.8, output_type="ndarray")
    solucion = asignacion_inicial.copy()
    _, _, _, _, f_act = evaluar_canales(coords, solucion, pares=pares)
    e_act = -float(np.mean(f_act[solucion >= 0]))
    mejor_sol, mejor_e, t, factor = solucion.copy(), e_act, t_ini, (t_fin / t_ini) ** (1.0 / max(1, pasos))
    ocupados = np.where(solucion >= 0)[0]
    for _ in range(pasos):
        ia, ib = rng.choice(ocupados, size=2, replace=False)
        sa, sb = solucion[ia], solucion[ib]
        if not (((submallas[sb] == 1) or es_submalla3[ia]) and ((submallas[sa] == 1) or es_submalla3[ib])):
            t *= factor; continue
        solucion[ia], solucion[ib] = sb, sa
        _, _, _, _, f_p = evaluar_canales(coords, solucion, pares=pares)
        e_p = -float(np.mean(f_p[solucion >= 0]))
        de = e_p - e_act
        if de < 0.0 or rng.random() < math.exp(-de / max(1e-6, t)):
            e_act = e_p
            if e_act < mejor_e: mejor_e, mejor_sol = e_act, solucion.copy()
        else:
            solucion[ia], solucion[ib] = sa, sb
        t *= factor
    return mejor_sol, -mejor_e

#formulacion milp con linealizacion rlt-1 y cortes k3 usando scipy highs
def resolver_milp_rlt_k3(coords_parche, aristas, triangulos_k3, demanda, es_sub3):
    #resuelve el milp de asignacion en un parche de la malla hexagonal
    n_p, n_s, n_e = len(coords_parche), n_especies, len(aristas)
    n_vars_x, n_vars_z = n_p * n_s, n_e * n_s
    n_total = n_vars_x + n_vars_z
    c_obj = np.zeros(n_total)
    for e_idx in range(n_e):
        for s in range(n_s): c_obj[n_vars_x + e_idx * n_s + s] = 1.0
    integridad = np.concatenate([np.ones(n_vars_x, dtype=int), np.zeros(n_vars_z, dtype=int)])
    filas_a, lb, ub = [], [], []
    for p in range(n_p):
        fila = np.zeros(n_total); fila[p * n_s : (p + 1) * n_s] = 1.0
        filas_a.append(fila); lb.append(0.0); ub.append(1.0)
        if not es_sub3[p]:
            for s in np.where(submallas == 3)[0]:
                fila_sub = np.zeros(n_total); fila_sub[p * n_s + s] = 1.0
                filas_a.append(fila_sub); lb.append(0.0); ub.append(0.0)
    for e_idx, (p, q) in enumerate(aristas):
        for s in range(n_s):
            fila_rlt = np.zeros(n_total); fila_rlt[n_vars_x + e_idx * n_s + s] = -1.0
            fila_rlt[p * n_s + s], fila_rlt[q * n_s + s] = 1.0, 1.0
            filas_a.append(fila_rlt); lb.append(-np.inf); ub.append(1.0)
    for tri in triangulos_k3:
        for s in np.where(submallas == 3)[0]:
            fila_k3 = np.zeros(n_total)
            for nodo in tri: fila_k3[nodo * n_s + s] = 1.0
            filas_a.append(fila_k3); lb.append(0.0); ub.append(1.0)
    res = milp(c=c_obj, integrality=integridad, constraints=LinearConstraint(np.array(filas_a), lb=lb, ub=ub))
    asignacion = np.full(n_p, -1, dtype=int)
    if res.success:
        x_mat = res.x[:n_vars_x].reshape((n_p, n_s))
        for p in range(n_p):
            sp_opt = int(np.argmax(x_mat[p]))
            if x_mat[p, sp_opt] > 0.5: asignacion[p] = sp_opt
    return asignacion, res.success

#simulacion monte carlo de 1000 corridas y cadena de markov
def ejecutar_1000_simulaciones(n_sims=1000):
    #ejecuta las 1000 simulaciones estocasticas y estima la matriz de transicion
    coords, indices_red, es_sub3 = construir_malla_hexagonal()
    j_vals = np.array([idx[1] for idx in indices_red])
    filas_unicas = np.sort(np.unique(j_vals))
    orden_boustro = []
    for num_fila, f_val in enumerate(filas_unicas):
        nodos_fila = np.where(j_vals == f_val)[0]
        orden_x = np.argsort(coords[nodos_fila, 0])
        if num_fila % 2 == 1: orden_x = orden_x[::-1]
        orden_boustro.extend(nodos_fila[orden_x])
    orden_boustro = np.array(orden_boustro, dtype=int)
    transiciones = np.zeros((n_especies, n_especies), dtype=int)
    costos = []
    for s in range(n_sims):
        nu, dem, _, _ = muestrear_suministros(semilla=s)
        costos.append(float(np.sum(dem * precios_vivero)))
        bolsa = []
        for sp_idx, cant in enumerate(dem): bolsa.extend([sp_idx] * cant)
        rng = np.random.default_rng(s)
        rng.shuffle(bolsa)
        for t in range(len(bolsa) - 1): transiciones[bolsa[t], bolsa[t + 1]] += 1
    sumas = transiciones.sum(axis=1, keepdims=True)
    p_mat = np.divide(transiciones, sumas, out=np.zeros_like(transiciones, dtype=float), where=sumas > 0)
    vals, vecs = np.linalg.eig(p_mat.T)
    pi_vec = np.real(vecs[:, np.argmin(np.abs(vals - 1.0))])
    pi_vec = np.maximum(0.0, pi_vec) / pi_vec.sum()
    tiempos_retorno = np.where(pi_vec > 1e-9, 1.0 / pi_vec, np.inf)
    return p_mat, pi_vec, tiempos_retorno, float(np.mean(costos)), float(np.std(costos)), orden_boustro, coords

#generacion del orden secuencial por etapas de plantacion
def generar_etapas_plantacion(orden_nodos, asignacion_especies, coords):
    #clasifica cada cepa en su etapa operativa: 1 nodrizas, 2 intermedias, 3 menores
    bitacora, paso, coord_ant = [], 1, None
    for nodo in orden_nodos:
        sp = asignacion_especies[nodo]
        if sp < 0: continue
        c_act = coords[nodo]
        d_paso = math.hypot(c_act[0] - coord_ant[0], c_act[1] - coord_ant[1]) if coord_ant is not None else 0.0
        coord_ant = c_act
        etapa = "etapa 1: nodriza/estructural" if submallas[sp] == 3 else ("etapa 2: maguey/nopal" if sp in [2,3,4,5,6] else "etapa 3: rosetofila menor")
        bitacora.append((paso, nodo, round(c_act[0], 2), round(c_act[1], 2), especies[sp], etapa, round(d_paso, 2)))
        paso += 1
    return bitacora

if __name__ == "__main__":
    #ejecucion del modelo completo de reforestacion estocastica
    print("modelo matematico y estocastico de reforestacion en 1 ha (sierra de alvarez)")
    coords, indices, es_sub3 = construir_malla_hexagonal()
    nu_ej, dem_ej, _, _ = muestrear_suministros(semilla=1)
    costo_base = float(np.sum(dem_ej * precios_vivero))
    print(f"malla: {len(coords)} nodos ({np.sum(es_sub3)} submalla 3) | preexistentes: {nu_ej.sum()} | nuevas: {dem_ej.sum()} | costo: ${costo_base:,.2f} mxn")
    asignacion = np.full(len(coords), -1, dtype=int)
    bolsa = []
    for sp_idx, cant in enumerate(dem_ej): bolsa.extend([sp_idx] * cant)
    rng = np.random.default_rng(1)
    rng.shuffle(bolsa)
    for i, nodo in enumerate(rng.choice(len(coords), size=len(bolsa), replace=False)): asignacion[nodo] = bolsa[i]
    _, _, _, _, f_ini = evaluar_canales(coords, asignacion)
    sol_opt, f_opt = optimizar_recocido(coords, asignacion, es_sub3, pasos=200, semilla=1)
    print(f"aptitud inicial: {np.mean(f_ini[asignacion >= 0]):.4f} | optimizada recocido: {f_opt:.4f}")
    idx_p = np.arange(14)
    arbol = cKDTree(coords[idx_p])
    sol_milp, exito = resolver_milp_rlt_k3(coords[idx_p], list(arbol.query_pairs(4.5)), [[0, 1, 2], [1, 2, 3]], dem_ej, es_sub3[idx_p])
    print(f"milp rlt-1 k3 (highs/scipy) resuelto: {exito}")
    p_mat, pi_vec, ret, c_med, c_std, orden_b, _ = ejecutar_1000_simulaciones(n_sims=1000)
    print(f"1000 simulaciones: costo ${c_med:,.2f} (+/- ${c_std:,.2f}) mxn | pi: {np.round(pi_vec, 3)}")
    bitacora = generar_etapas_plantacion(orden_b, sol_opt, coords)
    print(f"orden boustrophedon generado: {len(bitacora)} plantas secuenciadas")
