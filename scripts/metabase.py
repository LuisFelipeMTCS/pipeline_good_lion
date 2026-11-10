"""Monta no Metabase local o painel das 3 perguntas de negócio, contado como uma história em três atos.

    uv run --env-file .env python scripts/metabase.py

Cada ato abre com a conclusão já escrita (calculada no Postgres na hora em que o script roda: rode de novo depois
de cada `make dashboard-load` e os títulos acompanham os dados). Formas e cores seguem uma regra só:
- categorias (MEI/ME/EPP/Demais) sempre nas mesmas 4 cores, em barras 100% empilhadas com o valor escrito;
- rankings (capital, municípios) em barras ordenadas de uma cor só; capital social sempre em violeta;
- aberturas para cima (azul) e baixas para baixo (vermelho), em torno do zero.
Pode rodar de novo: banco, coleção, perguntas e painel são achados pelo nome; perguntas antigas são arquivadas.
Usa METABASE_API_KEY (Admin → Authentication → API Keys) e as credenciais do Postgres do .env.
"""
import json
import os
import urllib.error
import urllib.request

import psycopg

URL = os.environ.get("METABASE_URL", "http://localhost:3001")
NOME_BANCO = "Dashboard Good Lion"
NOME_COLECAO = "Good Lion"
NOME_PAINEL = "Empresas no Brasil: categorias, capital social e movimentação"

# Paleta validada (skill dataviz, validate_palette.js no fundo branco): as 4 categorias passam nas checagens de
# daltonismo; verde-água e amarelo ficam abaixo de 3:1 de contraste, por isso os gráficos mostram os valores.
COR_CATEGORIA = {"MEI": "#2a78d6", "ME": "#eb6834", "EPP": "#1baf7a", "Demais": "#eda100"}
COR_CAPITAL = "#6250d6"
COR_ABERTURA, COR_BAIXA = "#2a78d6", "#e34948"


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


# ---------------------------------------------------------------- os fatos que viram títulos

def _br(numero, casas=0):
    texto = f"{numero:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def fatos():
    conninfo = (f"host={os.environ.get('POSTGRES_HOST', 'localhost')} port=5432 dbname=dashboard "
                f"user={os.environ['POSTGRES_USER']} password={os.environ['POSTGRES_PASSWORD']}")
    with psycopg.connect(conninfo) as c:
        def um(sql, *parametros):
            return c.execute(sql, parametros).fetchone()

        mes = um("SELECT MAX(ano_mes) FROM fato_empresa_mensal")[0]
        return {
            "mes": mes,
            "mais_comum": um("SELECT c.nome, COUNT(*)::numeric / SUM(COUNT(*)) OVER () FROM fato_empresa_mensal f "
                             "JOIN dim_categoria c USING (id_categoria) WHERE f.ano_mes = %s GROUP BY c.nome "
                             "ORDER BY 2 DESC LIMIT 1", mes),
            "mei_uf": um("SELECT sigla_uf, proporcao FROM mv_categorias_uf WHERE ano_mes = %s AND categoria = 'MEI' "
                         "ORDER BY proporcao DESC LIMIT 1", mes),
            "capital_uf": um("SELECT sigla_uf, media_capital_social FROM mv_capital_uf WHERE ano_mes = %s "
                             "ORDER BY media_capital_social DESC LIMIT 1", mes),
            "capital_mei": um("SELECT AVG(capital_social) FROM fato_empresa_mensal WHERE ano_mes = %s "
                              "AND id_categoria = 'MEI'", mes)[0],
            "capital_demais": um("SELECT AVG(capital_social) FROM fato_empresa_mensal WHERE ano_mes = %s "
                                 "AND id_categoria = 'DEMAIS'", mes)[0],
            "eventos": um("SELECT COALESCE(SUM(qtd_eventos) FILTER (WHERE tipo_evento = 'abertura'), 0), "
                          "COALESCE(SUM(qtd_eventos) FILTER (WHERE tipo_evento = 'baixa'), 0), "
                          "COALESCE(SUM(qtd_eventos) FILTER (WHERE tipo_evento = 'abertura' AND categoria = 'MEI'), 0) "
                          "FROM mv_movimentacao_uf WHERE ano_mes = %s", mes),
        }


