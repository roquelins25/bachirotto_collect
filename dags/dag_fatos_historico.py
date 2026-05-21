import sys
import time
from pathlib import Path
from datetime import datetime, timedelta, date
import calendar

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from airflow import DAG
from airflow.operators.python import PythonOperator

import pandas as pd
from extract import ColetorFatos
from load import process_table

_HISTORICO_INICIO = date(2024, 1, 1)
_RATE_LIMIT_SLEEP = 15  # segundos entre meses para não bater no rate limit da API

_DEFAULT_ARGS = {
    "owner": "baschirotto",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}


def _run_fatos_mes(data_inicial: str, data_final: str) -> None:
    df_gerencial = ColetorFatos(dataInicial=data_inicial, dataFinal=data_final).process("gerencial")
    df_fiscal = ColetorFatos(dataInicial=data_inicial, dataFinal=data_final).process("fiscal")
    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True)
    process_table("tb_fatos", df)
    time.sleep(_RATE_LIMIT_SLEEP)


def _gerar_meses(inicio: date, fim: date):
    """Gera tuplas (data_inicial, data_final) mês a mês entre inicio e fim."""
    cursor = inicio.replace(day=1)
    while cursor <= fim:
        ultimo_dia = calendar.monthrange(cursor.year, cursor.month)[1]
        data_final = min(date(cursor.year, cursor.month, ultimo_dia), fim)
        yield cursor.strftime("%Y-%m-%d"), data_final.strftime("%Y-%m-%d"), cursor.strftime("%Y_%m")
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


with DAG(
    dag_id="baschirotto_fatos_historico",
    default_args=_DEFAULT_ARGS,
    description="Backfill histórico de tb_fatos mês a mês desde 2024-01 — trigger manual",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["baschirotto", "fatos", "historico"],
) as dag:

    tasks = []
    hoje = date.today()

    for data_ini, data_fim, label in _gerar_meses(_HISTORICO_INICIO, hoje):
        t = PythonOperator(
            task_id=f"fatos_{label}",
            python_callable=_run_fatos_mes,
            op_kwargs={"data_inicial": data_ini, "data_final": data_fim},
        )
        if tasks:
            tasks[-1] >> t
        tasks.append(t)
