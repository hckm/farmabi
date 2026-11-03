"""Gera o modelo semantico TMDL do FarmaBI (powerbi/FarmaBI.SemanticModel)."""
import json
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2] / "powerbi"
SM = RAIZ / "FarmaBI.SemanticModel"
NS = uuid.UUID("6f1d2a5e-0b7c-4c1e-9d55-2a6f0f6b9e11")

# tipo: (dataType TMDL, tipo M)
T = {"int": ("int64", "Int64.Type"), "txt": ("string", "type text"), "data": ("dateTime", "type date"),
     "ts": ("dateTime", "type datetime"), "moeda": ("decimal", "Currency.Type"), "num": ("double", "type number"),
     "bool": ("boolean", "type logical")}

# tabela: (origem, [(coluna, tipo, oculta, formato)])
TABELAS = {
    "Calendario": ("dim_calendario", [
        ("data", "data", False, "dd/mm/yyyy"), ("ano", "int", False, "0"), ("mes", "int", True, "0"),
        ("inicio_mes", "data", True, "dd/mm/yyyy"), ("fim_mes", "data", True, "dd/mm/yyyy"),
        ("mes_ano", "txt", False, None), ("mes_ano_ordem", "int", True, "0"), ("periodo_analise", "bool", True, None)]),
    "Canal": ("dim_canal", [
        ("canal_id", "int", True, "0"), ("nome", "txt", False, None), ("ordem", "int", True, "0"),
        ("cor", "txt", True, None)]),
    "Atendente": ("dim_atendente", [("atendente_id", "int", True, "0"), ("nome", "txt", False, None)]),
    "Cliente": ("dim_cliente", [
        ("cliente_id", "int", True, "0"), ("codigo", "txt", False, None), ("data_cadastro", "data", False, "dd/mm/yyyy"),
        ("data_primeira_compra", "data", False, "dd/mm/yyyy")]),
    "Pedido": ("fato_pedido", [
        ("pedido_id", "int", True, "0"), ("cliente_id", "int", True, "0"), ("canal_id", "int", True, "0"),
        ("atendente_id", "int", True, "0"), ("oportunidade_id", "int", True, "0"), ("data_venda", "data", False, "dd/mm/yyyy"),
        ("status", "txt", False, None), ("valor_bruto", "moeda", True, None), ("desconto", "moeda", True, None),
        ("valor_liquido", "moeda", True, None), ("valor_devolvido", "moeda", True, None)]),
    "PedidoItem": ("fato_pedido_item", [
        ("pedido_item_id", "int", True, "0"), ("pedido_id", "int", True, "0"), ("formula_codigo", "txt", False, None),
        ("categoria_formula", "txt", False, None), ("forma_farmaceutica", "txt", False, None),
        ("quantidade", "int", True, "0"), ("valor_liquido", "moeda", True, None)]),
    "Oportunidade": ("fato_oportunidade", [
        ("oportunidade_id", "int", True, "0"), ("atendimento_id", "int", True, "0"), ("cliente_id", "int", True, "0"),
        ("canal_id", "int", True, "0"), ("atendente_id", "int", True, "0"), ("criada_em", "ts", False, "General Date"),
        ("data_envio", "ts", False, "General Date"), ("data_aprovacao", "ts", False, "General Date"),
        ("status", "txt", False, None), ("motivo_perda", "txt", False, None), ("pedido_id", "int", True, "0"),
        ("data_criacao", "data", True, "dd/mm/yyyy")]),
    "OrcamentoVersao": ("fato_orcamento_versao", [
        ("orcamento_versao_id", "int", True, "0"), ("oportunidade_id", "int", True, "0"), ("versao", "int", False, "0"),
        ("criada_em", "ts", False, "General Date"), ("valor", "moeda", True, None), ("vigente", "bool", False, None)]),
    "Atendimento": ("fato_atendimento", [
        ("atendimento_id", "int", True, "0"), ("cliente_id", "int", True, "0"), ("canal_id", "int", True, "0"),
        ("atendente_id", "int", True, "0"), ("iniciado_em", "ts", False, "General Date"),
        ("primeira_resposta_humana_em", "ts", False, "General Date"), ("encerrado_em", "ts", False, "General Date"),
        ("transferencias", "int", False, "0"), ("avaliacao", "int", False, "0"), ("data_inicio", "data", True, "dd/mm/yyyy"),
        ("segundos_primeira_resposta", "int", True, "0")]),
    "Insumo": ("dim_insumo", [
        ("insumo_id", "int", True, "0"), ("descricao", "txt", False, None), ("categoria", "txt", False, None),
        ("unidade_medida", "txt", False, None), ("estoque_minimo", "num", False, "#,##0.###")]),
    "Estoque": ("vw_saldo_estoque", [
        ("data_posicao", "data", False, "dd/mm/yyyy"), ("lote_id", "int", True, "0"), ("lote_codigo", "txt", False, None),
        ("insumo_id", "int", True, "0"), ("deposito", "txt", False, None), ("data_validade", "data", False, "dd/mm/yyyy"),
        ("dias_para_vencer", "int", False, "0"), ("faixa_validade", "txt", False, None),
        ("faixa_validade_ordem", "int", True, "0"), ("vencido", "bool", False, None),
        ("saldo_fisico", "num", False, "#,##0.###"), ("saldo_reservado", "num", False, "#,##0.###"),
        ("saldo_bloqueado", "num", False, "#,##0.###"), ("saldo_disponivel", "num", False, "#,##0.###"),
        ("valor_total", "moeda", True, None), ("custo_unitario", "num", True, "#,##0.0000")]),
    "InsumoPosicao": ("vw_insumo_posicao", [
        ("data_posicao", "data", True, "dd/mm/yyyy"), ("insumo_id", "int", True, "0"),
        ("saldo_disponivel", "num", False, "#,##0.###"), ("estoque_minimo", "num", False, "#,##0.###"),
        ("abaixo_minimo", "bool", False, None)]),
    "Coorte": ("vw_coorte_recompra", [
        ("cliente_id", "int", True, "0"), ("canal_id", "int", True, "0"), ("data_primeira_compra", "data", True, "dd/mm/yyyy"),
        ("mes_coorte", "data", False, "mmm/yyyy"), ("recomprou_90d", "int", True, "0")]),
    "EtapaFunil": ("aux_etapa_funil", [("etapa_id", "int", True, "0"), ("etapa", "txt", False, None),
                                       ("cor", "txt", True, None)]),
    "FaixaFrequencia": ("aux_faixa_frequencia", [
        ("faixa_id", "int", True, "0"), ("faixa", "txt", False, None), ("compras_min", "int", True, "0"),
        ("compras_max", "int", True, "0")]),
}
ORDENAR_POR = {("Calendario", "mes_ano"): "mes_ano_ordem", ("Canal", "nome"): "ordem",
               ("EtapaFunil", "etapa"): "etapa_id", ("FaixaFrequencia", "faixa"): "faixa_id",
               ("Estoque", "faixa_validade"): "faixa_validade_ordem"}

