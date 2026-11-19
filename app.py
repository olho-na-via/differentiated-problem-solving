"""
Differentiated Problem Solving - Global Solution 2026.2 (CitizenTech).

Olho na Via: cálculo diferencial e integral aplicado aos pedidos de
tapa-buraco da cidade de São Paulo (SP156, 2025 e 2026).

Aluno: Erick Nathan Capito Pereira - RM573635
Repositório: github.com/olho-na-via/differentiated-problem-solving

Como executar:
    pip install -r requirements.txt
    python app.py

Requisitos: numpy, pandas, scipy, sympy e matplotlib (seaborn só no notebook).
O script lê as bases agregadas em dados/ (geradas por preparar_dados.py
a partir dos microdados oficiais), imprime as análises de limites,
derivadas e integrais, salva os gráficos em figuras/ e grava os
resultados em resultados.json.

Estrutura (a mesma do notebook app.ipynb):
    Parte 1 - Demanda semanal de tapa-buraco: ajuste, derivadas,
              extremos e integral
    Parte 2 - Estoque de pedidos em aberto: integral de
              (entradas - saídas)
    Parte 3 - Tempo até o reparo: limites, derivada, integral
              imprópria e custo do atraso
    Parte 4 - Decisão: o que os resultados indicam para o protótipo
"""
import json
import pathlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sympy as sp
from scipy.integrate import cumulative_trapezoid, quad, trapezoid
from scipy.optimize import curve_fit

plt.switch_backend("Agg")

PASTA = pathlib.Path(__file__).parent
DADOS = PASTA / "dados"
FIGURAS = PASTA / "figuras"
FIGURAS.mkdir(exist_ok=True)

# Identidade visual do Olho na Via
VERDE = "#72C000"
VERDE_ESCURO = "#4E8A00"
ESCURO = "#16230E"
CINZA = "#8A9483"
plt.rcParams.update({
    "figure.figsize": (9, 4.8), "figure.dpi": 110, "savefig.dpi": 200,
    "axes.titlesize": 13, "axes.labelsize": 11,
    "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.7,
    "axes.edgecolor": "#B8C2B0", "axes.titleweight": "bold",
    "axes.titlecolor": ESCURO, "axes.labelcolor": ESCURO,
    "text.color": ESCURO, "xtick.color": ESCURO, "ytick.color": ESCURO,
    "mathtext.fontset": "dejavusans",
})

resultados = {}


def secao(titulo: str) -> None:
    """Imprime um título de seção no terminal."""
    print("\n" + "=" * 78)
    print(titulo)
    print("=" * 78)


def salvar(figura, nome: str) -> None:
    """Ajusta o layout, salva a figura em figuras/ e libera a memória."""
    figura.tight_layout()
    figura.savefig(FIGURAS / f"{nome}.png", facecolor="white")
    plt.close(figura)


def r2_rmse(observado: np.ndarray, estimado: np.ndarray) -> tuple:
    """R² e RMSE calculados explicitamente, sem funções prontas."""
    residuos = observado - estimado
    sse = float(np.sum(residuos ** 2))
    sst = float(np.sum((observado - observado.mean()) ** 2))
    return 1 - sse / sst, float(np.sqrt(sse / len(observado))), sse


def simpson_composto(f, a: float, b: float, n: int) -> float:
    """Regra de Simpson 1/3 composta (n par), sem chamar o SciPy."""
    if n <= 0 or n % 2:
        raise ValueError("A regra de Simpson 1/3 exige n par e positivo.")
    x = np.linspace(a, b, n + 1)
    y = f(x)
    h = (b - a) / n
    soma_impares = y[1:-1:2].sum()
    soma_pares = y[2:-1:2].sum()
    return float(h / 3 * (y[0] + y[-1] + 4 * soma_impares + 2 * soma_pares))


def media_movel(valores: np.ndarray) -> np.ndarray:
    """Média móvel centrada de 7 dias (remove o ciclo semanal)."""
    serie = pd.Series(valores).rolling(7, center=True, min_periods=1)
    return np.asarray(serie.mean(), dtype=float)


def modelo_sobrevivencia(d, amp_r, taxa_r, amp_l, taxa_l):
    """Fração ainda sem reparo após d dias.

    Soma de duas exponenciais: casos rápidos (amp_r, taxa_r) e
    cauda lenta (amp_l, taxa_l).
    """
    return amp_r * np.exp(-taxa_r * d) + amp_l * np.exp(-taxa_l * d)


def fmt_data(valor, formato: str = "%d/%m/%Y") -> str:
    """Formata uma data do pandas como texto."""
    return pd.Timestamp(valor).strftime(formato)


# ===========================================================================
# Dados
# ===========================================================================
secao("DADOS — SP156, serviço 'Tapa-buraco' "
      "(Portal de Dados Abertos da Prefeitura de SP)")
