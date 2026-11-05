"""Monta no Metabase local o painel das 3 perguntas de negócio, a partir das visões do dashboard/schema.sql.

    uv run --env-file .env python scripts/metabase.py

Pode rodar de novo: o banco, a coleção, as perguntas e o painel são achados pelo nome e atualizados.
Usa METABASE_API_KEY (Admin → Authentication → API Keys) e as credenciais do Postgres do .env.
"""
import json
import os
import urllib.error
import urllib.request

URL = os.environ.get("METABASE_URL", "http://localhost:3001")
NOME_BANCO = "Dashboard Good Lion"
NOME_COLECAO = "Good Lion"
NOME_PAINEL = "Empresas no Brasil: categorias, capital social e movimentação"


def api(metodo, caminho, corpo=None):
    pedido = urllib.request.Request(
        f"{URL}/api{caminho}",
        method=metodo,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=120) as resposta:
            texto = resposta.read()
    except urllib.error.HTTPError as erro:
        raise SystemExit(f"{metodo} {caminho}: {erro.code} {erro.read().decode()[:800]}") from None
    return json.loads(texto) if texto else None


def _lista(resposta):
    return resposta["data"] if isinstance(resposta, dict) and "data" in resposta else resposta


def banco():
    for b in _lista(api("GET", "/database")):
        if b["name"] == NOME_BANCO:
            return b["id"]
    # Host "postgres": o Metabase roda no mesmo docker compose.
    detalhes = {"host": "postgres", "port": 5432, "dbname": "dashboard", "ssl": False,
                "user": os.environ["POSTGRES_USER"], "password": os.environ["POSTGRES_PASSWORD"]}
    criado = api("POST", "/database", {"engine": "postgres", "name": NOME_BANCO, "details": detalhes})
    api("POST", f"/database/{criado['id']}/sync_schema")
    return criado["id"]


def colecao():
    for c in _lista(api("GET", "/collection")):
        if c.get("name") == NOME_COLECAO and not c.get("archived"):
            return c["id"]
    # O H2 interno do Metabase às vezes está com o contador de IDs atrás dos registros (erro 500 de chave
    # duplicada): cada tentativa avança o contador. Sem sucesso, fica na coleção raiz ("Our analytics").
    for _ in range(8):
        try:
            return api("POST", "/collection", {"name": NOME_COLECAO})["id"]
        except SystemExit as erro:
            if "Unique index or primary key violation" not in str(erro):
                raise
    return None


def _ultimo_mes(visao):
    return f"(SELECT MAX(ano_mes) FROM {visao})"


# (nome, SQL, display, visualization_settings). Cada pergunta mostra o mês mais recente carregado.
PERGUNTAS = [
    ("1. Categorias por região (proporção)",
     "SELECT regiao, categoria, proporcao FROM mv_categorias_regiao "
     f"WHERE ano_mes = {_ultimo_mes('mv_categorias_regiao')} ORDER BY regiao, ordem",
     "bar", {"graph.dimensions": ["regiao", "categoria"], "graph.metrics": ["proporcao"],
             "stackable.stack_type": "stacked", "graph.y_axis.title_text": "Proporção das empresas ativas"}),
    ("1. Categorias por UF",
     "SELECT sigla_uf, categoria, qtd_empresas FROM mv_categorias_uf "
     f"WHERE ano_mes = {_ultimo_mes('mv_categorias_uf')} ORDER BY sigla_uf, ordem",
     "bar", {"graph.dimensions": ["sigla_uf", "categoria"], "graph.metrics": ["qtd_empresas"],
             "stackable.stack_type": "stacked", "graph.y_axis.title_text": "Empresas ativas"}),
    ("1. Categorias por município",
     f"SELECT sigla_uf AS uf, municipio, categoria, qtd_empresas, ROUND(proporcao * 100, 1) AS \"proporção (%)\" "
     f"FROM mv_categorias_municipio WHERE ano_mes = {_ultimo_mes('mv_categorias_municipio')} "
     "ORDER BY sigla_uf, municipio, ordem",
     "table", {}),
    ("2. Mediana do capital social por UF",
     f"SELECT sigla_uf, mediana_capital_social FROM mv_capital_uf WHERE ano_mes = {_ultimo_mes('mv_capital_uf')} "
     "ORDER BY mediana_capital_social DESC",
     "bar", {"graph.dimensions": ["sigla_uf"], "graph.metrics": ["mediana_capital_social"],
             "graph.y_axis.title_text": "Mediana do capital social (R$)"}),
    ("2. Capital social por região",
     f"SELECT regiao, qtd_empresas, mediana_capital_social, soma_capital_social FROM mv_capital_regiao "
     f"WHERE ano_mes = {_ultimo_mes('mv_capital_regiao')} ORDER BY mediana_capital_social DESC",
     "table", {}),
    ("2. Mediana do capital social por município",
     f"SELECT sigla_uf AS uf, municipio, qtd_empresas, mediana_capital_social, soma_capital_social "
     f"FROM mv_capital_municipio WHERE ano_mes = {_ultimo_mes('mv_capital_municipio')} "
     "ORDER BY mediana_capital_social DESC",
     "table", {}),
    ("3. Aberturas e fechamentos por UF",
     f"SELECT sigla_uf, tipo_evento, SUM(qtd_eventos) AS eventos FROM mv_movimentacao_uf "
     f"WHERE ano_mes = {_ultimo_mes('mv_movimentacao_uf')} AND tipo_evento IN ('abertura', 'baixa') "
     "GROUP BY 1, 2 ORDER BY 1, 2",
     "bar", {"graph.dimensions": ["sigla_uf", "tipo_evento"], "graph.metrics": ["eventos"]}),
    ("3. Movimentação por região e tipo de evento",
     f"SELECT regiao, tipo_evento, categoria, qtd_eventos FROM mv_movimentacao_regiao "
     f"WHERE ano_mes = {_ultimo_mes('mv_movimentacao_regiao')} ORDER BY regiao, tipo_evento, categoria",
     "table", {}),
    ("3. Aberturas e fechamentos de MEI por município",
     f"SELECT sigla_uf AS uf, municipio, tipo_evento, qtd_eventos FROM mv_movimentacao_municipio "
     f"WHERE ano_mes = {_ultimo_mes('mv_movimentacao_municipio')} AND categoria = 'MEI' "
     "ORDER BY qtd_eventos DESC",
     "table", {}),
]

