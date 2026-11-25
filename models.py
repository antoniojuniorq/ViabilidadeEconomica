"""
models.py
Substitui a lógica de "pastas e planilhas interligadas por hiperlink"
descrita na monografia por um schema relacional simples.

Um Projeto tem N Cenários (ex.: 60%, 80%, 100% da capacidade, como no
Anexo 2 da monografia, ou qualquer outra combinação de premissas).
Cada Cenário gera um Resultado (os indicadores calculados por financial.py).
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Projeto(Base):
    __tablename__ = "projeto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(String(500), default="")
    horizonte_anos: Mapped[int] = mapped_column(Integer, default=10)
    tma: Mapped[float] = mapped_column(Float)  # Taxa Mínima de Atratividade
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    cenarios: Mapped[list["Cenario"]] = relationship(back_populates="projeto", cascade="all, delete-orphan")


class Cenario(Base):
    __tablename__ = "cenario"

    id: Mapped[int] = mapped_column(primary_key=True)
    projeto_id: Mapped[int] = mapped_column(ForeignKey("projeto.id"))
    nome: Mapped[str] = mapped_column(String(120))          # ex: "80% da capacidade"
    capacidade_pct: Mapped[float] = mapped_column(Float)     # ex: 0.8
    preco_unitario: Mapped[float] = mapped_column(Float)
    quantidade_anual: Mapped[float] = mapped_column(Float)
    custo_fixo_anual: Mapped[float] = mapped_column(Float)
    custo_variavel_unitario: Mapped[float] = mapped_column(Float)
    investimento_inicial: Mapped[float] = mapped_column(Float)
    crescimento_anual: Mapped[float] = mapped_column(Float, default=0.0)  # inflação + crescimento

    projeto: Mapped["Projeto"] = relationship(back_populates="cenarios")
    resultado: Mapped["Resultado"] = relationship(back_populates="cenario", uselist=False, cascade="all, delete-orphan")


class Resultado(Base):
    __tablename__ = "resultado"

    id: Mapped[int] = mapped_column(primary_key=True)
    cenario_id: Mapped[int] = mapped_column(ForeignKey("cenario.id"), unique=True)

    receita_total: Mapped[float] = mapped_column(Float)
    custo_total: Mapped[float] = mapped_column(Float)
    lucro_operacional: Mapped[float] = mapped_column(Float)
    vpl: Mapped[float] = mapped_column(Float)
    tir: Mapped[float | None] = mapped_column(Float, nullable=True)
    payback_simples: Mapped[float | None] = mapped_column(Float, nullable=True)
    payback_descontado: Mapped[float | None] = mapped_column(Float, nullable=True)
    roi: Mapped[float] = mapped_column(Float)
    ponto_equilibrio_qtd: Mapped[float] = mapped_column(Float)
    ponto_equilibrio_receita: Mapped[float] = mapped_column(Float)
    viavel: Mapped[bool] = mapped_column(default=False)

    cenario: Mapped["Cenario"] = relationship(back_populates="resultado")


def get_engine(caminho_db: str = "sqlite:///viabilidade.db"):
    return create_engine(caminho_db, echo=False)


def get_session_factory(engine):
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