semanal = pd.read_csv(DADOS / "tapa_buraco_semanal.csv",
                      parse_dates=["inicio_semana", "fim_semana"])
coorte = pd.read_csv(DADOS / "coorte_2025_diaria.csv", parse_dates=["data"])
sobrevivencia = pd.read_csv(DADOS / "sobrevivencia_2025.csv")

entradas = coorte["entradas"].to_numpy(dtype=float)
finalizadas = coorte["finalizadas"].to_numpy(dtype=float)
canceladas = coorte["canceladas"].to_numpy(dtype=float)
datas = pd.to_datetime(coorte["data"])
total_2025 = int(entradas.sum())

intervalos = semanal["fim_semana"].diff().dropna()
contagens = coorte[["entradas", "finalizadas", "canceladas"]].to_numpy()
fracao = sobrevivencia["fracao_sem_reparo"].to_numpy(dtype=float)
checagens = {
    "Total de 2025 igual ao divulgado pela SMSUB (113,1 mil)":
        round(total_2025 / 1000, 1) == 113.1,
    "Semanas completas e consecutivas":
        bool((intervalos == pd.Timedelta(days=7)).all()),
    "Sem contagens negativas":
        bool((semanal["pedidos"].to_numpy() >= 0).all()
             and (contagens >= 0).all()),
    "Sem valores ausentes":
        not any(base.isna().to_numpy().any()
                for base in (semanal, coorte, sobrevivencia)),
    "Sobrevivência não crescente": bool((np.diff(fracao) <= 1e-12).all()),
}
for criterio, ok in checagens.items():
    print(f"  [{'OK' if ok else 'FALHA'}] {criterio}")
assert all(checagens.values())
print(f"Pedidos de tapa-buraco abertos em 2025: {total_2025}")
resultados["total_2025"] = total_2025

# ===========================================================================
# PARTE 1 - Demanda semanal: ajuste, derivadas, extremos e integral
# ===========================================================================
secao("PARTE 1 — Demanda semanal de tapa-buraco em 2025")
s25 = semanal[semanal["fim_semana"].dt.year == 2025].reset_index(drop=True)
s26 = semanal[semanal["fim_semana"].dt.year == 2026].reset_index(drop=True)
inicio_25 = pd.to_datetime(s25["inicio_semana"])
# Ponto médio de cada semana (semanas desde 06/01/2025)
tempo = np.arange(len(s25)) + 0.5
taxa = np.asarray(s25["pedidos"], dtype=float)  # pedidos por semana
n_sem = len(s25)
soma_semanas = int(taxa.sum())
i_max, i_min = int(np.argmax(taxa)), int(np.argmin(taxa))
print(f"Semanas completas em 2025: {n_sem} (06/01 a 28/12) | "
      f"pedidos nessas semanas: {soma_semanas}")
print(f"Média: {taxa.mean():.1f} pedidos/semana | "
      f"máximo: {taxa[i_max]:.0f} na semana de "
      f"{fmt_data(inicio_25[i_max], '%d/%m')} | "
      f"mínimo: {taxa[i_min]:.0f} na semana de "
      f"{fmt_data(inicio_25[i_min], '%d/%m')}")

# Taxa média de variação entre a 6ª semana (fev.) e a 46ª semana (nov.)
ta, tb = tempo[5], tempo[45]
tmv = (taxa[45] - taxa[5]) / (tb - ta)
print(f"Taxa média de variação entre t={ta} e t={tb}: "
      f"({taxa[45]:.0f} - {taxa[5]:.0f})/({tb}-{ta}) = "
      f"{tmv:.2f} pedidos/semana²")

coef_2 = np.polyfit(tempo, taxa, 2)
coef_3 = np.polyfit(tempo, taxa, 3)
q2, q3 = np.poly1d(coef_2), np.poly1d(coef_3)
a3, b3, c3, d3 = coef_3
r2_2, rmse_2, _ = r2_rmse(taxa, q2(tempo))
r2_3, rmse_3, sse_3 = r2_rmse(taxa, q3(tempo))
_, res_poly, _, _, _ = np.polyfit(tempo, taxa, 3, full=True)
assert np.isclose(sse_3, float(res_poly[0]))
print(f"q2(t) = {coef_2[0]:.6f} t² {coef_2[1]:+.6f} t {coef_2[2]:+.4f}"
      f"  | R² = {r2_2:.4f} | RMSE = {rmse_2:.1f}")
print(f"q3(t) = {a3:.8f} t³ {b3:+.6f} t² {c3:+.5f} t {d3:+.3f}"
      f"  | R² = {r2_3:.4f} | RMSE = {rmse_3:.1f}")

residuos_3 = taxa - q3(tempo)
pior = np.argsort(residuos_3)[:3]
print("Maiores superestimações (semanas com feriados):",
      [f"{fmt_data(inicio_25[i], '%d/%m')} ({residuos_3[i]:.0f})"
       for i in pior])

