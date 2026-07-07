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


def _month_bounds(hoje: date, months_ago: int) -> tuple[str, str]:
    month = hoje.month - 1 - months_ago
    year = hoje.year + month // 12
    month = month % 12 + 1
    inicio = date(year, month, 1)
    if months_ago == 0:
        fim = hoje
    elif month == 12:
        fim = date(year, 12, 31)
    else:
        fim = date(year, month + 1, 1) - timedelta(days=1)
    return inicio.strftime("%Y-%m-%d"), fim.strftime("%Y-%m-%d")


def _run_caixaBanco_incremental() -> None:
    hoje = date.today()
    dfs = []
    for months_ago in (2, 1, 0):
        start_date, end_date = _month_bounds(hoje, months_ago)
        dfs.append(ColetorCaixaBancos(start_date=start_date, end_date=end_date).process("gerencial"))
        dfs.append(ColetorCaixaBancos(start_date=start_date, end_date=end_date).process("fiscal"))

    df = pd.concat(dfs, ignore_index=True)
    if not df.empty:
        process_table("tb_caixaBanco", df)


with DAG(
    dag_id="baschirotto_incremental",
    default_args=_DEFAULT_ARGS,
    description="Carga incremental de tb_fatos (últimos 90 dias) e tb_caixaBanco (últimos 3 meses fechados), a cada 2 horas",
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
        task_id="caixaBanco_ultimos_3_meses_fechados",
        python_callable=_run_caixaBanco_incremental,
    )

    op_fatos >> op_caixa
