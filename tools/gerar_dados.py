"""Gera db/init/02_seed.sql com dados ficticios deterministicos do FarmaBI.

As agregacoes reproduzem os numeros de referencia do prototipo (tools/referencia.py):
vendas, pedidos, frequencia, compradores, novos, orcamentos, atendimentos, primeira resposta e estoque.
Uso: python tools/gerar_dados.py
"""
from __future__ import annotations

import calendar
import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import referencia as ref

SEMENTE = 20261031
ARQUIVO_SEED = Path(__file__).resolve().parent.parent / "db" / "init" / "02_seed.sql"

CLIENTES_ANTIGOS_POR_CANAL = {"wa": 1700, "balcao": 950, "site": 480}

ATENDENTES = (
    ("Bianca Rocha", "wa"), ("Diego Lima", "wa"), ("Elisa Nunes", "wa"),
    ("Caio Martins", "balcao"), ("Renata Alves", "balcao"), ("Samuel Costa", "balcao"),
    ("Lívia Prado", "site"), ("Tomás Ribeiro", "site"),
)

CATEGORIAS_FORMULA = ("Dermocosmética", "Suplementação", "Fitoterápica", "Medicamento manipulado", "Pediátrica")
FORMAS_FARMACEUTICAS = ("Cápsula", "Creme", "Gel", "Loção", "Solução oral", "Sachê", "Xarope", "Shampoo")
FORNECEDORES = ("Distribuidora Alfa", "Insumos Beta", "Química Gama", "Pharma Delta", "Embalagens Épsilon",
                "Nutri Zeta")

INSUMOS = {
    "Ativos": ("kg", (0.5, 3.0), (
        "Magnésio bisglicinato", "Niacinamida", "Vitamina D3", "Vitamina C", "Ácido hialurônico",
        "Colágeno hidrolisado", "Coenzima Q10", "Ômega 3 em pó", "Biotina", "Zinco quelato", "Ferro bisglicinato",
        "Melatonina", "Creatina monoidratada", "L-carnitina", "Cafeína anidra", "Ácido glicólico",
        "Ácido salicílico", "Ácido kójico", "Retinol", "Alfa-arbutin", "Pantenol", "Ureia", "Minoxidil",
        "Finasterida", "Resveratrol", "Cúrcuma extrato seco", "Ashwagandha extrato seco", "Spirulina",
        "Vitamina B12", "Ácido fólico", "Selênio quelato", "Cromo picolinato", "Silimarina", "Glucosamina",
        "Condroitina", "Lactobacillus acidophilus")),
    "Bases": ("kg", (3.0, 15.0), (
        "Base creme não iônica", "Base gel de natrosol", "Base loção hidratante", "Base shampoo neutro",
        "Base sérum", "Gel de carbopol", "Creme Lanette", "Pomada base", "Base xarope", "Base protetor solar",
        "Veículo oral sem açúcar", "Base condicionador")),
    "Excipientes": ("kg", (2.0, 10.0), (
        "Celulose microcristalina", "Amido de milho", "Estearato de magnésio", "Talco farmacêutico", "Lactose",
        "Dióxido de silício", "Glicerina", "Propilenoglicol", "Metilparabeno", "Fenoxietanol", "EDTA dissódico",
        "BHT", "Manitol", "Sorbitol", "Álcool cetoestearílico")),
    "Embalagens": ("un", (300, 3000), (
        "Cápsula gelatinosa nº 0", "Cápsula gelatinosa nº 1", "Cápsula vegetal nº 0", "Pote 60 g", "Pote 120 g",
        "Frasco âmbar 100 ml", "Frasco conta-gotas 30 ml", "Bisnaga 50 g", "Bisnaga 100 g",
        "Frasco airless 30 ml", "Sachê laminado", "Tampa flip-top", "Rótulo adesivo", "Caixa cartonada",
        "Frasco PET 200 ml")),
}
PREFIXO_LOTE = {"Ativos": "MP", "Excipientes": "MP", "Bases": "BS", "Embalagens": "EM"}
FAIXAS_DIAS = ((-60, -1), (0, 30), (31, 60), (61, 90), (91, 720))