# Derivada pela definição (limite do quociente de Newton), com SymPy
t_s, h_s = sp.symbols("t h", real=True)
q3_s = (sp.Float(a3) * t_s**3 + sp.Float(b3) * t_s**2
        + sp.Float(c3) * t_s + sp.Float(d3))
quociente_s = (q3_s.subs(t_s, t_s + h_s) - q3_s) / h_s
derivada_definicao = sp.limit(quociente_s, h_s, 0)
dq3 = np.polyder(q3)
coef_definicao = [
    float(c)
    for c in sp.Poly(sp.expand(derivada_definicao), t_s).all_coeffs()
]
assert np.allclose(coef_definicao, dq3.coeffs, rtol=1e-9)
T0 = 20.5
quocientes = [(h, (q3(T0 + h) - q3(T0)) / h) for h in (1, 0.1, 0.01, 0.001)]
print(f"Quocientes de Newton em t0={T0}: "
      + ", ".join(f"h={h}: {v:.4f}" for h, v in quocientes)
      + f" → q3'({T0}) = {dq3(T0):.4f}")

pontos_derivada = [5.5, 25.5, 45.5]
for t_ in pontos_derivada:
    print(f"  q3'({t_}) = 3a·t² + 2b·t + c = {dq3(t_):.3f} pedidos/semana²")

coef_a, coef_b, coef_c = 3 * a3, 2 * b3, c3
delta = coef_b**2 - 4 * coef_a * coef_c
criticos = sorted([(-coef_b + np.sqrt(delta)) / (2 * coef_a),
                   (-coef_b - np.sqrt(delta)) / (2 * coef_a)])
d2q3 = np.polyder(q3, 2)
INICIO, FIM = 0.5, float(tempo[-1])


def classificar(t_critico: float) -> str:
    """Classifica um ponto crítico pelo sinal da segunda derivada."""
    return "mínimo local" if d2q3(t_critico) > 0 else "máximo local"


candidatos = (
    [(INICIO, "extremidade")]
    + [(c, classificar(c)) for c in criticos if INICIO < c < FIM]
    + [(FIM, "extremidade")]
)
for t_, tipo in candidatos:
    print(f"  t = {t_:.3f} semanas ({tipo}): q3 = {q3(t_):.1f} pedidos/semana")
for c in criticos:
    if not INICIO < c < FIM:
        print(f"  Ponto crítico fora do domínio de 2025: t = {c:.2f} semanas "
              f"({classificar(c)}, q3 = {q3(c):.1f})")
t_critico_q2 = -coef_2[1] / (2 * coef_2[0])
print(f"  Ponto crítico de q2: t = {t_critico_q2:.2f} semanas "
      f"(fora de [0,5; {FIM}])")
t_abs_max = max(candidatos, key=lambda z: q3(z[0]))[0]
t_abs_min = min(candidatos, key=lambda z: q3(z[0]))[0]
t_inflexao = -b3 / (3 * a3)
print(f"Máximo absoluto do modelo em t={t_abs_max:.2f}; "
      f"mínimo absoluto em t={t_abs_min:.2f}; "
      f"inflexão (queda mais rápida) em t={t_inflexao:.2f} "
      f"com q3'={dq3(t_inflexao):.2f}")


def primitiva_q3(t):
    """Primitiva de q3 obtida pela regra da potência (Q' = q3)."""
    return a3 / 4 * t**4 + b3 / 3 * t**3 + c3 / 2 * t**2 + d3 * t


integral_centros = primitiva_q3(FIM) - primitiva_q3(INICIO)
integral_ano = primitiva_q3(n_sem) - primitiva_q3(0)
assert np.isclose(integral_ano, quad(q3, 0, n_sem)[0])
trap_centros = trapezoid(taxa, tempo)
erro_ano = 100 * abs(integral_ano - soma_semanas) / soma_semanas
print(f"∫_0^{n_sem} q3 dt = {integral_ano:.1f} pedidos | "
      f"soma real = {soma_semanas} | erro = {erro_ano:.3f}%")
print(f"∫ entre centros = {integral_centros:.1f} | "
      f"trapézios dos dados = {trap_centros:.1f}")

# Comportamento extremo e validação fora da amostra (2026)
tempo_26 = FIM + np.arange(1, len(s26) + 1)
obs_26 = np.asarray(s26["pedidos"], dtype=float)
integral_26 = float(primitiva_q3(tempo_26[-1] + 0.5)
                    - primitiva_q3(tempo_26[0] - 0.5))
erro_26 = 100 * (integral_26 - obs_26.sum()) / obs_26.sum()
t_zero = [float(z.real) for z in np.roots(q3)
          if abs(z.imag) < 1e-9 and z.real > FIM]
raiz_futura = (f"t = {t_zero[0]:.1f}" if t_zero
               else "nenhuma (q3 > 0 depois de 2025)")
print(f"lim t→∞ q3(t) = {'+∞' if a3 > 0 else '-∞'} "
      f"(coeficiente líder a = {a3:.3e})")
