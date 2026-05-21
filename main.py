import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
from extract import ColectorParceiros
from load import process_table

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _extrair_parceiros(tipo: str) -> pd.DataFrame:
    collector = ColectorParceiros(tipo=tipo)
    df_g = collector.process_type("gerencial")
    df_f = collector.process_type("fiscal")
    return pd.concat([df_g, df_f], ignore_index=True)


def run_tb_cliente() -> None:
    df_g1 = ColectorParceiros(tipo="1").process_type("gerencial")
    df_g5 = ColectorParceiros(tipo="5").process_type("gerencial")
    df_gerencial = pd.concat([df_g1, df_g5], ignore_index=True).drop_duplicates(subset=["_idCliente"])

    df_fiscal = ColectorParceiros(tipo="1").process_type("fiscal")

    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True)
    logger.info("tb_cliente: %d registros extraídos", len(df))
    process_table("tb_cliente", df)


def run_tb_representante() -> None:
    df = _extrair_parceiros("4")
    logger.info("tb_representante: %d registros extraídos", len(df))
    process_table("tb_representante", df)


def run_tb_produto() -> None:
    logger.info("tb_produto: não implementado — pulando")


def run_tb_operacao() -> None:
    logger.info("tb_operacao: não implementado — pulando")


TASKS = [
    ("tb_cliente", run_tb_cliente),
    ("tb_representante", run_tb_representante),
    ("tb_produto", run_tb_produto),
    ("tb_operacao", run_tb_operacao),
]


def main() -> None:
    inicio = datetime.now()
    logger.info("Processo iniciado")
    erros = []

    for nome, func in TASKS:
        try:
            func()
        except Exception:
            logger.exception("Falha em %s", nome)
            erros.append(nome)

    duracao = (datetime.now() - inicio).total_seconds()
    logger.info("Processo finalizado em %.1fs", duracao)

    if erros:
        logger.error("Tasks com erro: %s", erros)
        sys.exit(1)


if __name__ == "__main__":
    main()
