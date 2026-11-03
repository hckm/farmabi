-- FarmaBI: esquema estrela. Dados 100% ficticios, carregados por 02_seed.sql.

-- ---------------------------------------------------------------- dimensoes
CREATE TABLE dim_calendario (
    data             date PRIMARY KEY,
    ano              smallint NOT NULL,
    mes              smallint NOT NULL,
    dia              smallint NOT NULL,
    inicio_mes       date     NOT NULL,
    fim_mes          date     NOT NULL,
    mes_ano          text     NOT NULL,   -- 'Out/2026'
    mes_ano_ordem    integer  NOT NULL,   -- 202610
    periodo_analise  boolean  NOT NULL DEFAULT false
);

INSERT INTO dim_calendario (data, ano, mes, dia, inicio_mes, fim_mes, mes_ano, mes_ano_ordem)
SELECT d::date,
       extract(year FROM d)::smallint,
       extract(month FROM d)::smallint,
       extract(day FROM d)::smallint,
       date_trunc('month', d)::date,
       (date_trunc('month', d) + interval '1 month - 1 day')::date,
       (ARRAY['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'])[extract(month FROM d)]
           || '/' || extract(year FROM d),
       (extract(year FROM d) * 100 + extract(month FROM d))::integer
FROM generate_series(DATE '2024-01-01', DATE '2026-12-31', interval '1 day') AS d;

CREATE TABLE dim_canal (
    canal_id  smallint PRIMARY KEY,
    codigo    text     NOT NULL UNIQUE,
    nome      text     NOT NULL,
    ordem     smallint NOT NULL,
    cor       text     NOT NULL
);

CREATE TABLE dim_atendente (
    atendente_id  smallint PRIMARY KEY,
    nome          text     NOT NULL,
    canal_id      smallint NOT NULL REFERENCES dim_canal
);

CREATE TABLE dim_cliente (
    cliente_id            integer  PRIMARY KEY,
    codigo                text     NOT NULL UNIQUE,
    canal_id              smallint NOT NULL REFERENCES dim_canal,   -- canal principal (um por cliente)
    data_cadastro         date     NOT NULL,
    data_primeira_compra  date     NOT NULL
);

CREATE TABLE dim_insumo (
    insumo_id       smallint      PRIMARY KEY,
    descricao       text          NOT NULL UNIQUE,
    categoria       text          NOT NULL CHECK (categoria IN ('Ativos','Bases','Excipientes','Embalagens')),
    unidade_medida  text          NOT NULL,
    estoque_minimo  numeric(12,3) NOT NULL
);

CREATE TABLE dim_lote (
    lote_id           integer  PRIMARY KEY,
    lote_codigo       text     NOT NULL UNIQUE,
    insumo_id         smallint NOT NULL REFERENCES dim_insumo,
    fornecedor        text     NOT NULL,
    data_recebimento  date     NOT NULL,
    data_validade     date     NOT NULL
);

-- -------------------------------------------------------------------- fatos
CREATE TABLE fato_atendimento (
    atendimento_id               integer   PRIMARY KEY,
    cliente_id                   integer   NOT NULL REFERENCES dim_cliente,
    canal_id                     smallint  NOT NULL REFERENCES dim_canal,
    atendente_id                 smallint  NOT NULL REFERENCES dim_atendente,
    iniciado_em                  timestamp NOT NULL,
    primeira_resposta_humana_em  timestamp,
    encerrado_em                 timestamp,
    status                       text      NOT NULL,
    transferencias               smallint  NOT NULL DEFAULT 0,
    avaliacao                    smallint  CHECK (avaliacao BETWEEN 1 AND 5),
    data_inicio                  date      GENERATED ALWAYS AS (iniciado_em::date) STORED,
    segundos_primeira_resposta   integer   GENERATED ALWAYS AS
        (extract(epoch FROM primeira_resposta_humana_em - iniciado_em)::integer) STORED
);

CREATE TABLE fato_pedido (
    pedido_id        integer       PRIMARY KEY,
    cliente_id       integer       NOT NULL REFERENCES dim_cliente,
    canal_id         smallint      NOT NULL REFERENCES dim_canal,
    atendente_id     smallint      NOT NULL REFERENCES dim_atendente,
    oportunidade_id  integer,
    data_venda       date          NOT NULL,
    status           text          NOT NULL CHECK (status IN ('CONFIRMADO','CANCELADO','DEVOLVIDO')),
    valor_bruto      numeric(12,2) NOT NULL,
    desconto         numeric(12,2) NOT NULL,
    valor_liquido    numeric(12,2) NOT NULL,
    valor_devolvido  numeric(12,2) NOT NULL DEFAULT 0
);

CREATE TABLE fato_oportunidade (
    oportunidade_id   integer   PRIMARY KEY,
    atendimento_id    integer   NOT NULL REFERENCES fato_atendimento,
    cliente_id        integer   NOT NULL REFERENCES dim_cliente,
    canal_id          smallint  NOT NULL REFERENCES dim_canal,
    atendente_id      smallint  NOT NULL REFERENCES dim_atendente,
    criada_em         timestamp NOT NULL,
    data_envio        timestamp NOT NULL,
    data_aprovacao    timestamp,
    data_encerramento timestamp,
    status            text      NOT NULL CHECK (status IN ('PENDENTE','CONVERTIDA','PERDIDA')),
    motivo_perda      text,
    pedido_id         integer   REFERENCES fato_pedido,
    data_criacao      date      GENERATED ALWAYS AS (criada_em::date) STORED
);