def textos(f):
    uf, prop = f["mei_uf"]
    categoria, parte = f["mais_comum"]
    uf_cap, media_cap = f["capital_uf"]
    aberturas, baixas, aberturas_mei = f["eventos"]
    pct_mei_aberturas = aberturas_mei / aberturas if aberturas else 0
    razao = (f["capital_demais"] / f["capital_mei"]) if f["capital_mei"] else 0
    sinal = "+" if aberturas >= baixas else ""
    return {
        "intro": (f"# Empresas ativas: quem são, quanto declararam de capital e onde abrem e fecham\n"
                  f"Mês de referência **{f['mes']}**. Empresa ativa = estabelecimento matriz com situação cadastral 02 "
                  "(Receita Federal, CNPJ). Os indicadores abaixo comparam com o mês anterior."),
        "ato1": (f"## 1. A categoria mais comum é **{categoria}**: **{_br(parte * 100, 1)}%** das empresas ativas\n"
                 f"O MEI pesa mais em **{uf}**, onde **{_br(prop * 100, 1)}%** das empresas ativas são MEI. "
                 "As barras mostram a divisão de cada lugar entre MEI, ME, EPP e Demais (todo MEI também tem "
                 "porte 01; ele é contado primeiro)."),
        "ato2": (f"## 2. Capital social: a média em **{uf_cap}** é a mais alta, **R$ {_br(media_cap)}**\n"
                 f"A média das Demais (R$ {_br(f['capital_demais'])}) é {_br(razao)} vezes a do MEI "
                 f"(R$ {_br(f['capital_mei'])}). **Capital social é o valor declarado na abertura**, não faturamento "
                 "nem lucro, que a base não tem. Cadastros com valores na casa dos bilhões puxam a média para cima: "
                 "ela serve para comparar lugares e categorias, não como o capital de uma empresa típica."),
        "ato3": (f"## 3. No mês, abriram **{_br(aberturas)}** empresas e **{_br(baixas)}** foram baixadas: "
                 f"saldo de **{sinal}{_br(aberturas - baixas)}**\n"
                 f"**{_br(pct_mei_aberturas * 100)}%** das aberturas são de MEI. Eventos tirados do Change Data "
                 "Feed da base consolidada: abertura = empresa nova e ativa; baixa = situação passou a 08."),
    }


# ---------------------------------------------------------------- as perguntas

def _mes(visao):
    return f"(SELECT MAX(ano_mes) FROM {visao})"


PERCENTUAL = {"number_style": "percent", "decimals": 1}
REAIS = {"number_style": "currency", "currency": "BRL", "decimals": 0}


def _cor(serie, cor):
    return {serie: {"color": cor}}


