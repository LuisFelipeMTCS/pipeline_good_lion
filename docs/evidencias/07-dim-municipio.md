# Evidência do ticket 07: dim_municipio (Receita × IBGE)

## Casamento no Brasil inteiro (03/11/2026, local)

Mesmo SQL do job (`jobs/sql/gold/dim_municipio.sql`) sobre o domínio completo de municípios da Receita (2026-10), a lista completa da API do IBGE (5.571 municípios) e a UF de cada código tirada dos estabelecimentos da base completa de 2026-09.

| Medida | Valor |
|---|---|
| Municípios na `dim_municipio` | 5.571 (domínio da Receita tem 5.572: o `9707 EXTERIOR` fica de fora) |
| Sem par no IBGE | **0** |
| Códigos do IBGE distintos | 5.571 (casamento 1 para 1) |
| Corrigidos pela tabela manual | 22 (`jobs/referencias/municipios_correcoes.csv`) |

Por região: Centro-Oeste 468, Nordeste 1.794, Norte 450, Sudeste 1.668, Sul 1.191.

**Por que as 22 correções:** grafia (`PARATI` × Paraty, `ARES` × Arez), hífen e apóstrofo (`PINDARE MIRIM` × Pindaré-Mirim, `SANTANA DO LIVRAMENTO` × Sant'Ana do Livramento), preposição (`AMPARO DA SERRA` × Amparo do Serra) e 3 municípios renomeados que a Receita não atualizou (`BOA SAUDE` → Januário Cicco, `FORTALEZA DO TABOCAO` → Tabocão, `SAO VALERIO DA NATIVIDADE` → São Valério).

**Achados no caminho:**
- O domínio de municípios da Receita só tem código e nome, e há nomes repetidos entre estados (`BOM JESUS` existe em 5 UFs). A UF vem dos estabelecimentos.
- Dois códigos aparecem com mais de uma UF nos estabelecimentos (`0403`: PA 4.645 × SC 1; `6969`: SP 384.377 × PA 1). Vale a UF com mais estabelecimentos.
- Na API do IBGE, `Boa Esperança do Norte` (MT) vem com `microrregiao` nulo: a UF e a região saem de `regiao-imediata.regiao-intermediaria.UF`.
- A API responde em gzip mesmo sem `Accept-Encoding`; a `ingest_ibge` descompacta antes de gravar.

## Na AWS (amostra)

Pendente: `terraform apply`, `make deploy-jobs` e as execuções (ver o ticket).
