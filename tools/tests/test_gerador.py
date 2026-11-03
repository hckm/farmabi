import hashlib
import sys
import unittest
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gerar_dados  # noqa: E402
import referencia as ref  # noqa: E402


def mes_de(dia: date) -> date:
    return dia.replace(day=1)


class GeradorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = gerar_dados.gerar()
        cls.confirmados = [p for p in cls.base.pedidos if p.status == "CONFIRMADO"]

    def test_vendas_pedidos_e_frequencia_batem_com_a_referencia_por_mes_e_canal(self):
        vendas, pedidos, por_cliente = Counter(), Counter(), defaultdict(Counter)
        for p in self.confirmados:
            chave = (mes_de(p.data_venda), p.canal)
            vendas[chave] += p.centavos_liquido
            pedidos[chave] += 1
            por_cliente[chave][p.cliente.seq] += 1
        for mes in ref.MESES:
            for canal in ref.CANAIS:
                alvo, chave = ref.COMERCIAL[mes][canal.codigo], (mes, canal.codigo)
                with self.subTest(mes=mes, canal=canal.codigo):
                    self.assertEqual(vendas[chave], alvo.vendas * 100)
                    self.assertEqual(pedidos[chave], alvo.pedidos)
                    faixas = Counter(min(q, 3) for q in por_cliente[chave].values())
                    self.assertEqual((faixas[1], faixas[2], faixas[3]), ref.frequencia_ajustada(alvo))

    def test_novos_clientes_tem_primeira_compra_no_mes(self):
        compradores = defaultdict(set)
        for p in self.confirmados:
            compradores[(mes_de(p.data_venda), p.canal)].add(p.cliente.seq)
        primeira = {c.seq: c.primeira_compra for c in self.base.clientes}
        for mes in ref.MESES:
            for canal in ref.CANAIS:
                clientes = compradores[(mes, canal.codigo)]
                novos = sum(1 for seq in clientes if mes_de(primeira[seq]) == mes)
                with self.subTest(mes=mes, canal=canal.codigo):
                    self.assertEqual(len(clientes), ref.COMERCIAL[mes][canal.codigo].compradores)
                    self.assertEqual(novos, ref.COMERCIAL[mes][canal.codigo].novos)

    def test_cliente_compra_em_um_unico_canal(self):
        canais = defaultdict(set)
        for p in self.base.pedidos:
            canais[p.cliente.seq].add(p.canal)
        self.assertTrue(all(len(c) == 1 for c in canais.values()))

    def test_orcamentos_e_atendimentos_batem_e_estados_sao_exclusivos(self):
        oport, status, atend, segundos = Counter(), Counter(), Counter(), Counter()
        for o in self.base.oportunidades:
            chave = (mes_de(o.criada_em.date()), o.atendimento.canal)
            oport[chave] += 1
            status[chave + (o.status,)] += 1
        for a in self.base.atendimentos:
            chave = (mes_de(a.iniciado_em.date()), a.canal)
            atend[chave] += 1
            segundos[chave] += (a.primeira_resposta - a.iniciado_em).total_seconds()
        for mes in ref.MESES:
            for canal in ref.CANAIS:
                alvo, chave = ref.COMERCIAL[mes][canal.codigo], (mes, canal.codigo)
                with self.subTest(mes=mes, canal=canal.codigo):
                    self.assertEqual(oport[chave], alvo.orcamentos)
                    self.assertEqual(status[chave + ("CONVERTIDA",)], alvo.pedidos)
                    soma = sum(status[chave + (s,)] for s in ("CONVERTIDA", "PERDIDA", "PENDENTE"))
                    self.assertEqual(soma, alvo.orcamentos)
                    self.assertEqual(atend[chave], alvo.atendimentos)
                    self.assertAlmostEqual(segundos[chave] / atend[chave] / 60, alvo.resposta_min, places=6)

    def test_cancelados_e_devolvidos_existem_e_ficam_fora_dos_confirmados(self):
        status = Counter(p.status for p in self.base.pedidos)
        self.assertGreater(status["CANCELADO"], 0)
        self.assertGreater(status["DEVOLVIDO"], 0)
        self.assertTrue(all(p.oportunidade is None for p in self.base.pedidos if p.status != "CONFIRMADO"))

    def test_recompra_90d_das_coortes_calibradas_fica_proxima_do_prototipo(self):
        pedidos_cliente = defaultdict(list)
        for p in self.confirmados:
            pedidos_cliente[p.cliente.seq].append(p.data_venda)
        for indice, mes in enumerate(ref.MESES[:3]):
            exibido = ref.MESES[indice + 3]
            for canal in ref.CANAIS:
                coorte = [c for c in self.base.clientes
                          if c.canal == canal.codigo and c.primeira_compra and mes_de(c.primeira_compra) == mes]
                recompraram = sum(
                    1 for c in coorte
                    if sum(1 for d in pedidos_cliente[c.seq]
                           if c.primeira_compra <= d <= c.primeira_compra + timedelta(days=90)) >= 2)
                taxa = recompraram / len(coorte) * 100
                with self.subTest(coorte=mes, canal=canal.codigo):
                    # granularidade de um cliente na coorte
                    self.assertLessEqual(abs(taxa - ref.COMERCIAL[exibido][canal.codigo].recompra_90d),
                                         50 / len(coorte) + 1e-9)

    def test_estoque_bate_com_a_referencia(self):
        lotes = {lote[0]: lote for lote in self.base.lotes}
        insumos = {i[0]: i for i in self.base.insumos}
        for posicao, alvo in ref.ESTOQUE.items():
            saldos = [s for s in self.base.saldos if s[0] == posicao]
            categorias, faixas, risco, disponivel = Counter(), Counter(), Decimal(0), defaultdict(Decimal)
            for _, lote_id, _, fisico, reservado, bloqueado, valor, _ in saldos:
                lote = lotes[lote_id]
                insumo = insumos[lote[2]]
                dias = (lote[5] - posicao).days
                faixa = 0 if dias < 0 else 1 if dias <= 30 else 2 if dias <= 60 else 3 if dias <= 90 else 4
                faixas[faixa] += 1
                categorias[insumo[2]] += valor
                if faixa == 1:
                    risco += valor
                if faixa != 0:
                    disponivel[insumo[0]] += fisico - reservado - bloqueado
            abaixo = sum(1 for i in insumos.values() if disponivel[i[0]] < i[4])
            codigos = {lotes[s[1]][1]: s for s in saldos}
            with self.subTest(posicao=posicao):
                self.assertEqual(tuple(faixas[f] for f in range(5)), alvo.faixas)
                self.assertEqual(sum(categorias.values()), alvo.valor_total)
                self.assertEqual({k: int(v) for k, v in categorias.items()}, alvo.categorias)
                self.assertEqual(risco, alvo.valor_em_risco)
                self.assertEqual(abaixo, alvo.abaixo_minimo)
                for amostra in alvo.amostra:
                    self.assertEqual(codigos[amostra.lote_codigo][3], Decimal(str(amostra.saldo)))
                    self.assertEqual(lotes[codigos[amostra.lote_codigo][1]][5], amostra.validade)

    def test_seed_versionado_e_reproduzivel(self):
        sql = gerar_dados.renderizar_sql(gerar_dados.gerar())
        self.assertEqual(sql, gerar_dados.renderizar_sql(self.base))
        arquivo = gerar_dados.ARQUIVO_SEED.read_text(encoding="utf-8")
        self.assertEqual(hashlib.sha256(sql.encode()).hexdigest(), hashlib.sha256(arquivo.encode()).hexdigest(),
                         "rode python tools/gerar_dados.py e versione o 02_seed.sql")


if __name__ == "__main__":
    unittest.main()
