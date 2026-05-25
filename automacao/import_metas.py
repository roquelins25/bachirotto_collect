import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.conectDB import connect_db

_XLSX_PATH = Path(__file__).resolve().parent.parent / "metas basch.xlsx"


def _parse_meta(val) -> float | None:
    if pd.isna(val):
        return None
    s = str(val).strip().replace("\xa0", "").replace(",", ".")
    if not s or set(s) <= {"-", " "}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def import_metas(xlsx_path: Path = _XLSX_PATH) -> None:
    print(f"Lendo: {xlsx_path}")
    df = pd.read_excel(xlsx_path, dtype=str)
    df = df.dropna(how="all")
    df.columns = [c.strip().lower() for c in df.columns]

    df = df[df["ano"].notna() & df["mes"].notna()]
    df["ano"] = df["ano"].astype(float).astype(int)
    df["mes"] = df["mes"].astype(float).astype(int)
    df["meta"] = df["meta"].apply(_parse_meta)
    df["id_vend"] = pd.to_numeric(df["id_vend"], errors="coerce").astype("Int64")
    df["tipo"] = df["tipo"].str.strip()
    df["vendedor"] = df["vendedor"].str.strip()
    df["data_vendedor"] = df["data_vendedor"].str.strip()

    periods = df[["ano", "mes"]].drop_duplicates().values.tolist()

    conn = connect_db()
    try:
        with conn.cursor() as cur:
            for ano, mes in periods:
                cur.execute(
                    "DELETE FROM tb_metas WHERE ano = %s AND mes = %s",
                    (ano, mes),
                )
                deleted = cur.rowcount

                chunk = df[(df["ano"] == ano) & (df["mes"] == mes)]
                for _, row in chunk.iterrows():
                    cur.execute(
                        """
                        INSERT INTO tb_metas (ano, mes, data_vendedor, vendedor, tipo, meta, id_vend)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            row["ano"],
                            row["mes"],
                            row["data_vendedor"],
                            row["vendedor"],
                            row["tipo"],
                            row["meta"],
                            int(row["id_vend"]) if pd.notna(row["id_vend"]) else None,
                        ),
                    )
                print(f"  {ano}/{mes:02d}: {deleted} deletados, {len(chunk)} inseridos")

        conn.commit()
        print(f"\nConcluído: {len(df)} registros importados.")
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Erro ao importar metas: {e}") from e
    finally:
        conn.close()


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else _XLSX_PATH
    if not path.exists():
        print(f"Arquivo não encontrado: {path}")
        sys.exit(1)
    import_metas(path)
