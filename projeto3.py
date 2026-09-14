import psycopg2
import os 
import pandas as pd 
import unicodedata

#Conexão 1: no banco "postgres", criar o dw_pata_amiga
conn_admin = psycopg2.connect(
    dbname="postgres", user="postgres", password="MySQL95", host="localhost", port="5432"
)
conn_admin.autocommit = True #Create database obrigatório
with conn_admin.cursor() as cur:
    cur.execute("DROP DATABASE IF EXISTS dw_pata_amiga;")
    cur.execute("CREATE DATABASE dw_pata_amiga;")
conn_admin.close()

#conexão 2: dentro do banco novo
conn = psycopg2.connect(
    dbname="dw_pata_amiga", user="postgres", password="MySQL95", host="localhost", port="5432"
)
conn.autocommit = True

#OS
pasta_script = os.path.dirname(os.path.abspath(__file__))
caminho_sql = os.path.join(pasta_script, "01-carga-staging.sql")

with open(caminho_sql, "r", encoding="utf-8") as f:
    linhas = f.readlines()
linhas_filtradas = []
for linha in linhas:
    linha_limpa = linha.lstrip().upper() #Tira espaços do inicio e deixa maiúsculo
    if linha_limpa.startswith("\\C") or linha_limpa.startswith("DROP DATABASE") or linha_limpa.startswith("CREATE DATABASE"):
         continue; #Pule essa linha, não adiciona na lista final
    linhas_filtradas.append(linha) #Guardar a linha original

sql_staging = "".join(linhas_filtradas)
with conn.cursor() as cur:
    cur.execute(sql_staging)

print("Staging carregada com sucesso!")

#Mostrar colunas selec
df_pedido = pd.read_sql('SELECT*FROM stg_pedido', conn)

print(df_pedido.columns.tolist()) 
print(df_pedido.shape) 

qtd_grafias_categoria = df_pedido["CategoriaProduto"].unique()

print("Grafias distintas de categoria:", qtd_grafias_categoria)

#Grafias distintas de loja
qtd_grafias_loja = df_pedido["Loja-Nome"].nunique()

print("Grafias distintas de loja:", qtd_grafias_loja)

#Pedidos sem "Cos Loja" preenchido
sem_cod_loja = (df_pedido["Cod Loja"] == '').sum() + df_pedido["Cod Loja"].isna().sum()

print("Pedidos sem Cod Loja:", sem_cod_loja)

#Marco de processo m branco (4 marco da entrega)
marcos = ["Dt Separacao Estoque", "DtNotaFiscal", "Dt_Despacho_Transportadora","DtEntregaCliente"]
for marco in marcos:
    qtd_branco = (df_pedido[marco] == '').sum() + df_pedido[marco].isna().sum()
    print(f"{marco}: {qtd_branco} em branco")

#Pedidos sem "Loja-Nome" preenchidos
sem_nome_loja = (df_pedido["Loja-Nome"] == '').sum() + df_pedido["Loja-Nome"].isna().sum()

print("Pedidos sem Loja-Nome:", sem_nome_loja)

#Part2
def normalizar (texto):
    if pd.isna(texto):
        return ""

    texto = str(texto).upper()
    texto =  unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    return texto

#test
print(normalizar("Racao Medicamentosa"))

def classificar_categoria(valor_bruto):
    v = normalizar(valor_bruto)
    if ("MED") in v:
        return ("Medicamentos", "Saude e Higiene")
    if ("PETISC") in v:
        return ("Petisco", "Alimentacao")
    if ("RAC") in v:
        return ("Racao", "Alimentacao")
    if ("HIG") in v:
        return ("Higiene", "Saude e Higiene")
    if ("BRINQ") in v:
        return ("Brinquedos", "Bem-estar")
    if ("ACESS") in v:
        return ("Acessorios", "Bem-estar")
    if ("SERV") in v:
        return ("Servicos", "Bem-estar")
    else:
        return("Nao Informado", "Nao Informado")