TEXTOS = {
    0: "## 1. Em quais regiões há mais MEI, ME, EPP e Demais?\nEmpresas ativas (matriz com situação 02) no mês "
       "mais recente. MEI vem primeiro: todo MEI também tem porte 01.",
    3: "## 2. Onde as empresas têm maior capital social?\n**Capital social declarado na abertura da empresa.** "
       "Não é faturamento nem lucro, que a base da Receita não tem. A **mediana** é a medida principal: há muitos "
       "MEIs com R$ 1 e erros de cadastro na casa dos bilhões, que distorcem a soma.",
    6: "## 3. Onde mais se abrem e se fecham empresas e MEIs?\nEventos do mês tirados do Change Data Feed: "
       "abertura (empresa nova e ativa), baixa (situação passou a 08), mudança de porte, entrada e saída do MEI.",
}


def pergunta(id_banco, id_colecao, existentes, nome, sql, display, ajustes):
    corpo = {"name": nome, "collection_id": id_colecao, "display": display, "visualization_settings": ajustes,
             "dataset_query": {"type": "native", "native": {"query": sql}, "database": id_banco}}
    if nome in existentes:
        api("PUT", f"/card/{existentes[nome]}", corpo)
        return existentes[nome]
    return api("POST", "/card", corpo)["id"]


def main():
    id_banco = banco()
    id_colecao = colecao()
    itens = _lista(api("GET", f"/collection/{id_colecao}/items"))
    existentes = {i["name"]: i["id"] for i in itens if i.get("model") == "card"}
    paineis = {i["name"]: i["id"] for i in itens if i.get("model") == "dashboard"}

    cartoes, linha, novo_id = [], 0, -1
    for indice, (nome, sql, display, ajustes) in enumerate(PERGUNTAS):
        if indice in TEXTOS:
            cartoes.append({"id": novo_id, "card_id": None, "row": linha, "col": 0, "size_x": 24, "size_y": 2,
                            "visualization_settings": {"text": TEXTOS[indice], "virtual_card": {
                                "name": None, "display": "text", "visualization_settings": {}, "dataset_query": {},
                                "archived": False}}})
            novo_id -= 1
            linha += 2
        id_pergunta = pergunta(id_banco, id_colecao, existentes, nome, sql, display, ajustes)
        coluna = (indice % 3) * 8
        cartoes.append({"id": novo_id, "card_id": id_pergunta, "row": linha, "col": coluna, "size_x": 8, "size_y": 6})
        novo_id -= 1
        if indice % 3 == 2:
            linha += 6

    id_painel = paineis.get(NOME_PAINEL) or api(
        "POST", "/dashboard", {"name": NOME_PAINEL, "collection_id": id_colecao})["id"]
    api("PUT", f"/dashboard/{id_painel}", {"dashcards": cartoes})
    print(f"painel: {URL}/dashboard/{id_painel}")


if __name__ == "__main__":
    main()
