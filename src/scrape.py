import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup



URL_BASE = "https://tabuademares.com/br/paraiba/joao-pessoa"
URL_ONDAS = f"{URL_BASE}/previsao/ondas"
URL_VENTO = f"{URL_BASE}/previsao/vento"
URL_CHUVA = f"{URL_BASE}/previsao/probabilidade-chuva"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


PAUSA = 1.5

DIR_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def baixar_html(url: str, dados_post: dict | None = None) -> str:

    if dados_post is None:
        resp = requests.get(url, headers=HEADERS)
        
    else:
        resp = requests.post(url, data=dados_post, headers=HEADERS)

    resp.raise_for_status()

    return resp.text

def bloco_cache(url: str, nome: str, dados_post: dict | None = None) -> str:
    arquivo = DIR_RAW / nome
    if not arquivo.exists():
        arquivo.write_text(baixar_html(url, dados_post), encoding="utf-8")
        time.sleep(PAUSA)
    return arquivo.read_text(encoding="utf-8")

def parsear_mares(html: str, ano: int, mes: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tabela = soup.find("table", id="tabla_mareas")
    ocorrencia_mares = []

    for linha in tabela.find_all("tr", onclick=True):
        texto_data = linha["onclick"]
        coeficiente = linha.find("div", class_="tabla_mareas_coeficiente_numero")

        if coeficiente is None:
            texto_coeficiente = ""
        else:
            texto_coeficiente = coeficiente.get_text(" ", strip=True)

                
        for mare in linha.find_all("td", class_="tabla_mareas_marea"):
            texto_mare = mare.get_text(" ", strip=True)

            if texto_mare == "":
                continue

            bloco_tipo = mare.find("div", class_="tabla_mareas_marea_bajamar_pleamar")

            if "tabla_mareas_marea_pleamar" in bloco_tipo.get("class"):
                tipo = "alta"
            else:
                tipo = "baixa"

            ocorrencia_mares.append({
                "data": texto_data,
                "mare": texto_mare,
                "tipo_mare": tipo,
                "coeficiente": texto_coeficiente,
            })

    return ocorrencia_mares
            


def parsear_previsao(html: str, ano: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    ocorrencia_previsao = []

    for dia in soup.find_all("div", class_="f_cont"):
        texto_dia = dia.find("div", class_="f_fecha").get_text(" ", strip=True)
        
        if texto_dia == "":
            continue

        for hora in dia.find_all("div", class_="f_temp_horas"):
            elemento = hora.find_all("div", class_="f_temp_hora")

            if not elemento:
                continue

            hora_dia = elemento[0].get_text(strip=True)
            segundo_campo = elemento[1].get_text(strip=True)

            campo = hora.find("div", class_="grafico_temp_barra_relleno")

            if campo is None:
                continue

            valor = campo.get_text(strip=True)

            ocorrencia_previsao.append({
                "ano": ano,
                "dia": texto_dia,
                "hora_dia": hora_dia,
                "segundo_campo": segundo_campo,
                "valor": valor,
            })

    return ocorrencia_previsao



def coletar_mares_do_ano(ano: int) -> pd.DataFrame:
    mares_ano = []

    for mes in range(1, 13):
        fecha = f"{ano}-{mes:02d}-01"
        html = bloco_cache(URL_BASE, f"mares_dia_{fecha}.html", {"fecha": fecha})
        mares = parsear_mares(html, ano, mes)
        mares_ano.extend(mares)

    return pd.DataFrame(mares_ano)
        



def main(ano: int = 2025) -> None:
    DIR_RAW.mkdir(parents=True, exist_ok=True) 
    hoje = datetime.now()

#marés:
    html = bloco_cache(URL_BASE, "mares.html")
    mares = parsear_mares(html, hoje.year, hoje.month)

    pd.DataFrame(mares).to_csv(DIR_RAW / "mares_previsao.csv", index=False)

    print(f"Quantidade de linhas de mares_previsao.csv: {len(mares)}")


#vento:
    html = bloco_cache(URL_VENTO, "vento.html")
    vento = parsear_previsao(html, hoje.year)

    pd.DataFrame(vento).rename(
        columns={"segundo_campo": "direcao", "valor": "velocidade"}
    ).to_csv(DIR_RAW / "vento.csv", index=False)

    print(f"Quantidade de linhas de vento.csv: {len(vento)}")


#ondas:
    html = bloco_cache(URL_ONDAS, "ondas.html")
    ondas = parsear_previsao(html, hoje.year)

    pd.DataFrame(ondas).rename(
        columns={"segundo_campo": "direcao", "valor": "altura(m)"}
    ).to_csv(DIR_RAW / "ondas.csv", index=False)

    print(f"Quantidade de linhas de ondas.csv: {len(ondas)}")
    

#chuva
    html = bloco_cache(URL_CHUVA, "probabilidade-chuva.html")
    chuva = parsear_previsao(html, hoje.year)

    pd.DataFrame(chuva).rename(
        columns={"segundo_campo": "altura_chuva(mm)", "valor": "probabilidade(%)"}
    ).to_csv(DIR_RAW / "probabilidade-chuva.csv", index=False)

    print(f"Quantidade de linhas de probabilidade-chuva.csv: {len(chuva)}")

#marés do ano:
    mares_do_ano = coletar_mares_do_ano(ano)
    mares_do_ano.to_csv(DIR_RAW / f"mares_{ano}.csv", index=False)
    print(f"Quantidade de linhas de mares_{ano}.csv: {len(mares_do_ano)}")


if __name__ == "__main__":
    main()