def perguntas():
    """Os indicadores do topo e uma lista por ato. Cada item: (nome, SQL, display, visualization_settings)."""
    por_mes = "to_date(ano_mes || '-01', 'YYYY-MM-DD') AS mes"
    indicadores = [
        ("Empresas ativas",
         f"SELECT {por_mes}, COUNT(*) AS empresas_ativas FROM fato_empresa_mensal GROUP BY 1 ORDER BY 1",
         "smartscalar", {}),
        ("Participação do MEI",
         f"SELECT {por_mes}, AVG((id_categoria = 'MEI')::int) AS participacao FROM fato_empresa_mensal "
         "GROUP BY 1 ORDER BY 1",
         "smartscalar", {"column_settings": {'["name","participacao"]': PERCENTUAL}}),
        ("Média do capital social",
         f"SELECT {por_mes}, AVG(capital_social) AS media FROM fato_empresa_mensal GROUP BY 1 ORDER BY 1",
         "smartscalar", {"column_settings": {'["name","media"]': REAIS}}),
        ("Saldo do mês (aberturas − baixas)",
         "SELECT SUM(CASE tipo_evento WHEN 'abertura' THEN qtd_eventos WHEN 'baixa' THEN -qtd_eventos ELSE 0 END) "
         f"AS saldo FROM mv_movimentacao_uf WHERE ano_mes = {_mes('mv_movimentacao_uf')}",
         "scalar", {}),
    ]
    empilhado = {"stackable.stack_type": "normalized", "graph.show_values": True,
                 "series_settings": {nome: {"color": cor} for nome, cor in COR_CATEGORIA.items()},
                 "graph.y_axis.title_text": "Parte das empresas ativas", "graph.metrics": ["qtd_empresas"]}
    ato1 = [
        ("Divisão das empresas ativas por UF",
         "SELECT sigla_uf AS uf, categoria, qtd_empresas FROM mv_categorias_uf "
         f"WHERE ano_mes = {_mes('mv_categorias_uf')} ORDER BY sigla_uf, ordem",
         "bar", {**empilhado, "graph.dimensions": ["uf", "categoria"]}),
        ("Divisão das empresas ativas por região",
         "SELECT regiao, categoria, qtd_empresas FROM mv_categorias_regiao "
         f"WHERE ano_mes = {_mes('mv_categorias_regiao')} ORDER BY regiao, ordem",
         "bar", {**empilhado, "graph.dimensions": ["regiao", "categoria"]}),
        ("Municípios onde o MEI mais pesa (mín. 200 empresas ativas)",
         "SELECT municipio || ' (' || sigla_uf || ')' AS municipio, proporcao AS participacao_mei "
         f"FROM mv_categorias_municipio WHERE ano_mes = {_mes('mv_categorias_municipio')} AND categoria = 'MEI' "
         "AND qtd_empresas / NULLIF(proporcao, 0) >= 200 ORDER BY proporcao DESC LIMIT 10",
         "row", {"graph.dimensions": ["municipio"], "graph.metrics": ["participacao_mei"], "graph.show_values": True,
                 "series_settings": _cor("participacao_mei", COR_CATEGORIA["MEI"]),
                 "column_settings": {'["name","participacao_mei"]': PERCENTUAL}}),
    ]
    capital = {"series_settings": _cor("media", COR_CAPITAL), "graph.show_values": True,
               "graph.metrics": ["media"], "column_settings": {'["name","media"]': REAIS}}
    ato2 = [
        ("Média do capital social por UF",
         "SELECT sigla_uf AS uf, media_capital_social AS media FROM mv_capital_uf "
         f"WHERE ano_mes = {_mes('mv_capital_uf')} ORDER BY media DESC",
         "row", {**capital, "graph.dimensions": ["uf"]}),
        ("Média do capital social por categoria",
         "SELECT c.nome AS categoria, AVG(f.capital_social) AS media "
         "FROM fato_empresa_mensal f JOIN dim_categoria c USING (id_categoria) "
         "WHERE f.ano_mes = (SELECT MAX(ano_mes) FROM fato_empresa_mensal) GROUP BY c.nome ORDER BY media DESC",
         "row", {**capital, "graph.dimensions": ["categoria"]}),
        ("Municípios com maior média de capital social (mín. 200 empresas)",
         "SELECT municipio || ' (' || sigla_uf || ')' AS municipio, media_capital_social AS media "
         f"FROM mv_capital_municipio WHERE ano_mes = {_mes('mv_capital_municipio')} AND qtd_empresas >= 200 "
         "ORDER BY media DESC LIMIT 10",
         "row", {**capital, "graph.dimensions": ["municipio"]}),
    ]
    ato3 = [
        ("Aberturas (para cima) e baixas (para baixo) por UF",
         "SELECT sigla_uf AS uf, SUM(qtd_eventos) FILTER (WHERE tipo_evento = 'abertura') AS aberturas, "
         "-SUM(qtd_eventos) FILTER (WHERE tipo_evento = 'baixa') AS baixas FROM mv_movimentacao_uf "
         f"WHERE ano_mes = {_mes('mv_movimentacao_uf')} GROUP BY 1 ORDER BY 1",
         "bar", {"stackable.stack_type": "stacked", "graph.show_values": True,
                 "series_settings": {**_cor("aberturas", COR_ABERTURA), **_cor("baixas", COR_BAIXA)},
                 "graph.dimensions": ["uf"], "graph.metrics": ["aberturas", "baixas"],
                 "graph.y_axis.title_text": "Empresas no mês"}),
        ("Quem abre: aberturas por categoria",
         "SELECT categoria, SUM(qtd_eventos) AS aberturas FROM mv_movimentacao_uf "
         f"WHERE ano_mes = {_mes('mv_movimentacao_uf')} AND tipo_evento = 'abertura' GROUP BY 1 ORDER BY 2 DESC",
         "row", {"graph.dimensions": ["categoria"], "graph.metrics": ["aberturas"], "graph.show_values": True,
                 "series_settings": _cor("aberturas", COR_ABERTURA)}),
        ("Municípios com maior saldo (aberturas − baixas)",
         "SELECT municipio || ' (' || sigla_uf || ')' AS municipio, "
         "SUM(CASE tipo_evento WHEN 'abertura' THEN qtd_eventos WHEN 'baixa' THEN -qtd_eventos ELSE 0 END) AS saldo "
         f"FROM mv_movimentacao_municipio WHERE ano_mes = {_mes('mv_movimentacao_municipio')} "
         "GROUP BY 1 ORDER BY saldo DESC LIMIT 10",
         "row", {"graph.dimensions": ["municipio"], "graph.metrics": ["saldo"], "graph.show_values": True,
                 "series_settings": _cor("saldo", COR_ABERTURA)}),
    ]
    return indicadores, [ato1, ato2, ato3]


