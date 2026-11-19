"""
Preparação dos dados - GS 2026.2 · Differentiated Problem Solving.

Projeto Olho na Via.

Este script NÃO precisa ser executado para rodar app.py ou app.ipynb: as
bases agregadas já estão na pasta dados/. Ele documenta como elas foram
produzidas a partir dos microdados oficiais do SP156 (Prefeitura de São
Paulo), garantindo a reprodutibilidade.

Fonte: Portal de Dados Abertos da Prefeitura de São Paulo - "Dados do
SP156 - Solicitações" (https://dados.prefeitura.sp.gov.br/dataset/
dados-do-sp156). Arquivos trimestrais de 2025 (1º ao 4º TRI) e de 2026
(1º ao 3º TRI), baixados em 09/11/2026. Coloque-os em microdados/ com os
nomes 2025_1.csv ... 2026_3.csv (ou indique a pasta na variável de
ambiente MICRODADOS_SP156).

Saídas (pasta dados/):
- tapa_buraco_semanal.csv : pedidos de tapa-buraco por semana (seg-dom),
                            2025 e 2026
- coorte_2025_diaria.csv  : entradas e saídas diárias dos pedidos
                            abertos em 2025
- sobrevivencia_2025.csv  : fração de pedidos de 2025 ainda sem reparo
                            após d dias
"""
import os
import pathlib

import numpy as np
import pandas as pd

PASTA = pathlib.Path(__file__).parent
MICRODADOS = pathlib.Path(
    os.environ.get("MICRODADOS_SP156", PASTA / "microdados")
)
SAIDA = PASTA / "dados"

ARQUIVOS = ["2025_1.csv", "2025_2.csv", "2025_3.csv", "2025_4.csv",
            "2026_1.csv", "2026_2.csv", "2026_3.csv"]
COLUNAS = ["Data de Abertura", "Data de Finalização", "Serviço", "Status"]
MESES_TRIMESTRE = {"1": (1, 3), "2": (4, 6), "3": (7, 9), "4": (10, 12)}
FORMATOS_DATA = ("%d/%m/%Y", "%m/%d/%Y")


def detectar_separador(arquivo: pathlib.Path) -> str:
    """Escolhe ';' ou ',' conforme o que aparece mais no cabeçalho."""
    with arquivo.open("rb") as entrada:
        primeira_linha = entrada.readline()
    if primeira_linha.count(b";") > primeira_linha.count(b","):
        return ";"
    return ","


