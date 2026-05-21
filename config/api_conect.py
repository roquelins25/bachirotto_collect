import os

import requests
from dotenv import load_dotenv


class SimDataAPI:
    _BASE_URL = "https://api.simdata.com.br"

    def __init__(self):
        load_dotenv()
        self._tokens = {
            "gerencial": os.getenv("GERENCIAL"),
            "fiscal":    os.getenv("FISCAL"),
        }

    def get(self, endpoint: str, type_process: str) -> dict:
        token = self._tokens.get(type_process)
        if not token:
            raise ValueError(f"Tipo de empresa inválido: {type_process}")
        response = requests.get(
            f"{self._BASE_URL}/{endpoint}",
            headers={"apitoken": token},
        )
        response.raise_for_status()
        return response.json()
