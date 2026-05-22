import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def connect_db():
    load_dotenv(_ENV_PATH, override=True)
    try:
        connection = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=os.getenv('DB_PORT')
        )
        print("Conexão com o banco de dados estabelecida com sucesso!")
        return connection
    except Exception as e:
        raise RuntimeError(f"Erro ao conectar ao banco de dados: {e}") from e


if __name__ == "__main__":
    conn = connect_db()
    if conn:
        conn.close()
        print("Conexão fechada.")