#!/bin/sh
# Cria o usuario somente leitura usado pelo Power BI.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v senha="$FARMABI_LEITURA_SENHA" <<'EOSQL'
CREATE ROLE farmabi_leitura LOGIN PASSWORD :'senha';
GRANT CONNECT ON DATABASE farmabi TO farmabi_leitura;
GRANT USAGE ON SCHEMA public TO farmabi_leitura;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO farmabi_leitura;
EOSQL