df_pedido["nome_categoria_teste"] = df_pedido["CategoriaProduto"].apply(classificar_categoria)
print(df_pedido["nome_categoria_teste"].apply(lambda x: x[0]).value_counts())

categorias_nao_identificadas = df_pedido[df_pedido["nome_categoria_teste"].apply(lambda x: x[0]) == "Nao Informado"]["CategoriaProduto"].unique()
print(categorias_nao_identificadas)

#Confirmar nomes colunas tabela stg_loja_praca 
df_loja_praca = pd.read_sql('SELECT * FROM stg_loja_praca', conn)
print(df_loja_praca.columns.tolist())

#Verificar formato PercentualPublico
print(df_loja_praca["PercentualPublico"].unique()[:10])

# Rodar o 02-dimensoes-prontas.sql
caminho_sql_02 = os.path.join(pasta_script, "02-dimensoes-prontas.sql")

with open(caminho_sql_02, "r", encoding="utf-8") as f:
    sql_dim_prontas = f.read()

with conn.cursor() as cur:
    cur.execute(sql_dim_prontas)

print("Dimensões prontas (02) carregadas com sucesso!")

# Rodar o 03-dimensoes.sql
caminho_sql_03 = os.path.join(pasta_script, "03-dimensoes.sql")

with open(caminho_sql_03, "r", encoding="utf-8") as f:
    sql_dimensoes = f.read()

with conn.cursor() as cur:
    cur.execute(sql_dimensoes)

print("Dimensões (03) carregadas com sucesso!")

#Verif .
df_categoria = pd.read_sql('SELECT COUNT(*) FROM dim_categoria', conn)
df_praca = pd.read_sql('SELECT COUNT(*) FROM dim_praca', conn)
df_bridge = pd.read_sql('SELECT COUNT(*) FROM bridge_loja_praca', conn)

print("dim_categoria:", df_categoria.iloc[0,0])
print("dim_praca:", df_praca.iloc[0,0])
print("bridge_loja_praca:", df_bridge.iloc[0,0])

#Checagem do fator de rastreio
df_fator = pd.read_sql(
    'SELECT cod_loja, SUM(fator_publico) AS soma FROM bridge_loja_praca GROUP BY cod_loja',
    conn
)

print(df_fator[df_fator["soma"] != 1.00])  # deve vir vazio - se aparecer algo, tem problema

#Rodar o 04-fato.sql Teste1
query_teste_loja = '''
SELECT
    sp."NumeroPedido",
    COALESCE(dl.sk_loja, -1) AS sk_loja_encontrada
FROM stg_pedido sp
LEFT JOIN dim_loja dl
    ON dl.chave_loja =
        CASE
            WHEN UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC')) = 'PATA AMIGA BLUMENAL CENTRO' THEN 'PATA AMIGA BLUMENAU CENTRO'
            WHEN UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC')) = 'PATA AMIGA FLORIPA NORTE' THEN 'PATA AMIGA FLORIANOPOLIS NORTE'
            WHEN UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC')) = 'PATA AMIGA JGUA DO SUL' THEN 'PATA AMIGA JARAGUA DO SUL'
            ELSE UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC'))
        END;
'''

df_teste = pd.read_sql(query_teste_loja, conn)

print("Total de linhas:", len(df_teste))
print("Pedidos com sk_loja = -1:", (df_teste["sk_loja_encontrada"] == -1).sum())

