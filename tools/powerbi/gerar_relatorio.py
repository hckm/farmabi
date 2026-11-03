"""Gera o relatorio PBIR do FarmaBI (powerbi/FarmaBI.Report) fiel ao prototipo HTML.

Uso: python tools/powerbi/gerar_relatorio.py [paginas...]
O tema base CY24SU10 (Microsoft) fica versionado em StaticResources e nao e regenerado.
"""
import json
import shutil
import sys
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2] / "powerbi"
SOMENTE = set(sys.argv[1:])
REL = RAIZ / "FarmaBI.Report"
DEF = REL / "definition"
NS = uuid.UUID("a3c1e7d2-5f4b-4e8a-9c21-7b6d0e4f1a33")

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
V_VISUAL = f"{SCHEMA}/visualContainer/2.0.0/schema.json"
V_PAGE = f"{SCHEMA}/page/1.4.0/schema.json"

TINTA, MUTED, NAV, VERDE = "#172D34", "#6B7C85", "#10242B", "#0D9E80"
X0, LARG = 216, 1048          # area principal
FIM = X0 + LARG


def nid(*partes) -> str:
    return uuid.uuid5(NS, "/".join(partes)).hex[:20]


# ------------------------------------------------------------ expressoes
def lit(valor: str) -> dict:
    return {"expr": {"Literal": {"Value": valor}}}


def txt(texto: str) -> dict:
    return lit("'" + texto.replace("'", "''") + "'")


def cor(hexa: str) -> dict:
    return {"solid": {"color": txt(hexa)}}


def coluna(entidade: str, prop: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": entidade}}, "Property": prop}}


def medida(prop: str) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "Medidas"}}, "Property": prop}}


def proj(campo: dict, rotulo: str | None = None) -> dict:
    tipo = "Measure" if "Measure" in campo else "Column"
    item = campo[tipo]
    p = {"field": campo, "queryRef": f"{item['Expression']['SourceRef']['Entity']}.{item['Property']}"}
    if rotulo:
        p["displayName"] = rotulo
    return p


def filtro_in(entidade: str, prop: str, valores: list[str]) -> dict:
    return {"Version": 2, "From": [{"Name": "c", "Entity": entidade, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": prop}}],
                "Values": [[{"Literal": {"Value": v}}] for v in valores]}}}]}


def filtro_visual(nome: str, entidade: str, prop: str, valores: list[str]) -> dict:
    return {"filters": [{"name": nome, "field": coluna(entidade, prop), "type": "Categorical",
                         "filter": filtro_in(entidade, prop, valores), "howCreated": "User",
                         "isHiddenInViewMode": True}]}


SO_ANALISE = ("Calendario", "periodo_analise", ["true"])


