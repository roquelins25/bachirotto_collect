# %%
from datetime import datetime, timedelta

hoje = datetime.now()

semana = hoje.isocalendar().week
ano = hoje.year

inicio = hoje - timedelta(days=hoje.weekday())
fim = inicio + timedelta(days=6)

texto_semana = (
    f"Semana {semana}/{ano} "
    f"({inicio.strftime('%d/%m')} a {fim.strftime('%d/%m')})"
)
# %%
print(texto_semana)
# %%