# ------------------------------------------------------------------ entidades
@dataclass
class Cliente:
    seq: int
    canal: str
    data_cadastro: date
    primeira_compra: date | None = None


@dataclass
class Atendimento:
    cliente: Cliente
    canal: str
    atendente: int
    iniciado_em: datetime
    primeira_resposta: datetime
    encerrado_em: datetime
    transferencias: int
    avaliacao: int | None
    id: int = 0


@dataclass
class Pedido:
    cliente: Cliente
    canal: str
    atendente: int
    data_venda: date
    status: str
    centavos_liquido: int
    centavos_desconto: int
    itens: list = field(default_factory=list)
    oportunidade: "Oportunidade | None" = None
    id: int = 0


@dataclass
class Oportunidade:
    atendimento: Atendimento
    criada_em: datetime
    data_envio: datetime
    status: str
    motivo_perda: str | None = None
    data_aprovacao: datetime | None = None
    data_encerramento: datetime | None = None
    pedido: Pedido | None = None
    versoes: list = field(default_factory=list)
    id: int = 0


@dataclass
class Base:
    clientes: list = field(default_factory=list)
    atendimentos: list = field(default_factory=list)
    pedidos: list = field(default_factory=list)
    oportunidades: list = field(default_factory=list)
    insumos: list = field(default_factory=list)          # (id, descricao, categoria, unidade, minimo)
    lotes: list = field(default_factory=list)            # (id, codigo, insumo_id, fornecedor, recebimento, validade)
    saldos: list = field(default_factory=list)           # (data, lote_id, deposito, fisico, reserv, bloq, valor, custo)


# -------------------------------------------------------------------- helpers
def distribuir(total: int, n: int, rng: random.Random, sigma: float = 0.5, minimo: int = 1) -> list[int]:
    """Divide um inteiro em n partes positivas, com soma exata."""
    if n <= 0:
        raise ValueError("n deve ser positivo")
    livre = total - minimo * n
    if livre < 0:
        raise ValueError(f"total {total} insuficiente para {n} partes de no minimo {minimo}")
    pesos = [rng.lognormvariate(0, sigma) for _ in range(n)]
    soma = sum(pesos)
    brutos = [livre * p / soma for p in pesos]
    partes = [math.floor(b) for b in brutos]
    sobra = livre - sum(partes)
    for i in sorted(range(n), key=lambda i: brutos[i] - partes[i], reverse=True)[:sobra]:
        partes[i] += 1
    return [p + minimo for p in partes]


def dias_do_mes(inicio: date) -> int:
    return calendar.monthrange(inicio.year, inicio.month)[1]


def dia_aleatorio(inicio: date, rng: random.Random, de: int = 1, ate: int | None = None) -> date:
    ate = ate or dias_do_mes(inicio)
    return inicio.replace(day=rng.randint(de, ate))


def horario_comercial(dia: date, rng: random.Random) -> datetime:
    return datetime(dia.year, dia.month, dia.day, rng.randint(8, 17), rng.randint(0, 59), rng.randint(0, 59))


