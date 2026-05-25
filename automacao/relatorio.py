import io
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH, override=True)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.conectDB import connect_db

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _query(conn, sql: str, params: dict) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def _semana_str() -> str:
    hoje = datetime.now()
    semana = hoje.isocalendar().week
    ano = hoje.year
    inicio = hoje - timedelta(days=hoje.weekday())
    fim = inicio + timedelta(days=6)
    return f"Semana {semana}/{ano} ({inicio.strftime('%d/%m')} a {fim.strftime('%d/%m')})"


def _brl(val) -> str:
    return f"R$ {float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _int_br(valor) -> str:
    return f"{int(valor):,}".replace(",", ".")


def _lista(df: pd.DataFrame) -> str:
    if df.empty:
        return "• Nenhum cliente nesta situacao"
    linhas = []
    for _, row in df.iterrows():
        if pd.notnull(row["ultima_compra"]):
            data  = row["ultima_compra"].strftime("%d/%m/%Y")
            valor = _brl(row["valor_ultima_compra"])
            linhas.append(f"• {row['nome']} | Ultima compra: {data} | Valor: {valor}")
        else:
            linhas.append(f"• {row['nome']} | Sem compras")
    return "\n".join(linhas)


# ──────────────────────────────────────────────
# Queries
# ──────────────────────────────────────────────

class RelatorioData:
    def __init__(self, codvendedor: int, ano: int, mes: int):
        self.codvendedor = codvendedor
        self.ano = ano
        self.mes = mes
        self.conn = connect_db()

    def _rep_meta(self, codvendedor: int, ano: int, mes: int) -> pd.DataFrame:
        return _query(self.conn, """
            SELECT
                r.razao AS nome,
                COALESCE(SUM(m.meta), 0)                                      AS meta_geral,
                COALESCE(MAX(CASE WHEN m.tipo = 'FEIJAO' THEN m.meta END), 0) AS meta_feijao,
                COALESCE(MAX(CASE WHEN m.tipo = 'MIX'   THEN m.meta END), 0) AS meta_mix
            FROM tb_representante r
            LEFT JOIN tb_metas m
                ON  m.id_vend = r.codvendedor
                AND m.ano     = %(ano)s
                AND m.mes     = %(mes)s
            WHERE r.codvendedor = %(codvendedor)s
            GROUP BY r.razao
        """, {"codvendedor": codvendedor, "ano": ano, "mes": mes})
    
    def _representante(self, codvendedor: int) -> pd.DataFrame:
        return _query(self.conn, """
            SELECT
                r.razao AS nome
            FROM tb_representante r
            WHERE r.codigo = %(codvendedor)s
        """, {"codvendedor": codvendedor})

    def _faturamento(self, codvendedor: int, ano: int, mes: int) -> pd.DataFrame:
        return _query(self.conn, """
            SELECT
                p.xtipo,
                COALESCE(SUM(f.itens_total), 0) AS total,
                COALESCE(SUM(f.itens_qtd), 0)   AS quantidade
            FROM tb_fatos f
            JOIN tb_produto      p   ON p.idprod     = f.idcodpro
            JOIN tb_operacao     t   ON t.idop        = f.idcodop
            JOIN tb_cliente      tc  ON tc.idcliente  = f.idcodcli
            JOIN tb_representante rep ON rep.idrep    = f.idcodrep
            WHERE rep.codigo = %(codvendedor)s
              AND EXTRACT(YEAR  FROM f.emissao) = %(ano)s
              AND EXTRACT(MONTH FROM f.emissao) = %(mes)s
              AND tc.ativo = TRUE
              AND t.codigo NOT IN ('11', '68')
            GROUP BY p.xtipo
            ORDER BY p.xtipo
        """, {"codvendedor": codvendedor, "ano": ano, "mes": mes})

    def _carteira(self, codvendedor: int) -> pd.DataFrame:
        return _query(self.conn, """
            SELECT
                COUNT(*) FILTER (WHERE ativo = TRUE)  AS ativos,
                COUNT(*) FILTER (WHERE ativo = FALSE) AS inativos
            FROM tb_cliente
            WHERE codvendedor = %(codvendedor)s
        """, {"codvendedor": codvendedor})

    def _clientes_inativos(self, codvendedor: int) -> pd.DataFrame:
        """Retorna todos os clientes ativos com a data e valor da ultima compra."""
        return _query(self.conn, """
            SELECT
                DISTINCT TRIM(c.razao) AS nome,
                (
                    SELECT MAX(f2.data)
                    FROM tb_fatos f2
                    WHERE f2.idcodcli = c.idcliente
                      AND f2.situacao <> 'Pendente'
                ) AS ultima_compra,
                (
                    SELECT COALESCE(SUM(f3.itens_total), 0)
                    FROM tb_fatos f3
                    WHERE f3.idcodcli = c.idcliente
                      AND f3.situacao <> 'Pendente'
                      AND f3.data = (
                          SELECT MAX(f4.data)
                          FROM tb_fatos f4
                          WHERE f4.idcodcli = c.idcliente
                            AND f4.situacao <> 'Pendente'
                      )
                ) AS valor_ultima_compra
            FROM tb_cliente c
            WHERE c.codvendedor = %(codvendedor)s
              AND c.ativo = TRUE
              AND c.razao IS NOT NULL
            ORDER BY TRIM(c.razao)
        """, {"codvendedor": codvendedor})


