#!/bin/bash
# Crea el rol de aplicación con permisos mínimos (solo DML).
# Se ejecuta una vez, al inicializar el volumen de PostgreSQL.
set -euo pipefail

: "${POSTGRES_APP_USER:?POSTGRES_APP_USER no definido}"
: "${POSTGRES_APP_PASSWORD:?POSTGRES_APP_PASSWORD no definido}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE ${POSTGRES_APP_USER} LOGIN PASSWORD '${POSTGRES_APP_PASSWORD}';

    REVOKE CREATE ON SCHEMA public FROM PUBLIC;

    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_APP_USER};
    GRANT USAGE ON SCHEMA public TO ${POSTGRES_APP_USER};

    -- Las tablas futuras las crea el rol migrador, que es el propietario.
    ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${POSTGRES_APP_USER};
    ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO ${POSTGRES_APP_USER};
EOSQL
