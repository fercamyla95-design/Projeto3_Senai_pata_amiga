import psycopg2
import os 
import unicodedata

def normalizar (texto):
    texto= texto.upper()
    texto = unicodedata.normalize('NFKD', texto.encode('ASCII', 'ignore').decode('ASCII'))
    return texto

#test
print(normalizar("Ração Medicamentosa"))

def classificar_categoria(valor_bruto):
    v = normalizar(valor_bruto)
    if "MED" in v:
        return ("Medicamentos", "Saude e Higiene")
    if "PETISC" in v:
        return ("Petisco", "Alimentacao")
    if "RA" in v:
        return ("Racao", "Alimentacao")
    if ("HIG") in v:
        return ("Higiene", "Saude e Higiene")
    if ("Brinq") in v:
        return ("Brinquedos", "Bem-estar")
    if ("ACESS") in v:
        return ("Acessorios", "Bem-estar")
    if ("SERV") in v:
        return ("Servicos", "Bem-estar")
    else:
        return("Nao Informado", "Nao Informado")

df_pedido["nome_categoria_teste"] = df_pedido["CategoriaProduto"].apply(classificar_categoria)

print(df_pedido["nome_categoria_teste"].apply(lambda x: x[0]).value_counts())

