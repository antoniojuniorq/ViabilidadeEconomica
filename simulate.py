"""
simulate.py
Gera e calcula automaticamente N cenários para um projeto, grava tudo no
banco e exporta uma tabela plana (CSV) pronta para o Power BI (ou
qualquer outra ferramenta de BI) consumir.

É o equivalente automatizado de, na monografia, o projetista ficar
alterando manualmente preço/custo/capacidade em cada planilha e conferir
o resultado na planilha "Análise de Viabilidade".
"""

import itertools
import pandas as pd
from sqlalchemy.orm import Session

from models import get_engine, get_session_factory, Projeto, Cenario, Resultado
import financial as fin


def calcular_cenario(c: Cenario, horizonte_anos: int, tma: float) -> dict:
    receita_total = c.preco_unitario * c.quantidade_anual
    custo_variavel_total = c.custo_variavel_unitario * c.quantidade_anual
    custo_total = c.custo_fixo_anual + custo_variavel_total
    lucro_operacional = receita_total - custo_total

    fluxos = fin.montar_fluxo_de_caixa(
        investimento_inicial=c.investimento_inicial,
        lucro_operacional_anual=lucro_operacional,
        horizonte_anos=horizonte_anos,
        crescimento_anual=c.crescimento_anual,
    )

    pe = fin.ponto_equilibrio(c.custo_fixo_anual, c.preco_unitario, c.custo_variavel_unitario)

    valor_vpl = fin.vpl(tma, fluxos)
    valor_tir = fin.tir(fluxos)

    return dict(
        receita_total=receita_total,
        custo_total=custo_total,
        lucro_operacional=lucro_operacional,
        vpl=valor_vpl,
        tir=valor_tir,
        payback_simples=fin.payback_simples(fluxos),
        payback_descontado=fin.payback_descontado(fluxos, tma),
        roi=fin.roi(lucro_operacional, c.investimento_inicial),
        ponto_equilibrio_qtd=pe.quantidade,
        ponto_equilibrio_receita=pe.receita_total,
        viavel=valor_vpl > 0,
    )


def gerar_grade_de_cenarios(base: dict, variacoes: dict) -> list[dict]:
    """
    base: dicionário com os parâmetros fixos de um cenário (preco_unitario,
          quantidade_anual, custo_fixo_anual, custo_variavel_unitario,
          investimento_inicial, crescimento_anual).
    variacoes: dict {parametro: [lista de valores a testar]}.
    Retorna a combinação (produto cartesiano) de todas as variações —
    é assim que se chega a "centenas ou milhares de cenários automaticamente".
    """
    chaves = list(variacoes.keys())
    combinacoes = itertools.product(*variacoes.values())
    cenarios = []
    for combo in combinacoes:
        params = dict(base)
        nome_partes = []
        for chave, valor in zip(chaves, combo):
            params[chave] = valor
            nome_partes.append(f"{chave}={valor}")
        params["nome"] = " | ".join(nome_partes)
        cenarios.append(params)
    return cenarios


def rodar_projeto(session: Session, nome_projeto: str, descricao: str, tma: float,
                   horizonte_anos: int, lista_cenarios: list[dict]) -> Projeto:
    projeto = Projeto(nome=nome_projeto, descricao=descricao, tma=tma, horizonte_anos=horizonte_anos)
    session.add(projeto)
    session.flush()  # garante projeto.id

    for params in lista_cenarios:
        c = Cenario(
            projeto_id=projeto.id,
            nome=params["nome"],
            capacidade_pct=params.get("capacidade_pct", 1.0),
            preco_unitario=params["preco_unitario"],
            quantidade_anual=params["quantidade_anual"],
            custo_fixo_anual=params["custo_fixo_anual"],
            custo_variavel_unitario=params["custo_variavel_unitario"],
            investimento_inicial=params["investimento_inicial"],
            crescimento_anual=params.get("crescimento_anual", 0.0),
        )
        session.add(c)
        session.flush()

        indicadores = calcular_cenario(c, horizonte_anos, tma)
        resultado = Resultado(cenario_id=c.id, **indicadores)
        session.add(resultado)

    session.commit()
    return projeto