print(f"2026 (jan-set, {len(s26)} semanas): observado {obs_26.sum():.0f} | "
      f"previsto pela cúbica {integral_26:.0f} ({erro_26:+.1f}%) | "
      f"primeira raiz futura de q3: {raiz_futura}")

resultados["parte1"] = {
    "n_semanas": n_sem,
    "soma_semanas": soma_semanas,
    "media": float(taxa.mean()),
    "max": float(taxa[i_max]),
    "semana_max": fmt_data(inicio_25[i_max]),
    "min": float(taxa[i_min]),
    "semana_min": fmt_data(inicio_25[i_min]),
    "tmv": float(tmv),
    "tmv_t": [float(ta), float(tb)],
    "tmv_q": [float(taxa[5]), float(taxa[45])],
    "coef2": [float(c) for c in coef_2],
    "coef3": [float(c) for c in coef_3],
    "r2_2": r2_2, "rmse_2": rmse_2, "r2_3": r2_3, "rmse_3": rmse_3,
    "piores": [[fmt_data(inicio_25[i], "%d/%m"), float(residuos_3[i])]
               for i in pior],
    "quocientes": [[h, float(v)] for h, v in quocientes],
    "t0": T0,
    "derivada_t0": float(dq3(T0)),
    "derivadas": [[t_, float(dq3(t_)), float(q3(t_))]
                  for t_ in pontos_derivada],
    "delta": float(delta),
    "criticos": [float(c) for c in criticos],
    "q_criticos": [float(q3(c)) for c in criticos],
    "t_critico_q2": float(t_critico_q2),
    "candidatos": [[float(t_), tipo, float(q3(t_)), float(d2q3(t_))]
                   for t_, tipo in candidatos],
    "t_abs_max": float(t_abs_max), "t_abs_min": float(t_abs_min),
    "q_abs_max": float(q3(t_abs_max)), "q_abs_min": float(q3(t_abs_min)),
    "t_inflexao": float(t_inflexao),
    "dq_inflexao": float(dq3(t_inflexao)),
    "integral_ano": float(integral_ano),
    "integral_centros": float(integral_centros),
    "trap_centros": float(trap_centros),
    "obs_26": float(obs_26.sum()),
    "prev_26": integral_26,
    "erro_26": float(erro_26),
    "semanas_26": len(s26),
    "raiz_futura": t_zero[0] if t_zero else None,
}

fig, ax = plt.subplots(figsize=(9.5, 4.6))
malha = np.linspace(INICIO, FIM, 600)
ax.scatter(tempo, taxa, s=22, color=ESCURO,
           label="Pedidos observados (2025)", zorder=3)
ax.plot(malha, q2(malha), color=CINZA, lw=1.8, ls="--",
        label=f"Grau 2 (R² = {r2_2:.3f})")
ax.plot(malha, q3(malha), color=VERDE, lw=2.6,
        label=f"Grau 3 (R² = {r2_3:.3f})")
for i in pior:
    ax.annotate(fmt_data(inicio_25[i], "%d/%m"), (tempo[i], taxa[i]),
                xytext=(0, -13), textcoords="offset points", ha="center",
                fontsize=8, color=CINZA)
ax.set(title="Pedidos semanais de tapa-buraco no SP156 (2025) "
             "e modelos ajustados",
       xlabel="Tempo t (semanas desde 06/01/2025)",
       ylabel="Pedidos por semana")
ax.legend(loc="upper right")
salvar(fig, "p1_ajuste")

fig, ax = plt.subplots(figsize=(9.5, 3.4))
ax.axhline(0, color=ESCURO, lw=0.9, ls="--")
ax.bar(tempo, residuos_3, width=0.7,
       color=[VERDE if r_ >= 0 else ESCURO for r_ in residuos_3])
for i in pior:
    ax.annotate(fmt_data(inicio_25[i], "%d/%m"), (tempo[i], residuos_3[i]),
                xytext=(0, -12), textcoords="offset points", ha="center",
                fontsize=8, color=ESCURO)
ax.set(title="Resíduos do modelo cúbico: subestima o verão e "
             "superestima feriados",
       xlabel="Tempo t (semanas desde 06/01/2025)",
       ylabel="Resíduo (pedidos/semana)")
salvar(fig, "p1_residuos")

fig, ax = plt.subplots(figsize=(9.5, 4.2))
ax.plot(malha, dq3(malha), color=VERDE_ESCURO, lw=2.4, label="q3'(t)")
ax.axhline(0, color=ESCURO, lw=0.9)
for c in criticos:
    if INICIO < c < FIM:
        ax.axvline(c, color=CINZA, ls="--", lw=1)
        ax.annotate(f"crítico\nt = {c:.1f}", (c, 0), xytext=(6, 12),
                    textcoords="offset points", fontsize=8)