MOEDA = '"R$ "#,##0'
MOEDA2 = '"R$ "#,##0.00'
PCT = "0.0%"
INT = "#,##0"
CONF = 'KEEPFILTERS ( Pedido[status] = "CONFIRMADO" )'

# pasta: [(nome, expressao, formato)]
MEDIDAS = {
    "1. Executivo": [
        ("Vendas líquidas", f"CALCULATE ( SUM ( Pedido[valor_liquido] ), {CONF} )", MOEDA),
        ("Pedidos vendidos", f"CALCULATE ( DISTINCTCOUNT ( Pedido[pedido_id] ), {CONF} )", INT),
        ("Ticket médio", "DIVIDE ( [Vendas líquidas], [Pedidos vendidos] )", MOEDA2),
        ("Vendas mês anterior", "CALCULATE ( [Vendas líquidas], DATEADD ( Calendario[data], -1, MONTH ) )", MOEDA),
        ("Crescimento %", "VAR anterior = [Vendas mês anterior]\n"
                          "RETURN IF ( NOT ISBLANK ( anterior ), DIVIDE ( [Vendas líquidas], anterior ) - 1 )", "+0.0%;-0.0%;0.0%"),
        ("Crescimento", 'VAR c = [Crescimento %]\nRETURN IF ( ISBLANK ( c ), "N/D", FORMAT ( c, "+0.0%;-0.0%;0.0%" ) )',
         None),
        ("Participação %", "DIVIDE ( [Vendas líquidas], CALCULATE ( [Vendas líquidas], REMOVEFILTERS ( Canal ) ) )", PCT),
        ("Fórmulas vendidas", f"CALCULATE ( COUNTROWS ( PedidoItem ), {CONF} )", INT),
        ("Pedidos cancelados", 'CALCULATE ( COUNTROWS ( Pedido ), KEEPFILTERS ( Pedido[status] = "CANCELADO" ) )', INT),
        ("Pedidos devolvidos", 'CALCULATE ( COUNTROWS ( Pedido ), KEEPFILTERS ( Pedido[status] = "DEVOLVIDO" ) )', INT),
        ("Valor devolvido", "SUM ( Pedido[valor_devolvido] )", MOEDA),
        ("Descontos concedidos", f"CALCULATE ( SUM ( Pedido[desconto] ), {CONF} )", MOEDA),
    ],
    "2. Orçamentos": [
        ("Orçamentos gerados", "DISTINCTCOUNT ( Oportunidade[oportunidade_id] )", INT),
        ("Convertidos", 'CALCULATE ( [Orçamentos gerados], KEEPFILTERS ( Oportunidade[status] = "CONVERTIDA" ) )', INT),
        ("Perdidos", 'CALCULATE ( [Orçamentos gerados], KEEPFILTERS ( Oportunidade[status] = "PERDIDA" ) )', INT),
        ("Em negociação", 'CALCULATE ( [Orçamentos gerados], KEEPFILTERS ( Oportunidade[status] = "PENDENTE" ) )', INT),
        ("Taxa de conversão", "DIVIDE ( [Convertidos], [Orçamentos gerados] )", PCT),
        ("Taxa de perda", "DIVIDE ( [Perdidos], [Perdidos] + [Convertidos] )", PCT),
        ("Quantidade na etapa", "SWITCH ( SELECTEDVALUE ( EtapaFunil[etapa_id] ),\n"
                                "    1, [Orçamentos gerados],\n    2, [Convertidos],\n    3, [Perdidos],\n"
                                "    4, [Em negociação]\n)", INT),
        ("Horas até a 1ª cotação", "AVERAGEX ( Oportunidade, DATEDIFF ( Oportunidade[criada_em], "
                                   "Oportunidade[data_envio], MINUTE ) ) / 60", '0.0" h"'),
    ],
    "3. Clientes": [
        ("Clientes compradores", f"CALCULATE ( DISTINCTCOUNT ( Pedido[cliente_id] ), {CONF} )", INT),
        ("Novos clientes", "VAR inicio = MIN ( Calendario[data] )\nVAR fim = MAX ( Calendario[data] )\n"
                           "RETURN\n    CALCULATE (\n        [Clientes compradores],\n"
                           "        FILTER ( VALUES ( Cliente[data_primeira_compra] ),\n"
                           "            Cliente[data_primeira_compra] >= inicio && Cliente[data_primeira_compra] <= fim )\n"
                           "    )", INT),
        ("Clientes recorrentes", "VAR c = [Clientes compradores]\nRETURN IF ( NOT ISBLANK ( c ), c - [Novos clientes] )",
         INT),
        ("Recompra 90d %", "VAR mes = MAX ( Calendario[inicio_mes] )\nVAR mesCoorte = EDATE ( mes, -3 )\n"
                           "RETURN\n    CALCULATE (\n        DIVIDE ( SUM ( Coorte[recomprou_90d] ), COUNTROWS ( Coorte ) ),\n"
                           "        Coorte[mes_coorte] = mesCoorte\n    )", PCT),
        ("Recompra em 90 dias", 'VAR r = [Recompra 90d %]\nRETURN IF ( ISBLANK ( r ), "N/D", FORMAT ( r, "0.0%" ) )', None),
        ("Clientes na faixa", "VAR minimo = SELECTEDVALUE ( FaixaFrequencia[compras_min] )\n"
                              "VAR maximo = SELECTEDVALUE ( FaixaFrequencia[compras_max] )\n"
                              f"VAR clientes = CALCULATETABLE ( VALUES ( Pedido[cliente_id] ), {CONF} )\n"
                              "RETURN\n    COUNTROWS (\n        FILTER (\n"
                              '            ADDCOLUMNS ( clientes, "@pedidos", [Pedidos vendidos] ),\n'
                              "            [@pedidos] >= minimo && [@pedidos] <= maximo\n        )\n    )", INT),
    ],
    "4. Estoque": [
        ("Valor em estoque", "SUM ( Estoque[valor_total] )", MOEDA),
        ("Lotes", "COUNTROWS ( Estoque )", INT),
        ("Lotes vencendo em 30 dias", "CALCULATE ( COUNTROWS ( Estoque ), KEEPFILTERS ( Estoque[faixa_validade_ordem] = 2 ) )",
         INT),
        ("Valor em risco", "CALCULATE ( [Valor em estoque], KEEPFILTERS ( Estoque[faixa_validade_ordem] = 2 ) )", MOEDA),
        ("Lotes vencidos", "CALCULATE ( COUNTROWS ( Estoque ), KEEPFILTERS ( Estoque[vencido] = TRUE () ) )", INT),
        ("Insumos abaixo do mínimo", "CALCULATE ( COUNTROWS ( InsumoPosicao ), KEEPFILTERS ( InsumoPosicao[abaixo_minimo] = "
                                     "TRUE () ) )", INT),
        ("Alerta vencidos", 'VAR n = [Lotes vencidos]\nRETURN FORMAT ( n + 0, "0" ) & " lote(s) vencido(s)"', None),
        ("Alerta mínimo", 'VAR n = [Insumos abaixo do mínimo]\nRETURN FORMAT ( n + 0, "0" ) & " insumos abaixo do mínimo"',
         None),
    ],
    "5. Canais": [
        ("Atendimentos", "COUNTROWS ( Atendimento )", INT),
        ("Primeira resposta (min)", "DIVIDE ( SUM ( Atendimento[segundos_primeira_resposta] ), "
                                    "COUNT ( Atendimento[segundos_primeira_resposta] ) ) / 60", '0.0" min"'),
        ("Avaliação média", "AVERAGE ( Atendimento[avaliacao] )", "0.0"),
    ],
    "0. Geral": [
        ("Posição", 'VAR fim = MAX ( Calendario[fim_mes] )\nRETURN "Posição: " & FORMAT ( fim, "dd/MM/yyyy" )', None),
    ],
}

