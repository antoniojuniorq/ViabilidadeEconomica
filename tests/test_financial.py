"""Testes das fórmulas financeiras (financial.py)."""
import pytest
import financial as fin

FLUXOS = [-1000, 300, 300, 300, 300, 300]


def test_vpl_valor_conhecido():
    assert fin.vpl(0.10, FLUXOS) == pytest.approx(137.24, abs=0.01)


def test_vpl_taxa_zero_e_soma_simples():
    assert fin.vpl(0.0, FLUXOS) == pytest.approx(500.0)


def test_tir_zera_o_vpl():
    r = fin.tir(FLUXOS)
    assert r == pytest.approx(0.1524, abs=0.0001)
    assert fin.vpl(r, FLUXOS) == pytest.approx(0.0, abs=1e-6)


def test_tir_negativa_quando_nao_recupera_o_investimento():
    assert fin.tir([-1000, 100, 100]) < 0


def test_tir_inexistente_sem_troca_de_sinal():
    assert fin.tir([100, 100, 100]) is None


def test_payback_simples():
    assert fin.payback_simples(FLUXOS) == pytest.approx(3.33, abs=0.01)


def test_payback_nao_recupera():
    assert fin.payback_simples([-1000, 100, 100]) is None


def test_payback_descontado_maior_que_simples():
    assert fin.payback_descontado(FLUXOS, 0.10) > fin.payback_simples(FLUXOS)


def test_roi():
    assert fin.roi(30_000, 100_000) == pytest.approx(0.30)


def test_ponto_equilibrio():
    pe = fin.ponto_equilibrio(custo_fixo=50_000, preco_unitario=25, custo_variavel_unitario=9.5)
    assert pe.quantidade == pytest.approx(50_000 / 15.5)
    assert pe.receita_total == pytest.approx(pe.quantidade * 25)


def test_ponto_equilibrio_margem_negativa():
    with pytest.raises(ValueError):
        fin.ponto_equilibrio(1000, preco_unitario=5, custo_variavel_unitario=6)


def test_montar_fluxo_com_crescimento():
    f = fin.montar_fluxo_de_caixa(1000, 100, 3, crescimento_anual=0.10)
    assert f == pytest.approx([-1000, 100, 110, 121])