#Teste2
df_teste2 = pd.read_sql('''
SELECT sp."NumeroPedido", sp."Loja-Nome",
       COALESCE(dl.sk_loja, -1) AS sk_loja_encontrada
FROM stg_pedido sp
LEFT JOIN dim_loja dl
    ON dl.chave_loja =
        CASE
            WHEN UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC')) = 'PATA AMIGA BLUMENAL CENTRO' THEN 'PATA AMIGA BLUMENAU CENTRO'
            WHEN UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC')) = 'PATA AMIGA FLORIPA NORTE' THEN 'PATA AMIGA FLORIANOPOLIS NORTE'
            WHEN UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC')) = 'PATA AMIGA JGUA DO SUL' THEN 'PATA AMIGA JARAGUA DO SUL'
            ELSE UPPER(TRANSLATE(TRIM(REPLACE(REPLACE(sp."Loja-Nome", '/SC', ''), '  ', ' ')), 'áàâãäÁÀÂÃÄéèêëÉÈÊËíìîïÍÌÎÏóòôõöÓÒÔÕÖúùûüÚÙÛÜçÇ', 'aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcC'))
        END
''', conn)

suspeitas = df_teste2[(df_teste2["sk_loja_encontrada"] == -1) & (df_teste2["Loja-Nome"].notna()) & (df_teste2["Loja-Nome"] != '')]

print(suspeitas["Loja-Nome"].unique()[:15])

#Query teste categoria
query_teste_categoria = '''
SELECT
    sp."NumeroPedido",
    COALESCE(dc.sk_categoria, -1) AS sk_categoria_encontrada
FROM stg_pedido sp
LEFT JOIN dim_categoria dc
    ON dc.categoria_origem = sp."CategoriaProduto";
'''

df_teste_cat = pd.read_sql (query_teste_categoria, conn)

print("Total de linhas:", len (df_teste_cat))
print("Pedidos com sk_categoria = -1", (df_teste_cat["sk_categoria_encontrada"]== -1).sum())

#Query teste tempo
query_teste_tempo = '''
SELECT
    sp."NumeroPedido",
    TO_CHAR(TO_TIMESTAMP(sp."DtHoraPedido", 'MM/DD/YYYY HH12:MI AM'), 'YYYYMMDD')::int AS sk_tempo_pedido,
    CASE
    WHEN sp."DtEntregaCliente" = '' THEN -1
    ELSE TO_CHAR(sp."DtEntregaCliente"::date, 'YYYYMMDD')::int
END AS sk_tempo_entrega
FROM stg_pedido sp;
'''
df_teste_tempo = pd.read_sql(query_teste_tempo, conn)

print(df_teste_tempo.head())
print("Entregas com sk_tempo_entrega = -1:", (df_teste_tempo["sk_tempo_entrega"] == -1).sum())

#Houve desconto, Canal pedido
query_teste_canal_desc = '''
SELECT
CASE
    WHEN TRIM(UPPER(sp."HouveDesconto")) IN ('S', 'SIM', '1', 'X', 'TRUE', 'V') THEN 'Sim'
    WHEN TRIM(UPPER(sp."HouveDesconto")) IN ('N', 'NAO', '0', 'FALSE', 'F') THEN 'Nao'
    ELSE 'Nao Informado'
END AS houve_desconto,

CASE
    WHEN UPPER(sp."CanalPedido") LIKE '%WHATS%' THEN 'WhatsApp'
    WHEN UPPER(sp."CanalPedido") LIKE '%APP%' THEN 'App'
    WHEN UPPER(sp."CanalPedido") LIKE '%SITE%' THEN 'Site'
    WHEN UPPER(sp."CanalPedido") LIKE '%LOJA%' THEN 'Loja Fisica'
    WHEN UPPER(sp."CanalPedido") LIKE '%TEL%' THEN 'Telefone'
    ELSE 'Nao Informado'
END AS canal_pedido

FROM stg_pedido sp;
'''
df_teste_cd = pd.read_sql(query_teste_canal_desc, conn)

print(df_teste_cd["houve_desconto"].value_counts())
print(df_teste_cd["canal_pedido"].value_counts())

