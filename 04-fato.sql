-- =====================================================================================
--  ARQUIVO 4:  A TABELA FATO
--  Case: Pata Amiga - rede de petshops de SC  |  PostgreSQL 16
-- =====================================================================================
--  Rode depois de: 03-dimensoes.sql
--
--  UMA fato, UM unico INSERT ... SELECT. A tabela ja existe, vazia (arquivo 02).
--  4.044 linhas = 4.044 pedidos.
--
--  Regra geral: a limpeza dos dados fica nas dimensoes; a fato apenas procura a
--  linha correta (por JOIN). Nenhuma FK fica nula: quando o dado falta, ela
--  aponta para a linha -1 (CASE WHEN ... IS NULL THEN -1).
--
--  Sugestao: comece pelo esqueleto (numero_pedido + as duas FKs de tempo +
--  FROM), rode e confira 4.044 linhas; depois acrescente as colunas aos poucos.
-- =====================================================================================

-- >>> ESCREVA AQUI o INSERT INTO fato_pedido (...) SELECT ... FROM stg_pedido ...
INSERT INTO fato_pedido (
    numero_pedido, sk_tempo_pedido, sk_tempo_entrega, sk_loja, sk_categoria,
    houve_desconto, canal_pedido, dt_pedido, qt_itens, vl_liquido,
    dias_integracao_separacao, dias_separacao_nota, dias_nota_despacho,
    dias_despacho_entrega, dias_total_ate_entrega
)
SELECT
    sp."NumeroPedido",

    TO_CHAR(TO_TIMESTAMP(sp."DtHoraPedido", 'MM/DD/YYYY HH12:MI AM'), 'YYYYMMDD')::int,

    CASE
        WHEN sp."DtEntregaCliente" = '' THEN -1
        ELSE TO_CHAR(sp."DtEntregaCliente"::date, 'YYYYMMDD')::int
    END,

    COALESCE(dl.sk_loja, -1),

    COALESCE(dc.sk_categoria, -1),

    CASE
        WHEN TRIM(UPPER(sp."HouveDesconto")) IN ('S', 'SIM', '1', 'X', 'TRUE', 'V') THEN 'Sim'
        WHEN TRIM(UPPER(sp."HouveDesconto")) IN ('N', 'NAO', '0', 'FALSE', 'F') THEN 'Nao'
        ELSE 'Nao Informado'
    END,

    CASE
        WHEN UPPER(sp."CanalPedido") LIKE '%WHATS%' THEN 'WhatsApp'
        WHEN UPPER(sp."CanalPedido") LIKE '%APP%' THEN 'App'
        WHEN UPPER(sp."CanalPedido") LIKE '%SITE%' THEN 'Site'
        WHEN UPPER(sp."CanalPedido") LIKE '%LOJA%' THEN 'Loja Fisica'
        WHEN UPPER(sp."CanalPedido") LIKE '%TEL%' THEN 'Telefone'
        ELSE 'Nao Informado'
    END,

    TO_TIMESTAMP(sp."DtHoraPedido", 'MM/DD/YYYY HH12:MI AM'),

    CASE
        WHEN TRIM(sp."QTD.Itens") IN ('', '-') THEN NULL
        ELSE CAST(sp."QTD.Itens" AS INTEGER)
    END,

    CASE
        WHEN TRIM(REPLACE(sp."ValorLiquidoPedido(R$)",'R$','')) IN ('','-') THEN NULL
        WHEN sp."ValorLiquidoPedido(R$)" LIKE '%,%'
            THEN CAST(REPLACE(REPLACE(REPLACE(REPLACE(sp."ValorLiquidoPedido(R$)",'R$',''),' ',''),'.',''),',','.')
                 AS DECIMAL(15,2))
        ELSE CAST(REPLACE(REPLACE(sp."ValorLiquidoPedido(R$)",'R$',''),' ','') AS DECIMAL(15,2))
    END,

    CASE
        WHEN sp."Dt Separacao Estoque" = '' THEN NULL
        ELSE sp."Dt Separacao Estoque"::date - TO_TIMESTAMP(sp."DtHoraIntegracaoERP", 'MM/DD/YYYY HH12:MI AM')::date
    END,

    CASE
        WHEN sp."DtNotaFiscal" = '' THEN NULL
        ELSE sp."DtNotaFiscal"::date - sp."Dt Separacao Estoque"::date
    END,

    CASE
        WHEN sp."Dt_Despacho_Transportadora" = '' THEN NULL
        ELSE sp."Dt_Despacho_Transportadora"::date - sp."DtNotaFiscal"::date
    END,

    CASE
        WHEN sp."DtEntregaCliente" = '' THEN NULL
        ELSE sp."DtEntregaCliente"::date - sp."Dt_Despacho_Transportadora"::date
    END,

    CASE
        WHEN sp."DtEntregaCliente" = '' THEN NULL
        ELSE sp."DtEntregaCliente"::date - TO_TIMESTAMP(sp."DtHoraIntegracaoERP", 'MM/DD/YYYY HH12:MI AM')::date
    END

