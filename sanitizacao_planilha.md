# Sanitização da base de fraude em cartão de crédito

Script em Python (pandas), reutilizável — basta trocar o caminho do arquivo de entrada na base completa.

## Regras aplicadas

| Coluna original | Nova coluna (ao lado) | Regra |
|---|---|---|
| `transaction_id` | `transaction_id_validacao` | "Valido" se único; "Invalido" se houver ID repetido |
| `merchant_category` | `merchant_category_traducao` | Tradução PT-BR via dicionário fixo; categoria fora do dicionário → "Invalido" |
| `card_type` | `card_type_classificacao` | Mantém Mastercard/Visa/Amex; qualquer outra bandeira → "Demais Cartoes" |
| `channel` | `channel_traducao` | "Contactless" → "Aproximacao"; demais mantidos |
| `is_foreign_transaction` | `is_foreign_transaction_traducao` | False → "Nacional"; True → "Exterior" |
| `is_new_merchant` | `is_new_merchant_traducao` | False → "Velho"; True → "Novo" |
| `ip_country_mismatch` | `ip_country_mismatch_traducao` | False → "Compativel"; True → "Incompativel" |
| `billing_shipping_mismatch` | `billing_shipping_mismatch_traducao` | False → "Compativel"; True → "Incompativel" |
| `day_of_week` | `day_of_week_traducao` | 0 a 6 → Domingo...Sábado (0 = Domingo, confirmado com você) |
| `is_ai_generated_scam_attempt` | `is_ai_generated_scam_attempt_traducao` | False → "Sem IA"; True → "Tem IA" |
| `is_fraud` | `is_fraud_traducao` | 0 → "Nao Fraude"; 1 → "Fraude" |

Todas as demais colunas (`amount_usd`, `auth_method`, `device_type`, `hours_since_last_txn`, `txn_count_last_24h`, `distance_from_home_km`, `card_age_months`, `customer_age`, `account_balance_usd`, `used_vpn`, `cvv_retry_count`, `velocity_score`, `time_of_day_hour`, `merchant_risk_score`, `prior_disputes`) permanecem **inalteradas**, sem coluna nova.

**Nenhuma linha ou coluna original é removida.** Qualquer valor que não se encaixe em nenhuma regra é marcado como `"Invalido"` — nada é deduzido.

⚠️ **Atenção para a base completa**: o dicionário de tradução de `merchant_category` foi montado com as 10 categorias vistas na amostra (Electronics, Fuel, Gaming, Gift Cards, Groceries, Online Retail, Restaurants, Streaming, Travel, Utilities). Se a base completa tiver categorias diferentes, o script marca automaticamente como "Invalido" e **imprime no console a lista de categorias não mapeadas** para você revisar e completar o dicionário.

## Comando (script Python completo)

```python
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
ARQUIVO_ENTRADA = "credit_card_fraud_2026.csv"   # troque pelo caminho da base completa (.csv ou .xlsx)
ARQUIVO_SAIDA   = "credit_card_fraud_2026_sanitizado.xlsx"
SEPARADOR_CSV   = ";"   # a amostra recebida usa ";" como separador

# =========================================================
# 2. DICIONARIOS DE TRADUCAO / CLASSIFICACAO
# =========================================================

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

BANDEIRAS_PRINCIPAIS = {"Mastercard", "Visa", "Amex"}

MAPA_CHANNEL = {
    "Contactless": "Aproximacao",
}

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
```

## Como reutilizar na base completa

1. Salve este script como `sanitizar_planilha.py`.
2. Ajuste as variáveis `ARQUIVO_ENTRADA` e `ARQUIVO_SAIDA` no topo.
3. Rode com `python3 sanitizar_planilha.py`.
4. Confira no console se apareceu o aviso de categorias não mapeadas em `merchant_category` — se aparecer, adicione a tradução no dicionário `MAPA_MERCHANT_CATEGORY` e rode de novo.

## Suposição assumida (confirmada com você)

- `day_of_week`: 0 = Domingo (padrão Python/US), 6 = Sábado.
- Para `transaction_id_validacao`, como você só especificou a regra para IDs repetidos, os IDs únicos foram marcados como **"Valido"** (complemento direto da regra que você deu).
