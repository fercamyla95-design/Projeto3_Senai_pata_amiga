-- =====================================================================================
--  ARQUIVO 5:  AS CINCO PERGUNTAS DE NEGOCIO
--  Case: Pata Amiga - rede de petshops de SC  |  PostgreSQL 16
-- =====================================================================================
--  Rode depois de: 04-fato.sql
--
--  Cada pergunta e UMA consulta: um SELECT com JOIN e GROUP BY. A subconsulta
--  aparece na P2 e na P5, e serve para trazer o total da rede como denominador.
--
--  ATENCAO AO POSTGRESQL: int / int TRUNCA. Nos percentuais e taxas use o fator
--  100.0 / 1000.0 (com ponto); e ROUND(x, casas) exige x numerico.
-- =====================================================================================

-- =====================================================================================
--  P1 - ONDE ESTA O GARGALO DO PROCESSO DE ENTREGA?
-- =====================================================================================
--  Media (AVG) dos quatro intervalos ja calculados na carga, agrupada por porte
--  de loja. AVG ignora NULL - por isso a etapa nao cumprida foi gravada como NULL.
--  dias_total_ate_entrega e o processo inteiro, nao um dos quatro intervalos.

SELECT
    dl.porte,
    AVG(fp.dias_integracao_separacao) AS media_integracao_separacao,
    AVG(fp.dias_separacao_nota) AS media_separacao_nota,
    AVG(fp.dias_nota_despacho) AS media_nota_despacho,
    AVG(fp.dias_despacho_entrega) AS media_despacho_entrega,
    AVG(fp.dias_total_ate_entrega) AS media_total_ate_entrega
FROM fato_pedido fp
JOIN dim_loja dl ON dl.sk_loja = fp.sk_loja
GROUP BY dl.porte
ORDER BY dl.porte;

-- =====================================================================================
--  P2 - QUAL CATEGORIA CONCENTRA O FATURAMENTO?
-- =====================================================================================
--  Esta e a pergunta que paga a dim_categoria. Agrupe pelo nome_categoria
--  PADRONIZADO (nunca pela grafia crua). O percentual do total usa uma
--  subconsulta com o faturamento da rede como denominador.

SELECT
    dc.nome_categoria,
    SUM(fp.vl_liquido) AS faturamento,
    ROUND(100.0 * SUM(fp.vl_liquido) / (SELECT SUM(vl_liquido) FROM fato_pedido), 2) AS percentual
FROM fato_pedido fp
JOIN dim_categoria dc ON dc.sk_categoria = fp.sk_categoria
GROUP BY dc.nome_categoria
ORDER BY faturamento DESC;

-- =====================================================================================
--  P3 - O DESCONTO FUNCIONA IGUAL EM TODO CANAL?
-- =====================================================================================
--  Aqui NAO ha JOIN: desconto e canal foram padronizados na carga e moram na
--  propria fato. Compare o TICKET MEDIO com e sem desconto DENTRO de cada canal.
--  Confira se o WhatsApp aparece - se nao, o CASE do arquivo 04 testou APP antes
--  de WHATS.

SELECT
    fp.canal_pedido,
    AVG(CASE WHEN fp.houve_desconto = 'Sim' THEN fp.vl_liquido END) AS ticket_medio_com_desconto,
    AVG(CASE WHEN fp.houve_desconto = 'Nao' THEN fp.vl_liquido END) AS ticket_medio_sem_desconto,
    SUM(fp.vl_liquido) AS faturamento_canal,
    ROUND(100.0 * SUM(fp.vl_liquido) / (SELECT SUM(vl_liquido) FROM fato_pedido), 2) AS percentual_faturamento
FROM fato_pedido fp
GROUP BY fp.canal_pedido
ORDER BY faturamento_canal DESC;

