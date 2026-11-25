"""Testes do motor de simulação (simulate.py) usando banco em memória."""
import pytest
from models import get_engine, get_session_factory
from simulate import gerar_grade_de_cenarios, rodar_projeto, exportar_para_bi

BASE = dict(
    preco_unitario=1.0, quantidade_anual=456_000, custo_fixo_anual=124_749.70,
    custo_variavel_unitario=252_840.49 / 456_000, investimento_inicial=179_661.73,
    crescimento_anual=0.045,
)


def test_grade_gera_produto_cartesiano():
    grade = gerar_grade_de_cenarios(BASE, {"preco_unitario": [0.9, 1.0, 1.1],
                                           "quantidade_anual": [1, 2]})
    assert len(grade) == 6


def test_cenario_unico_quando_listas_tem_um_valor():
    grade = gerar_grade_de_cenarios(BASE, {"preco_unitario": [1.0]})
    assert len(grade) == 1


def test_rodar_e_exportar_sem_duplicar(tmp_path):
    engine = get_engine("sqlite://")
    Session = get_session_factory(engine)
    grade = gerar_grade_de_cenarios(BASE, {"preco_unitario": [0.9, 1.0, 1.1]})
    with Session() as s:
        for _ in range(2):  # roda duas vezes no mesmo banco
            p = rodar_projeto(s, "Teste", "", tma=0.116, horizonte_anos=10, lista_cenarios=grade)
        df = exportar_para_bi(s, str(tmp_path / "out.csv"), projeto_id=p.id)
    assert len(df) == 3  # só a rodada atual


def test_estudo_de_caso_bate_com_monografia(tmp_path):
    """A 80% da capacidade o ROI do estudo de caso é ~21% (Quadro de Viabilidade)."""
    engine = get_engine("sqlite://")
    Session = get_session_factory(engine)
    grade = gerar_grade_de_cenarios(BASE, {"quantidade_anual": [364_800]})
    with Session() as s:
        p = rodar_projeto(s, "Pura Fruta", "", tma=0.116, horizonte_anos=10, lista_cenarios=grade)
        df = exportar_para_bi(s, str(tmp_path / "out.csv"), projeto_id=p.id)
    assert df.loc[0, "roi"] == pytest.approx(0.21, abs=0.005)
    assert bool(df.loc[0, "viavel"]) is True
