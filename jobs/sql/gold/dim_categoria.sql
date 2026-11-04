-- Nó SQL Query do Glue Studio (job gold_dimensoes). Tabela fixa de 4 linhas; não lê a entrada.
SELECT * FROM VALUES
    ('MEI', 'MEI', 1),
    ('ME', 'ME', 2),
    ('EPP', 'EPP', 3),
    ('DEMAIS', 'Demais', 4)
AS categorias (id_categoria, nome, ordem)
