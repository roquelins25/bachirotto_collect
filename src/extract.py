# %%
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.api_conect import SimDataAPI
from transform import TransformParceiros, TransformOperacoes , TransformProdutos

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
        return df
# %%
fatos = ColetorFatos(dataInicial="2026-01-01", dataFinal="2026-01-31")
fatos = fatos.process(type_process="gerencial")

# %%
fatos.info()

# %%
fatos.head()
# %%