RELACOES = [
    ("Pedido", "data_venda", "Calendario", "data"), ("Oportunidade", "data_criacao", "Calendario", "data"),
    ("Atendimento", "data_inicio", "Calendario", "data"), ("Estoque", "data_posicao", "Calendario", "data"),
    ("InsumoPosicao", "data_posicao", "Calendario", "data"),
    ("Pedido", "canal_id", "Canal", "canal_id"), ("Oportunidade", "canal_id", "Canal", "canal_id"),
    ("Atendimento", "canal_id", "Canal", "canal_id"), ("Coorte", "canal_id", "Canal", "canal_id"),
    ("Pedido", "cliente_id", "Cliente", "cliente_id"),
    ("Pedido", "atendente_id", "Atendente", "atendente_id"), ("Oportunidade", "atendente_id", "Atendente", "atendente_id"),
    ("Atendimento", "atendente_id", "Atendente", "atendente_id"),
    ("PedidoItem", "pedido_id", "Pedido", "pedido_id"), ("OrcamentoVersao", "oportunidade_id", "Oportunidade", "oportunidade_id"),
    ("Estoque", "insumo_id", "Insumo", "insumo_id"), ("InsumoPosicao", "insumo_id", "Insumo", "insumo_id"),
]


def tag(*partes) -> str:
    return str(uuid.uuid5(NS, "/".join(partes)))


