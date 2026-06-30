import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
from extract import ColectorParceiros, ColetorOperacoes, ColetorProdutos, ColetorFatos, ColetorCategoriaFinanceira, ColetorCaixaBancos
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
    logger.info("tb_cliente: %d registros extraidos", len(df))
    process_table("tb_cliente", df)


def run_tb_representante() -> None:
    df = _extrair_parceiros("4")
    logger.info("tb_representante: %d registros extraidos", len(df))
    process_table("tb_representante", df)


def run_tb_produto() -> None:
    df_gerencial = ColetorProdutos().process("gerencial")
    df_fiscal = ColetorProdutos().process("fiscal")
    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True).drop_duplicates(subset=["_idProd"])
    logger.info("tb_produto: %d registros extraidos", len(df))
    process_table("tb_produto", df)


def run_tb_operacao() -> None:
    df_operacao_gerencial = ColetorOperacoes().process("gerencial")
    logger.info("tb_operacao: %d registros extraidos", len(df_operacao_gerencial))
    df_operacao_fiscal = ColetorOperacoes().process("fiscal")
    logger.info("tb_operacao: %d registros extraidos", len(df_operacao_fiscal))

    df = pd.concat([df_operacao_gerencial, df_operacao_fiscal], ignore_index=True).drop_duplicates(subset=["_idOperacao"])
    process_table("tb_operacao", df)

def run_tb_categoria_financeira() -> None:
    df_categoria_gerencial = ColetorCategoriaFinanceira().process("gerencial")
    logger.info("tb_categoriaFinanceira: %d registros extraidos", len(ColetorCategoriaFinanceira))
    df_categoria_fiscal = ColetorCategoriaFinanceira().process("fiscal")
    logger.info("tb_categoriaFinanceira: %d registros extraidos", len(df_categoria_fiscal))

    df = pd.concat([df_categoria_gerencial, df_categoria_fiscal], ignore_index=True).drop_duplicates(subset=["_idCatFin"])
    process_table("tb_categoriaFinanceira", df)


def run_tb_caixaBanco() -> None:
    start_date = "2024-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")

    df_gerencial = ColetorCaixaBancos(start_date=start_date, end_date=end_date).process("gerencial")
    logger.info("tb_caixaBanco gerencial: %d registros extraidos", len(df_gerencial))
    df_fiscal = ColetorCaixaBancos(start_date=start_date, end_date=end_date).process("fiscal")
    logger.info("tb_caixaBanco fiscal: %d registros extraidos", len(df_fiscal))

    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True)
    if df.empty:
        logger.warning("tb_caixaBanco: nenhum registro encontrado")
        return
    process_table("tb_caixaBanco", df)


def run_tb_fatos() -> None:
    df_gerencial = ColetorFatos(dataInicial="2026-01-01", dataFinal="2026-01-31").process("gerencial")
    logger.info("tb_fatos gerencial: %d registros extraidos", len(df_gerencial))
    df_fiscal = ColetorFatos(dataInicial="2026-01-01", dataFinal="2026-01-31").process("fiscal")
    logger.info("tb_fatos fiscal: %d registros extraidos", len(df_fiscal))

    df = pd.concat([df_gerencial, df_fiscal], ignore_index=True)

    process_table("tb_fatos", df)
TASKS = [
    ("tb_cliente", run_tb_cliente),
    ("tb_representante", run_tb_representante),
    ("tb_produto", run_tb_produto),
    ("tb_operacao", run_tb_operacao),
    ("tb_fatos", run_tb_fatos),
    ("tb_categoriaFinanceira", run_tb_categoria_financeira),
    ("tb_caixaBanco", run_tb_caixaBanco),
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