ax.scatter([t_inflexao], [dq3(t_inflexao)], color=VERDE, s=50, zorder=3,
           label=f"Inflexão: queda mais rápida (t = {t_inflexao:.1f})")
ax.set(title="Derivada do modelo cúbico: quando a demanda cresce ou cai",
       ylim=(None, 4), xlabel="Tempo t (semanas)",
       ylabel="q3'(t) (pedidos/semana²)")
ax.legend(loc="upper center")
salvar(fig, "p1_derivada")

fig, ax = plt.subplots(figsize=(9.5, 4.4))
ax.scatter(tempo, taxa, s=18, color=ESCURO, label="Observado 2025 (ajuste)")
ax.scatter(tempo_26, obs_26, s=18, color=VERDE,
           label="Observado 2026 (validação)")
malha_ext = np.linspace(INICIO, tempo_26[-1] + 6, 800)
ax.plot(malha_ext, q3(malha_ext), color=VERDE_ESCURO, lw=2.2,
        label="Modelo cúbico extrapolado")
ax.axvspan(FIM + 0.5, malha_ext[-1], color=VERDE, alpha=0.07)
ax.axhline(0, color=ESCURO, lw=0.8)
ax.set(title="Comportamento extremo: a cúbica não serve para prever 2026",
       xlabel="Tempo t (semanas desde 06/01/2025)",
       ylabel="Pedidos por semana")
ax.legend(loc="lower left")
salvar(fig, "p1_validacao")

# ===========================================================================
# PARTE 2 - Estoque de pedidos em aberto: B(t) = ∫ (entradas - saídas) dt
# ===========================================================================
secao("PARTE 2 — Estoque de pedidos de 2025 ainda sem resposta")
saidas = finalizadas + canceladas
dias = np.arange(len(coorte), dtype=float)
saldo = entradas - saidas
estoque_discreto = np.cumsum(saldo)  # soma exata das contagens diárias
saldo_suave = media_movel(saldo)
estoque_continuo = (cumulative_trapezoid(saldo_suave, dias, initial=0)
                    + saldo_suave[0])
i_pico = int(np.argmax(estoque_discreto))
data_pico = datas.iloc[i_pico]
data_final = datas.iloc[-1]
fim_2025 = int(np.flatnonzero(datas == pd.Timestamp("2025-12-31"))[0])
abertos_final = int(estoque_discreto[-1])
assert abertos_final == (total_2025 - int(finalizadas.sum())
                         - int(canceladas.sum()))
print(f"B(t) = ∫ [e(s) - s(s)] ds | pico: {estoque_discreto[i_pico]:.0f} "
      f"pedidos em aberto em {fmt_data(data_pico)}")
print(f"Em 31/12/2025: {estoque_discreto[fim_2025]:.0f} pedidos de 2025 "
      "ainda abertos")
print(f"Em {fmt_data(data_final)}: {abertos_final} abertos "
      f"({100 * abertos_final / total_2025:.2f}% dos pedidos de 2025)")
print("Aproximação contínua (trapézios da média móvel) no pico: "
      f"{estoque_continuo[i_pico]:.0f}")
jan_abr = (datas < "2025-05-01").to_numpy()
mai_ago = ((datas >= "2025-05-01") & (datas < "2025-09-01")).to_numpy()
saldo_jan_abr = float(saldo[jan_abr].sum())
saldo_mai_ago = float(saldo[mai_ago].sum())
print(f"Variação do estoque: jan-abr {saldo_jan_abr:+.0f} | "
      f"mai-ago {saldo_mai_ago:+.0f}")
resultados["parte2"] = {
    "pico": float(estoque_discreto[i_pico]),
    "data_pico": fmt_data(data_pico),
    "fim_2025": float(estoque_discreto[fim_2025]),
    "abertos_final": abertos_final,
    "data_final": fmt_data(data_final),
    "pct_abertos": 100 * abertos_final / total_2025,
    "finalizadas": int(finalizadas.sum()),
    "canceladas": int(canceladas.sum()),
    "saldo_jan_abr": saldo_jan_abr,
    "saldo_mai_ago": saldo_mai_ago,
    "continuo_pico": float(estoque_continuo[i_pico]),
}

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.5, 6.4), sharex=True)
ax1.plot(datas, media_movel(entradas), color=ESCURO, lw=1.8,
         label="Entradas e(t) (média de 7 dias)")
ax1.plot(datas, media_movel(saidas), color=VERDE, lw=1.8,
         label="Saídas s(t) (média de 7 dias)")
ax1.set(ylabel="Pedidos por dia",
        title="Entradas e saídas dos pedidos de tapa-buraco abertos em 2025")
ax1.legend(loc="upper right")
ax2.fill_between(datas, estoque_discreto, color=VERDE, alpha=0.25)
ax2.plot(datas, estoque_discreto, color=VERDE_ESCURO, lw=2.2,
         label="B(t) = ∫ [e(s) − s(s)] ds")
