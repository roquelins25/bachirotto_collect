#%%
import os
import json
import pandas as pd
import numpy as np

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
            df["_idVendedor"] = df["_idEmp"].astype(str) + "_" + df["codvendedor"].astype(str)
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
    
class TransformProdutos(BaseTransform):

    def __init__(self, type: str):
        self.type = type.lower()

    def expandir_coluna(self, df, coluna):

        if coluna not in df.columns:
            return df

        expandido = pd.json_normalize(df[coluna])

        expandido.columns = [
            f"{coluna}_{c}"
            for c in expandido.columns
        ]

        df = pd.concat(
            [
                df.drop(columns=[coluna]),
                expandido
            ],
            axis=1
        )

        return df

    def transform(self, df):

        cols = [
            "codigo",
            "referencia",
            "descricao",
            "unidade",
            "ativo",
            "tipo",
            "categoria"
        ]

        cols_existentes = [
            c for c in cols
            if c in df.columns
        ]

        df = df[cols_existentes].copy()

        # Expande categoria
        df = self.expandir_coluna(df, "categoria")

        return df

    def add_id_empresa(self, df):

        df = df.copy()

        df["_idEmp"] = self.get_id_empresa()

        df["_idProd"] = (
            df["_idEmp"].astype(str)
            + "_"
            + df["codigo"].astype(str)
        )
        df["xtipo"] = np.where(
                 df["descricao"].str.contains("feijao", case=False, na=False),
                "FEIJAO",
                "MIX")

        return df

class TransformFatos(BaseTransform):

    def __init__(self, type: str):
        self.type = type.lower()
   
    def expandir_campo(self, df, coluna, campo, novo_nome=None):

        if coluna not in df.columns:
            return df

        if novo_nome is None:
            novo_nome = f"{coluna}_{campo}"

        df[novo_nome] = df[coluna].apply(
            lambda x: x.get(campo) if isinstance(x, dict) else None
        )

        return df
    
    def expandir_lista(self, df, coluna, campos=None):

        if coluna not in df.columns:
            return df

        # explode lista
        df = df.explode(coluna)

        # se vazio
        if df[coluna].isna().all():
            return df

        # normaliza
        expandido = pd.json_normalize(df[coluna])

        # filtra somente campos desejados
        if campos is not None:

            cols_existentes = [
                c for c in campos
                if c in expandido.columns
            ]

            expandido = expandido[cols_existentes]

        # prefixa colunas
        expandido.columns = [
            f"{coluna}_{c}"
            for c in expandido.columns
        ]

        # concatena
        df = pd.concat(
            [
                df.drop(columns=[coluna]).reset_index(drop=True),
                expandido.reset_index(drop=True)
            ],
            axis=1
        )

        return df
    
    def filterSituacao(self,df):
        df = df.copy()
        df = df[df["situacao"].isin(["Emitido", "Entregue", "Pendente"])]
        return df
    
    def filterOperacao(self, df):

        df = df.copy()

        col = "itens_codigooperacao"
        if col not in df.columns:
            return df

        df = df[~df[col].isin([12])]

        return df
   
    def transform(self, df):
        cols = [
            "numero",
            "data",
            "emissao",
            "situacao",
            "cliente",
            "codvendedor",
            "totalprodutos",
            "totalPedido",
            "itens"
        ]

        cols_existentes = [
            c for c in cols
            if c in df.columns
        ]
        df = df[cols_existentes].copy()
        # Expande cliente
        df = self.expandir_campo(df, coluna="cliente", campo="codigo", novo_nome="cliente_codigo")
        df = df.drop(columns=["cliente"])

        df = self.filterSituacao(df)

        df = self.expandir_lista(df, coluna="itens", campos=["codigoproduto", "codigooperacao", "qtd", "unitario", "total"])

        df = self.filterOperacao(df)

        return df
    
    def add_id_empresa(self, df):

        df = df.copy()

        df["_idEmp"] = self.get_id_empresa()
        
        df["_idcodcli"] = (
            df["_idEmp"].astype(str)
            + "_"
            + df["cliente_codigo"].astype(str)
        )

        df["_idcodpro"] = (
            df["_idEmp"].astype(str)
            + "_"
            + df["itens_codigoproduto"].astype(str)
        )
        
        df["_idcodop"] = (
            df["_idEmp"].astype(str)
            + "_"
            + df["itens_codigooperacao"].astype(str)
        )        

        df["_idcodrep"] = (
            df["_idEmp"].astype(str)
            + "_"
            + df["codvendedor"].astype(str)
        )

        return df
    
class TransformCategoriaFinanceira(BaseTransform):
    def __init__(self, type: str):
        self.type = type.lower()

    def transform(self, df):

        cols = [
            "codigo",
            "descricao",
            "tipo",
            "grupo"
        ]

        cols_existentes = [
            c for c in cols
            if c in df.columns
        ]

        return df[cols_existentes]
    def add_id_empresa(self, df):
        df = df.copy()

        df["_idEmp"] = self.get_id_empresa()

        df["_idCatFin"] = df["_idEmp"].astype(str) + "_" + df["codigo"].astype(str)

        return df

class TransformCaixaBancos(BaseTransform):
    _EXCLUIR_CAT = {
        10001: {"93", "8", "null",""},
        10002: {"8", "100", "null",""},
    }

    def __init__(self, type: str):
        self.type = type.lower()

    def transform(self, df):
        cols = [
            "tipo", "historico", "numdoc", "categoriaFinanceira",
            "codCategoriaFinanceira", "lancamento", "movimento",
            "valor", "codBanco",
        ]
        cols_existentes = [c for c in cols if c in df.columns]
        df = df[cols_existentes].copy()

        df = df.replace("null", pd.NA)

        id_empresa = self.get_id_empresa()
        categorias_excluir = self._EXCLUIR_CAT.get(id_empresa, set())

        df = df[df["tipo"].notna()]
        df = df[~df["codCategoriaFinanceira"].isin(categorias_excluir)]
        df = df[df["codCategoriaFinanceira"].notna()]

        df["valorCorrigido"] = np.where(df["tipo"] == "E", df["valor"], df["valor"] * -1)

        df["lancamento"] = pd.to_datetime(df["lancamento"], errors="coerce").dt.date
        df["movimento"] = pd.to_datetime(df["movimento"], errors="coerce").dt.date
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        df["valorCorrigido"] = pd.to_numeric(df["valorCorrigido"], errors="coerce")

        return df

    def add_id_empresa(self, df):
        df = df.copy()
        df["_idEmp"] = self.get_id_empresa()
        df["_idCodCategoria"] = df["_idEmp"].astype(str) + "_" + df["codCategoriaFinanceira"].astype(str)
        return df
# %%