# ------------------------------------------------------------------ gerador
class Gerador:
    def __init__(self, semente: int = SEMENTE):
        self.rng = random.Random(semente)
        self.base = Base()
        self.atendentes = {c.codigo: [] for c in ref.CANAIS}
        for i, (_, canal) in enumerate(ATENDENTES, start=1):
            self.atendentes[canal].append(i)
        self.elegiveis = {c.codigo: [] for c in ref.CANAIS}       # podem fazer compras recorrentes
        self.antigos = {c.codigo: [] for c in ref.CANAIS}         # clientes anteriores a janela de dados
        self.forcados = {}                                        # (mes, canal) -> clientes que precisam recomprar

    # ............................................................. clientes
    def novo_cliente(self, canal: str, primeira_compra: date | None) -> Cliente:
        referencia = primeira_compra or date(2025, 12, 31)
        cadastro = referencia - timedelta(days=self.rng.randint(0, 120))
        cliente = Cliente(len(self.base.clientes) + 1, canal, cadastro, primeira_compra)
        self.base.clientes.append(cliente)
        return cliente

    def criar_clientes_antigos(self):
        for canal, qtde in CLIENTES_ANTIGOS_POR_CANAL.items():
            for _ in range(qtde):
                primeira = date(2024, 1, 1) + timedelta(days=self.rng.randint(0, 729))
                cliente = self.novo_cliente(canal, primeira)
                self.antigos[canal].append(cliente)
                self.elegiveis[canal].append(cliente)

    # .............................................................. comercial
    def gerar_comercial(self):
        self.criar_clientes_antigos()
        for indice, mes in enumerate(ref.MESES):
            for canal in ref.CANAIS:
                alvo = ref.COMERCIAL[mes][canal.codigo]
                recompra_alvo = self.recompra_da_coorte(indice, canal.codigo)
                self.gerar_mes_canal(mes, canal.codigo, alvo, recompra_alvo)

    @staticmethod
    def recompra_da_coorte(indice_mes: int, canal: str) -> float | None:
        """A coorte do mes M e exibida em M+3; sem M+3 na janela, a coorte nao e calibrada."""
        if indice_mes + 3 >= len(ref.MESES):
            return None
        return ref.COMERCIAL[ref.MESES[indice_mes + 3]][canal].recompra_90d

    def gerar_mes_canal(self, mes: date, canal: str, alvo: ref.RefComercial, recompra_alvo: float | None):
        rng = self.rng
        f1, f2, f3 = ref.frequencia_ajustada(alvo)
        assert f1 + f2 + f3 == alvo.compradores, (mes, canal, "frequencia x compradores")
        assert alvo.orcamentos <= alvo.atendimentos and alvo.pedidos <= alvo.orcamentos, (mes, canal)

        novos = [self.novo_cliente(canal, None) for _ in range(alvo.novos)]
        recorrentes_qtde = alvo.compradores - alvo.novos
        forcados = self.forcados.pop((mes, canal), [])
        assert len(forcados) <= recorrentes_qtde, (mes, canal, "recompras forcadas excedem recorrentes")
        ja = set(id(c) for c in forcados)
        candidatos = [c for c in self.elegiveis[canal] if id(c) not in ja]
        recorrentes = forcados + rng.sample(candidatos, recorrentes_qtde - len(forcados))

        # Coorte calibrada: apenas os designados podem recomprar em ate 90 dias.
        if recompra_alvo is not None:
            qtde = round(len(novos) * recompra_alvo / 100)
            designados = rng.sample(novos, qtde)
        else:
            designados = list(novos)
        ids_designados = set(id(c) for c in designados)
        nao_designados = [c for c in novos if id(c) not in ids_designados]

        terceira_faixa = [3] * f3
        for _ in range(alvo.pedidos - (f1 + 2 * f2 + 3 * f3)):
            terceira_faixa[rng.randrange(f3)] += 1
        frequencias = [1] * f1 + [2] * f2 + terceira_faixa
        assert sum(frequencias) == alvo.pedidos, (mes, canal, "frequencia x pedidos")
        assert len(nao_designados) <= f1, (mes, canal, "coorte sem recompra excede clientes de 1 compra")
        restantes = frequencias[len(nao_designados):]
        rng.shuffle(restantes)
        livres = designados + recorrentes
        rng.shuffle(livres)
        compras = [(c, 1) for c in nao_designados] + list(zip(livres, restantes))

        # Pedidos confirmados
        pedidos = []
        proximo_mes = ref.MESES[ref.MESES.index(mes) + 1] if mes != ref.MESES[-1] else None
        for cliente, qtde in compras:
            dias = sorted(dia_aleatorio(mes, rng) for _ in range(qtde))
            if cliente.primeira_compra is None:
                cliente.primeira_compra = dias[0]
                cliente.data_cadastro = dias[0] - timedelta(days=rng.randint(0, 20))
            for dia in dias:
                pedidos.append(Pedido(cliente, canal, rng.choice(self.atendentes[canal]), dia, "CONFIRMADO", 0, 0))
            if recompra_alvo is not None and id(cliente) in ids_designados and qtde == 1:
                assert proximo_mes is not None
                self.forcados.setdefault((proximo_mes, canal), []).append(cliente)

        for pedido, centavos in zip(pedidos, distribuir(alvo.vendas * 100, len(pedidos), rng, 0.55, 2500)):
            self.precificar(pedido, centavos)

        # Elegiveis para recompras nos proximos meses. Nao designados da coorte calibrada nunca recompram;
        # designados que ainda devem a recompra so entram depois de cumpri-la no mes seguinte.
        if recompra_alvo is None:
            self.elegiveis[canal].extend(novos)
        else:
            devendo = set(id(c) for c in self.forcados.get((proximo_mes, canal), []))
            self.elegiveis[canal].extend(c for c in designados if id(c) not in devendo)
        self.elegiveis[canal].extend(forcados)

        self.gerar_cancelados_devolvidos(mes, canal, alvo)
        clientes_mes = novos + recorrentes
        self.gerar_funil(mes, canal, alvo, pedidos, clientes_mes)
        self.base.pedidos.extend(pedidos)

    def precificar(self, pedido: Pedido, centavos_liquido: int):
        rng = self.rng
        pedido.centavos_liquido = centavos_liquido
        if rng.random() < 0.35:
            percentual = rng.uniform(0.05, 0.15)
            bruto = round(centavos_liquido / (1 - percentual))
            pedido.centavos_desconto = bruto - centavos_liquido
        qtde_itens = rng.choices((1, 2, 3), weights=(60, 30, 10))[0]
        valores = distribuir(centavos_liquido, qtde_itens, rng, 0.4, 500) if qtde_itens > 1 else [centavos_liquido]
        for valor in valores:
            pedido.itens.append((f"F-{rng.randint(10000, 99999)}", rng.choice(CATEGORIAS_FORMULA),
                                 rng.choice(FORMAS_FARMACEUTICAS), rng.choice((1, 1, 1, 2)), valor))

    def gerar_cancelados_devolvidos(self, mes: date, canal: str, alvo: ref.RefComercial):
        rng = self.rng
        for status, taxa in (("CANCELADO", ref.TAXA_CANCELADOS), ("DEVOLVIDO", ref.TAXA_DEVOLVIDOS)):
            for _ in range(round(alvo.pedidos * taxa)):
                pedido = Pedido(rng.choice(self.antigos[canal]), canal, rng.choice(self.atendentes[canal]),
                                dia_aleatorio(mes, rng), status, 0, 0)
                self.precificar(pedido, max(2500, round(rng.lognormvariate(math.log(14000), 0.5))))
                self.base.pedidos.append(pedido)

    # ............................................... atendimento e orcamento
    def gerar_funil(self, mes: date, canal: str, alvo: ref.RefComercial, pedidos: list, clientes_mes: list):
        rng = self.rng
        perdidas = round((alvo.orcamentos - alvo.pedidos) * ref.FATOR_PERDIDOS)
        pendentes = alvo.orcamentos - alvo.pedidos - perdidas
        motivos = []
        for nome, peso in ref.MOTIVOS_PERDA:
            motivos += [nome] * (round(perdidas * peso) if peso else perdidas - len(motivos))
        rng.shuffle(motivos)

        segundos = distribuir(round(alvo.resposta_min * 60 * alvo.atendimentos), alvo.atendimentos, rng, 0.8, 20)
        rng.shuffle(segundos)
        conhecidos = clientes_mes + self.elegiveis[canal]

        def atender(cliente: Cliente, ultimo_dia: date | None = None) -> Atendimento:
            ate = ultimo_dia.day if ultimo_dia else dias_do_mes(mes)
            de = max(1, ate - 4) if ultimo_dia else 1
            inicio = horario_comercial(dia_aleatorio(mes, rng, de, ate), rng)
            resposta = inicio + timedelta(seconds=segundos.pop())
            atendimento = Atendimento(
                cliente, canal, rng.choice(self.atendentes[canal]), inicio, resposta,
                resposta + timedelta(minutes=rng.randint(5, 120)),
                rng.choices((0, 1, 2), weights=(80, 15, 5))[0],
                rng.choices((None, 5, 4, 3, 2, 1), weights=(45, 27, 17, 6, 3, 2))[0])
            self.base.atendimentos.append(atendimento)
            return atendimento

        def orcar(atendimento: Atendimento, status: str) -> Oportunidade:
            criada = atendimento.primeira_resposta + timedelta(minutes=rng.randint(2, 40))
            envio = criada + timedelta(minutes=rng.randint(20, 240))
            oportunidade = Oportunidade(atendimento, criada, envio, status)
            self.base.oportunidades.append(oportunidade)
            return oportunidade

        for pedido in pedidos:
            atendimento = atender(pedido.cliente, pedido.data_venda)
            oportunidade = orcar(atendimento, "CONVERTIDA")
            pedido.atendente = atendimento.atendente
            pedido.oportunidade = oportunidade
            oportunidade.pedido = pedido
            aprovacao = datetime.combine(pedido.data_venda, oportunidade.data_envio.time())
            oportunidade.data_aprovacao = max(aprovacao, oportunidade.data_envio)
            oportunidade.data_encerramento = oportunidade.data_aprovacao
            self.versionar(oportunidade, pedido.centavos_liquido)

        for status, qtde in (("PERDIDA", perdidas), ("PENDENTE", pendentes)):
            for _ in range(qtde):
                oportunidade = orcar(atender(rng.choice(conhecidos)), status)
                if status == "PERDIDA":
                    oportunidade.motivo_perda = motivos.pop()
                    oportunidade.data_encerramento = oportunidade.data_envio + timedelta(days=rng.randint(2, 20))
                self.versionar(oportunidade, max(2500, round(rng.lognormvariate(math.log(15000), 0.5))))

        for _ in range(alvo.atendimentos - alvo.orcamentos):
            atender(rng.choice(conhecidos))
        assert not segundos and not motivos

    def versionar(self, oportunidade: Oportunidade, centavos_vigente: int):
        rng = self.rng
        qtde = rng.choices((1, 2, 3), weights=(55, 33, 12))[0]
        momento = oportunidade.data_envio
        for versao in range(1, qtde + 1):
            vigente = versao == qtde
            valor = centavos_vigente if vigente else round(centavos_vigente * rng.uniform(1.03, 1.2))
            oportunidade.versoes.append((versao, momento, valor, vigente))
            momento += timedelta(hours=rng.randint(2, 30))

    # ................................................................ estoque
    def gerar_insumos(self):
        rng = self.rng
        for categoria in ref.CATEGORIAS:
            unidade, (minimo, maximo), nomes = INSUMOS[categoria]
            for nome in nomes:
                if unidade == "un":
                    estoque_minimo = Decimal(rng.randrange(minimo, maximo + 1, 50))
                else:
                    estoque_minimo = Decimal(str(round(rng.uniform(minimo, maximo), 1)))
                self.base.insumos.append((len(self.base.insumos) + 1, nome, categoria, unidade, estoque_minimo))

    def gerar_estoque(self):
        self.gerar_insumos()
        codigos_usados = set(lote.lote_codigo for alvo in ref.ESTOQUE.values() for lote in alvo.amostra)
        for posicao, alvo in ref.ESTOQUE.items():
            self.gerar_posicao(posicao, alvo, codigos_usados)

    def novo_codigo(self, categoria: str, usados: set) -> str:
        while True:
            codigo = f"{PREFIXO_LOTE[categoria]}-{self.rng.randint(0, 9999):04d}"
            if codigo not in usados:
                usados.add(codigo)
                return codigo

    def gerar_posicao(self, posicao: date, alvo: ref.RefEstoque, usados: set):
        rng = self.rng
        assert alvo.faixas[0] == alvo.vencidos and alvo.faixas[1] == alvo.vencendo_30d
        assert sum(alvo.categorias.values()) == alvo.valor_total
        por_nome = {i[1]: i for i in self.base.insumos}

        # lotes: (insumo, faixa, codigo, validade, saldo_fixo)
        lotes = [(por_nome[a.insumo], 1, a.lote_codigo, a.validade, Decimal(str(a.saldo))) for a in alvo.amostra]
        faixas = []
        for faixa, qtde in enumerate(alvo.faixas):
            faixas += [faixa] * (qtde - (len(alvo.amostra) if faixa == 1 else 0))
        rng.shuffle(faixas)
        nao_vencidas = [f for f in faixas if f != 0]
        vencidas = [f for f in faixas if f == 0]
        cobertura = list(self.base.insumos)
        rng.shuffle(cobertura)
        assert len(nao_vencidas) >= len(cobertura)
        insumos_por_lote = cobertura + [rng.choice(self.base.insumos) for _ in nao_vencidas[len(cobertura):]]
        insumos_por_lote += [rng.choice(self.base.insumos) for _ in vencidas]
        for insumo, faixa in zip(insumos_por_lote, nao_vencidas + vencidas):
            de, ate = FAIXAS_DIAS[faixa]
            validade = posicao + timedelta(days=rng.randint(de, ate))
            lotes.append((insumo, faixa, self.novo_codigo(insumo[2], usados), validade, None))

        valores = self.valorizar_lotes(lotes, alvo)
        saldos = self.quantificar_lotes(lotes, alvo, posicao)

        for (insumo, faixa, codigo, validade, _), valor, (fisico, reservado, bloqueado) in zip(lotes, valores, saldos):
            lote_id = len(self.base.lotes) + 1
            recebimento = min(posicao - timedelta(days=rng.randint(5, 200)),
                              validade - timedelta(days=rng.randint(365, 900)))
            self.base.lotes.append((lote_id, codigo, insumo[0], rng.choice(FORNECEDORES), recebimento, validade))
            deposito = "Laboratório" if rng.random() < 0.25 else "Almoxarifado"
            custo = (Decimal(valor) / 100 / fisico).quantize(Decimal("0.0001"))
            self.base.saldos.append((posicao, lote_id, deposito, fisico, reservado, bloqueado,
                                     Decimal(valor) / 100, custo))

    def valorizar_lotes(self, lotes: list, alvo: ref.RefEstoque) -> list[int]:
        """Valor em centavos por lote: risco (0-30 dias) e categorias batem exatamente."""
        rng = self.rng
        valores = [0] * len(lotes)
        risco = [i for i, lote in enumerate(lotes) if lote[1] == 1]
        for i, v in zip(risco, distribuir(alvo.valor_em_risco * 100, len(risco), rng, 0.6, 5000)):
            valores[i] = v
        for categoria, total in alvo.categorias.items():
            demais = [i for i, lote in enumerate(lotes) if lote[0][2] == categoria and lote[1] != 1]
            restante = total * 100 - sum(valores[i] for i, lote in enumerate(lotes)
                                         if lote[0][2] == categoria and lote[1] == 1)
            for i, v in zip(demais, distribuir(restante, len(demais), rng, 0.7, 5000)):
                valores[i] = v
        return valores

    def quantificar_lotes(self, lotes: list, alvo: ref.RefEstoque, posicao: date) -> list[tuple]:
        """Saldos fisico/reservado/bloqueado; exatamente `abaixo_minimo` insumos ficam abaixo do minimo."""
        rng = self.rng
        com_amostra = set(lote[0][0] for lote in lotes if lote[4] is not None)
        candidatos = [i for i in self.base.insumos if i[0] not in com_amostra]
        abaixo = set(i[0] for i in rng.sample(candidatos, alvo.abaixo_minimo))
        saldos = [None] * len(lotes)

        for insumo in self.base.insumos:
            inteiro = insumo[3] == "un"
            arred = (lambda x: Decimal(max(1, round(x)))) if inteiro else \
                (lambda x: Decimal(str(max(0.05, round(x, 3)))))
            indices = [i for i, lote in enumerate(lotes) if lote[0][0] == insumo[0]]
            fixos = [i for i in indices if lotes[i][4] is not None]
            vencidos = [i for i in indices if lotes[i][1] == 0 and lotes[i][4] is None]
            ativos = [i for i in indices if lotes[i][1] != 0 and lotes[i][4] is None]

            for i in fixos:
                saldos[i] = (lotes[i][4], Decimal(0), Decimal(0))
            for i in vencidos:
                saldos[i] = (arred(float(insumo[4]) * rng.uniform(0.1, 0.6)), Decimal(0), Decimal(0))

            minimo = float(insumo[4])
            fixo_disponivel = sum(float(lotes[i][4]) for i in fixos)
            alvo_disponivel = minimo * rng.uniform(0.25, 0.8) if insumo[0] in abaixo \
                else minimo * rng.uniform(1.3, 3.0) + fixo_disponivel
            restante = alvo_disponivel - fixo_disponivel
            if not ativos:
                continue
            bloqueados = [i for i in ativos[1:] if rng.random() < 0.05]
            livres = [i for i in ativos if i not in bloqueados]
            pesos = [rng.lognormvariate(0, 0.5) for _ in livres]
            for i, peso in zip(livres, pesos):
                contribuicao = restante * peso / sum(pesos)
                fracao_reserva = rng.uniform(0.05, 0.2) if rng.random() < 0.3 else 0.0
                fisico = arred(contribuicao / (1 - fracao_reserva))
                reservado = arred(float(fisico) * fracao_reserva) if fracao_reserva else Decimal(0)
                saldos[i] = (fisico, min(reservado, fisico), Decimal(0))
            for i in bloqueados:
                fisico = arred(minimo * rng.uniform(0.2, 0.8))
                saldos[i] = (fisico, Decimal(0), fisico)
        return saldos

    # ................................................................ execucao
    def gerar(self) -> Base:
        self.gerar_comercial()
        assert not self.forcados, "recompras forcadas nao cumpridas"
        self.gerar_estoque()
        self.numerar()
        return self.base

    def numerar(self):
        b = self.base
        for i, a in enumerate(sorted(b.atendimentos, key=lambda a: a.iniciado_em), start=1):
            a.id = i
        for i, p in enumerate(sorted(b.pedidos, key=lambda p: (p.data_venda, p.canal)), start=1):
            p.id = i
        for i, o in enumerate(sorted(b.oportunidades, key=lambda o: o.criada_em), start=1):
            o.id = i


