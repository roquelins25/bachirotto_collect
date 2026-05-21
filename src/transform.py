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
        
        # garante que só pega colunas existentes
        cols_existentes = [c for c in cols if c in df.columns]
        
        return df[cols_existentes]
    

    def add_id_empresa(self, df):
        df = df.copy()
        
        mapa = {
            "gerencial": 10001,
            "fiscal": 10002
        }

        
        
        if self.type not in mapa:
            raise ValueError(f"Tipo inválido: {self.type}")
        
        df["_idEmp"] = mapa[self.type]
        
        if self.tipo == 1:
            df["_idCliente"] = df["_idEmp"].astype(str) + "_" + df["codigo"].astype(str)
        elif self.tipo == 4:
            df["_idRep"] = df["_idEmp"].astype(str) + "_" + df["codigo"].astype(str)
        
        return df


    def load_process(self,data):
        # garante estrutura correta
        data = data.get('data', [])
        
        df = pd.DataFrame(data)
        
        df_tratado = self.transform(df)
        df_final = self.add_id_empresa(df_tratado)
        
        return df_final