def _categorias_inatividade(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    hoje = datetime.now().date()

    def dias(d):
        if pd.isnull(d):
            return None
        return (hoje - d).days

    df = df.copy()
    df["dias"] = df["ultima_compra"].apply(dias)

    return {
        "30_60":     df[(df["dias"] >= 30) & (df["dias"] < 60)].reset_index(drop=True),
        "60_90":     df[(df["dias"] >= 60) & (df["dias"] < 90)].reset_index(drop=True),
        "90_plus":   df[df["dias"] >= 90].reset_index(drop=True),
        "sem_compra": df[df["dias"].isna()].reset_index(drop=True),
    }


# ──────────────────────────────────────────────
# Planilha anexo
# ──────────────────────────────────────────────

def _build_excel(df_inativos: pd.DataFrame) -> bytes:
    hoje = datetime.now().date()

    df = df_inativos.copy()
    df["dias_sem_compra"] = df["ultima_compra"].apply(
        lambda d: (hoje - d).days if pd.notnull(d) else None
    )

    df = df.rename(columns={
        "nome":               "Razao Cliente",
        "ultima_compra":      "Ultima Venda",
        "dias_sem_compra":    "Dias Sem Compra",
        "valor_ultima_compra": "Valor Ultima Venda",
    })[["Razao Cliente", "Ultima Venda", "Dias Sem Compra", "Valor Ultima Venda"]]

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inatividade")
    return buf.getvalue()


# ──────────────────────────────────────────────
# Montagem do corpo do email
# ──────────────────────────────────────────────

def build_email_body(codvendedor: int) -> str:
    hoje = datetime.now()
    ano, mes = hoje.year, hoje.month

    rel = RelatorioData(codvendedor, ano, mes)
    try:
        df_rep      = rel._rep_meta(codvendedor, ano, mes)
        df_representante = rel._representante(codvendedor)
        df_fat      = rel._faturamento(codvendedor, ano, mes)
        df_cart     = rel._carteira(codvendedor)
        df_inativos = rel._clientes_inativos(codvendedor)
    finally:
        rel.conn.close()

    cats = _categorias_inatividade(df_inativos)

    nome_rep   = df_representante.iloc[0]["nome"] if not df_representante.empty else "---"
    meta_geral = float(df_rep.iloc[0]["meta_geral"])  if not df_rep.empty else 0

    fat_dict   = {row["xtipo"]: row["total"]     for _, row in df_fat.iterrows()}
    qtd_dict   = {row["xtipo"]: row["quantidade"] for _, row in df_fat.iterrows()}

    fat_feijao = float(fat_dict.get("FEIJAO", 0))
    fat_mix    = float(fat_dict.get("MIX", 0))
    qtd_feijao = float(qtd_dict.get("FEIJAO", 0))
    qtd_mix    = float(qtd_dict.get("MIX", 0))
    fat_total  = fat_feijao + fat_mix
    qtd_total  = qtd_feijao + qtd_mix

    atingimento = (fat_total / meta_geral * 100) if meta_geral > 0 else 0

    ativos   = int(df_cart.iloc[0]["ativos"])   if not df_cart.empty else 0
    inativos = int(df_cart.iloc[0]["inativos"]) if not df_cart.empty else 0

    return (
        "Prezados,\n\n"
        "Segue abaixo a analise comercial semanal referente ao periodo informado.\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "ANALISE COMERCIAL SEMANAL\n\n"
        f"Representante: {nome_rep}\n"
        f"Semana: {_semana_str()}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "METAS\n\n"
        f"  Meta Geral:           {_brl(meta_geral)}\n"
        f"  Faturamento Atual:    {_brl(fat_total)}\n"
        f"  Atingimento:          {atingimento:.1f}%\n"
        f"  Quantidade Vendida:   {_int_br(qtd_total)}\n"
        f"  Carteira de Clientes: {ativos}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "FATURAMENTO POR CATEGORIA\n\n"
        f"  Feijao: {_brl(fat_feijao)}\n"
        f"  Mix:    {_brl(fat_mix)}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "BASE DE CLIENTES\n\n"
        f"  Clientes Ativos:   {ativos}\n"
        f"  Clientes Inativos: {inativos}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "CLIENTES SEM VENDAS (30 a 60 DIAS)\n\n"
        f"{_lista(cats['30_60'])}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "CLIENTES SEM VENDAS (60 a 90 DIAS)\n\n"
        f"{_lista(cats['60_90'])}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "CLIENTES SEM COMPRA (ACIMA DE 90 DIAS)\n\n"
        f"{_lista(cats['90_plus'])}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "CLIENTES ATIVOS SEM COMPRAS\n\n"
        f"{_lista(cats['sem_compra'])}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "PROSPECCAO - OBJETIVO DO MES\n\n"
        "Clientes previstos para prospeccao na rota:\n\n"
        "  •\n  •\n  •\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "OBSERVACAO\n\n"
        "O faturamento e considerado de forma geral. Em caso de devolucao de pedidos,\n"
        "os valores serao descontados no fechamento do mes.\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "ANALISE DE RESULTADO\n\n"
        "1. Principal motivo de nao atingir a meta anterior:\n"
        "2. Acao corretiva para esta semana:\n"
        "3. Expectativa para fechamento do mes:\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Atenciosamente,\n\n"
        f"{nome_rep}"
    )


# ──────────────────────────────────────────────
# Envio via Gmail SMTP
# ──────────────────────────────────────────────

def send_email(codvendedor: int) -> None:
    email_from = os.getenv("EMAIL_FROM")
    email_pass = os.getenv("EMAIL_PASSWORD")
    email_to   = os.getenv("EMAIL_TO")

    if not all([email_from, email_pass, email_to]):
        raise RuntimeError("Variaveis EMAIL_FROM, EMAIL_PASSWORD ou EMAIL_TO ausentes no .env")

    corpo = build_email_body(codvendedor)

    hoje = datetime.now()
    rel = RelatorioData(codvendedor, hoje.year, hoje.month)
    try:
        df_inativos = rel._clientes_inativos(codvendedor)
    finally:
        rel.conn.close()

    excel_bytes = _build_excel(df_inativos)

    lines      = corpo.splitlines()
    nome_rep   = next((l.replace("Representante: ", "") for l in lines if l.startswith("Representante: ")), "Rep")
    semana_str = next((l.replace("Semana: ", "")        for l in lines if l.startswith("Semana: ")),        "")

    msg = MIMEMultipart()
    msg["Subject"] = f"Analise Comercial Semanal - {nome_rep} - {semana_str}"
    msg["From"]    = email_from
    msg["To"]      = email_to
    msg.attach(MIMEText(corpo, "plain", "utf-8"))

    part = MIMEBase("application", "octet-stream")
    part.set_payload(excel_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="inatividade_{nome_rep}.xlsx"')
    msg.attach(part)

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(email_from, email_pass)
        smtp.sendmail(email_from, email_to, msg.as_bytes())

    print(f"Email enviado para {email_to}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python relatorio.py <codvendedor> [--preview]")
        print("Exemplo: python relatorio.py 13221 --preview")
        sys.exit(1)

    codvendedor = int(sys.argv[1])

    if "--preview" in sys.argv:
        sys.stdout.buffer.write((build_email_body(codvendedor) + "\n").encode("utf-8"))
    else:
        send_email(codvendedor)
