#%%
import os
import json
import pandas as pd

class BaseTransform:
    MAPA_EMPRESA = {
        "gerencial": 10001,
        "fiscal": 10002
    }

    def get_id_empresa(self):

        if self.type not in self.MAPA_EMPRESA:
            raise ValueError(
                f"Tipo inválido: {self.type}"
            )

        return self.MAPA_EMPRESA[self.type]
    
class TransformParceiros(BaseTransform):
    def __init__(self, type: str, tipo: int):
        self.type = type.lower()
        self.tipo = tipo
    
    def transform(self, df):
        cols = [
            "codigo",
            "razao",
            "nome",
            "cnpjcpf",
            "ativo",
            "codvendedor",
            "cidade",
            "cep",
            "uf",
            "datacadastro"
        ]
        
        cols_existentes = [c for c in cols if c in df.columns]
        df = df[cols_existentes].copy()

        # API retorna a string "null" para campos sem valor
        df = df.replace("null", pd.NA)

        for col in ["codigo", "codvendedor"]:
            if col in df.columns:
                df[col] = df[col].astype("Int64")

        return df
    

    def add_id_empresa(self, df):
        df = df.copy()

        df["_idEmp"] = self.get_id_empresa()
        
        if self.tipo in (1, 5):
            df["_idCliente"] = df["_idEmp"].astype(str) + "_" + df["codigo"].astype(str)
        elif self.tipo == 4:
            df["_idRep"] = df["_idEmp"].astype(str) + "_" + df["codigo"].astype(str)
        
        return df


class TransformOperacoes(BaseTransform):
    def __init__(self, type: str):      
        self.type = type.lower()
    
    def transform(self, df):

        cols = [
            "codigo",
            "descricao"
        ]

        cols_existentes = [
            c for c in cols
            if c in df.columns
        ]

        return df[cols_existentes]
    def add_id_empresa(self, df):
        df = df.copy()

        df["_idEmp"] = self.get_id_empresa()

        df["_idOperacao"] = df["_idEmp"].astype(str) + "_" + df["codigo"].astype(str)

        return df