import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from airflow import DAG
from airflow.operators.python import PythonOperator

import pandas as pd
from extract import ColectorParceiros, ColetorOperacoes, ColetorProdutos, ColetorCategoriaFinanceira
from load import process_table

_DEFAULT_ARGS = {
    "owner": "baschirotto",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}


def _run_tb_cliente() -> None:
    df_g1 = ColectorParceiros(tipo="1").process_type("gerencial")
    df_g5 = ColectorParceiros(tipo="5").process_type("gerencial")
    df_gerencial = pd.concat([df_g1, df_g5], ignore_index=True).drop_duplicates(subset=["_idCliente"])
    df_fiscal = ColectorParceiros(tipo="1").process_type("fiscal")
    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True)
    process_table("tb_cliente", df)


def _run_tb_representante() -> None:
    collector = ColectorParceiros(tipo="4")
    df_g = collector.process_type("gerencial")
    df_f = collector.process_type("fiscal")
    df = pd.concat([df_g, df_f], ignore_index=True)
    process_table("tb_representante", df)


def _run_tb_produto() -> None:
    df_gerencial = ColetorProdutos().process("gerencial")
    df_fiscal = ColetorProdutos().process("fiscal")
    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True).drop_duplicates(subset=["_idProd"])
    process_table("tb_produto", df)


def _run_tb_operacao() -> None:
    df_gerencial = ColetorOperacoes().process("gerencial")
    df_fiscal = ColetorOperacoes().process("fiscal")
    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True).drop_duplicates(subset=["_idOperacao"])
    process_table("tb_operacao", df)

def _run_tb_categoria_financeira() -> None:
    df_categoria_gerencial = ColetorCategoriaFinanceira().process("gerencial")
    df_categoria_fiscal = ColetorCategoriaFinanceira().process("fiscal")

    df = pd.concat([df_categoria_gerencial, df_categoria_fiscal], ignore_index=True).drop_duplicates(subset=["_idCatFin"])
    process_table("tb_categoriaFinanceira", df)


with DAG(
    dag_id="baschirotto_dimensoes",
    default_args=_DEFAULT_ARGS,
    description="Carga das tabelas dimensão Baschirotto a cada 4 horas",
    schedule="0 */4 * * *",
    start_date=datetime(2026, 5, 21),
    catchup=False,
    tags=["baschirotto", "dimensoes"],
) as dag:

    op_cliente = PythonOperator(task_id="tb_cliente", python_callable=_run_tb_cliente)
    op_representante = PythonOperator(task_id="tb_representante", python_callable=_run_tb_representante)
    op_produto = PythonOperator(task_id="tb_produto", python_callable=_run_tb_produto)
    op_operacao = PythonOperator(task_id="tb_operacao", python_callable=_run_tb_operacao)
    op_catfinanceiro = PythonOperator(task_id="tb_categoriaFinanceira", python_callable=_run_tb_categoria_financeira)

    # paralelo — sem dependência entre dimensões
    [op_cliente, op_representante, op_produto, op_operacao, op_catfinanceiro]