# --------------------------------------------------------------- visuais
def container(nome, x, y, w, h, visual, z=0, filtros=None) -> dict:
    v = {"$schema": V_VISUAL, "name": nome,
         "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}, "visual": visual}
    if filtros:
        v["filterConfig"] = filtros
    return v


def titulo(texto: str | None) -> dict:
    if not texto:
        return {"title": [{"properties": {"show": lit("false")}}]}
    return {"title": [{"properties": {"show": lit("true"), "text": txt(texto), "fontColor": cor(TINTA),
                                      "fontSize": lit("11D"), "bold": lit("true")}}]}


def sem_fundo() -> dict:
    return {"background": [{"properties": {"show": lit("false")}}],
            "border": [{"properties": {"show": lit("false")}}]}


def caixa_texto(paragrafos: list[list[tuple]], alinhamento: str = "left") -> dict:
    """paragrafos: lista de listas de (texto, tamanho_pt, cor, negrito)."""
    ps = []
    for runs in paragrafos:
        ps.append({"textRuns": [{"value": t, "textStyle": {
            "fontSize": f"{tam}pt", "color": c, **({"fontWeight": "bold"} if b else {})}} for t, tam, c, b in runs],
            "horizontalTextAlignment": alinhamento})
    return {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": ps}}]},
            "visualContainerObjects": sem_fundo(), "drillFilterOtherVisuals": True}


def forma(preenchimento: str) -> dict:
    return {"visualType": "basicShape",
            "objects": {"general": [{"properties": {"shapeType": txt("rectangle")}}],
                        "fill": [{"properties": {"fillColor": cor(preenchimento), "transparency": lit("0D")}}],
                        "line": [{"properties": {"lineColor": cor(preenchimento)}}]},
            "visualContainerObjects": sem_fundo(), "drillFilterOtherVisuals": True}


def cartao(nome_medida: str) -> dict:
    return {"visualType": "card",
            "query": {"queryState": {"Values": {"projections": [proj(medida(nome_medida))]}}},
            "objects": {"labels": [{"properties": {"color": cor(TINTA), "fontSize": lit("22D"),
                                                   "labelDisplayUnits": lit("1D")}}],
                        "categoryLabels": [{"properties": {"show": lit("true"), "color": cor(MUTED),
                                                           "fontSize": lit("10D")}}]},
            "visualContainerObjects": titulo(None), "drillFilterOtherVisuals": True}


def cartao_texto(nome_medida: str, cor_texto: str, fundo: str) -> dict:
    return {"visualType": "card",
            "query": {"queryState": {"Values": {"projections": [proj(medida(nome_medida))]}}},
            "objects": {"labels": [{"properties": {"color": cor(cor_texto), "fontSize": lit("12D")}}],
                        "categoryLabels": [{"properties": {"show": lit("false")}}]},
            "visualContainerObjects": {**titulo(None),
                                       "background": [{"properties": {"show": lit("true"), "color": cor(fundo)}}]},
            "drillFilterOtherVisuals": True}


def segmentacao(entidade: str, prop: str, rotulo: str, padrao: str | None, grupo: str) -> dict:
    objetos = {"data": [{"properties": {"mode": txt("Dropdown")}}],
               "selection": [{"properties": {"singleSelect": lit("true")}}],
               "header": [{"properties": {"show": lit("false")}}]}
    if padrao:
        objetos["general"] = [{"properties": {"filter": {"filter": filtro_in(entidade, prop, [padrao])}}}]
    return {"visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": [proj(coluna(entidade, prop))]}}},
            "objects": objetos, "visualContainerObjects": titulo(rotulo),
            "syncGroup": {"groupName": grupo, "fieldChanges": True, "filterChanges": True},
            "drillFilterOtherVisuals": True}


def grafico(tipo: str, categoria: dict, valores: list[dict], rotulo: str, rotulos_dados: bool = True,
            series: dict | None = None) -> dict:
    estado = {"Category": {"projections": [proj(categoria)]},
              "Y": {"projections": [proj(v) for v in valores]}}
    if series:
        estado["Series"] = {"projections": [proj(series)]}
    objetos = {}
    if rotulos_dados:
        objetos["labels"] = [{"properties": {"show": lit("true"), "labelDisplayUnits": lit("1D")}}]
    if tipo not in ("donutChart", "funnel"):
        objetos["categoryAxis"] = [{"properties": {"showAxisTitle": lit("false")}}]
        objetos["valueAxis"] = [{"properties": {"showAxisTitle": lit("false"), "labelDisplayUnits": lit("1D")}}]
    if tipo == "donutChart":
        objetos["legend"] = [{"properties": {"show": lit("true"), "position": txt("Right"),
                                             "showTitle": lit("false")}}]
        objetos["labels"] = [{"properties": {"show": lit("true"), "labelStyle": txt("Percent of total")}}]
    return {"visualType": tipo, "query": {"queryState": estado}, "objects": objetos,
            "visualContainerObjects": titulo(rotulo), "drillFilterOtherVisuals": True}


def tabela(campos: list[tuple], rotulo: str) -> dict:
    return {"visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": [proj(c, r) for c, r in campos]}}},
            "visualContainerObjects": titulo(rotulo), "drillFilterOtherVisuals": True}


# ----------------------------------------------------------------- paginas
NAV_PAGINAS = [
    ("executivo", "Executivo e Vendas", "Gestão & performance", "Resultados comerciais, faturamento e participação por canal."),
    ("orcamentos", "Orçamentos e Conversão", "Gestão comercial", "Funil comercial, conversão e oportunidades perdidas."),
    ("clientes", "Clientes e Recompra", "Relacionamento", "Aquisição, fidelização e frequência de compras."),
    ("estoque", "Estoque e Validade", "Operação & suprimentos", "Saldos, lotes, insumos e alertas de vencimento."),
    ("canais", "Canais e Atendimento", "Gestão comercial", "Solicitações, tempo de resposta e eficiência dos canais."),
]