def ler_csv(arquivo: pathlib.Path, separador: str) -> pd.DataFrame:
    """Lê as colunas necessárias, tentando UTF-8 e depois Latin-1."""
    for codificacao in ("utf-8", "latin1"):
        try:
            return pd.read_csv(arquivo, sep=separador, encoding=codificacao,
                               usecols=COLUNAS, dtype=str,
                               on_bad_lines="skip", low_memory=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não foi possível ler {arquivo.name}")


def converter_datas(valores: pd.Series, formato: str) -> pd.Series:
    """Converte texto em datas no formato informado (inválidas viram NaT)."""
    return pd.Series(pd.to_datetime(valores, format=formato, errors="coerce"),
                     index=valores.index)


def detectar_formato(abertura: pd.Series, arquivo: pathlib.Path) -> tuple:
    """Descobre se as datas estão em dia/mês ou mês/dia.

    O arquivo do 3º TRI de 2026 usa mês/dia/ano; os demais usam dia/mês/ano.
    O formato correto é o que coloca mais aberturas dentro do trimestre.
    """
    mes_inicial, mes_final = MESES_TRIMESTRE[arquivo.stem.split("_")[1]]
    melhor_formato, melhor_fracao = FORMATOS_DATA[0], -1.0
    for formato in FORMATOS_DATA:
        meses = converter_datas(abertura, formato).dt.month
        fracao = float(meses.between(mes_inicial, mes_final).mean())
        if fracao > melhor_fracao:
            melhor_formato, melhor_fracao = formato, fracao
    return melhor_formato, melhor_fracao


def coluna(tabela: pd.DataFrame, nome: str) -> pd.Series:
    """Devolve uma coluna da tabela como Series."""
    return pd.Series(tabela[nome])


def ler_trimestre(arquivo: pathlib.Path) -> pd.DataFrame:
    """Lê um arquivo trimestral e devolve só os pedidos de tapa-buraco."""
    separador = detectar_separador(arquivo)
    tabela = ler_csv(arquivo, separador)
    servico = tabela["Serviço"].str.strip().str.lower()
    tabela = pd.DataFrame(tabela.loc[servico == "tapa-buraco"]).copy()

    abertura = coluna(tabela, "Data de Abertura")
    formato, fracao = detectar_formato(abertura, arquivo)
    tabela["abertura"] = converter_datas(abertura, formato)
    tabela["finalizacao"] = converter_datas(
        coluna(tabela, "Data de Finalização"), formato)
    tabela["arquivo"] = arquivo.name
    print(f"{arquivo.name}: {len(tabela)} pedidos de tapa-buraco | "
          f"separador '{separador}' | formato {formato} | "
          f"{fracao:.2%} das datas no trimestre")
    return tabela


def contar_por_dia(datas: pd.Series, dias: pd.DatetimeIndex) -> np.ndarray:
    """Conta quantos registros caem em cada dia do intervalo."""
    contagem = datas.dropna().value_counts()
    return contagem.reindex(dias, fill_value=0).to_numpy(dtype=int)


def gerar_semanal(base: pd.DataFrame) -> None:
    """Série semanal (semanas completas de segunda a domingo)."""
    dias = pd.date_range("2025-01-06", "2026-09-27", freq="D")
    diaria = pd.Series(contar_por_dia(coluna(base, "abertura"), dias),
                       index=dias)
    semanal = diaria.resample("W-SUN").sum()
    fim = pd.DatetimeIndex(semanal.index)
    inicio = fim - pd.Timedelta(days=6)
    pd.DataFrame({
        "inicio_semana": inicio.strftime("%Y-%m-%d"),
        "fim_semana": fim.strftime("%Y-%m-%d"),
        "pedidos": semanal.to_numpy(dtype=int),
    }).to_csv(SAIDA / "tapa_buraco_semanal.csv", index=False)


def gerar_coorte(coorte: pd.DataFrame, fim: pd.Timestamp) -> None:
    """Entradas (abertura) e saídas (finalização ou cancelamento) por dia."""
    dias = pd.date_range("2025-01-01", fim, freq="D")
    status = coorte["Status"]
    pd.DataFrame({
        "data": dias.strftime("%Y-%m-%d"),
        "entradas": contar_por_dia(coluna(coorte, "abertura"), dias),
        "finalizadas": contar_por_dia(
            pd.Series(coorte.loc[status == "Finalizada", "finalizacao"]),
            dias),
        "canceladas": contar_por_dia(
            pd.Series(coorte.loc[status == "Cancelada", "finalizacao"]),
            dias),
    }).to_csv(SAIDA / "coorte_2025_diaria.csv", index=False)


def gerar_sobrevivencia(coorte: pd.DataFrame, fim: pd.Timestamp) -> tuple:
    """Fração de pedidos (não cancelados) ainda sem reparo após d dias.

    Todos os pedidos de 2025 têm acompanhamento até `fim`, de modo que
    S(d) é exata para d <= (fim - 31/12/2025).
    """
    validos = pd.DataFrame(coorte.loc[coorte["Status"] != "Cancelada"])
    espera = pd.Series(validos["finalizacao"] - validos["abertura"])
    dias_ate_reparo = espera.dt.days.to_numpy(dtype=float)
    finalizado = (validos["Status"] == "Finalizada").to_numpy()
    horizonte = int((fim - pd.Timestamp("2025-12-31")).days)
    total = len(validos)
    linhas = []
    for d in range(horizonte + 1):
        reparados = int((finalizado & (dias_ate_reparo <= d)).sum())
        linhas.append({"dias": d, "reparados_ate_d": reparados,
                       "fracao_sem_reparo": (total - reparados) / total})
    pd.DataFrame(linhas).to_csv(SAIDA / "sobrevivencia_2025.csv",
                                index=False)
    return total, horizonte


def main() -> None:
    """Lê os microdados e grava as três bases agregadas em dados/."""
    SAIDA.mkdir(exist_ok=True)
    base = pd.concat([ler_trimestre(MICRODADOS / nome) for nome in ARQUIVOS],
                     ignore_index=True)
    assert bool(base["abertura"].notna().all()), \
        "Há pedidos sem data de abertura válida."

    gerar_semanal(base)

    ano_abertura = pd.Series(base["abertura"]).dt.year
    coorte = pd.DataFrame(base.loc[ano_abertura == 2025])
    finalizacoes = coluna(coorte, "finalizacao").dropna().to_numpy()
    fim_observacao = pd.Timestamp(finalizacoes.max())
    if not isinstance(fim_observacao, pd.Timestamp):
        raise TypeError("Nenhum pedido de 2025 tem data de finalização.")
    gerar_coorte(coorte, fim_observacao)
    total, horizonte = gerar_sobrevivencia(coorte, fim_observacao)

    print(f"Pedidos de 2025: {len(coorte)} | não cancelados: {total} | "
          f"fim da observação: {fim_observacao.date()} | "
          f"horizonte completo: {horizonte} dias")


if __name__ == "__main__":
    main()
