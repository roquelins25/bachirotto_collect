# %%
import requests
import os
import pandas as pd
from dotenv import load_dotenv
from transform import TransformParceiros

load_dotenv()

gerencial_token = os.getenv("GERENCIAL")
fiscal_token = os.getenv("FISCAL")

# %%
class ColectorParceiros:

    def __init__(self, type=None, tipo='1'):

        self.type = type.lower() if type else None
        self.tipo = int(tipo)

        self.gerencial_token = gerencial_token
        self.fiscal_token = fiscal_token

        self.url = "https://api.simdata.com.br"

        self.endpoint = (
            f"parceiros/listar?tipo={tipo}"
        )

    def get_extract(self, type_process):

        if type_process == 'gerencial':

            token = self.gerencial_token

        elif type_process == 'fiscal':

            token = self.fiscal_token

        else:
            raise ValueError(
                f"Tipo inválido: {type_process}"
            )

        headers = {
            "apitoken": token
        }

        response = requests.get(
            f"{self.url}/{self.endpoint}",
            headers=headers
        )

        response.raise_for_status()

        return response.json()

    def process_type(self, type_process):

        data_json = self.get_extract(type_process)

        data = data_json.get("data", [])

        df = pd.DataFrame(data)

        transform = TransformParceiros(
            type=type_process,
            tipo=self.tipo
        )

        df_tratado = transform.transform(df)

        df_final = transform.add_id_empresa(
            df_tratado
        )

        return df_final

    def loadProcess(self, filename='extract.parquet'):

        if self.type in ['gerencial', 'fiscal']:

            df_final = self.process_type(self.type)

        elif self.type is None:

            df_gerencial = self.process_type(
                'gerencial'
            )

            df_fiscal = self.process_type(
                'fiscal'
            )

            # junta os dois
            df_final = pd.concat(
                [df_gerencial, df_fiscal],
                ignore_index=True
            )

        else:
            raise ValueError(
                f"Tipo inválido: {self.type}"
            )

        # salva parquet
        df_final.to_parquet(
            filename,
            index=False
        )

        print("Arquivo salvo com sucesso")

# %%
colect = ColectorParceiros(
    type=None,
    tipo='1'
)

colect.loadProcess()
# %%