INSIGHTS = {
    "executivo": ("Leitura gerencial: ", "o indicador de vendas considera apenas pedidos confirmados, sem multiplicar a "
                  "receita pelo número de fórmulas de cada pedido. Cancelados e devolvidos ficam fora. Dados fictícios."),
    "orcamentos": ("Regra funcional: ", "cada oportunidade é contada uma única vez, mesmo quando o orçamento tem "
                   "revisões. Em produção, a conversão deverá considerar uma janela de maturação configurável "
                   "(ex.: 30 dias)."),
    "clientes": ("Importante: ", "a recompra em 90 dias usa a coorte de novos clientes de três meses antes, cuja janela "
                 "já terminou (Mai a Jul mostram N/D). Não equivale ao percentual de recorrentes no mês nem indica "
                 "necessidade clínica de reposição."),
    "estoque": ("Posição histórica: ", "estoque exibido no fechamento do mês, sem filtro de canal; a validade é "
                "comparada com a data da posição. Os alertas são gerenciais: a decisão de bloqueio, segregação ou "
                "descarte é do farmacêutico responsável."),
    "canais": ("Definição de tempo: ", "a primeira resposta mede o intervalo entre a solicitação e a primeira "
               "resposta humana, ponderado pelo número de atendimentos. Respostas automáticas não contam."),
}

Y_FILTRO, Y_KPI, Y_GRAF, Y_TAB, Y_INS = 80, 152, 254, 518, 672
H_KPI, H_GRAF, H_TAB = 90, 252, 146
L_KPI = (LARG - 3 * 12) / 4
L_ESQ = 612
X_DIR, L_DIR = X0 + L_ESQ + 12, LARG - L_ESQ - 12


def comuns(pid: str, indice: int, nome: str, secao: str, descricao: str, com_canal: bool) -> list:
    vs = [
        container(nid(pid, "lateral"), 0, 0, 200, 720, forma(NAV), z=0),
        container(nid(pid, "marca"), 12, 18, 180, 60, caixa_texto([
            [("FarmaBI", 20, "#FFFFFF", True), (".", 20, "#50D5B2", True)],
            [("INTELIGÊNCIA EM FARMÁCIA", 7, "#9DB0B4", False)]]), z=1000),
        container(nid(pid, "rotulo_nav"), 12, 92, 180, 24, caixa_texto([[("DASHBOARDS", 7, "#7F999F", True)]]), z=1000),
        container(nid(pid, "navegador"), 12, 118, 176, 270, {"visualType": "pageNavigator",
                                                            "objects": {"layout": [{"properties": {
                                                                "orientation": lit("1D")}}]},
                                                            "visualContainerObjects": sem_fundo(),
                                                            "drillFilterOtherVisuals": True}, z=2000),
        container(nid(pid, "demo"), 12, 640, 180, 66, caixa_texto([
            [("● Ambiente demonstrativo", 8, "#BDD0CC", True)],
            [("Dados fictícios para avaliação visual e validação funcional.", 7, "#8199A0", False)]]), z=1000),
        container(nid(pid, "titulo"), X0, 8, 760, 72, caixa_texto([
            [(f"{secao.upper()} · VISÃO 0{indice}", 7, "#08775F", True)],
            [(nome, 18, TINTA, True)],
            [(descricao, 9, MUTED, False)]]), z=1000),
        container(nid(pid, "posicao"), FIM - 300, 14, 170, 30, cartao_texto("Posição", "#8898A0", "#F5F7F9"), z=1000),
        container(nid(pid, "tag"), FIM - 122, 14, 122, 30, caixa_texto([[("● Dados simulados", 8, "#0B7961", True)]],
                                                                     "center"), z=1000),
        container(nid(pid, "periodo"), X0, Y_FILTRO, 200, 64,
                  segmentacao("Calendario", "mes_ano", "PERÍODO", "'Out/2026'", "Periodo"), z=3000,
                  filtros=filtro_visual(nid(pid, "f_periodo"), *SO_ANALISE)),
    ]
    if com_canal:
        vs.append(container(nid(pid, "canal"), X0 + 212, Y_FILTRO, 200, 64,
                            segmentacao("Canal", "nome", "CANAL", None, "Canal"), z=3000))
    vs.append(container(nid(pid, "insight"), X0, Y_INS, LARG, 44, caixa_texto([[
        (INSIGHTS[pid][0], 8, "#176C5A", True), (INSIGHTS[pid][1], 8, "#397367", False)]]), z=1000))
    return vs


