import csv
import logging
import os
import sys
from io import StringIO

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.conectDB import connect_db

logger = logging.getLogger(__name__)

_SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "sql")

_COLUMN_RENAME = {
    "tb_cliente": {"_idEmp": "idemp", "_idCliente": "idcliente"},
    "tb_representante": {"_idEmp": "idemp", "_idRep": "idrep"},
    "tb_operacao": {"_idEmp": "idemp", "_idOperacao": "idop"},
}


def create_table_if_not_exists(conn, table: str) -> None:
    sql_path = os.path.join(_SQL_DIR, f"{table}.sql")
    if not os.path.exists(sql_path):
        logger.warning("SQL não encontrado para %s — tabela não será criada", table)
        return
    with open(sql_path, encoding="utf-8") as f:
        ddl = f.read()
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _truncate(conn, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table}")
    conn.commit()
    logger.info("%s truncada", table)


def _load(conn, df: pd.DataFrame, table: str) -> None:
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, quoting=csv.QUOTE_MINIMAL)
    buffer.seek(0)

    cols = ", ".join(df.columns.tolist())
    sql = f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT CSV, NULL '')"

    with conn.cursor() as cur:
        cur.copy_expert(sql, buffer)
    conn.commit()
    logger.info("%s: %d registros carregados", table, len(df))


def process_table(table: str, df: pd.DataFrame) -> None:
    rename_map = _COLUMN_RENAME.get(table, {})
    if rename_map:
        df = df.rename(columns=rename_map)

    conn = connect_db()
    try:
        create_table_if_not_exists(conn, table)
        _truncate(conn, table)
        _load(conn, df, table)
    except Exception:
        conn.rollback()
        logger.exception("Falha ao processar %s", table)
        raise
    finally:
        conn.close()