ALTER TABLE fato_pedido
    ADD CONSTRAINT fk_pedido_oportunidade FOREIGN KEY (oportunidade_id) REFERENCES fato_oportunidade
    DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE fato_orcamento_versao (
    orcamento_versao_id  integer       PRIMARY KEY,
    oportunidade_id      integer       NOT NULL REFERENCES fato_oportunidade,
    versao               smallint      NOT NULL,
    criada_em            timestamp     NOT NULL,
    valor                numeric(12,2) NOT NULL,
    vigente              boolean       NOT NULL,
    UNIQUE (oportunidade_id, versao)
);

CREATE TABLE fato_pedido_item (
    pedido_item_id      integer       PRIMARY KEY,
    pedido_id           integer       NOT NULL REFERENCES fato_pedido,
    formula_codigo      text          NOT NULL,
    categoria_formula   text          NOT NULL,
    forma_farmaceutica  text          NOT NULL,
    quantidade          smallint      NOT NULL,
    valor_liquido       numeric(12,2) NOT NULL
);

CREATE TABLE fato_saldo_estoque (
    data_posicao     date          NOT NULL,
    lote_id          integer       NOT NULL REFERENCES dim_lote,
    deposito         text          NOT NULL,
    saldo_fisico     numeric(12,3) NOT NULL,
    saldo_reservado  numeric(12,3) NOT NULL,
    saldo_bloqueado  numeric(12,3) NOT NULL,
    valor_total      numeric(12,2) NOT NULL,   -- saldo valorizado pelo custo do lote
    custo_unitario   numeric(14,4) NOT NULL,
    PRIMARY KEY (data_posicao, lote_id)
);

CREATE INDEX ix_pedido_cliente_data ON fato_pedido (cliente_id, data_venda);

-- ---------------------------------------------------- tabelas auxiliares
CREATE TABLE aux_etapa_funil (
    etapa_id  smallint PRIMARY KEY,
    etapa     text     NOT NULL,
    cor       text     NOT NULL
);
INSERT INTO aux_etapa_funil VALUES
    (1, 'Orçamentos gerados', '#0e9e82'),
    (2, 'Convertidos',        '#4489bc'),
    (3, 'Perdidos',           '#bf7b70'),
    (4, 'Em negociação',      '#8575bf');

CREATE TABLE aux_faixa_frequencia (
    faixa_id       smallint PRIMARY KEY,
    faixa          text     NOT NULL,
    compras_min    smallint NOT NULL,
    compras_max    smallint NOT NULL
);
INSERT INTO aux_faixa_frequencia VALUES
    (1, '1 compra',   1, 1),
    (2, '2 compras',  2, 2),
    (3, '3+ compras', 3, 32767);

-- -------------------------------------------------------------------- views
-- Validade sempre comparada com a data da posicao, nunca com a data atual.
CREATE VIEW vw_saldo_estoque AS
SELECT s.data_posicao,
       s.lote_id,
       l.lote_codigo,
       l.insumo_id,
       s.deposito,
       l.data_validade,
       (l.data_validade - s.data_posicao)                       AS dias_para_vencer,
       CASE
           WHEN l.data_validade < s.data_posicao             THEN 'Vencidos'
           WHEN l.data_validade - s.data_posicao <= 30       THEN '0–30 dias'
           WHEN l.data_validade - s.data_posicao <= 60       THEN '31–60 dias'
           WHEN l.data_validade - s.data_posicao <= 90       THEN '61–90 dias'
           ELSE 'Mais de 90 dias'
       END                                                      AS faixa_validade,
       CASE
           WHEN l.data_validade < s.data_posicao             THEN 1
           WHEN l.data_validade - s.data_posicao <= 30       THEN 2
           WHEN l.data_validade - s.data_posicao <= 60       THEN 3
           WHEN l.data_validade - s.data_posicao <= 90       THEN 4
           ELSE 5
       END                                                      AS faixa_validade_ordem,
       (l.data_validade < s.data_posicao)                       AS vencido,
       s.saldo_fisico,
       s.saldo_reservado,
       s.saldo_bloqueado,
       CASE WHEN l.data_validade < s.data_posicao THEN 0
            ELSE s.saldo_fisico - s.saldo_reservado - s.saldo_bloqueado
       END                                                      AS saldo_disponivel,
       s.valor_total,
       s.custo_unitario
FROM fato_saldo_estoque s
JOIN dim_lote l ON l.lote_id = s.lote_id;

CREATE VIEW vw_insumo_posicao AS
SELECT v.data_posicao,
       v.insumo_id,
       sum(v.saldo_disponivel)                    AS saldo_disponivel,
       i.estoque_minimo,
       (sum(v.saldo_disponivel) < i.estoque_minimo) AS abaixo_minimo
FROM vw_saldo_estoque v
JOIN dim_insumo i ON i.insumo_id = v.insumo_id
GROUP BY v.data_posicao, v.insumo_id, i.estoque_minimo;

-- Coorte = clientes cuja primeira compra valida caiu dentro da janela de dados.
-- Recomprou = teve outro pedido confirmado ate 90 dias depois da primeira compra.
CREATE VIEW vw_coorte_recompra AS
SELECT c.cliente_id,
       c.canal_id,
       c.data_primeira_compra,
       date_trunc('month', c.data_primeira_compra)::date AS mes_coorte,
       ((SELECT count(*)
           FROM fato_pedido p
          WHERE p.cliente_id = c.cliente_id
            AND p.status = 'CONFIRMADO'
            AND p.data_venda BETWEEN c.data_primeira_compra AND c.data_primeira_compra + 90) >= 2)::int
                                                         AS recomprou_90d
FROM dim_cliente c
WHERE c.data_primeira_compra >= (SELECT min(data_venda) FROM fato_pedido);
