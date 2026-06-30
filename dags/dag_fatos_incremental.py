import sys
from pathlib import Path
from datetime import datetime, timedelta, date

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from airflow import DAG
from airflow.operators.python import PythonOperator

import pandas as pd
from extract import ColetorFatos, ColetorCaixaBancos
from load import process_table

_JANELA_DIAS = 90

_DEFAULT_ARGS = {
    "owner": "baschirotto",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}


def _run_fatos_incremental() -> None:
    hoje = date.today()
    data_inicial = (hoje - timedelta(days=_JANELA_DIAS)).strftime("%Y-%m-%d")
    data_final = hoje.strftime("%Y-%m-%d")

    df_gerencial = ColetorFatos(dataInicial=data_inicial, dataFinal=data_final).process("gerencial")
    df_fiscal = ColetorFatos(dataInicial=data_inicial, dataFinal=data_final).process("fiscal")
    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True)
    process_table("tb_fatos", df)


def _run_caixaBanco_incremental() -> None:
    hoje = date.today()
    inicio = hoje - timedelta(days=_JANELA_DIAS)
    start_date = date(inicio.year, inicio.month, 1).strftime("%Y-%m-%d")
    end_date = hoje.strftime("%Y-%m-%d")

    df_gerencial = ColetorCaixaBancos(start_date=start_date, end_date=end_date).process("gerencial")
    df_fiscal = ColetorCaixaBancos(start_date=start_date, end_date=end_date).process("fiscal")
    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True)
    if not df.empty:
        process_table("tb_caixaBanco", df)


with DAG(
    dag_id="baschirotto_incremental",
    default_args=_DEFAULT_ARGS,
    description="Carga incremental de tb_fatos e tb_caixaBanco — últimos 90 dias, a cada 2 horas",
    schedule="0 */2 * * *",
    start_date=datetime(2026, 5, 21),
    catchup=False,
    tags=["baschirotto", "incremental"],
) as dag:

    op_fatos = PythonOperator(
        task_id="fatos_ultimos_90_dias",
        python_callable=_run_fatos_incremental,
    )

    op_caixa = PythonOperator(
        task_id="caixaBanco_ultimos_90_dias",
        python_callable=_run_caixaBanco_incremental,
    )

    op_fatos >> op_caixa
