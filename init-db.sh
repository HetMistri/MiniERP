#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE mini_erp OWNER odoo;
    CREATE DATABASE odoo OWNER odoo;
    ALTER USER odoo CREATEDB;
EOSQL