def ident(nome: str) -> str:
    return nome if nome.replace("_", "").isalnum() and nome.isascii() else "'" + nome.replace("'", "''") + "'"


def escrever(caminho: Path, texto: str):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")


def tabela_tmdl(nome: str, origem: str, colunas: list) -> str:
    linhas = [f"table {nome}", f"\tlineageTag: {tag(nome)}"]
    if nome == "Calendario":
        linhas.append("\tdataCategory: Time")
    linhas.append("")
    for coluna, tipo, oculta, formato in colunas:
        linhas.append(f"\tcolumn {coluna}")
        linhas.append(f"\t\tdataType: {T[tipo][0]}")
        if oculta:
            linhas.append("\t\tisHidden")
        if nome == "Calendario" and coluna == "data":
            linhas.append("\t\tisKey")
        if tipo == "moeda":
            linhas.append(f"\t\tformatString: {MOEDA2}")
        elif formato:
            linhas.append(f"\t\tformatString: {formato}")
        linhas.append(f"\t\tlineageTag: {tag(nome, coluna)}")
        linhas.append("\t\tsummarizeBy: none")
        linhas.append(f"\t\tsourceColumn: {coluna}")
        if (nome, coluna) in ORDENAR_POR:
            linhas.append(f"\t\tsortByColumn: {ORDENAR_POR[(nome, coluna)]}")
        linhas.append("")
        linhas.append("\t\tannotation SummarizationSetBy = User")
        linhas.append("")
    tipos = ", ".join(f'{{"{c}", {T[t][1]}}}' for c, t, _, _ in colunas)
    nomes = ", ".join(f'"{c}"' for c, _, _, _ in colunas)
    linhas += [
        f"\tpartition {nome} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        "\t\t\t\t    Fonte = PostgreSQL.Database(Servidor, BancoDados),",
        f'\t\t\t\t    Dados = Fonte{{[Schema = "public", Item = "{origem}"]}}[Data],',
        f"\t\t\t\t    Colunas = Table.SelectColumns(Dados, {{{nomes}}}),",
        f"\t\t\t\t    Tipos = Table.TransformColumnTypes(Colunas, {{{tipos}}})",
        "\t\t\t\tin",
        "\t\t\t\t    Tipos",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    return "\n".join(linhas)


def medidas_tmdl() -> str:
    linhas = ["table Medidas", f"\tlineageTag: {tag('Medidas')}", ""]
    for pasta, medidas in MEDIDAS.items():
        for nome, expressao, formato in medidas:
            corpo = expressao.split("\n")
            if len(corpo) == 1:
                linhas.append(f"\tmeasure {ident(nome)} = {corpo[0]}")
            else:
                linhas.append(f"\tmeasure {ident(nome)} =")
                linhas += [f"\t\t\t{l}" for l in corpo]
            if formato:
                linhas.append(f"\t\tformatString: {formato}")
            linhas.append(f"\t\tdisplayFolder: {pasta}")
            linhas.append(f"\t\tlineageTag: {tag('Medidas', nome)}")
            linhas.append("")
    linhas += [
        "\tcolumn Coluna",
        "\t\tdataType: string",
        "\t\tisHidden",
        f"\t\tlineageTag: {tag('Medidas', 'Coluna')}",
        "\t\tsummarizeBy: none",
        "\t\tisNameInferred",
        "\t\tsourceColumn: [Coluna]",
        "",
        "\t\tannotation SummarizationSetBy = Automatic",
        "",
        "\tpartition Medidas = calculated",
        "\t\tmode: import",
        '\t\tsource = ROW ( "Coluna", BLANK () )',
        "",
        "\tannotation PBI_Id = medidas",
        "",
    ]
    return "\n".join(linhas)


def main():
    d = SM / "definition"
    escrever(SM / "definition.pbism", json.dumps({"version": "4.0", "settings": {}}, indent=2) + "\n")
    escrever(SM / ".platform", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": "FarmaBI"},
        "config": {"version": "2.0", "logicalId": tag("semanticModel")}}, indent=2) + "\n")
    escrever(d / "database.tmdl", "database\n\tcompatibilityLevel: 1601\n\n")
    tabelas = list(TABELAS) + ["Medidas"]
    escrever(d / "model.tmdl", "\n".join([
        "model Model",
        "\tculture: pt-BR",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: pt-BR",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        f"annotation PBI_QueryOrder = {json.dumps(['Servidor', 'BancoDados'] + list(TABELAS))}",
        "",
    ] + [f"ref table {t}" for t in tabelas]) + "\n")
    escrever(d / "expressions.tmdl", "\n".join([
        'expression Servidor = "localhost:5433" meta [IsParameterQuery = true, Type = "Text", '
        "IsParameterQueryRequired = true]",
        f"\tlineageTag: {tag('Servidor')}",
        "",
        "\tannotation PBI_ResultType = Text",
        "",
        'expression BancoDados = "farmabi" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
        f"\tlineageTag: {tag('BancoDados')}",
        "",
        "\tannotation PBI_ResultType = Text",
        "",
    ]))
    escrever(d / "relationships.tmdl", "\n".join(
        f"relationship {tag('rel', a, b, c, e)}\n\tfromColumn: {a}.{b}\n\ttoColumn: {c}.{e}\n"
        for a, b, c, e in RELACOES))
    for nome, (origem, colunas) in TABELAS.items():
        escrever(d / "tables" / f"{nome}.tmdl", tabela_tmdl(nome, origem, colunas))
    escrever(d / "tables" / "Medidas.tmdl", medidas_tmdl())
    print(f"modelo gerado em {SM}")


main()
