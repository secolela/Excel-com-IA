# -*- coding: utf-8 -*-
"""
Script de sanitizacao - Base de fraude em cartao de credito
-------------------------------------------------------------
Le a planilha original, cria colunas novas de "tratamento/traducao"
logo ao lado de cada coluna original que precisa ser sanitizada,
SEM excluir nem alterar nenhuma coluna/linha original.

Regra geral: qualquer valor que nao se encaixe nas regras definidas
abaixo e marcado como "Invalido" (nunca e deduzido).
"""

import pandas as pd

# =========================================================
# 1. CONFIGURACAO - AJUSTE AQUI PARA RODAR NA BASE COMPLETA
# =========================================================
ARQUIVO_ENTRADA = r"C:\Users\sergi\Downloads\Projeto DIO\credit_card_fraud_2026.csv"
ARQUIVO_SAIDA   = r"C:\Users\sergi\Downloads\Projeto DIO\credit_card_fraud_2026_sanitizado.xlsx"
SEPARADOR_CSV   = ","   # a amostra recebida usa ";" como separador

# =========================================================
# 2. DICIONARIOS DE TRADUCAO / CLASSIFICACAO
# =========================================================

# Traducao de merchant_category (PT-BR). Qualquer categoria que
# aparecer na base completa e NAO estiver neste dicionario sera
# marcada como "Invalido" (nao adivinhamos traducao).
MAPA_MERCHANT_CATEGORY = {
    "Electronics": "Eletronicos",
    "Fuel": "Combustivel",
    "Gaming": "Jogos",
    "Gift Cards": "Cartoes-Presente",
    "Groceries": "Supermercado",
    "Online Retail": "Varejo Online",
    "Restaurants": "Restaurantes",
    "Streaming": "Streaming",
    "Travel": "Viagem",
    "Utilities": "Utilidades (Contas/Servicos Publicos)",
}

# Bandeiras que devem ser mantidas como estao; qualquer outra vira "Demais Cartoes"
BANDEIRAS_PRINCIPAIS = {"Mastercard", "Visa", "Amex"}

# Traducao de channel: apenas Contactless muda, o resto permanece igual
MAPA_CHANNEL = {
    "Contactless": "Aproximacao",
}

# Traducao de dia da semana (0 = Domingo, conforme confirmado pelo usuario)
MAPA_DIA_SEMANA = {
    0: "Domingo",
    1: "Segunda-feira",
    2: "Terca-feira",
    3: "Quarta-feira",
    4: "Quinta-feira",
    5: "Sexta-feira",
    6: "Sabado",
}


# =========================================================
# 3. FUNCOES DE SANITIZACAO
# =========================================================

def to_bool(valor):
    """Converte texto 'True'/'False' (ou bool nativo) em bool. Retorna None se nao reconhecer."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        v = valor.strip().lower()
        if v == "true":
            return True
        if v == "false":
            return False
    return None


def traduzir_bool(valor, texto_true, texto_false):
    b = to_bool(valor)
    if b is True:
        return texto_true
    if b is False:
        return texto_false
    return "Invalido"


def validar_transaction_id(df):
    duplicados = df["transaction_id"].duplicated(keep=False)
    return duplicados.map({True: "Invalido", False: "Valido"})


def traduzir_merchant_category(valor):
    return MAPA_MERCHANT_CATEGORY.get(valor, "Invalido")


def classificar_card_type(valor):
    if valor in BANDEIRAS_PRINCIPAIS:
        return valor
    if pd.isna(valor) or valor == "":
        return "Invalido"
    return "Demais Cartoes"


def traduzir_channel(valor):
    return MAPA_CHANNEL.get(valor, valor)


def traduzir_dia_semana(valor):
    try:
        v = int(valor)
    except (ValueError, TypeError):
        return "Invalido"
    return MAPA_DIA_SEMANA.get(v, "Invalido")


def traduzir_is_fraud(valor):
    try:
        v = int(valor)
    except (ValueError, TypeError):
        return "Invalido"
    if v == 0:
        return "Nao Fraude"
    if v == 1:
        return "Fraude"
    return "Invalido"


# =========================================================
# 4. LEITURA DA BASE
# =========================================================

if ARQUIVO_ENTRADA.lower().endswith(".csv"):
    df = pd.read_csv(ARQUIVO_ENTRADA, sep=SEPARADOR_CSV, encoding="utf-8-sig")
else:
    df = pd.read_excel(ARQUIVO_ENTRADA)

# =========================================================
# 5. APLICACAO DAS REGRAS (colunas novas ao lado da original)
# =========================================================

df.insert(df.columns.get_loc("transaction_id") + 1,
          "transaction_id_validacao", validar_transaction_id(df))

df.insert(df.columns.get_loc("merchant_category") + 1,
          "merchant_category_traducao", df["merchant_category"].apply(traduzir_merchant_category))

df.insert(df.columns.get_loc("card_type") + 1,
          "card_type_classificacao", df["card_type"].apply(classificar_card_type))

df.insert(df.columns.get_loc("channel") + 1,
          "channel_traducao", df["channel"].apply(traduzir_channel))

df.insert(df.columns.get_loc("is_foreign_transaction") + 1,
          "is_foreign_transaction_traducao",
          df["is_foreign_transaction"].apply(lambda v: traduzir_bool(v, "Exterior", "Nacional")))

df.insert(df.columns.get_loc("is_new_merchant") + 1,
          "is_new_merchant_traducao",
          df["is_new_merchant"].apply(lambda v: traduzir_bool(v, "Novo", "Velho")))

df.insert(df.columns.get_loc("ip_country_mismatch") + 1,
          "ip_country_mismatch_traducao",
          df["ip_country_mismatch"].apply(lambda v: traduzir_bool(v, "Incompativel", "Compativel")))

df.insert(df.columns.get_loc("billing_shipping_mismatch") + 1,
          "billing_shipping_mismatch_traducao",
          df["billing_shipping_mismatch"].apply(lambda v: traduzir_bool(v, "Incompativel", "Compativel")))

df.insert(df.columns.get_loc("day_of_week") + 1,
          "day_of_week_traducao", df["day_of_week"].apply(traduzir_dia_semana))

df.insert(df.columns.get_loc("is_ai_generated_scam_attempt") + 1,
          "is_ai_generated_scam_attempt_traducao",
          df["is_ai_generated_scam_attempt"].apply(lambda v: traduzir_bool(v, "Tem IA", "Sem IA")))

df.insert(df.columns.get_loc("is_fraud") + 1,
          "is_fraud_traducao", df["is_fraud"].apply(traduzir_is_fraud))

# =========================================================
# 6. ALERTA DE CATEGORIAS NAO MAPEADAS (para revisao manual)
# =========================================================
categorias_nao_mapeadas = sorted(
    set(df.loc[df["merchant_category_traducao"] == "Invalido", "merchant_category"].unique())
)
if categorias_nao_mapeadas:
    print("ATENCAO: categorias de merchant_category sem traducao definida (marcadas como Invalido):")
    for c in categorias_nao_mapeadas:
        print(f"  - {c}")

# =========================================================
# 7. EXPORTACAO
# =========================================================
df.to_excel(ARQUIVO_SAIDA, index=False)
print(f"\nArquivo sanitizado salvo em: {ARQUIVO_SAIDA}")
print(f"Linhas: {len(df)} | Colunas: {len(df.columns)}")
