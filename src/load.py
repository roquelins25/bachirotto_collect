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
    "tb_produto": {"_idEmp": "idemp", "_idProd": "idprod", "categoria_codigo": "codcat", "categoria_descricao": "catdesc"},
    "tb_fatos": {
        "_idEmp": "idemp",
        "_idcodcli": "idcodcli",
        "_idcodrep": "idcodrep",
        "_idcodop": "idcodop",
        "_idcodpro": "idcodpro",
    },
}

_TABLE_PK = {
    "tb_cliente": "idcliente",
    "tb_representante": "idrep",
    "tb_operacao": "idop",
    "tb_produto": "idprod",
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


def _copy_to_buffer(df: pd.DataFrame) -> StringIO:
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, quoting=csv.QUOTE_MINIMAL)
    buffer.seek(0)
    return buffer


def _upsert_dimensao(conn, df: pd.DataFrame, table: str, pk_col: str) -> None:
    cols = df.columns.tolist()
    cols_str = ", ".join(cols)
    tmp = f"tmp_{table}"

    update_cols = [c for c in cols if c != pk_col]
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)

    copy_sql = f"COPY {tmp} ({cols_str}) FROM STDIN WITH (FORMAT CSV, NULL '')"
    upsert_sql = f"""
        INSERT INTO {table} ({cols_str})
        SELECT {cols_str} FROM {tmp}
        ON CONFLICT ({pk_col}) DO UPDATE SET {update_set}
    """

    with conn.cursor() as cur:
        cur.execute(f"CREATE TEMP TABLE {tmp} (LIKE {table} INCLUDING DEFAULTS) ON COMMIT DROP")
        cur.copy_expert(copy_sql, _copy_to_buffer(df))
        cur.execute(upsert_sql)

    conn.commit()
    logger.info("%s: %d registros upserted", table, len(df))


def _load_fatos(conn, df: pd.DataFrame, table: str) -> None:
    cols = df.columns.tolist()
    cols_str = ", ".join(cols)
    copy_sql = f"COPY {table} ({cols_str}) FROM STDIN WITH (FORMAT CSV, NULL '')"

    data_min = pd.to_datetime(df["data"]).min().date()
    data_max = pd.to_datetime(df["data"]).max().date()
    idemp_list = df["idemp"].unique().tolist()

    delete_sql = f"DELETE FROM {table} WHERE data BETWEEN %s AND %s AND idemp = ANY(%s)"

    with conn.cursor() as cur:
        cur.execute(delete_sql, (data_min, data_max, idemp_list))
        deleted = cur.rowcount
        cur.copy_expert(copy_sql, _copy_to_buffer(df))

    conn.commit()
    logger.info(
        "%s: %d registros deletados, %d inseridos (período %s → %s)",
        table, deleted, len(df), data_min, data_max,
    )


def process_table(table: str, df: pd.DataFrame) -> None:
    rename_map = _COLUMN_RENAME.get(table, {})
    if rename_map:
        df = df.rename(columns=rename_map)

    conn = connect_db()
    try:
        create_table_if_not_exists(conn, table)

        if table == "tb_fatos":
            _load_fatos(conn, df, table)
        else:
            pk_col = _TABLE_PK[table]
            _upsert_dimensao(conn, df, table, pk_col)

    except Exception:
        conn.rollback()
        logger.exception("Falha ao processar %s", table)
        raise
    finally:
        conn.close()

def process_select(sql_file: str) -> None:
    sql_path = os.path.join(_SQL_DIR, sql_file)
    if not os.path.exists(sql_path):
        logger.error("SQL não encontrado: %s", sql_file)
        return

    with open(sql_path, encoding="utf-8") as f:
        sql = f.read()

    conn = connect_db()
    try:
        df = pd.read_sql_query(sql, conn)
        table = sql_file.replace(".sql", "")
        process_table(table, df)
    except Exception:
        logger.exception("Falha ao processar %s", sql_file)
        raise
    finally:
        conn.close()