#Query teste valor
query_teste_valor = '''
SELECT
    sp."NumeroPedido",

    CASE
        WHEN TRIM(REPLACE(sp."ValorLiquidoPedido(R$)", 'R$', '')) IN ('', '-') THEN NULL

        WHEN sp."ValorLiquidoPedido(R$)" LIKE '%,%'
            THEN CAST(
                REPLACE(
                    REPLACE(
                        REPLACE(
                            REPLACE(sp."ValorLiquidoPedido(R$)", 'R$', ''),
                            ' ', ''
                        ),
                        '.', ''
                    ),
                    ',', '.'
                )
                AS DECIMAL(15,2)
            )

        ELSE CAST(
            REPLACE(
                REPLACE(sp."ValorLiquidoPedido(R$)", 'R$', ''),
                ' ', ''
            )
            AS DECIMAL(15,2)
        )
    END AS vl_liquido

FROM stg_pedido sp;
'''

df_teste_valor = pd.read_sql(query_teste_valor, conn)

print("Total de linhas:", len(df_teste_valor))
print("Valores nulos:", df_teste_valor["vl_liquido"].isna().sum())
print("Soma total:", df_teste_valor["vl_liquido"].sum())

#Marco início/fim
query_teste_dias = '''
SELECT
    sp."NumeroPedido",
    CASE
        WHEN sp."Dt Separacao Estoque" = '' THEN NULL
        ELSE sp."Dt Separacao Estoque"::date - TO_TIMESTAMP(sp."DtHoraIntegracaoERP", 'MM/DD/YYYY HH12:MI AM')::date
    END AS dias_integracao_separacao,
    CASE
        WHEN sp."DtNotaFiscal" = '' THEN NULL
        ELSE sp."DtNotaFiscal"::date - sp."Dt Separacao Estoque"::date
    END AS dias_separacao_nota,
    CASE
        WHEN sp."Dt_Despacho_Transportadora" = '' THEN NULL
        ELSE sp."Dt_Despacho_Transportadora"::date - sp."DtNotaFiscal"::date
    END AS dias_nota_despacho,
    CASE
        WHEN sp."DtEntregaCliente" = '' THEN NULL
        ELSE sp."DtEntregaCliente"::date - sp."Dt_Despacho_Transportadora"::date
    END AS dias_despacho_entrega,
    CASE
        WHEN sp."DtEntregaCliente" = '' THEN NULL
        ELSE sp."DtEntregaCliente"::date - TO_TIMESTAMP(sp."DtHoraIntegracaoERP", 'MM/DD/YYYY HH12:MI AM')::date
    END AS dias_total_ate_entrega
FROM stg_pedido sp;
'''
df_teste_dias = pd.read_sql(query_teste_dias, conn)

print("Total de linhas:", len(df_teste_dias))
for col in ["dias_integracao_separacao", "dias_separacao_nota", "dias_nota_despacho", "dias_despacho_entrega", "dias_total_ate_entrega"]:
    print(f"{col}: {df_teste_dias[col].isna().sum()} nulos")

#Query teste final
query_teste_final = '''
SELECT
    sp."NumeroPedido",
    TO_TIMESTAMP(sp."DtHoraPedido", 'MM/DD/YYYY HH12:MI AM') AS dt_pedido,
    CASE
        WHEN TRIM(sp."QTD.Itens") IN ('', '-') THEN NULL
        ELSE CAST(sp."QTD.Itens" AS INTEGER)
    END AS qt_itens
FROM stg_pedido sp;
'''
df_teste_final = pd.read_sql(query_teste_final, conn)

print(df_teste_final.head())
print("qt_itens nulos:", df_teste_final["qt_itens"].isna().sum())

#Confere 04-fato.sql-leitura direta
caminho_sql_04 = os.path.join(pasta_script, "04-fato.sql")
with open(caminho_sql_04, "r", encoding="utf-8") as f:
    sql_fato = f.read()
with conn.cursor() as cur:
    cur.execute(sql_fato)

print("Fato (04) carregada com sucesso!")

