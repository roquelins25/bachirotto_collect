#%%
import os
import json
import pandas as pd

class TransformParceiros:
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
        
        mapa = {
            "gerencial": 10001,
            "fiscal": 10002
        }

        
        
        if self.type not in mapa:
            raise ValueError(f"Tipo inválido: {self.type}")
        
        df["_idEmp"] = mapa[self.type]
        
        if self.tipo in (1, 5):
            df["_idCliente"] = df["_idEmp"].astype(str) + "_" + df["codigo"].astype(str)
        elif self.tipo == 4:
            df["_idRep"] = df["_idEmp"].astype(str) + "_" + df["codigo"].astype(str)
        
        return df


