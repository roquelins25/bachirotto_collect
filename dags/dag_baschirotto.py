import logging
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "src"))

from extract import ColectorParceiros  # noqa: E402
from load import process_table  # noqa: E402

logger = logging.getLogger(__name__)

_DEFAULT_ARGS = {
    "owner": "baschirotto",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}


def _extrair_parceiros(tipo: str) -> pd.DataFrame:
    collector = ColectorParceiros(tipo=tipo)
    df_g = collector.process_type("gerencial")
    df_f = collector.process_type("fiscal")
    return pd.concat([df_g, df_f], ignore_index=True)


def _run_tb_cliente() -> None:
    df_g1 = ColectorParceiros(tipo="1").process_type("gerencial")
    df_g5 = ColectorParceiros(tipo="5").process_type("gerencial")
    df_gerencial = pd.concat([df_g1, df_g5], ignore_index=True).drop_duplicates(subset=["_idCliente"])

    df_fiscal = ColectorParceiros(tipo="1").process_type("fiscal")

    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True)
    logger.info("tb_cliente: %d registros extraídos", len(df))
    process_table("tb_cliente", df)


def _run_tb_representante() -> None:
    df = _extrair_parceiros("4")
    logger.info("tb_representante: %d registros extraídos", len(df))
    process_table("tb_representante", df)


def _run_tb_produto() -> None:
    # TODO: implementar quando o endpoint estiver definido
    pass


def _run_tb_operacao() -> None:
    # TODO: implementar quando o endpoint estiver definido
    pass


with DAG(
    dag_id="baschirotto_collect",
    default_args=_DEFAULT_ARGS,
    description="Coleta e carga truncate+insert das tabelas Baschirotto no PostgreSQL",
    schedule_interval="0 6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["baschirotto", "etl"],
) as dag:

    op_cliente = PythonOperator(task_id="tb_cliente", python_callable=_run_tb_cliente)
    op_representante = PythonOperator(task_id="tb_representante", python_callable=_run_tb_representante)
    op_produto = PythonOperator(task_id="tb_produto", python_callable=_run_tb_produto)
    op_operacao = PythonOperator(task_id="tb_operacao", python_callable=_run_tb_operacao)

    op_cliente >> op_representante >> op_produto >> op_operacao