ax2.scatter([data_pico], [estoque_discreto[i_pico]], color=ESCURO, zorder=3)
rotulo_pico = (f"pico: {estoque_discreto[i_pico]:,.0f}".replace(",", ".")
               + f"\n{fmt_data(data_pico)}")
ax2.annotate(rotulo_pico, (data_pico, estoque_discreto[i_pico]),
             xytext=(14, -26), textcoords="offset points", fontsize=9)
ax2.set(ylabel="Pedidos em aberto", xlabel="Data",
        title="Estoque acumulado de pedidos sem resposta")
salvar(fig, "p2_estoque")

# ===========================================================================
# PARTE 3 - Tempo até o reparo: S(d), limites, derivada e integral imprópria
# ===========================================================================
secao("PARTE 3 — Tempo até o reparo dos pedidos de 2025")
d_obs = sobrevivencia["dias"].to_numpy(dtype=float)
s_obs = fracao
horizonte = int(d_obs[-1])
mediana_obs = int(d_obs[np.argmax(s_obs <= 0.5)])
print(f"S(d) observada para d = 0..{horizonte} dias | S(0) = {s_obs[0]:.4f} "
      f"| mediana empírica: {mediana_obs} dias")
for d_ in (7, 30, 60, 90, 180, horizonte):
    print(f"  S({d_}) = {s_obs[d_]:.4f}  "
          f"({100 * s_obs[d_]:.1f}% ainda sem reparo)")

# Modelo 1: exponencial simples, ln S(d) = ln S0 - λ d (mínimos quadrados)
coef_log = np.polyfit(d_obs, np.log(s_obs), 1)
lam_1, s0_1 = -coef_log[0], float(np.exp(coef_log[1]))


def modelo_1(d):
    """Exponencial simples S(d) = S0·e^(-λ d), ajustada por logaritmos."""
    return s0_1 * np.exp(-lam_1 * d)


r2_m1, rmse_m1, _ = r2_rmse(s_obs, modelo_1(d_obs))

# Modelo 2: soma de duas exponenciais (rápidos + cauda lenta), curve_fit
params, _ = curve_fit(modelo_sobrevivencia, d_obs, s_obs,
                      p0=[0.8, 0.15, 0.1, 0.01], bounds=(0, [1, 5, 1, 5]),
                      maxfev=50000)
amp_a, lam_r, amp_b, lam_l = (float(p) for p in params)


def f_modelo(x):
    """Modelo de duas exponenciais com os parâmetros ajustados."""
    return modelo_sobrevivencia(x, amp_a, lam_r, amp_b, lam_l)


r2_m2, rmse_m2, _ = r2_rmse(s_obs, f_modelo(d_obs))
print(f"Modelo 1: S(d) = {s0_1:.4f}·e^(-{lam_1:.5f} d) | "
      f"R² = {r2_m1:.4f} | RMSE = {rmse_m1:.4f}")
print(f"Modelo 2: S(d) = {amp_a:.4f}·e^(-{lam_r:.5f} d) + "
      f"{amp_b:.4f}·e^(-{lam_l:.5f} d) | "
      f"R² = {r2_m2:.4f} | RMSE = {rmse_m2:.4f}")
meia_vida_r, meia_vida_l = np.log(2) / lam_r, np.log(2) / lam_l
print(f"Meia-vida dos casos rápidos: {meia_vida_r:.1f} dias | "
      f"da cauda lenta: {meia_vida_l:.1f} dias")

# Limites e derivadas com SymPy
d_s = sp.symbols("d", nonnegative=True)
k_s = sp.symbols("k", real=True)
s_sym = (sp.Float(amp_a) * sp.exp(-sp.Float(lam_r) * d_s)
         + sp.Float(amp_b) * sp.exp(-sp.Float(lam_l) * d_s))
lim_zero = float(sp.N(sp.limit(s_sym, d_s, 0, dir="+")))
lim_inf = sp.limit(s_sym, d_s, sp.oo)
ds_sym = sp.diff(s_sym, d_s)
risco = sp.simplify(-ds_sym / s_sym)  # taxa diária de reparo dos abertos
ds_num = sp.lambdify(d_s, ds_sym, "numpy")
risco_num = sp.lambdify(d_s, risco, "numpy")
print(f"lim d→0+ S(d) = {lim_zero:.4f} | lim d→∞ S(d) = {lim_inf} | "
      f"lim d→∞ h(d) = {lam_l:.5f} por dia")
for d_ in (1, 7, 30, 90):
    print(f"  S'({d_}) = {float(ds_num(d_)):.5f} por dia | "
          f"h({d_}) = -S'/S = {100 * float(risco_num(d_)):.2f}% ao dia")

# Integral imprópria: tempo médio = ∫_0^∞ S(d) dd = lim_{T→∞} ∫_0^T S dd
media_exata = float(sp.N(sp.integrate(s_sym, (d_s, 0, sp.oo))))
assert np.isclose(media_exata, amp_a / lam_r + amp_b / lam_l)