def exportar_para_bi(session: Session, caminho_csv: str = "resultados_bi.csv",
                      projeto_id: int | None = None) -> pd.DataFrame:
    """
    Achata Projeto + Cenário + Resultado em uma única tabela — formato que
    o Power BI (ou Metabase/Superset) consome sem nenhuma transformação.

    Se 'projeto_id' for informado, exporta só os cenários daquele projeto
    (evita que rodadas antigas, ainda guardadas no banco, se misturem com
    a rodada atual). Se vier None, exporta o histórico completo do banco.

    O CSV é salvo no formato do Excel brasileiro (vírgula decimal,
    ponto-e-vírgula separando colunas), então abre certo com duplo clique.
    """
    query = session.query(Cenario)
    if projeto_id is not None:
        query = query.filter(Cenario.projeto_id == projeto_id)

    linhas = []
    for c in query.all():
        r = c.resultado
        linhas.append(dict(
            projeto=c.projeto.nome,
            cenario=c.nome,
            capacidade_pct=c.capacidade_pct,
            preco_unitario=c.preco_unitario,
            quantidade_anual=c.quantidade_anual,
            investimento_inicial=c.investimento_inicial,
            receita_total=r.receita_total,
            custo_total=r.custo_total,
            lucro_operacional=r.lucro_operacional,
            vpl=r.vpl,
            tir=r.tir,
            payback_simples=r.payback_simples,
            payback_descontado=r.payback_descontado,
            roi=r.roi,
            ponto_equilibrio_qtd=r.ponto_equilibrio_qtd,
            ponto_equilibrio_receita=r.ponto_equilibrio_receita,
            viavel=r.viavel,
        ))
    df = pd.DataFrame(linhas)
    # sep=';' e decimal=',' -> formato que o Excel em português abre certo com duplo clique
    df.to_csv(caminho_csv, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return df


if __name__ == "__main__":
    import os

    # Recomeça do zero a cada execução: apaga o banco antigo (se existir)
    # para não acumular rodadas antigas junto com a atual. Se um dia você
    # quiser manter o histórico de todas as rodadas, é só remover essas
    # duas linhas e usar exportar_para_bi(session) sem o projeto_id.
    if os.path.exists("viabilidade.db"):
        os.remove("viabilidade.db")

    # Exemplo de ponta a ponta usando os próprios números do estudo de caso
    # "Pura Fruta Ltda" citados na monografia (Anexo 2 / Figuras 25 e 29).
    engine = get_engine("sqlite:///viabilidade.db")
    SessionLocal = get_session_factory(engine)

    with SessionLocal() as session:
        base = dict(
            preco_unitario=1.00,          # preço médio implícito na receita/demanda do caso
            quantidade_anual=456_000,
            custo_fixo_anual=124_749.70,
            custo_variavel_unitario=252_840.49 / 456_000,
            investimento_inicial=179_661.73,
            crescimento_anual=0.045,      # 4,5% a.a. citado no item 3.4.14
        )
        # grade automática: capacidade 60/80/100% e sensibilidade de +-10% no preço
        variacoes = {
            "quantidade_anual": [273_600, 364_800, 456_000],   # 60%, 80%, 100%
            "preco_unitario": [0.90, 1.00, 1.10],
        }
        cenarios = gerar_grade_de_cenarios(base, variacoes)

        projeto = rodar_projeto(
            session,
            nome_projeto="Pura Fruta Ltda",
            descricao="Reprodução do estudo de caso da monografia, com simulação automática de cenários.",
            tma=0.116,  # 11,6% a.a. citado na conclusão como taxa média da poupança
            horizonte_anos=10,
            lista_cenarios=cenarios,
        )

        df = exportar_para_bi(session, "resultados_bi.csv", projeto_id=projeto.id)
        print(f"Projeto '{projeto.nome}' criado com {len(cenarios)} cenários.")
        print(df[["cenario", "vpl", "tir", "payback_descontado", "roi", "viavel"]].to_string(index=False))