def gerar(semente: int = SEMENTE) -> Base:
    return Gerador(semente).gerar()


# -------------------------------------------------------------- renderizacao
def _valor(v) -> str:
    if v is None:
        return r"\N"
    if isinstance(v, bool):
        return "t" if v else "f"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    texto = str(v)
    return texto.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def _copy(tabela: str, colunas: str, linhas) -> str:
    corpo = "\n".join("\t".join(_valor(v) for v in linha) for linha in linhas)
    return f"COPY {tabela} ({colunas}) FROM stdin;\n{corpo}\n\\.\n"


def _reais(centavos: int) -> Decimal:
    return Decimal(centavos) / 100


def renderizar_sql(base: Base) -> str:
    canal_id = {c.codigo: c.canal_id for c in ref.CANAIS}
    partes = ["-- GERADO por tools/gerar_dados.py. Nao editar a mao.\n", "BEGIN;\n"]
    partes.append(_copy("dim_canal", "canal_id, codigo, nome, ordem, cor",
                        ((c.canal_id, c.codigo, c.nome, c.canal_id, c.cor) for c in ref.CANAIS)))
    partes.append(_copy("dim_atendente", "atendente_id, nome, canal_id",
                        ((i, nome, canal_id[canal]) for i, (nome, canal) in enumerate(ATENDENTES, start=1))))
    partes.append(_copy("dim_cliente", "cliente_id, codigo, canal_id, data_cadastro, data_primeira_compra",
                        ((c.seq, f"CLI-{c.seq:05d}", canal_id[c.canal], c.data_cadastro, c.primeira_compra)
                         for c in base.clientes if c.primeira_compra is not None)))
    partes.append(_copy("fato_atendimento",
                        "atendimento_id, cliente_id, canal_id, atendente_id, iniciado_em, primeira_resposta_humana_em,"
                        " encerrado_em, status, transferencias, avaliacao",
                        ((a.id, a.cliente.seq, canal_id[a.canal], a.atendente, a.iniciado_em, a.primeira_resposta,
                          a.encerrado_em, "ENCERRADO", a.transferencias, a.avaliacao)
                         for a in sorted(base.atendimentos, key=lambda a: a.id))))
    pedidos = sorted(base.pedidos, key=lambda p: p.id)
    partes.append(_copy("fato_pedido",
                        "pedido_id, cliente_id, canal_id, atendente_id, oportunidade_id, data_venda, status,"
                        " valor_bruto, desconto, valor_liquido, valor_devolvido",
                        ((p.id, p.cliente.seq, canal_id[p.canal], p.atendente,
                          p.oportunidade.id if p.oportunidade else None, p.data_venda, p.status,
                          _reais(p.centavos_liquido + p.centavos_desconto), _reais(p.centavos_desconto),
                          _reais(p.centavos_liquido),
                          _reais(p.centavos_liquido) if p.status == "DEVOLVIDO" else Decimal("0.00"))
                         for p in pedidos)))
    oportunidades = sorted(base.oportunidades, key=lambda o: o.id)
    partes.append(_copy("fato_oportunidade",
                        "oportunidade_id, atendimento_id, cliente_id, canal_id, atendente_id, criada_em, data_envio,"
                        " data_aprovacao, data_encerramento, status, motivo_perda, pedido_id",
                        ((o.id, o.atendimento.id, o.atendimento.cliente.seq, canal_id[o.atendimento.canal],
                          o.atendimento.atendente, o.criada_em, o.data_envio, o.data_aprovacao, o.data_encerramento,
                          o.status, o.motivo_perda, o.pedido.id if o.pedido else None) for o in oportunidades)))
    versoes = []
    for o in oportunidades:
        for versao, momento, centavos, vigente in o.versoes:
            versoes.append((len(versoes) + 1, o.id, versao, momento, _reais(centavos), vigente))
    partes.append(_copy("fato_orcamento_versao", "orcamento_versao_id, oportunidade_id, versao, criada_em, valor,"
                                                 " vigente", versoes))
    itens = []
    for p in pedidos:
        for codigo, categoria, forma, qtde, centavos in p.itens:
            itens.append((len(itens) + 1, p.id, codigo, categoria, forma, qtde, _reais(centavos)))
    partes.append(_copy("fato_pedido_item", "pedido_item_id, pedido_id, formula_codigo, categoria_formula,"
                                            " forma_farmaceutica, quantidade, valor_liquido", itens))
    partes.append(_copy("dim_insumo", "insumo_id, descricao, categoria, unidade_medida, estoque_minimo",
                        base.insumos))
    partes.append(_copy("dim_lote", "lote_id, lote_codigo, insumo_id, fornecedor, data_recebimento, data_validade",
                        base.lotes))
    partes.append(_copy("fato_saldo_estoque", "data_posicao, lote_id, deposito, saldo_fisico, saldo_reservado,"
                                              " saldo_bloqueado, valor_total, custo_unitario", base.saldos))
    partes.append("UPDATE dim_calendario SET periodo_analise = data BETWEEN DATE '2026-05-01' AND DATE '2026-10-31';\n")
    partes.append("COMMIT;\n")
    return "".join(partes)


def main():
    sql = renderizar_sql(gerar())
    ARQUIVO_SEED.write_text(sql, encoding="utf-8", newline="\n")
    print(f"{ARQUIVO_SEED} ({len(sql) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
