# %%
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.api_conect import SimDataAPI
from transform import TransformParceiros, TransformOperacoes, TransformProdutos, TransformFatos, TransformCategoriaFinanceira, TransformCaixaBancos

# %%
class ColectorParceiros(SimDataAPI):

    def __init__(self, tipo: str = "1"):
        super().__init__()
        self.tipo = int(tipo)
        self._endpoint = f"parceiros/listar?tipo={tipo}"

    def process_type(self, type_process: str) -> pd.DataFrame:
        data = self.get(self._endpoint, type_process).get("data", [])
        df = pd.DataFrame(data)
        transform = TransformParceiros(type=type_process, tipo=self.tipo)
        return transform.add_id_empresa(transform.transform(df))
# %%
class ColetorOperacoes(SimDataAPI):

    def __init__(self):
        super().__init__()
        self._endpoint = "operacoes/listar"

    def process(self, type_process: str) -> pd.DataFrame:
        data = self.get(self._endpoint, type_process).get("data", [])
        df = pd.DataFrame(data)
        transform = TransformOperacoes(type=type_process)
        return transform.add_id_empresa(transform.transform(df))

# %%
class ColetorProdutos(SimDataAPI):

    def __init__(self):
        super().__init__()
        self._endpoint = "produtos/listar"

    def process(self, type_process: str) -> pd.DataFrame:
        data = self.get(self._endpoint, type_process).get("data", [])
        df = pd.DataFrame(data)
        transform = TransformProdutos(type=type_process)
        return transform.add_id_empresa(transform.transform(df))
# %%
class ColetorFatos(SimDataAPI):

    def __init__(self, dataInicial: str, dataFinal: str):
        super().__init__()
        self.dataInicial = dataInicial
        self.dataFinal = dataFinal
        self._endpoint = f"vendas/listar?tipodata=cadastro&dataInicial={self.dataInicial}&dataFinal={self.dataFinal}"

    def process(self, type_process: str) -> pd.DataFrame:
        data = self.get(self._endpoint, type_process).get("data", [])
        df = pd.DataFrame(data)
        transform = TransformFatos(type=type_process)
        return transform.add_id_empresa(transform.transform(df))
    
class ColetorCategoriaFinanceira(SimDataAPI):

    def __init__(self):
        super().__init__()
        self._endpoint = "categoriafinanceira/listar"

    def process(self, type_process: str) -> pd.DataFrame:
        data = self.get(self._endpoint, type_process).get("data", [])
        df = pd.DataFrame(data)
        import logging; logging.getLogger(__name__).info("categoriaFinanceira colunas [%s]: %s", type_process, df.columns.tolist())
        transform = TransformCategoriaFinanceira(type=type_process)
        return transform.add_id_empresa(transform.transform(df))

# %%
class ColetorCaixaBancos(SimDataAPI):
    _BANCOS = {
        "gerencial": ["1","11","8","10"],
        "fiscal":    ["1","6","5","4","9","10","12","14","15","17","21","22","24","26","27","28"],
    }

    def __init__(self, start_date: str, end_date: str):
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date

    def process(self, type_process: str) -> pd.DataFrame:
        bancos = self._BANCOS[type_process]
        months = pd.date_range(
            start=pd.Timestamp(self.start_date).replace(day=1),
            end=pd.Timestamp(self.end_date),
            freq="MS",
        )

        frames = []
        for month in months:
            start = month.strftime("%Y-%m-01")
            end = (month + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
            for banco in bancos:
                endpoint = (
                    f"lancamentocaixa/listar?tipodata=movimento"
                    f"&datainicial={start}&datafinal={end}&codbanco={banco}"
                )
                response = self.get(endpoint, type_process)
                data = response.get("data", [])
                if not data or not isinstance(data, list):
                    if data and not isinstance(data, list):
                        import logging; logging.getLogger(__name__).warning(
                            "Resposta inesperada [%s banco=%s mes=%s]: type=%s valor=%r",
                            type_process, banco, start, type(data).__name__, str(data)[:200],
                        )
                    continue
                df_mes = pd.DataFrame(data)
                df_mes["codBanco"] = banco
                frames.append(df_mes)

        if not frames:
            return pd.DataFrame()

        df = pd.concat(frames, ignore_index=True)
        df.to_excel(f"caixa_bancos{type_process.capitalize()}.xlsx", index=False)
        transform = TransformCaixaBancos(type=type_process)
        return transform.add_id_empresa(transform.transform(df))