import zipfile

import pytest

from ingest.receita import abrir_convertido


def _zip_receita(caminho, conteudo_latin1):
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("K3241.K03200Y1.D60912.EMPRECSV", conteudo_latin1)
    return caminho


def test_empresas_vira_utf8_com_cabecalho_do_sdk(tmp_path):
    linhas = '"00000001";"JOSÉ DA CONCEIÇÃO";"2135";"50";"1000,00";"01";""\n'
    zip_path = _zip_receita(tmp_path / "Empresas1.zip", linhas.encode("latin1"))

    with abrir_convertido(zip_path, "empresas") as f:
        convertido = f.read()

    assert convertido == (
        "cnpj_basico;razao_social;natureza_juridica;qualificacao_responsavel;"
        "capital_social;porte;ente_federativo\n"
        '"00000001";"JOSÉ DA CONCEIÇÃO";"2135";"50";"1000,00";"01";""\n'
    ).encode()


def test_estabelecimentos_tem_uf_e_municipio_na_posicao_da_receita(tmp_path):
    # Linha real de 2026-09, com um ";" inserido no complemento para testar aspas.
    linha = (
        '"64904295";"0018";"51";"2";"";"08";"20161110";"01";"";"";"20050429";'
        '"4639701";"4637199";"AVENIDA";"MENINO MARCELO";"8551B";"LOTE 2; QUADRA F";'
        '"SERRARIA";"57046000";"AL";"2785";"11";"36491000";"31";"33880436";"82";'
        '"33118379";"CLAUDIO.GIGLIO@CAMIL.COM.BR";"";""\n'
    )
    zip_path = _zip_receita(tmp_path / "Estabelecimentos1.zip", linha.encode("latin1"))

    with abrir_convertido(zip_path, "estabelecimentos") as f:
        cabecalho, dados = f.read().decode("utf-8").split("\n", 1)

    assert cabecalho == (
        "cnpj_basico;cnpj_ordem;cnpj_dv;identificador_matriz_filial;nome_fantasia;"
        "situacao_cadastral;data_situacao_cadastral;motivo_situacao_cadastral;"
        "nome_cidade_exterior;id_pais;data_inicio_atividade;cnae_fiscal_principal;"
        "cnae_fiscal_secundaria;tipo_logradouro;logradouro;numero;complemento;bairro;"
        "cep;sigla_uf;id_municipio_rf;ddd_1;telefone_1;ddd_2;telefone_2;ddd_fax;fax;"
        "email;situacao_especial;data_situacao_especial"
    )
    assert dados == linha


@pytest.mark.parametrize(
    "tabela", ["cnaes", "motivos", "municipios", "naturezas", "paises", "qualificacoes"]
)
def test_dominios_tem_cabecalho_codigo_e_descricao(tmp_path, tabela):
    linha = '"0111399";"Cultivo de outros cereais não especificados anteriormente"\n'
    zip_path = _zip_receita(tmp_path / "Dominio.zip", linha.encode("latin1"))

    with abrir_convertido(zip_path, tabela) as f:
        assert f.read().decode("utf-8") == "codigo;descricao\n" + linha
