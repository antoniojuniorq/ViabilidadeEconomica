"""
financial.py
Motor de cálculos de viabilidade econômica de projetos.

Reimplementa em Python os mesmos indicadores que a monografia descreve
sendo montados manualmente em planilhas Excel interligadas:
VPL, TIR, Payback simples, Payback descontado, ROI, ROE e Ponto de
Equilíbrio.

Nenhuma biblioteca "caixa-preta" de finanças é usada para o cálculo do
VPL/TIR — as fórmulas seguem exatamente a definição matemática citada
no capítulo 2.3.1 do trabalho, o que facilita auditar o resultado
célula a célula, como o autor da monografia fazia no Excel.
"""

from dataclasses import dataclass
from typing import Sequence
from scipy.optimize import brentq


def vpl(taxa: float, fluxos: Sequence[float]) -> float:
    """
    Valor Presente Líquido.
    fluxos[0] é o investimento inicial (deve ser negativo).
    fluxos[1:] são os fluxos de caixa dos períodos 1..n.
    """
    return sum(cf / (1 + taxa) ** t for t, cf in enumerate(fluxos))


def tir(fluxos: Sequence[float], chute_min: float = -0.99, chute_max: float = 10.0) -> float | None:
    """
    Taxa Interna de Retorno: taxa que zera o VPL.
    Retorna None se não houver raiz no intervalo (projeto sem TIR real).
    """
    f = lambda r: vpl(r, fluxos)
    try:
        if f(chute_min) * f(chute_max) > 0:
            return None
        return brentq(f, chute_min, chute_max)
    except (ValueError, ZeroDivisionError):
        return None


def payback_simples(fluxos: Sequence[float]) -> float | None:
    """
    Período de Recuperação do Investimento sem desconto (em nº de períodos).
    fluxos[0] = investimento inicial (negativo).
    """
    saldo = fluxos[0]
    for t in range(1, len(fluxos)):
        saldo_anterior = saldo
        saldo += fluxos[t]
        if saldo >= 0:
            # interpola dentro do período para uma fração mais precisa
            fracao = -saldo_anterior / fluxos[t] if fluxos[t] != 0 else 0
            return (t - 1) + fracao
    return None  # não recupera dentro do horizonte


def payback_descontado(fluxos: Sequence[float], taxa: float) -> float | None:
    """Igual ao payback simples, mas descontando cada fluxo pela TMA antes de acumular."""
    descontados = [cf / (1 + taxa) ** t for t, cf in enumerate(fluxos)]
    return payback_simples(descontados)


def roi(lucro_operacional: float, investimento_total: float) -> float:
    """Retorno sobre o Investimento, em fração (multiplique por 100 para %)."""
    return lucro_operacional / investimento_total


def roe(lucro_liquido: float, patrimonio_liquido: float) -> float:
    """Retorno sobre o Patrimônio Líquido, em fração."""
    return lucro_liquido / patrimonio_liquido


@dataclass
class PontoEquilibrio:
    receita_total: float
    quantidade: float


def ponto_equilibrio(custo_fixo: float, preco_unitario: float, custo_variavel_unitario: float) -> PontoEquilibrio:
    """
    Ponto de equilíbrio contábil: quantidade e receita em que Receita Total = Custo Total.
    """
    margem_contribuicao = preco_unitario - custo_variavel_unitario
    if margem_contribuicao <= 0:
        raise ValueError("Preço unitário deve ser maior que o custo variável unitário.")
    qtd_equilibrio = custo_fixo / margem_contribuicao
    receita_equilibrio = qtd_equilibrio * preco_unitario
    return PontoEquilibrio(receita_total=receita_equilibrio, quantidade=qtd_equilibrio)


def montar_fluxo_de_caixa(investimento_inicial: float, lucro_operacional_anual: float, horizonte_anos: int,
                           crescimento_anual: float = 0.0) -> list[float]:
    """
    Monta um fluxo de caixa simples: investimento no ano 0 seguido de
    'horizonte_anos' fluxos que crescem geometricamente pela taxa informada
    (usado para simular o efeito de crescimento econômico + inflação, como
    no item 3.4.14 'Projeção de resultado econômico' da monografia).
    """
    fluxos = [-investimento_inicial]
    fluxo = lucro_operacional_anual
    for _ in range(horizonte_anos):
        fluxos.append(fluxo)
        fluxo *= (1 + crescimento_anual)
    return fluxos
