# FarmaBI

BI para farmácia de manipulação: **Power BI Desktop** lendo um **PostgreSQL** em Docker, com cinco visões
(Executivo e Vendas, Orçamentos e Conversão, Clientes e Recompra, Estoque e Validade, Canais e Atendimento).

> Todos os dados são **fictícios**, gerados de forma determinística para reproduzir o protótipo
> ([docs/prototipo](docs/prototipo/FarmaBI_Prototipo_Interativo.html)). Documentação completa em
> [docs/documentacao.md](docs/documentacao.md).

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `docker-compose.yml`, `.env.example` | Banco `farmabi-db` (PostgreSQL 16) em `127.0.0.1:${FARMABI_PORTA:-5433}` |
| `db/init/` | Roles, esquema estrela + views e carga `02_seed.sql` (gerada, versionada) |
| `tools/` | Gerador de dados, números de referência, conferência do banco e testes |
| `tools/powerbi/` | Geradores do projeto Power BI (TMDL + PBIR) |
| `powerbi/FarmaBI.pbip` | Projeto Power BI (modelo semântico + relatório) |
| `docs/` | Documentação, Entrega 1, protótipo HTML e evidências (PDF das páginas) |

## Roteiro 1 — Rodar só o banco (Windows, macOS ou Linux)

Pré-requisitos: Docker Desktop e Python 3.12+ (só para a conferência).

1. Copie o `.env.example` para `.env` e troque as duas senhas. Se a porta 5433 estiver ocupada, mude
   `FARMABI_PORTA`.
2. Suba o banco (a primeira subida cria o esquema e carrega os dados, ~10 s):

   ```bash
   docker compose up -d
   ```

3. Confira os números contra a referência do protótipo:

   ```bash
   python tools/conferir_banco.py
   ```

   Esperado: `OK: 18 combinacoes mes x canal e 3 posicoes de estoque`.

Para recriar do zero (apaga o volume): `docker compose down -v` e `docker compose up -d`.

## Roteiro 2 — Abrir o relatório (Windows)

Pré-requisitos: o banco do roteiro 1 rodando e o **Power BI Desktop** (Microsoft Store).

1. Abra `powerbi/FarmaBI.pbip`.
2. Se a porta não for 5433: **Página Inicial → Transformar dados → Editar parâmetros** e ajuste `Servidor`
   (ex.: `localhost:5440`).
3. Clique em **Atualizar**. Na credencial, escolha **Banco de dados**, usuário `farmabi_leitura` e a senha
   `FARMABI_LEITURA_SENHA` do seu `.env`. Aceite a conexão sem criptografia (o banco só escuta em `127.0.0.1`).
4. Confira em Out/2026, todos os canais: **R$ 185.400**, **1.248** pedidos, ticket **R$ 148,56**.

A credencial fica no cache local do Power BI (`.pbi/localSettings.json`, fora do git); nada sensível vai para o
repositório.

## Desenvolvimento

```bash
python -I -m unittest discover tools/tests
```

```bash
python tools/gerar_dados.py
```

```bash
python tools/powerbi/gerar_modelo.py
```

```bash
python tools/powerbi/gerar_relatorio.py
```

`gerar_dados.py` regrava `db/init/02_seed.sql` (idêntico byte a byte se nada mudou). Os geradores do Power BI
reescrevem `powerbi/`; feche o Desktop antes, ou ele sobrescreve os arquivos ao salvar.
