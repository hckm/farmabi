"""Numeros de referencia do prototipo docs/prototipo/FarmaBI_Prototipo_Interativo.html (objetos DATA e INVENTORY).

Fonte unica para o gerador de dados e para a conferencia do banco. Todos os valores sao ficticios.
"""
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Canal:
    canal_id: int
    codigo: str
    nome: str
    cor: str


@dataclass(frozen=True)
class RefComercial:
    vendas: int            # vendas liquidas em reais
    pedidos: int
    orcamentos: int
    atendimentos: int
    compradores: int
    novos: int
    resposta_min: float    # primeira resposta humana media, em minutos
    frequencia: tuple      # clientes com 1, 2 e 3 compras no mes
    recompra_90d: float    # % exibido no mes (coorte de tres meses antes)


@dataclass(frozen=True)
class LoteAmostra:
    insumo: str
    lote_codigo: str
    saldo: float
    validade: date


@dataclass(frozen=True)
class RefEstoque:
    valor_total: int
    abaixo_minimo: int
    vencendo_30d: int
    valor_em_risco: int
    vencidos: int
    faixas: tuple          # lotes: vencidos, 0-30, 31-60, 61-90, >90 dias
    categorias: dict       # valor por categoria
    amostra: tuple


CANAIS = (
    Canal(1, "wa", "WhatsApp", "#15a589"),
    Canal(2, "balcao", "Balcão", "#5488d8"),
    Canal(3, "site", "Site", "#8c7ad8"),
)

MESES = (date(2026, 5, 1), date(2026, 6, 1), date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1))

_R = RefComercial
COMERCIAL = {
    date(2026, 5, 1): {
        "wa": _R(73500, 525, 790, 920, 397, 120, 6.2, (310, 68, 19), 38.0),
        "balcao": _R(35700, 263, 355, 440, 210, 62, 3.2, (161, 39, 10), 36.3),
        "site": _R(16800, 120, 205, 247, 94, 37, 2.1, (70, 21, 3), 35.1),
    },
    date(2026, 6, 1): {
        "wa": _R(80000, 558, 833, 975, 420, 127, 6.0, (325, 73, 22), 39.1),
        "balcao": _R(39000, 283, 378, 465, 221, 63, 2.9, (168, 42, 11), 37.9),
        "site": _R(19000, 128, 214, 256, 99, 37, 1.9, (74, 22, 3), 36.2),
    },
    date(2026, 7, 1): {
        "wa": _R(83000, 586, 871, 1028, 445, 133, 5.9, (341, 79, 25), 40.2),
        "balcao": _R(40500, 293, 391, 474, 225, 61, 2.8, (170, 44, 11), 38.6),
        "site": _R(19500, 131, 221, 266, 100, 38, 1.8, (74, 22, 4), 37.4),
    },
    date(2026, 8, 1): {
        "wa": _R(88800, 627, 930, 1100, 485, 139, 5.8, (372, 84, 29), 41.4),
        "balcao": _R(42300, 308, 410, 493, 235, 64, 2.6, (175, 47, 13), 40.2),
        "site": _R(19900, 139, 231, 278, 103, 40, 1.6, (72, 26, 5), 38.7),
    },
    date(2026, 9, 1): {
        "wa": _R(95600, 652, 972, 1165, 503, 143, 5.6, (384, 89, 30), 42.1),
        "balcao": _R(46100, 332, 436, 525, 252, 67, 2.5, (186, 52, 14), 41.3),
        "site": _R(22700, 143, 238, 290, 113, 42, 1.5, (87, 22, 4), 39.8),
    },
    date(2026, 10, 1): {
        "wa": _R(108300, 729, 1080, 1280, 553, 160, 5.4, (413, 104, 36), 43.2),
        "balcao": _R(51200, 358, 470, 560, 265, 76, 2.3, (188, 61, 16), 42.1),
        "site": _R(25900, 161, 262, 320, 128, 51, 1.4, (99, 25, 4), 41.1),
    },
}

def frequencia_ajustada(alvo: RefComercial) -> tuple:
    """Frequencia (1, 2, 3+) compativel com pedidos e compradores.

    Em Mai-Jul o prototipo traz faixas que nao fecham com o total de pedidos. Pedidos e compradores sao
    preservados: sobra de pedidos vai para clientes da faixa 3+ (4 ou mais compras); falta de pedidos move
    clientes da faixa 2 para a faixa 1.
    """
    f1, f2, f3 = alvo.frequencia
    diferenca = alvo.pedidos - (f1 + 2 * f2 + 3 * f3)
    if diferenca < 0:
        if -diferenca > f2:
            raise ValueError(f"frequencia irreconciliavel: {alvo}")
        f1, f2 = f1 - diferenca, f2 + diferenca
    elif diferenca > 0 and f3 == 0:
        raise ValueError(f"frequencia irreconciliavel: {alvo}")
    return f1, f2, f3


# Regras do prototipo para orcamentos nao convertidos.
FATOR_PERDIDOS = 0.69
MOTIVOS_PERDA = (("Preço", 0.41), ("Prazo de entrega", 0.24), ("Sem retorno", 0.21), ("Outros motivos", None))

# Pedidos extras fora dos indicadores (decisao da sabatina).
TAXA_CANCELADOS = 0.03
TAXA_DEVOLVIDOS = 0.02

CATEGORIAS = ("Ativos", "Bases", "Excipientes", "Embalagens")

_E = RefEstoque
_L = LoteAmostra
ESTOQUE = {
    date(2026, 8, 31): _E(
        263800, 19, 13, 10900, 2, (2, 13, 19, 27, 143),
        {"Ativos": 119000, "Bases": 67000, "Excipientes": 49300, "Embalagens": 28500},
        (_L("Niacinamida", "MP-0831", 4.2, date(2026, 9, 8)),
         _L("Base creme não iônica", "BS-0127", 3.6, date(2026, 9, 17)),
         _L("Vitamina C", "MP-0672", 1.4, date(2026, 9, 26))),
    ),
    date(2026, 9, 30): _E(
        274600, 20, 14, 12400, 3, (3, 14, 21, 28, 151),
        {"Ativos": 124000, "Bases": 69000, "Excipientes": 51600, "Embalagens": 30000},
        (_L("Magnésio bisglicinato", "MP-0931", 2.1, date(2026, 10, 6)),
         _L("Niacinamida", "MP-0918", 1.7, date(2026, 10, 15)),
         _L("Vitamina D3", "MP-0755", 0.8, date(2026, 10, 24))),
    ),
    date(2026, 10, 31): _E(
        283400, 23, 17, 14800, 4, (4, 17, 22, 31, 158),
        {"Ativos": 128000, "Bases": 72100, "Excipientes": 51900, "Embalagens": 31400},
        (_L("Magnésio bisglicinato", "MP-1038", 1.2, date(2026, 11, 7)),
         _L("Niacinamida", "MP-1042", 2.4, date(2026, 11, 13)),
         _L("Vitamina D3", "MP-0992", 0.6, date(2026, 11, 21)),
         _L("Base creme não iônica", "BS-1085", 5.8, date(2026, 11, 28))),
    ),
}