#Teste final.2
df_fato_count = pd.read_sql('SELECT COUNT(*) FROM fato_pedido', conn)

print("fato_pedido:", df_fato_count.iloc[0,0])

df_fk_nula = pd.read_sql('''
    SELECT COUNT(*) FROM fato_pedido
    WHERE sk_tempo_pedido IS NULL OR sk_tempo_entrega IS NULL OR sk_loja IS NULL OR sk_categoria IS NULL
''', conn)

print("FKs nulas:", df_fk_nula.iloc[0,0])

#05-perguntas.sql
# P1
query_p1 = '''
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
'''
df_p1 = pd.read_sql(query_p1, conn)

print(df_p1)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

print(df_p1)

#P2
query_p2_geral = '''
SELECT
    dc.nome_categoria,
    SUM(fp.vl_liquido) AS faturamento,
    ROUND(100.0 * SUM(fp.vl_liquido) / (SELECT SUM(vl_liquido) FROM fato_pedido), 2) AS percentual
FROM fato_pedido fp
JOIN dim_categoria dc ON dc.sk_categoria = fp.sk_categoria
GROUP BY dc.nome_categoria
ORDER BY faturamento DESC;
'''
df_p2_geral = pd.read_sql(query_p2_geral, conn)

print(df_p2_geral)

query_p2_porte = '''
SELECT
    dl.porte,
    dc.nome_categoria,
    SUM(fp.vl_liquido) AS faturamento
FROM fato_pedido fp
JOIN dim_categoria dc ON dc.sk_categoria = fp.sk_categoria
JOIN dim_loja dl ON dl.sk_loja = fp.sk_loja
GROUP BY dl.porte, dc.nome_categoria
ORDER BY dl.porte, faturamento DESC;
'''
df_p2_porte = pd.read_sql(query_p2_porte, conn)

print(df_p2_porte)

#P3
query_p3 = '''
SELECT
    fp.canal_pedido,
    AVG(CASE WHEN fp.houve_desconto = 'Sim' THEN fp.vl_liquido END) AS ticket_medio_com_desconto,
    AVG(CASE WHEN fp.houve_desconto = 'Nao' THEN fp.vl_liquido END) AS ticket_medio_sem_desconto,
    SUM(fp.vl_liquido) AS faturamento_canal
FROM fato_pedido fp
GROUP BY fp.canal_pedido
ORDER BY faturamento_canal DESC;
'''
df_p3 = pd.read_sql(query_p3, conn)

print(df_p3)

query_p3_completo = '''
SELECT
    fp.canal_pedido,
    AVG(CASE WHEN fp.houve_desconto = 'Sim' THEN fp.vl_liquido END) AS ticket_medio_com_desconto,
    AVG(CASE WHEN fp.houve_desconto = 'Nao' THEN fp.vl_liquido END) AS ticket_medio_sem_desconto,
    SUM(fp.vl_liquido) AS faturamento_canal,
    ROUND(100.0 * SUM(fp.vl_liquido) / (SELECT SUM(vl_liquido) FROM fato_pedido), 2) AS percentual_faturamento
FROM fato_pedido fp
GROUP BY fp.canal_pedido
ORDER BY faturamento_canal DESC;
'''
df_p3_completo = pd.read_sql(query_p3_completo, conn)

print(df_p3_completo)

#P4
query_p4_completo = '''
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
'''
df_p4_completo = pd.read_sql(query_p4_completo, conn)

print(df_p4_completo)

#P5 - A)
query_p5_completo = '''
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
'''
df_p5_completo = pd.read_sql(query_p5_completo, conn)

print(df_p5_completo)

#B)
query_p5_completo = '''
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
'''
df_p5_completo = pd.read_sql(query_p5_completo, conn)
print(df_p5_completo)

#C)
query_p5_completo = '''
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
'''
df_p5_completo = pd.read_sql(query_p5_completo, conn)
print(df_p5_completo)