def pergunta(id_banco, id_colecao, existentes, nome, sql, display, ajustes):
    corpo = {"name": nome, "collection_id": id_colecao, "display": display, "visualization_settings": ajustes,
             "dataset_query": {"type": "native", "native": {"query": sql}, "database": id_banco}}
    if nome in existentes:
        api("PUT", f"/card/{existentes[nome]}", corpo)
        return existentes[nome]
    return api("POST", "/card", corpo)["id"]


def _texto(id_cartao, linha, conteudo, altura):
    return {"id": id_cartao, "card_id": None, "row": linha, "col": 0, "size_x": 24, "size_y": altura,
            "visualization_settings": {"text": conteudo, "virtual_card": {
                "name": None, "display": "text", "visualization_settings": {}, "dataset_query": {}, "archived": False}}}


def main():
    id_banco = banco()
    id_colecao = colecao()
    itens = _lista(api("GET", f"/collection/{id_colecao or 'root'}/items"))
    existentes = {i["name"]: i["id"] for i in itens if i.get("model") == "card"}
    paineis = {i["name"]: i["id"] for i in itens if i.get("model") == "dashboard"}
    historia = textos(fatos())
    indicadores, atos = perguntas()

    cartoes, usados, novo = [], set(), iter(range(-1, -100, -1))
    cartoes.append(_texto(next(novo), 0, historia["intro"], 2))
    for posicao, item in enumerate(indicadores):
        id_pergunta = pergunta(id_banco, id_colecao, existentes, *item)
        usados.add(id_pergunta)
        cartoes.append({"id": next(novo), "card_id": id_pergunta, "row": 2, "col": posicao * 6,
                        "size_x": 6, "size_y": 3})
    linha = 5
    for chave, ato in zip(("ato1", "ato2", "ato3"), atos):
        cartoes.append(_texto(next(novo), linha, historia[chave], 2))
        linha += 2
        for posicao, item in enumerate(ato):
            id_pergunta = pergunta(id_banco, id_colecao, existentes, *item)
            usados.add(id_pergunta)
            cartoes.append({"id": next(novo), "card_id": id_pergunta, "row": linha, "col": posicao * 8,
                            "size_x": 8, "size_y": 7})
        linha += 7

    id_painel = paineis.get(NOME_PAINEL) or api(
        "POST", "/dashboard", {"name": NOME_PAINEL, "collection_id": id_colecao})["id"]
    api("PUT", f"/dashboard/{id_painel}", {"dashcards": cartoes})
    # Perguntas da versão anterior do painel que ficaram de fora vão para o arquivo (não são apagadas).
    for id_pergunta in set(existentes.values()) - usados:
        api("PUT", f"/card/{id_pergunta}", {"archived": True})
    print(f"painel: {URL}/dashboard/{id_painel}")
    for chave in ("ato1", "ato2", "ato3"):
        print(" -", historia[chave].splitlines()[0].lstrip("# "))


if __name__ == "__main__":
    main()
