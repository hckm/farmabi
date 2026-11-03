"""Confere o banco farmabi (container farmabi-db) contra os numeros de referencia.

Uso: python tools/conferir_banco.py   (com o container de pe: docker compose up -d)
"""
import subprocess
import sys
from decimal import Decimal

import referencia as ref

CONTAINER = "farmabi-db"


def consultar(sql: str) -> list[list[str]]:
    resultado = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "farmabi_admin", "-d", "farmabi", "-At", "-F", "\t",
         "-v", "ON_ERROR_STOP=1"],
        input=sql, capture_output=True, text=True, encoding="utf-8", check=True)
    return [linha.split("\t") for linha in resultado.stdout.splitlines() if linha]


def main() -> int:
    falhas = []

    def conferir(descricao, obtido, esperado):
        if obtido != esperado:
            falhas.append(f"{descricao}: obtido {obtido}, esperado {esperado}")

    comercial = consultar("""
        SELECT date_trunc('month', p.data_venda)::date, c.codigo, sum(p.valor_liquido), count(DISTINCT p.pedido_id),
               count(DISTINCT p.cliente_id),
               count(DISTINCT p.cliente_id) FILTER (
                   WHERE date_trunc('month', cl.data_primeira_compra) = date_trunc('month', p.data_venda))
          FROM fato_pedido p
          JOIN dim_canal c ON c.canal_id = p.canal_id
          JOIN dim_cliente cl ON cl.cliente_id = p.cliente_id
         WHERE p.status = 'CONFIRMADO'
         GROUP BY 1, 2;""")
    funil = {(m, c): (int(g), int(conv), int(perd), int(pend)) for m, c, g, conv, perd, pend in consultar("""
        SELECT date_trunc('month', o.criada_em)::date, c.codigo, count(*),
               count(*) FILTER (WHERE status = 'CONVERTIDA'), count(*) FILTER (WHERE status = 'PERDIDA'),
               count(*) FILTER (WHERE status = 'PENDENTE')
          FROM fato_oportunidade o JOIN dim_canal c ON c.canal_id = o.canal_id GROUP BY 1, 2;""")}
    atendimentos = {(m, c): (int(n), Decimal(media)) for m, c, n, media in consultar("""
        SELECT date_trunc('month', a.iniciado_em)::date, c.codigo, count(*),
               round(avg(a.segundos_primeira_resposta) / 60.0, 6)
          FROM fato_atendimento a JOIN dim_canal c ON c.canal_id = a.canal_id GROUP BY 1, 2;""")}

    for mes_txt, canal, vendas, pedidos, compradores, novos in comercial:
        mes = ref.MESES[[m.isoformat() for m in ref.MESES].index(mes_txt)]
        alvo, chave = ref.COMERCIAL[mes][canal], (mes_txt, canal)
        rotulo = f"{mes_txt} {canal}"
        conferir(f"{rotulo} vendas", Decimal(vendas), Decimal(alvo.vendas))
        conferir(f"{rotulo} pedidos", int(pedidos), alvo.pedidos)
        conferir(f"{rotulo} compradores", int(compradores), alvo.compradores)
        conferir(f"{rotulo} novos", int(novos), alvo.novos)
        gerados, convertidos, perdidos, pendentes = funil[chave]
        conferir(f"{rotulo} orcamentos", gerados, alvo.orcamentos)
        conferir(f"{rotulo} convertidos", convertidos, alvo.pedidos)
        conferir(f"{rotulo} estados exclusivos", convertidos + perdidos + pendentes, gerados)
        conferir(f"{rotulo} atendimentos", atendimentos[chave][0], alvo.atendimentos)
        conferir(f"{rotulo} 1a resposta", atendimentos[chave][1], Decimal(str(alvo.resposta_min)).quantize(
            Decimal("0.000001")))
    conferir("meses x canais conferidos", len(comercial), len(ref.MESES) * len(ref.CANAIS))

    for posicao, alvo in ref.ESTOQUE.items():
        valor, risco, vencendo, vencidos = consultar(f"""
            SELECT sum(valor_total), sum(valor_total) FILTER (WHERE faixa_validade_ordem = 2),
                   count(*) FILTER (WHERE faixa_validade_ordem = 2), count(*) FILTER (WHERE vencido)
              FROM vw_saldo_estoque WHERE data_posicao = DATE '{posicao.isoformat()}';""")[0]
        abaixo = consultar(f"SELECT count(*) FROM vw_insumo_posicao "
                           f"WHERE data_posicao = DATE '{posicao.isoformat()}' AND abaixo_minimo;")[0][0]
        conferir(f"{posicao} valor em estoque", Decimal(valor), Decimal(alvo.valor_total))
        conferir(f"{posicao} valor em risco", Decimal(risco), Decimal(alvo.valor_em_risco))
        conferir(f"{posicao} vencendo 30d", int(vencendo), alvo.vencendo_30d)
        conferir(f"{posicao} vencidos", int(vencidos), alvo.vencidos)
        conferir(f"{posicao} abaixo do minimo", int(abaixo), alvo.abaixo_minimo)

    # Pedido com varias formulas conta uma vez; cancelados/devolvidos ficam fora.
    duplicacao = consultar("""
        SELECT count(DISTINCT p.pedido_id) = (SELECT count(*) FROM fato_pedido WHERE status = 'CONFIRMADO')
          FROM fato_pedido p JOIN fato_pedido_item i ON i.pedido_id = p.pedido_id WHERE p.status = 'CONFIRMADO';""")
    conferir("pedidos nao duplicam com itens", duplicacao[0][0], "t")
    leitura = consultar("SELECT has_table_privilege('farmabi_leitura', 'vw_saldo_estoque', 'SELECT'),"
                        " has_table_privilege('farmabi_leitura', 'fato_pedido', 'INSERT');")[0]
    conferir("farmabi_leitura somente leitura", leitura, ["t", "f"])

    if falhas:
        print("\n".join(["FALHAS:"] + falhas))
        return 1
    print(f"OK: {len(ref.MESES) * len(ref.CANAIS)} combinacoes mes x canal e {len(ref.ESTOQUE)} posicoes de estoque")
    return 0


if __name__ == "__main__":
    sys.exit(main())
