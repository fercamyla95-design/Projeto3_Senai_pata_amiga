-- =====================================================================================
--  ARQUIVO 3:  AS DIMENSOES QUE VOCE PREENCHE
--  Case: Pata Amiga - rede de petshops de SC  |  PostgreSQL 16
-- =====================================================================================
--  Rode depois de: 01-carga-staging.sql  e  02-dimensoes-prontas.sql
--
--  As tabelas ja existem, vazias, criadas no arquivo 02. Aqui voce as PREENCHE.
--  Sao duas dimensoes e uma ponte:
--      dim_categoria       o de-para das grafias
--      dim_praca           uma linha por praca de atendimento
--      bridge_loja_praca   a ligacao N:N entre loja e praca, com o rateio
--
--  Regras para as duas dimensoes:
--    * PK = surrogate key inteira (ja definida no 02 como IDENTITY)
--    * a chave natural (a grafia, o cod da praca) fica como atributo
--    * sempre a linha -1 = "Nao Informado", inserida ANTES do INSERT ... SELECT
--    * as tabelas stg_ NAO se alteram
--
--  Comandos: INSERT ... VALUES, INSERT ... SELECT, SELECT DISTINCT, JOIN,
--  GROUP BY, CASE WHEN, REPLACE, UPPER, TRIM, TRANSLATE, CAST, MAX
-- =====================================================================================

-- =====================================================================================
--  DIM_CATEGORIA        grao: UMA GRAFIA DA ORIGEM
-- =====================================================================================
--  Guarde a grafia CRUA em categoria_origem e a versao padronizada em
--  nome_categoria (uma linha por grafia; varias grafias podem apontar para o
--  mesmo nome). Depois a fato acha a linha por categoria_origem.
--  Insira primeiro a linha -1. No INSERT ... SELECT DISTINCT, um CASE traduz as
--  grafias em 7 categorias.
--  ATENCAO: a ordem do CASE importa - "Racao Medicamentosa" e Medicamento, entao
--  teste MED antes de RA. Compare em UPPER e use trechos SEM acento.

-- >>> ESCREVA AQUI: a linha -1 e o INSERT ... SELECT da dim_categoria
INSERT INTO dim_categoria (sk_categoria, categoria_origem, nome_categoria, grupo_categoria)
VALUES (-1, 'Nao Informado', 'Nao Informado', 'Nao Informado');

INSERT INTO dim_categoria (categoria_origem, nome_categoria, grupo_categoria)
SELECT DISTINCT
    "CategoriaProduto",
    CASE
        WHEN UPPER (TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%MED%' THEN 'Medicamento'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%PETISC%' THEN 'Petisco'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%RA%' THEN 'Racao'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%HIG%' THEN 'Higiene'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%BRINQ%' THEN 'Brinquedo'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%ACESS%' THEN 'Acessorio'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%SERV%' THEN 'Servico'
        ELSE 'Nao Informado'
    END,
    CASE
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%MED%' THEN 'Saude e Higiene'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%PETISC%' THEN 'Alimentacao'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%RA%' THEN 'Alimentacao'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%HIG%' THEN 'Saude e Higiene'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%BRINQ%' THEN 'Bem-estar'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%ACESS%' THEN 'Bem-estar'
        WHEN UPPER(TRANSLATE("CategoriaProduto", 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC')) LIKE '%SERV%' THEN 'Bem-estar'
        ELSE 'Nao Informado'
    END
FROM stg_pedido;

-- =====================================================================================
--  DIM_PRACA  +  BRIDGE_LOJA_PRACA
-- =====================================================================================
--  A stg_loja_praca tem 48 linhas: a mesma loja aparece uma vez por praca. Um
--  GROUP BY por CodPraca colapsa em 12 pracas. Colunas fora do GROUP BY precisam
--  de agregacao (MAX serve). domicilios_com_pet vem como '148.000': o ponto e
--  milhar, tire-o antes do CAST.

-- >>> ESCREVA AQUI: a linha -1 e o INSERT ... SELECT da dim_praca
INSERT INTO dim_praca (sk_praca, cod_praca, nome_praca, regional,domicilios_com_pet)
VALUES (-1, 'N/I', 'Nao Informado', 'Nao Informado', NULL);

INSERT INTO dim_praca (cod_praca, nome_praca, regional, domicilios_com_pet)
SELECT 
    "CodPraca",
    MAX("NomePraca"),
    MAX("Regional"),
    MAX( CAST( REPLACE("DomiciliosComPet", '.', '') AS INTEGER ) )
From stg_loja_praca
GROUP  BY "CodPraca";

-- -------------------------------------------------------------------------------------
--  A TABELA PONTE
-- -------------------------------------------------------------------------------------
--  Uma loja entrega em mais de uma praca (N:N) - por isso a ligacao vive numa
--  tabela propria, com o FATOR DE RATEIO dentro (os fatores de uma loja somam
--  1,00). A ponte usa o COD DA LOJA, nao a sk_loja.

-- >>> ESCREVA AQUI: o INSERT ... SELECT da bridge_loja_praca
INSERT INTO bridge_loja_praca (cod_loja, sk_praca, fator_publico)
SELECT 
    slp."CodLoja",
    dp.sk_praca,
    CAST(slp."PercentualPublico" AS DECIMAL(6,4))
FROM stg_loja_praca slp
JOIN dim_praca dp ON dp.cod_praca = slp."CodPraca";

-- =====================================================================================
--  Confira o resultado com o 00-conferencia.sql (bloco "DEPOIS DO 03").
-- =====================================================================================
