# ======================================================================
#                               ANÁLISES INICIAIS
# ======================================================================

import numpy as np
import pandas as pd

# Mostrar floats sem notação científica
pd.set_option("display.float_format", lambda v: f"{v:.6f}")

# ======================================================================
# PARTE 1 - IMPORTANDO E ARRUMANDO OS DADOS
# ======================================================================

df = pd.read_csv("./vehicle_data_1.csv")

city_gasoline = [13.5]
road_gasoline = [15.7]
city_ethanol  = [9.3]
road_ethanol  = [10.9]

def assign_series(vec, name):
    if len(vec) == 1:
        df[name] = vec[0]
    elif len(vec) == len(df):
        df[name] = pd.to_numeric(pd.Series(vec), errors="coerce").values
    else:
        raise ValueError(f"Comprimento de {name} ({len(vec)}) difere do n de linhas ({len(df)})")

assign_series(city_gasoline, "city_gasoline")
assign_series(road_gasoline, "road_gasoline")
assign_series(city_ethanol,  "city_ethanol")
assign_series(road_ethanol,  "road_ethanol")

for col in ["city_gasoline", "road_gasoline", "city_ethanol", "road_ethanol"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

Carbon_Price_European = [89.08]
assign_series(Carbon_Price_European, "Carbon_Price_European")

Euro_price = [6.1708]
assign_series(Euro_price, "Euro_price")

df["Real_price"] = pd.to_numeric(df["Carbon_Price_European"], errors="coerce") * pd.to_numeric(df["Euro_price"], errors="coerce")

# df["Tanque_gasoline"] = 100 - pd.to_numeric(df["ethanol (%)"], errors="coerce")

# ======================================================================
# PARTE 2 - CALCULANDO A META DE EMISSÃO
# ======================================================================

def safe_div(numerador, denominador):
    numerador = pd.to_numeric(numerador, errors="coerce")
    denominador = pd.to_numeric(denominador, errors="coerce")
    
    # Convert scalar to array if needed
    if np.isscalar(numerador):
        numerador = np.full_like(denominador, numerador, dtype=float)
    
    out = np.divide(numerador, denominador, out=np.zeros_like(numerador, dtype=float), where=(denominador!=0))
    out[~np.isfinite(out)] = 0.0
    return out

EMISSAO_GASOLINA = 1.720
EMISSAO_ETANOL   = 1.510

dist_highway = pd.to_numeric(df["distance_highway"], errors="coerce")
dist_city    = pd.to_numeric(df["distance_city"],    errors="coerce")

# p_gas = pd.to_numeric(df["Tanque_gasoline"], errors="coerce")/100.0
# p_etanol = pd.to_numeric(df["ethanol (%)"], errors="coerce")/100.0

parte_1_1 = dist_highway * ( safe_div(1, df["road_gasoline"]) * 1 * EMISSAO_GASOLINA ) * 1000
parte_1_2 = dist_highway * ( safe_div(1, df["road_ethanol"])  * 1 * EMISSAO_ETANOL   ) * 1000
parte_1_1[~np.isfinite(parte_1_1)] = 0
parte_1_2[~np.isfinite(parte_1_2)] = 0
df["parte_1"] = parte_1_1 + parte_1_2

parte_2_1 = dist_city * ( safe_div(1, df["city_gasoline"]) * 1 * EMISSAO_GASOLINA ) * 1000
parte_2_2 = dist_city * ( safe_div(1, df["city_ethanol"])  * 1 * EMISSAO_ETANOL ) * 1000
parte_2_1[~np.isfinite(parte_2_1)] = 0
parte_2_2[~np.isfinite(parte_2_2)] = 0
df["parte_2"] = parte_2_1 + parte_2_2

df["Meta_CO2"] = df["parte_1"] + df["parte_2"]

# linha original
# df["Diff"] = df["Meta_CO2"] - pd.to_numeric(df["co2_etanol_original_gas_1720_flex"], errors="coerce")

# df["Diff"] = df["Meta_CO2"] - pd.to_numeric(df["Meta_CO2"] / 2, errors="coerce")

df["Diff"] = df["Meta_CO2"] - pd.to_numeric(df["CO2"], errors="coerce")
df["e1"] = df["Diff"] * pd.to_numeric(df["Real_price"], errors="coerce") / 1_000_000.0

print(df["e1"])