-- =====================================================================================
--  P4 - QUAL PRACA DE ATENDIMENTO CONCENTRA O FATURAMENTO?
-- =====================================================================================
--  Esta e a pergunta que paga a dim_praca e a ponte.
--  Caminho: fato_pedido -> dim_loja -> bridge_loja_praca -> dim_praca (a ponte
--  entra pelo cod_loja). O JOIN com a ponte DUPLICA a linha do pedido, uma por
--  praca - isso esta certo. Multiplique por b.fator_publico para o faturamento
--  nao ser contado duas vezes.

SELECT
    dp.nome_praca,
    dp.domicilios_com_pet,
    ROUND(SUM(fp.vl_liquido * b.fator_publico)::numeric, 2) AS faturamento_rateado,
    ROUND(SUM(fp.vl_liquido * b.fator_publico)::numeric / dp.domicilios_com_pet, 4)
        AS faturamento_por_domicilio
FROM fato_pedido fp
JOIN dim_loja dl ON dl.sk_loja = fp.sk_loja
JOIN bridge_loja_praca b ON b.cod_loja = dl.cod_loja
JOIN dim_praca dp ON dp.sk_praca = b.sk_praca
GROUP BY dp.nome_praca, dp.domicilios_com_pet
ORDER BY faturamento_rateado DESC;

-- =====================================================================================
--  P5 - ONDE ABRIR A PROXIMA LOJA, E O QUE OS DADOS NAO PERMITEM AFIRMAR?
-- =====================================================================================
--  (a) Ranqueie as lojas por itens POR MIL HABITANTES (numerador na fato,
--      denominador na dimensao), calculado AQUI na consulta - nunca gravado
--      pronto. Cruze com o tempo medio de entrega.
--  (b) Mostre o faturamento por faixa de franquia e explique por que ele NAO
--      responde "quanto veio de lojas que JA ERAM Ouro na data do pedido": o
--      cadastro so tem a foto de hoje.
--  (c) Meca o que ficou de fora: pedidos sem loja, entregas nao concluidas,
--      itens e valores em branco.
--A)
SELECT
    dl.nome_loja,
    dl.cidade,
    dl.populacao_cidade,
    SUM(fp.qt_itens) AS itens_vendidos,
    ROUND(SUM(fp.qt_itens)::numeric * 1000 / dl.populacao_cidade, 2) AS itens_por_mil_hab,
    ROUND(AVG(fp.dias_total_ate_entrega)::numeric, 2) AS tempo_medio_entrega_dias
FROM fato_pedido fp
JOIN dim_loja dl ON dl.sk_loja = fp.sk_loja
WHERE fp.sk_loja <> -1
GROUP BY dl.nome_loja, dl.cidade, dl.populacao_cidade
ORDER BY itens_por_mil_hab DESC;
-- B)
SELECT
    dl.faixa_franquia,
    COUNT(DISTINCT dl.sk_loja) AS qtd_lojas,
    ROUND(SUM(fp.vl_liquido)::numeric, 2) AS faturamento,
    ROUND(100.0 * SUM(fp.vl_liquido) / (SELECT SUM(vl_liquido) FROM fato_pedido), 2) AS percentual
FROM fato_pedido fp
JOIN dim_loja dl ON dl.sk_loja = fp.sk_loja
WHERE fp.sk_loja <> -1
GROUP BY dl.faixa_franquia
ORDER BY faturamento DESC;
--C)
SELECT 'Pedidos sem loja identificada' AS o_que_ficou_de_fora, COUNT(*) AS quantidade
FROM fato_pedido WHERE sk_loja = -1
UNION ALL
SELECT 'Entregas ainda nao concluidas', COUNT(*)
FROM fato_pedido WHERE sk_tempo_entrega = -1
UNION ALL
SELECT 'Pedidos sem qt_itens (em branco na origem)', COUNT(*)
FROM fato_pedido WHERE qt_itens IS NULL
UNION ALL
SELECT 'Pedidos sem vl_liquido (em branco na origem)', COUNT(*)
FROM fato_pedido WHERE vl_liquido IS NULL;