def area_modelo(limite):
    """∫_0^limite S(d) dd, pela primitiva do modelo de duas exponenciais."""
    return (amp_a / lam_r * (1 - np.exp(-lam_r * limite))
            + amp_b / lam_l * (1 - np.exp(-lam_l * limite)))


tabela_t = [(lim, float(area_modelo(lim)))
            for lim in (7, 30, 90, horizonte, 365, 730, 2000)]
area_trap = float(trapezoid(s_obs, d_obs))
n_simpson = horizonte if horizonte % 2 == 0 else horizonte - 1
area_simpson = simpson_composto(f_modelo, 0, horizonte, n_simpson)
print(f"∫_0^∞ S(d) dd = A/λr + B/λl = {media_exata:.2f} dias "
      "(tempo médio de espera previsto)")
print("  ∫_0^T S: " + ", ".join(f"T={lim}: {v:.2f}" for lim, v in tabela_t))
print(f"  Dados (trapézios, 0 a {horizonte} d): {area_trap:.2f} dias | "
      f"modelo (Simpson próprio): {area_simpson:.2f} dias")

# Quanto da espera está na cauda? Efeito de um limite máximo de τ dias
cauda = {tau: 1 - area_modelo(tau) / media_exata for tau in (14, 30, 60)}
reparados = float(sobrevivencia["reparados_ate_d"].to_numpy()[-1])
n_validos = int(reparados / (1 - s_obs[-1]))
buraco_dias = n_validos * media_exata
print(f"Pedidos de 2025 (não cancelados): {n_validos} | "
      f"buraco-dias de espera: {buraco_dias:,.0f}")
for tau, frac in cauda.items():
    print(f"  Fração da espera total acumulada depois de {tau} dias: "
          f"{100 * frac:.1f}% "
          f"(fração de pedidos: {100 * float(f_modelo(tau)):.1f}%)")

# Custo do atraso: buraco que cresce como e^(k d).
# D(k) = ∫_0^∞ S(d) e^(kd) dd converge somente se k < λl.
a_g, b_g, lr_g, ll_g = sp.symbols("A B lambda_r lambda_l", positive=True)
d_geral = a_g / (lr_g - k_s) + b_g / (ll_g - k_s)
lim_k = sp.limit(d_geral, k_s, ll_g, dir="-")
d_k = d_geral.subs({a_g: amp_a, b_g: amp_b, lr_g: lam_r, ll_g: lam_l})
d_k_num = sp.lambdify(k_s, d_k, "numpy")
dd_dk_num = sp.lambdify(k_s, sp.diff(d_k, k_s), "numpy")
cenarios_k = [0.0, 0.002, 0.005, 0.008]
tabela_k = [(k, float(d_k_num(k)), float(d_k_num(k)) / media_exata)
            for k in cenarios_k]
K_TESTE = 0.005
integral_k = quad(lambda x: (amp_a * np.exp((K_TESTE - lam_r) * x)
                             + amp_b * np.exp((K_TESTE - lam_l) * x)),
                  0, 20000, limit=500)[0]
assert np.isclose(tabela_k[2][1], integral_k, rtol=1e-6)
dd_dk0 = float(dd_dk_num(0.0))
print(f"D(k) = A/(λr-k) + B/(λl-k), válido para k < λl = {lam_l:.5f}; "
      f"lim k→λl⁻ D(k) = {lim_k}")
for k, v, razao in tabela_k:
    print(f"  k = {k:.3f}/dia: dano acumulado relativo D(k) = {v:.1f} "
          f"(×{razao:.2f} do caso sem crescimento)")
print(f"  dD/dk em k=0: {dd_dk0:.1f}")

resultados["parte3"] = {
    "S0": float(s_obs[0]),
    "mediana_obs": mediana_obs,
    "horizonte": horizonte,
    "S_pontos": {str(d_): float(s_obs[d_])
                 for d_ in (0, 1, 3, 6, 7, 14, 30, 60, 90, 180, horizonte)},
    "lam_1": float(lam_1), "S0_1": s0_1,
    "r2_m1": r2_m1, "rmse_m1": rmse_m1,
    "A": amp_a, "lam_r": lam_r, "B": amp_b, "lam_l": lam_l,
    "r2_m2": r2_m2, "rmse_m2": rmse_m2,
    "meia_vida_r": float(meia_vida_r), "meia_vida_l": float(meia_vida_l),
    "lim_zero": lim_zero,
    "derivadas": [[d_, float(ds_num(d_)), float(risco_num(d_))]
                  for d_ in (1, 7, 30, 90)],
    "media_exata": media_exata,
    "tabela_T": tabela_t,
    "area_trap": area_trap,
    "area_simpson": area_simpson,
    "cauda": {str(tau): v for tau, v in cauda.items()},
    "frac_pedidos": {str(tau): float(f_modelo(tau)) for tau in (14, 30, 60)},
    "n_validos": n_validos,
    "buraco_dias": float(buraco_dias),
    "tabela_k": tabela_k,
    "dD_dk0": dd_dk0,
}

