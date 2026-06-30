import sys
import time
from pathlib import Path
from datetime import datetime, timedelta, date
import calendar

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator

import pandas as pd
from extract import ColetorFatos, ColetorCaixaBancos
from load import process_table

_HISTORICO_INICIO = date(2024, 1, 1)
_RATE_LIMIT_SLEEP = 15

_DEFAULT_ARGS = {
    "owner": "baschirotto",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}


def _run_fatos_mes(data_inicial: str, data_final: str, **context) -> None:
    if not context["params"]["executar_fatos"]:
        return
    df_gerencial = ColetorFatos(dataInicial=data_inicial, dataFinal=data_final).process("gerencial")
    df_fiscal = ColetorFatos(dataInicial=data_inicial, dataFinal=data_final).process("fiscal")
    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True)
    process_table("tb_fatos", df)
    time.sleep(_RATE_LIMIT_SLEEP)


def _run_caixaBanco_mes(data_inicial: str, data_final: str, **context) -> None:
    if not context["params"]["executar_caixaBanco"]:
        return
    df_gerencial = ColetorCaixaBancos(start_date=data_inicial, end_date=data_final).process("gerencial")
    df_fiscal = ColetorCaixaBancos(start_date=data_inicial, end_date=data_final).process("fiscal")
    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True)
    if not df.empty:
        process_table("tb_caixaBanco", df)
    time.sleep(_RATE_LIMIT_SLEEP)


def _gerar_meses(inicio: date, fim: date):
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
    dag_id="baschirotto_historico",
    default_args=_DEFAULT_ARGS,
    description="Backfill histórico mês a mês desde 2024-01 — trigger manual",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["baschirotto", "historico"],
    params={
        "executar_fatos":      Param(True, type="boolean", description="Executar carga de tb_fatos"),
        "executar_caixaBanco": Param(True, type="boolean", description="Executar carga de tb_caixaBanco"),
    },
) as dag:

    tasks = []
    hoje = date.today()

    for data_ini, data_fim, label in _gerar_meses(_HISTORICO_INICIO, hoje):
        t_fatos = PythonOperator(
            task_id=f"fatos_{label}",
            python_callable=_run_fatos_mes,
            op_kwargs={"data_inicial": data_ini, "data_final": data_fim},
        )
        t_caixa = PythonOperator(
            task_id=f"caixaBanco_{label}",
            python_callable=_run_caixaBanco_mes,
            op_kwargs={"data_inicial": data_ini, "data_final": data_fim},
        )
        t_fatos >> t_caixa

        if tasks:
            tasks[-1] >> t_fatos
        tasks.append(t_caixa)
