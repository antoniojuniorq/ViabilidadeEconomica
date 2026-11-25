# Viabilidade de Projetos — Python + Banco de Dados + Power BI

Motor de análise de viabilidade econômica de projetos em Python. Calcula **VPL, TIR, Payback (simples e descontado), ROI e ponto de equilíbrio**, simula centenas de cenários automaticamente, guarda tudo em banco de dados e exporta uma tabela pronta para o **Power BI**.

O projeto parte de uma monografia da UFSC que montava esse tipo de análise com dezenas de planilhas Excel interligadas por hiperlink, e a reimplementa como código versionável e testável:

> MIRANDA, Edir Goulart de Souza. *Uma aplicação prática em Excel na análise de projetos de viabilidade econômica*. Monografia (Ciências Econômicas), UFSC, Florianópolis, 2010.

## Por que não Excel?

| Excel (monografia) | Este projeto |
|---|---|
| Alterar premissas célula a célula | Grade automática de cenários (produto cartesiano de premissas) |
| Um erro de fórmula pode comprometer tudo (item 3.4.9 da monografia) | Fórmulas isoladas em funções com testes automatizados |
| Dados espalhados em pastas e arquivos | Banco relacional: `projeto → cenário → resultado` |
| Gráficos montados manualmente | Dashboard no Power BI que atualiza com um clique |

## Estrutura

```
viabilidade-projetos/
├── financial.py        # fórmulas: VPL, TIR, Payback, ROI, ROE, ponto de equilíbrio
├── models.py           # tabelas do banco (SQLAlchemy): Projeto, Cenario, Resultado
├── simulate.py         # gera cenários, calcula, grava no banco e exporta o CSV
├── tests/              # testes automatizados (pytest)
├── requirements.txt
└── pytest.ini
```

Fluxo: **premissas → `simulate.py` → banco SQLite → `resultados_bi.csv` → Power BI**

## Instalação

Requer Python 3.10 ou superior.

```bash
git clone <url-do-seu-repositorio>
cd viabilidade-projetos

python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux / Mac:  source .venv/bin/activate

pip install -r requirements.txt
```

## Uso rápido

```bash
python simulate.py
```

Roda o estudo de caso "Pura Fruta Ltda" da monografia (9 cenários: 3 níveis de capacidade × 3 níveis de preço) e gera:

- `viabilidade.db`: banco SQLite com todos os cenários e resultados;
- `resultados_bi.csv`: tabela plana pronta para o Power BI e o Excel (separador `;`, decimal `,`).

> A cada execução o banco é recriado do zero, então rodar duas vezes não duplica cenários.

### Resultado do exemplo

| Quantidade anual | Preço | VPL | ROI | Viável |
|---|---|---|---|---|
| 273.600 (60%) | 1,00 | −199.028 | −1,6% | não |
| 364.800 (80%) | 1,00 | 76.681 | 21,0% | **sim** |
| 456.000 (100%) | 1,00 | 352.390 | 43,6% | **sim** |

O ROI de ~21% a 80% da capacidade coincide com o "Quadro de Viabilidade Econômica" da monografia, e é coberto por um teste automatizado.

## Usando com seus próprios números

Edite o bloco `if __name__ == "__main__":` no final de `simulate.py`.

```python
base = dict(
    preco_unitario=25.0,            # preço de venda de 1 unidade
    quantidade_anual=12000,         # unidades vendidas por ano
    custo_fixo_anual=180000,        # aluguel, salários fixos etc.
    custo_variavel_unitario=9.5,    # custo de produzir 1 unidade
    investimento_inicial=250000,    # quanto custa começar o projeto
    crescimento_anual=0.05,         # crescimento anual (0.05 = 5%)
)

variacoes = {                        # o que testar, em torno do base
    "preco_unitario": [22, 25, 28],
    "quantidade_anual": [9000, 12000, 15000],
}
# 3 x 3 = 9 cenários. Para testar só o seu número, use listas de 1 item.
```

Ajuste também `tma` (taxa mínima de atratividade, ex.: `0.12` = 12% a.a.) e `horizonte_anos` na chamada de `rodar_projeto`.

**Atenção:** os valores de `variacoes` têm prioridade sobre o `base` para o mesmo campo.

### Como usar como biblioteca

```python
import financial as fin

fluxos = [-100000, 30000, 30000, 30000, 30000, 30000]  # ano 0 negativo
fin.vpl(0.10, fluxos)
fin.tir(fluxos)
fin.payback_simples(fluxos)
fin.payback_descontado(fluxos, 0.10)
fin.roi(lucro_operacional=30000, investimento_total=100000)
fin.ponto_equilibrio(custo_fixo=50000, preco_unitario=25, custo_variavel_unitario=9.5)
```

## Indicadores

| Indicador | Interpretação |
|---|---|
| **VPL** | Valor presente dos fluxos descontados pela TMA, menos o investimento. Positivo = viável. |
| **TIR** | Taxa que zera o VPL. Viável quando maior que a TMA. Vazia quando não existe (fluxo sem troca de sinal). |
| **Payback simples / descontado** | Anos para recuperar o investimento (sem / com desconto). Vazio = não recupera no horizonte. |
| **ROI** | Lucro operacional anual ÷ investimento inicial. |
| **Ponto de equilíbrio** | Quantidade e receita em que receita total = custo total. |

Critério de viabilidade adotado: `VPL > 0`.

## Power BI

1. **Obter dados → Texto/CSV** e selecione `resultados_bi.csv`.
2. Crie um gráfico de colunas com `cenario` (eixo X) e `vpl` (eixo Y); arraste `viavel` para a legenda.
3. Salve o `.pbix`.
4. Para cada nova rodada: rode `python simulate.py` e clique em **Atualizar** no Power BI. O gráfico se redesenha sem refazer os campos.

Para uso contínuo, troque o SQLite por PostgreSQL (`pip install psycopg2-binary` e use `get_engine("postgresql+psycopg2://usuario:senha@host:5432/banco")`) e conecte o Power BI direto ao banco.

## Testes

```bash
pytest
```

Cobrem as fórmulas financeiras (valores conhecidos, casos de borda como TIR inexistente e margem negativa) e o motor de simulação (grade de cenários, ausência de duplicação, conferência com a monografia).

## Limitações

- O fluxo de caixa é simplificado: lucro operacional anual crescendo a uma taxa constante, sem impostos sobre o lucro, depreciação ou capital de giro modelados separadamente.
- O ponto de equilíbrio é contábil (não considera valor do dinheiro no tempo).
- O estudo de caso usa preço unitário de R$ 1,00, valor implícito na relação receita/demanda da monografia.

## Possíveis próximos passos

- Dashboard em Streamlit ou Plotly Dash, 100% Python;
- API (FastAPI) para simular cenários por requisição;
- Capital de giro, financiamento e imposto de renda no fluxo de caixa;
- Análise de sensibilidade (gráfico tornado) e simulação de Monte Carlo.

## Licença

Defina a licença do seu repositório (por exemplo, MIT) antes de publicar.