fig, ax = plt.subplots(figsize=(9.5, 4.6))
malha_d = np.linspace(0, horizonte, 800)
ax.scatter(d_obs, s_obs, s=9, color=ESCURO,
           label="S(d) observada (pedidos de 2025)", zorder=3)
ax.plot(malha_d, modelo_1(malha_d), color=CINZA, lw=1.8, ls="--",
        label=f"Exponencial simples (R² = {r2_m1:.3f})")
ax.plot(malha_d, f_modelo(malha_d), color=VERDE, lw=2.6,
        label=f"Duas exponenciais (R² = {r2_m2:.3f})")
ax.axhline(0.5, color=CINZA, lw=0.8, ls=":")
ax.annotate(f"mediana ≈ {mediana_obs} dias", (mediana_obs, 0.5),
            xytext=(12, 10), textcoords="offset points", fontsize=9)
ax.set(title="Fração de buracos ainda sem reparo após d dias",
       xlabel="Dias desde a abertura do pedido (d)", ylabel="S(d)",
       ylim=(0, 1))
ax.legend(loc="upper right")
salvar(fig, "p3_sobrevivencia")

fig, ax = plt.subplots(figsize=(9.5, 4.2))
d_h = np.linspace(0, 180, 600)
ax.plot(d_h, 100 * risco_num(d_h), color=VERDE_ESCURO, lw=2.4,
        label="h(d) = −S'(d)/S(d)")
ax.axhline(100 * lam_l, color=CINZA, ls="--", lw=1,
           label=f"limite quando d→∞: {100 * lam_l:.2f}% ao dia")
ax.set(title="Chance diária de reparo de um buraco que ainda está aberto",
       xlabel="Dias em aberto (d)", ylabel="Taxa de reparo (% ao dia)",
       ylim=(0, None))
ax.legend(loc="upper right")
salvar(fig, "p3_taxa_reparo")

LIMITE_CAUDA = 30
fig, ax = plt.subplots(figsize=(9.5, 4.2))
d_c = np.linspace(0, 400, 800)
ax.fill_between(d_c, f_modelo(d_c), where=d_c <= LIMITE_CAUDA, color=VERDE,
                alpha=0.45, label=f"Até {LIMITE_CAUDA} dias: "
                f"{100 * (1 - cauda[LIMITE_CAUDA]):.0f}% da espera")
ax.fill_between(d_c, f_modelo(d_c), where=d_c >= LIMITE_CAUDA, color=ESCURO,
                alpha=0.30, label=f"Depois de {LIMITE_CAUDA} dias: "
                f"{100 * cauda[LIMITE_CAUDA]:.0f}% da espera")
ax.plot(d_c, f_modelo(d_c), color=ESCURO, lw=1.6)
ax.set(title="A integral de S(d) é o tempo médio de espera: "
             "a cauda pesa muito",
       xlabel="Dias desde a abertura (d)", ylabel="S(d)", ylim=(0, 0.9))
ax.legend(loc="upper right")
salvar(fig, "p3_integral")

# ===========================================================================
# PARTE 4 - Decisão para o protótipo
# ===========================================================================
secao("PARTE 4 — O que os resultados indicam para o Olho na Via")
print("1. A demanda de 2025 foi maior no 1º semestre (pico na semana de "
      f"{resultados['parte1']['semana_max']}) e o modelo cúbico indica "
      f"queda mais rápida por volta da semana {t_inflexao:.0f}; porém ele "
      f"falha em 2026 ({erro_26:+.0f}% no acumulado): planejar com dados "
      "recentes, não com extrapolação.")
print("2. O estoque de pedidos abertos cresceu até "
      f"{fmt_data(data_pico)} ({estoque_discreto[i_pico]:.0f}): a derivada "
      "B'(t) = e(t) - s(t) é o alerta antecipado de sobrecarga.")
print(f"3. Mediana de {mediana_obs} dias, mas "
      f"{100 * cauda[LIMITE_CAUDA]:.0f}% de toda a espera ocorre depois de "
      f"{LIMITE_CAUDA} dias, concentrada em "
      f"{100 * float(f_modelo(LIMITE_CAUDA)):.0f}% dos pedidos: a "
      "verificação e a variável T do IPV devem mirar a cauda.")
print(f"4. Se o buraco piora mais rápido que λl = {100 * lam_l:.2f}% ao dia, "
      "o dano acumulado esperado diverge: cortar a cauda vale mais que "
      "acelerar a mediana.")

with (PASTA / "resultados.json").open("w", encoding="utf-8") as arquivo:
    json.dump(resultados, arquivo, ensure_ascii=False, indent=2,
              default=float)
print(f"\nResultados gravados em resultados.json; gráficos em {FIGURAS.name}/")