def kpis(pid: str, medidas: list[str]) -> list:
    return [container(nid(pid, "kpi", m), X0 + i * (L_KPI + 12), Y_KPI, L_KPI, H_KPI, cartao(m), z=4000 + i)
            for i, m in enumerate(medidas)]


def pagina_executivo(pid):
    linha = nid(pid, "linha")
    vs = kpis(pid, ["Vendas líquidas", "Pedidos vendidos", "Ticket médio", "Crescimento"]) + [
        container(linha, X0, Y_GRAF, L_ESQ, H_GRAF,
                  grafico("areaChart", coluna("Calendario", "mes_ano"), [medida("Vendas líquidas")],
                          "Evolução de vendas · faturamento líquido mensal"), z=5000,
                  filtros=filtro_visual(nid(pid, "f_linha"), *SO_ANALISE)),
        container(nid(pid, "rosca"), X_DIR, Y_GRAF, L_DIR, H_GRAF,
                  grafico("donutChart", coluna("Canal", "nome"), [medida("Vendas líquidas")],
                          "Participação por canal"), z=5001),
        container(nid(pid, "tabela"), X0, Y_TAB, LARG, H_TAB, tabela([
            (coluna("Canal", "nome"), "Canal"), (medida("Pedidos vendidos"), "Pedidos"),
            (medida("Vendas líquidas"), "Vendas líquidas"), (medida("Participação %"), "Participação")],
            "Desempenho comercial por canal"), z=6000),
    ]
    return vs, [linha]


def pagina_orcamentos(pid):
    vs = kpis(pid, ["Orçamentos gerados", "Convertidos", "Taxa de conversão", "Em negociação"]) + [
        container(nid(pid, "funil"), X0, Y_GRAF, L_ESQ, H_GRAF,
                  grafico("funnel", coluna("EtapaFunil", "etapa"), [medida("Quantidade na etapa")],
                          "Funil de orçamentos"), z=5000),
        container(nid(pid, "motivos"), X_DIR, Y_GRAF, L_DIR, H_GRAF,
                  grafico("clusteredBarChart", coluna("Oportunidade", "motivo_perda"), [medida("Perdidos")],
                          "Motivos de perda"), z=5001),
        container(nid(pid, "tabela"), X0, Y_TAB, LARG, H_TAB, tabela([
            (coluna("Canal", "nome"), "Canal"), (medida("Orçamentos gerados"), "Orçados"),
            (medida("Convertidos"), "Convertidos"), (medida("Taxa de conversão"), "Conversão")],
            "Conversão por canal"), z=6000),
    ]
    return vs, []


def pagina_clientes(pid):
    colunas = nid(pid, "colunas")
    vs = kpis(pid, ["Clientes compradores", "Novos clientes", "Clientes recorrentes", "Recompra em 90 dias"]) + [
        container(colunas, X0, Y_GRAF, L_ESQ, H_GRAF,
                  grafico("clusteredColumnChart", coluna("Calendario", "mes_ano"),
                          [medida("Novos clientes"), medida("Clientes recorrentes")], "Novos × recorrentes"), z=5000,
                  filtros=filtro_visual(nid(pid, "f_colunas"), *SO_ANALISE)),
        container(nid(pid, "frequencia"), X_DIR, Y_GRAF, L_DIR, H_GRAF,
                  grafico("clusteredBarChart", coluna("FaixaFrequencia", "faixa"), [medida("Clientes na faixa")],
                          "Frequência de compra no mês"), z=5001),
        container(nid(pid, "tabela"), X0, Y_TAB, LARG, H_TAB, tabela([
            (coluna("Canal", "nome"), "Canal"), (medida("Clientes compradores"), "Compradores"),
            (medida("Novos clientes"), "Novos"), (medida("Recompra em 90 dias"), "Recompra 90 dias")],
            "Perfil dos clientes por canal"), z=6000),
    ]
    return vs, [colunas]


