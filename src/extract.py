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
Prod = ColetorProdutos()
df_prod = Prod.process(type_process="gerencial")
# %%
df_prod.head()

# %%