FROM stg_pedido sp
LEFT JOIN dim_loja dl
    ON dl.chave_loja =
        CASE
            WHEN UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC')) = 'PATA AMIGA BLUMENAL CENTRO' THEN 'PATA AMIGA BLUMENAU CENTRO'
            WHEN UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC')) = 'PATA AMIGA FLORIPA NORTE' THEN 'PATA AMIGA FLORIANOPOLIS NORTE'
            WHEN UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC')) = 'PATA AMIGA JGUA DO SUL' THEN 'PATA AMIGA JARAGUA DO SUL'
            ELSE UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC'))
        END
LEFT JOIN dim_categoria dc
    ON dc.categoria_origem = sp."CategoriaProduto";
--
--  Roteiro das colunas:
--
--  * sk_tempo_pedido / sk_tempo_entrega: a chave e a data no formato AAAAMMDD.
--    Monte com TO_CHAR(<a data>, 'YYYYMMDD')::int. A data do PEDIDO vem no
--    formato americano com AM/PM: a mascara e 'MM/DD/YYYY HH12:MI AM'
--    (TO_TIMESTAMP). Usar 'DD/MM/YYYY' faz o PostgreSQL LANCAR ERRO nas datas
--    com mes maior que 12. Os marcos da entrega ja vem em ISO: ::date basta.
--    Entrega em branco -> -1.
--
--  * sk_loja, sk_categoria: vem de LEFT JOIN; se nao achou par, -1.
--
--  * LOJA (LEFT JOIN dim_loja): limpe o nome no ON. REPLACE tira '/SC' e o espaco
--    duplo; um CASE resolve 3 grafias (digitacao, apelido, abreviacao). O
--    PostgreSQL compara byte a byte, entao normalize acento e caixa com
--    UPPER(TRANSLATE(..., 'ÁÀÂÃÉÊÍÓÔÕÚÜÇáàâãéêíóôõúüç',
--    'AAAAEEIOOOUUCaaaaeeiooouuc')). A chave_loja da dim_loja ja veio em caixa
--    alta e sem acento.
--
--  * CATEGORIA (LEFT JOIN dim_categoria): uma linha so -
--    ON dc.categoria_origem = p."CategoriaProduto".
--
--  * houve_desconto e canal_pedido: padronize com CASE e grave na PROPRIA fato
--    (nao ha dimensao para eles). O de-para completo dos dois campos esta no
--    ENUNCIADO, na secao 7 ("Como padronizar o desconto e o canal").
--    A ordem importa: 'WHATSAPP' contem 'APP',
--    entao teste WHATS antes de APP. No desconto, tire o acento com TRANSLATE
--    antes do UPPER.
--
--  * dinheiro e itens: '' e '-' viram NULL; tire "R$" e trate o milhar.
--
--  * os lags em dias: em PostgreSQL, data - data ja da o numero de dias. Etapa
--    nao cumprida grava NULL, nunca 0. Use ::date em volta da integracao.

-- =====================================================================================
--  Confira o resultado com o 00-conferencia.sql (bloco "DEPOIS DO 04").
-- =====================================================================================