def pagina_estoque(pid):
    l_tab = 680
    vs = kpis(pid, ["Valor em estoque", "Insumos abaixo do mínimo", "Lotes vencendo em 30 dias", "Valor em risco"]) + [
        container(nid(pid, "faixas"), X0, Y_GRAF, L_ESQ, H_GRAF,
                  grafico("clusteredBarChart", coluna("Estoque", "faixa_validade"), [medida("Lotes")],
                          "Validade dos lotes"), z=5000),
        container(nid(pid, "categorias"), X_DIR, Y_GRAF, L_DIR, H_GRAF,
                  grafico("donutChart", coluna("Insumo", "categoria"), [medida("Valor em estoque")],
                          "Estoque por categoria"), z=5001),
        container(nid(pid, "tabela"), X0, Y_TAB, l_tab, H_TAB, tabela([
            (coluna("Insumo", "descricao"), "Matéria-prima"), (coluna("Estoque", "lote_codigo"), "Lote"),
            (coluna("Estoque", "saldo_fisico"), "Saldo"), (coluna("Insumo", "unidade_medida"), "Un."),
            (coluna("Estoque", "data_validade"), "Validade"), (coluna("Estoque", "dias_para_vencer"), "Dias")],
            "Matérias-primas com vencimento em até 30 dias"), z=6000,
                  filtros=filtro_visual(nid(pid, "f_tabela"), "Estoque", "faixa_validade_ordem", ["2L"])),
        container(nid(pid, "alerta_vencidos"), X0 + l_tab + 12, Y_TAB, LARG - l_tab - 12, 68,
                  cartao_texto("Alerta vencidos", "#94651C", "#FFF5F3"), z=6001),
        container(nid(pid, "alerta_minimo"), X0 + l_tab + 12, Y_TAB + 80, LARG - l_tab - 12, 68,
                  cartao_texto("Alerta mínimo", "#94651C", "#FFF8ED"), z=6002),
    ]
    return vs, []


def pagina_canais(pid):
    vs = kpis(pid, ["Atendimentos", "Primeira resposta (min)", "Orçamentos gerados", "Taxa de conversão"]) + [
        container(nid(pid, "volume"), X0, Y_GRAF, L_ESQ, H_GRAF,
                  grafico("clusteredBarChart", coluna("Canal", "nome"), [medida("Atendimentos")],
                          "Volume por canal"), z=5000),
        container(nid(pid, "conversao"), X_DIR, Y_GRAF, L_DIR, H_GRAF,
                  grafico("clusteredBarChart", coluna("Canal", "nome"), [medida("Taxa de conversão")],
                          "Conversão por canal"), z=5001),
        container(nid(pid, "tabela"), X0, Y_TAB, LARG, H_TAB, tabela([
            (coluna("Canal", "nome"), "Canal"), (medida("Atendimentos"), "Contatos"),
            (medida("Primeira resposta (min)"), "Primeira resposta"), (medida("Taxa de conversão"), "Conversão"),
            (medida("Vendas líquidas"), "Vendas líquidas")], "Eficiência do atendimento"), z=6000),
    ]
    return vs, []


CONSTRUTORES = {"executivo": pagina_executivo, "orcamentos": pagina_orcamentos, "clientes": pagina_clientes,
                "estoque": pagina_estoque, "canais": pagina_canais}


# ----------------------------------------------------------------- arquivos
def escrever(caminho: Path, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = dados if isinstance(dados, str) else json.dumps(dados, ensure_ascii=False, indent=2) + "\n"
    caminho.write_text(texto, encoding="utf-8", newline="\n")


def tema() -> dict:
    fundo_branco = [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}]
    sem_moldura = {"background": [{"show": False}], "border": [{"show": False}],
                   "padding": [{"top": 0, "bottom": 0, "left": 0, "right": 0}]}
    return {
        "name": "FarmaBI",
        "dataColors": ["#15A589", "#5488D8", "#8C7AD8", "#E4A34C", "#D4666E", "#0E9E82", "#4489BC", "#BF7B70"],
        "foreground": TINTA, "foregroundNeutralSecondary": MUTED, "background": "#FFFFFF",
        "backgroundLight": "#F5F7F9", "tableAccent": VERDE, "good": VERDE, "bad": "#D45C61", "neutral": "#E3A447",
        "textClasses": {
            "callout": {"fontSize": 22, "fontFace": "Segoe UI Semibold", "color": TINTA},
            "title": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": TINTA},
            "header": {"fontSize": 10, "fontFace": "Segoe UI Semibold", "color": TINTA},
            "label": {"fontSize": 9, "fontFace": "Segoe UI", "color": MUTED}},
        "visualStyles": {
            "*": {"*": {"background": fundo_branco,
                        "border": [{"show": True, "color": {"solid": {"color": "#E5EBEF"}}, "radius": 12}],
                        "padding": [{"top": 10, "bottom": 10, "left": 12, "right": 12}]}},
            "page": {"*": {"background": [{"color": {"solid": {"color": "#F5F7F9"}}, "transparency": 0}],
                           "outspace": [{"color": {"solid": {"color": "#F5F7F9"}}}]}},
            "tableEx": {"*": {"columnHeaders": [{"backColor": {"solid": {"color": "#F8FAFB"}},
                                                 "fontColor": {"solid": {"color": "#8B9BA3"}}, "bold": True}],
                              "values": [{"fontColorPrimary": {"solid": {"color": "#40575E"}},
                                          "fontColorSecondary": {"solid": {"color": "#40575E"}},
                                          "backColorPrimary": {"solid": {"color": "#FFFFFF"}},
                                          "backColorSecondary": {"solid": {"color": "#FFFFFF"}}}],
                              "grid": [{"gridHorizontal": True, "gridHorizontalColor": {"solid": {"color": "#EDF0F1"}},
                                        "gridVertical": False}]}},
            **{tipo: {"*": sem_moldura} for tipo in ("textbox", "basicShape", "pageNavigator")},
            "slicer": {"*": {"padding": [{"top": 4, "bottom": 4, "left": 10, "right": 10}]}},
        },
    }


def main():
    if DEF.exists():
        shutil.rmtree(DEF)
    escrever(RAIZ / "FarmaBI.pbip", {"version": "1.0", "artifacts": [{"report": {"path": "FarmaBI.Report"}}],
                                     "settings": {"enableAutoRecovery": True}})
    escrever(REL / "definition.pbir", {"version": "4.0",
                                       "datasetReference": {"byPath": {"path": "../FarmaBI.SemanticModel"}}})
    escrever(REL / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": "FarmaBI"},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(NS, "report"))}})
    base = REL / "StaticResources" / "SharedResources" / "BaseThemes" / "CY24SU10.json"
    if not base.exists():
        sys.exit(f"tema base ausente: {base}")
    escrever(REL / "StaticResources" / "RegisteredResources" / "FarmaBI.json", tema())
    escrever(DEF / "version.json", {"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    escrever(DEF / "report.json", {
        "$schema": f"{SCHEMA}/report/1.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": "CY24SU10", "reportVersionAtImport": "5.61", "type": "SharedResources"},
            "customTheme": {"name": "FarmaBI.json", "reportVersionAtImport": "5.61", "type": "RegisteredResources"}},
        "layoutOptimization": "None",
        "objects": {"outspacePane": [{"properties": {"expanded": lit("false")}}]},
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": "FarmaBI.json", "path": "FarmaBI.json", "type": "CustomTheme"}]}],
        "settings": {"exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True,
                     "allowChangeFilterTypes": True, "useEnhancedTooltips": True}})

    paginas = [p for p in NAV_PAGINAS if not SOMENTE or p[0] in SOMENTE]
    for indice, (pid, nome, secao, descricao) in enumerate(NAV_PAGINAS, start=1):
        if (pid, nome, secao, descricao) not in paginas:
            continue
        visuais, sem_filtro_periodo = CONSTRUTORES[pid](pid)
        visuais = comuns(pid, indice, nome, secao, descricao, pid != "estoque") + visuais
        nome_periodo = nid(pid, "periodo")
        pagina = {"$schema": V_PAGE, "name": pid, "displayName": nome, "displayOption": "FitToPage",
                  "height": 720, "width": 1280}
        if sem_filtro_periodo:
            pagina["visualInteractions"] = [{"source": nome_periodo, "target": alvo, "type": "NoFilter"}
                                            for alvo in sem_filtro_periodo]
        escrever(DEF / "pages" / pid / "page.json", pagina)
        for v in visuais:
            escrever(DEF / "pages" / pid / "visuals" / v["name"] / "visual.json", v)
    escrever(DEF / "pages" / "pages.json", {"$schema": f"{SCHEMA}/pagesMetadata/1.0.0/schema.json",
                                            "pageOrder": [p[0] for p in paginas], "activePageName": paginas[0][0]})
    print(f"relatorio gerado: {[p[0] for p in paginas]}")


main()
