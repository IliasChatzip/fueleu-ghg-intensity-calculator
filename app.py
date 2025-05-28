import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
import tempfile
import os
from decimal import Decimal, getcontext
import math
import re

# === PAGE CONFIG ===
st.set_page_config(page_title="FuelEU GHG Calculator", layout="wide")

# === STABLE RESET HANDLER ===
def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]  # Clear all session state
    st.session_state["trigger_reset"] = False
    
# === Check if Reset Was Triggered
if st.session_state.get("trigger_reset", False):
    reset_app()
    
st.sidebar.button(
    "🔁 Reset Calculator",
    on_click=lambda: st.session_state.update({"trigger_reset": True}))

# === CONFIGURATION ===
BASE_TARGET = 91.16
REDUCTIONS = {2025: 0.02, 2030: 0.06, 2035: 0.14, 2050: 0.80}
PENALTY_RATE = 2400
VLSFO_ENERGY_CONTENT = 41_000
REWARD_FACTOR_RFNBO_MULTIPLIER = 2
GWP_VALUES = {
    "AR4": {"CH4": 25, "N2O": 298},
    "AR5": {"CH4": 29.8, "N2O": 273},}

# === FUEL DATABASE ===
FUELS = [
    {"name": "Heavy Fuel Oil (HFO)",                                    "lcv": 0.0405,  "wtt": 13.5,  "ttw_co2": 3.114,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},
    {"name": "Low Sulphur Fuel Oil (LSFO)",                             "lcv": 0.0405,  "wtt": 13.7,  "ttw_co2": 3.114,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},
    {"name": "Ultra Low Sulphur Fuel Oil (ULSFO)",                      "lcv": 0.0405,  "wtt": 13.2,  "ttw_co2": 3.114,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)",                       "lcv": 0.041,   "wtt": 13.2,  "ttw_co2": 3.206,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},
    {"name": "Low Fuel Oil (LFO)",                                      "lcv": 0.041,   "wtt": 13.2,  "ttw_co2": 3.151,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},
    {"name": "Marine Diesel/Gas Oil (MDO/MGO)",                         "lcv": 0.0427,  "wtt": 14.4,  "ttw_co2": 3.206,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},
    {"name": "Liquefied Natural Gas (LNG)",                             "lcv": 0.0491,  "wtt": 18.5,  "ttw_co2": 2.750,  "ttw_ch4": 0.001276, "ttw_n20": 0.00011,  "rfnbo": False},
    {"name": "Liquefied Petroleum Gas (LPG)",                           "lcv": 0.0460,  "wtt": 7.8,   "ttw_co2": 3.015,  "ttw_ch4": 0.007,    "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Fossil Hydrogen (H2)",                                    "lcv": 0.12,    "wtt": 132,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Fossil Ammonia (NH3)",                                    "lcv": 0.0186,  "wtt": 121,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Fossil Methanol",                                         "lcv": 0.0199,  "wtt": 31.3,  "ttw_co2": 1.375,  "ttw_ch4": 0.003,    "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Rapeseed Oil,B100)",                           "lcv": 0.0430,  "wtt": 1.5,   "ttw_co2": 2.834,  "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Corn Oil,B100)",                               "lcv": 0.0430,  "wtt": 31.6,  "ttw_co2": 2.834,  "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Wheat Straw,B100)",                            "lcv": 0.0430,  "wtt": 15.7,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (UCO,B20)",                                     "lcv": 0.0410,  "wtt": 13.88, "ttw_co2": 2.4912, "ttw_ch4": 0.00004,  "ttw_n20": 0.000144, "rfnbo": False},
    {"name": "Biodiesel (UCO,B24)",                                     "lcv": 0.0411,  "wtt": 13.912,"ttw_co2": 2.36664,"ttw_ch4": 0.000038, "ttw_n20": 0.0001368,"rfnbo": False},
    {"name": "Biodiesel (UCO,B30)",                                     "lcv": 0.0412,  "wtt": 13.93, "ttw_co2": 2.1798, "ttw_ch4": 0.000035, "ttw_n20": 0.000126, "rfnbo": False},
    {"name": "Biodiesel (UCO,B65)",                                     "lcv": 0.0421,  "wtt": 14.345,"ttw_co2": 1.0899, "ttw_ch4": 0.0000175,"ttw_n20": 0.000063, "rfnbo": False},
    {"name": "Biodiesel (UCO,B80)",                                     "lcv": 0.0424,  "wtt": 14.62, "ttw_co2": 0.6228, "ttw_ch4": 0.00001,  "ttw_n20": 0.000036, "rfnbo": False},
    {"name": "Biodiesel (UCO,B100)",                                    "lcv": 0.0430,  "wtt": 14.9,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Animal Fats,B100)",                            "lcv": 0.0430,  "wtt": 20.8,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Sunflower Oil,B100)",                          "lcv": 0.0430,  "wtt": 44.7,  "ttw_co2": 2.834,  "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Soybean Oil,B100)",                            "lcv": 0.0430,  "wtt": 47.0,  "ttw_co2": 2.834,  "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Palm Oil,B100)",                               "lcv": 0.0430,  "wtt": 75.7,  "ttw_co2": 2.834,  "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Bioethanol (Sugar Beet,E100)",                            "lcv": 0.0268,  "wtt": 38.2,  "ttw_co2": 1.913,  "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Bioethanol (Maize,E100)",                                 "lcv": 0.0268,  "wtt": 56.8,  "ttw_co2": 1.913,  "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Bioethanol (Other cereals excluding maize,E100)",         "lcv": 0.0268,  "wtt": 58.5,  "ttw_co2": 1.913,  "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Bioethanol (Wheat,E100)",                                 "lcv": 0.0268,  "wtt": 15.7,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Bioethanol (Sugar Cane,E100)",                            "lcv": 0.0268,  "wtt": 28.6,  "ttw_co2": 1.913,  "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Hydrotreated Vegetable Oil (Rape Seed,HVO100)",           "lcv": 0.0440,  "wtt": 50.1,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},
    {"name": "Hydrotreated Vegetable Oil (Sunflower,HVO100)",           "lcv": 0.0440,  "wtt": 43.6,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},    
    {"name": "Hydrotreated Vegetable Oil (Soybean,HVO100)",             "lcv": 0.0440,  "wtt": 46.5,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},  
    {"name": "Hydrotreated Vegetable Oil (Palm Oil,HVO100)",            "lcv": 0.0440,  "wtt": 73.3,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Straight Vegetable Oil (Rape Seed,SVO100)",               "lcv": 0.0440,  "wtt": 40.0,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},
    {"name": "Straight Vegetable Oil (Sunflower,SVO100)",               "lcv": 0.0440,  "wtt": 34.3,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},    
    {"name": "Straight Vegetable Oil (Soybean,SVO100)",                 "lcv": 0.0440,  "wtt": 36.9,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},  
    {"name": "Straight Vegetable Oil (Palm Oil,SVO100)",                "lcv": 0.0440,  "wtt": 65.4,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Bio-LNG",                                                 "lcv": 0.0491,  "wtt": 14.1,  "ttw_co2": 2.75,   "ttw_ch4": 0.14,     "ttw_n20": 0.00011,  "rfnbo": False},
    {"name": "Bio-Hydrogen",                                            "lcv": 0.12,    "wtt": 0.0,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "Bio-Methanol",                                            "lcv": 0.0199,  "wtt": 13.5,  "ttw_co2": 0.0,    "ttw_ch4": 0.003,    "ttw_n20": 0.0,      "rfnbo": False},
    {"name": "E-Methanol",                                              "lcv": 0.0199,  "wtt": 1.0,   "ttw_co2": 1.375,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": True},
    {"name": "E-Diesel",                                                "lcv": 0.0427,  "wtt": 1.0,   "ttw_co2": 3.206,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": True},
    {"name": "E-LNG",                                                   "lcv": 0.0491,  "wtt": 1.0,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": True},
    {"name": "E-Hydrogen",                                              "lcv": 0.1200,  "wtt": 3.6,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": True},
    {"name": "E-Ammonia",                                               "lcv": 0.0186,  "wtt": 0.0,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n20": 0.0,      "rfnbo": True},  
]
    
# === TARGET FUNCTION ===
def target_intensity(year: int) -> float:
    if year <= 2020:
        return BASE_TARGET
    if year <= 2029:
        return BASE_TARGET * (1 - REDUCTIONS[2025])
    if year <= 2034:
        return BASE_TARGET * (1 - REDUCTIONS[2030])
    if year == 2035:
        return BASE_TARGET * (1 - REDUCTIONS[2035])
    frac = (year - 2035) / (2050 - 2035)
    red = REDUCTIONS[2035] + frac * (REDUCTIONS[2050] - REDUCTIONS[2035])
    return BASE_TARGET * (1 - red)
  
# === USER INPUT ===
st.title("FuelEU - GHG Intensity & Penalty Calculator")
st.sidebar.markdown("### Fuel Price Settings")
st.sidebar.info("Enter fuel prices in USD & provide exchange rate.")
st.sidebar.subheader("Fuel Inputs")
fuel_inputs = {}
fuel_price_inputs = {}

# Detect if any price was entered
user_entered_prices = any(
    st.session_state.get(f"price_{fuel['name']}", 0.0) > 0.0 for fuel in FUELS
)

categories = {
    "Fossil ": [f for f in FUELS if not f['rfnbo'] and "Bio" not in f['name'] and "Biodiesel" not in f['name'] and "E-" not in f['name'] and "Green" not in f['name'] and "Vegetable" not in f['name']],
    "Bio": [f for f in FUELS if "Bio" in f['name'] or "Biodiesel" in f['name'] or "Vegetable" in f['name']],
    "RFNBO": [f for f in FUELS if f['rfnbo'] or "E-" in f['name'] or "Green" in f['name']]
}

for category, fuels_in_cat in categories.items():
    with st.sidebar.expander(f"{category} Fuels", expanded=False):
        selected_fuels = st.multiselect(f"Select {category} Fuels", [f["name"] for f in fuels_in_cat], key=f"multiselect_{category}")
        for selected_fuel in selected_fuels:
            qty = st.number_input(f"{selected_fuel} (t)", min_value=0, step=1, value=0, format="%d", key=f"qty_{selected_fuel}")
            fuel_inputs[selected_fuel] = qty
            price = st.number_input(f"{selected_fuel} - Price (USD/t)",min_value=0.0,value=0.0,step=0.01, format="%.2f", key=f"price_{selected_fuel}")
            fuel_price_inputs[selected_fuel] = price


st.sidebar.markdown("---")
exchange_rate = st.sidebar.number_input(
    "EUR/USD Exchange Rate",
    min_value=0.000001,
    value=1.000000,
    step=0.000001,
    format="%.6f",
    help="Exchange rate for converting USD fuel prices to EUR."
)

st.sidebar.header("Input Parameters")

year = st.sidebar.selectbox(
    "Compliance Year",
    [2020, 2025, 2030, 2035, 2040, 2045, 2050],
    index=1,
    help="Select the reporting year to compare against the target intensity."
)

gwp_choice = st.sidebar.radio(
    "GWP Standard",
    ["AR4", "AR5"],
    index=0,
    help="Choose Global Warming Potential values: AR4 (CH₄: 25, N₂O: 298) or AR5 (CH₄: 29.8, N₂O: 273). The current regulation is based on AR4 values for TtW. Based on EMSA, it can be expected that the TtW values will be changed to AR5 before January 2026. Use AR4 for 2025 and AR5 for the years after. AR5 is based on the latest IPCC values and gives higher CH₄ impact — recommended for accurate methane-emitting fuels (e.g., LNG)."
)
gwp = GWP_VALUES[gwp_choice]

ops = st.sidebar.selectbox(
    "OPS Reward Factor (%)",
    [0, 1, 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],
    index=0,
    help="This is a reward factor of a ship which utilise the electricity from offshore power supply (OPS) connection point. This input is the percentage of electricity delivered to the ship per total amount of energy consumption onboard (max 20%)."
)

wind = st.sidebar.selectbox(
    "Wind Reward Factor",
    [1.00, 0.99, 0.97, 0.95],
    index=0,
    help="This is a reward factor wind-assisted propulsion if it is installed onboard. Reference can be made to the Regulation (EU) 2023/1805 of The European Parliament and of The Counsil. In case of no wind-assisted propulsion onboard, Wind Reward Factor of 1 can be selected (lower = more assistance)."
)
    
# === CALCULATIONS ===
total_energy = 0.0
emissions = 0.0
rows = []

for fuel in FUELS:
    qty = fuel_inputs.get(fuel["name"], 0.0)
    if qty > 0:
        mass_g = qty * 1_000_000
        lcv = fuel["lcv"]
        energy = mass_g * lcv
        if fuel["rfnbo"] and year <= 2033:
            energy *= REWARD_FACTOR_RFNBO_MULTIPLIER
            
        co2_total = fuel["ttw_co2"] * mass_g * (1 - ops / 100) * wind
        ch4_total = fuel["ttw_ch4"] * mass_g * gwp["CH4"]
        n2o_total = fuel["ttw_n20"] * mass_g * gwp["N2O"]
        ttw_total = co2_total + ch4_total + n2o_total
        wtt_total = energy * fuel["wtt"]
        total_emissions = ttw_total + wtt_total
            
        total_energy += energy
        emissions += total_emissions
        
        ghg_intensity_mj = total_emissions / energy if energy else 0
        
        price_usd = fuel_price_inputs.get(fuel["name"], 0.0)
        price_eur = price_usd * exchange_rate
        cost = qty * price_eur
        
        rows.append({
            "Fuel": fuel["name"],
            "Quantity (t)": qty,
            "Price per Tonne (USD)": price_usd,
            "Cost (Eur)": cost,
            "Emissions (gCO2eq)": total_emissions,
            "Energy (MJ)": energy,
            "GHG Intensity (gCO2eq/MJ)": ghg_intensity_mj,
           })
        
# after all fuels processed
ghg_intensity = emissions / total_energy if total_energy else 0.0
st.session_state["computed_ghg"] = ghg_intensity

compliance_balance = total_energy * (target_intensity(year) - ghg_intensity)
co2_balance_gco2eq = (target_intensity(year) - ghg_intensity) * compliance_balance

        
if compliance_balance >= 0:
     penalty = 0
else:
     penalty = (abs(compliance_balance) / (ghg_intensity * VLSFO_ENERGY_CONTENT)) * PENALTY_RATE

mitigation_total_cost = 0.0
# Safeguard for mitigation_rows
mitigation_rows = []


# === Reset Handler ===
if st.session_state.get("trigger_reset", False):
    exclude_keys = {"exchange_rate"}
    for key in list(st.session_state.keys()):
        if key not in exclude_keys and key != "trigger_reset":
            del st.session_state[key]
    st.session_state["trigger_reset"] = False
    st.experimental_rerun()

# === OUTPUT ===
st.subheader("Fuel Breakdown")
if rows:
    df_raw = pd.DataFrame(rows).sort_values("Emissions (gCO2eq)", ascending=False).reset_index(drop=True)
    df_formatted = df_raw.style.format({
        "Quantity (t)": "{:,.0f}",
        "Price per Tonne (USD)": "{:,.2f}",
        "Cost (Eur)": "{:,.2f}",
        "Emissions (gCO2eq)": "{:,.0f}",
        "Energy (MJ)": "{:,.0f}",
        "GHG Intensity (gCO2eq/MJ)": "{:,.5f}"
    })
    st.dataframe(df_formatted)
    total_cost = sum(row["Cost (Eur)"] for row in rows)
    st.metric("Total Fuel Cost (Eur)", f"{total_cost:,.2f}")


else:
    st.info("No fuel data provided yet.")

st.subheader("Summary")
st.metric("GHG Intensity (gCO2eq/MJ)", f"{ghg_intensity:.5f}")
balance_label = "Surplus" if compliance_balance >= 0 else "Deficit"
st.metric("Compliance Balance (MJ)", f"{compliance_balance:,.0f}")
balance_label = "Surplus" if co2_balance_gco2eq < 0 else "Deficit"
st.metric(f"CO2 {balance_label} (gCO2eq)", f"{co2_balance_gco2eq:,.0f}")
st.metric("Estimated Penalty (Eur)", f"{penalty:,.2f}")
if rows:
    conservative_total = total_cost + penalty
    st.metric("Total Cost of Selected Fuels + Penalty", f"{conservative_total:,.2f} Eur")

# === POOLING OPTION ===

show_pooling_option = False
pooling_price = 0.0
pooling_cost = 0.0
total_with_pooling = 0.0

if co2_balance_gco2eq > 0:
    show_pooling_option = True
    st.markdown("Pooling Option (Penalty Offset)")
    st.info(f"CO₂ Deficit: {co2_balance_gco2eq:,.0f} gCO₂eq. You may offset this via pooling if you have access to external credits.")

    pooling_price = st.number_input(
        "Enter Pooling Price (Eur/gCO₂eq)",
        min_value=0.0, value=0.0, step=0.01,
        help="The cost per gCO₂eq to buy compliance credits from the pool. If 0, pooling will not be applied.")

    if pooling_price > 0:
        pooling_cost = co2_balance_gco2eq * pooling_price
        total_with_pooling = total_cost + pooling_cost

        st.markdown("### Scenario 2: Initial Fuels + Pooling Option")
        st.metric("Pooling Cost (Eur)", f"{pooling_cost:,.2f}")
        st.metric("Total Cost (Fuels + Pooling)", f"{total_with_pooling:,.2f} Eur")
    else:
        st.info("Enter a non-zero pooling price to activate Scenario 2.")


# === MITIGATION OPTIONS ===

# Set precision to 12 digits
getcontext().prec = 12
if penalty > 0:
    st.subheader("Mitigation Options (Penalty Offset)")
    dec_ghg = Decimal(str(ghg_intensity))
    dec_emissions = Decimal(str(emissions))
    dec_energy = Decimal(str(total_energy))
    target = Decimal(str(target_intensity(year)))
    
    mitigation_rows = []
    for fuel in FUELS:
        co2_mj = Decimal(str(fuel["ttw_co2"])) * Decimal(str(1 - ops / 100)) * Decimal(str(wind))
        ch4_mj = Decimal(str(fuel["ttw_ch4"])) * Decimal(str(gwp["CH4"]))
        n2o_mj = Decimal(str(fuel["ttw_n20"])) * Decimal(str(gwp["N2O"]))
        total_ghg_mj = Decimal(str(fuel["wtt"])) + co2_mj + ch4_mj + n2o_mj

        if total_ghg_mj >= dec_ghg:
            continue

        low = Decimal("0.0")
        high = Decimal("100000.0")
        best_qty = None
        tolerance = Decimal("0.00001")

        for _ in range(50):
            mid = (low + high) / 2
            mass_g = mid * Decimal("1000000")
            energy_mj = mass_g * Decimal(str(fuel["lcv"]))

            if fuel["rfnbo"] and year <= 2033:
                energy_mj *= Decimal(str(REWARD_FACTOR_RFNBO_MULTIPLIER))

            ttw = (co2_mj + ch4_mj + n2o_mj) * mass_g
            wtt = energy_mj * Decimal(str(fuel["wtt"]))
            new_emissions = dec_emissions + ttw + wtt
            new_energy = dec_energy + energy_mj

            new_ghg = new_emissions / new_energy if new_energy else Decimal("99999")

            if new_ghg < target:
                best_qty = mid
                high = mid
            else:
                low = mid

            if (high - low) < tolerance:
                break

        if best_qty is not None:
            rounded_qty = math.ceil(float(best_qty))
            mitigation_rows.append({
                "Fuel": fuel["name"],
                "Required Amount (t)": rounded_qty,
            })
            
    if mitigation_rows:
        mitigation_rows = sorted(mitigation_rows, key=lambda x: x["Required Amount (t)"])
        default_fuel = "Biodiesel (UCO,B20)"
        fuel_names = [row["Fuel"] for row in mitigation_rows]
        default_index = fuel_names.index(default_fuel) if default_fuel in fuel_names else 0
        selected_fuel = st.selectbox("Select Mitigation Fuel for Price Input",fuel_names,index=default_index)
        price_usd = st.number_input(f"{selected_fuel} - Price (USD/t)", min_value=0.0, value=0.0, step=10.0, key="mitigation_price_input")
        
        for row in mitigation_rows:
            row["Price (USD/t)"] = price_usd if row["Fuel"] == selected_fuel else 0.0
            row["Estimated Cost (Eur)"] = row["Price (USD/t)"] * exchange_rate * row["Required Amount (t)"]
            
        mitigation_total_cost = sum(row.get("Estimated Cost (Eur)", 0) for row in mitigation_rows)
        user_entered_mitigation_price = price_usd > 0
            
        if user_entered_mitigation_price:
            # User entered price: Only show scenarios
            st.markdown("### Total Cost Scenarios")
            scenario1 = total_cost + penalty
            scenario3 = total_cost + mitigation_total_cost
            st.metric("Scenario 1: Initial Fuels + Penalty", f"{scenario1:,.2f} Eur")
            st.metric("Scenario 3: Initial Fuels + Mitigation Fuels (No Penalty)", f"{scenario3:,.2f} Eur")
        else:
             # No price: show mitigation table (quantity report)
             df_mit = pd.DataFrame(mitigation_rows)
             st.dataframe(df_mit.style.format({"Required Amount (t)": "{:,.0f}", "Price (USD/t)": "{:,.2f}", "Estimated Cost (Eur)": "{:,.2f}"}))

# === COMPLIANCE CHART ===
years = list(range(2020, 2051, 5))
targets = [target_intensity(y) for y in years]

st.subheader("Sector-wide GHG Intensity Targets")
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(years, targets, linestyle='--', marker='o', label='EU Target')
for x, y in zip(years, targets):
    ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)
ax.axhline(st.session_state["computed_ghg"], color='red', linestyle='-', label='Your GHG Intensity')
ax.set_xlabel("Year")
ax.set_ylabel("gCO2eq/MJ")
ax.set_title("Your Performance vs Sector Target")
ax.legend()
ax.grid(True)
st.pyplot(fig)


# === PDF EXPORT ===
if st.button("Export to PDF"):
    if not rows:
        st.warning("No data to export.")
    else:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Fuel EU Maritime GHG & Penalty Report", ln=True, align="C")
        pdf.cell(200, 10, txt=f"Year: {year} | GWP: {gwp_choice}", ln=True)
        pdf.cell(200, 10, txt=f"EU Target for {year}: {target_intensity(year):.2f} gCO2eq/MJ", ln=True)
        pdf.cell(200, 10, txt=f"GHG Intensity: {ghg_intensity:.2f} gCO2eq/MJ", ln=True)
        pdf.cell(200, 10, txt=f"Compliance Balance: {compliance_balance:,.0f} MJ", ln=True)
        co2_balance_gco2eq = (target_intensity(year) - ghg_intensity) * compliance_balance
        balance_label = "Surplus" if co2_balance_gco2eq < 0 else "Deficit"
        pdf.cell(200, 10, txt=f"CO2 {balance_label}: {co2_balance_gco2eq:,.0f} gCO2eq", ln=True)
        pdf.cell(200, 10, txt=f"Penalty: {penalty:,.2f} Eur", ln=True)
        pdf.ln(10)

        # Fuel Breakdown
        total_cost = 0
        pdf.set_font("Arial", size=11)
        pdf.cell(200, 10, txt="--- Fuel Breakdown ---", ln=True)
        user_entered_prices = any(fuel_price_inputs.get(f["name"], 0.0) > 0.0 for f in FUELS)
        for row in rows:
            fuel_name = row['Fuel']
            qty = row['Quantity (t)']
            price_usd = fuel_price_inputs.get(fuel_name, 0.0)
            cost = qty * price_usd * exchange_rate
            ghg_intensity = row['GHG Intensity (gCO2eq/MJ)']
            total_cost += cost
            line = f"{fuel_name}: {qty:,.0f} t @ {price_usd:,.2f} USD/t | {cost:,.2f} Eur | GHG Intensity: {ghg_intensity:.2f} gCO2eq/MJ"
            pdf.cell(200, 10, txt=line, ln=True)

        # Total Cost
        pdf.ln(5)
        pdf.set_font("Arial", "B", size=12)
        pdf.cell(200, 10, txt=f"Total Fuel Cost: {total_cost:,.2f} Eur", ln=True)
        if user_entered_prices:
            pdf.set_font("Arial", size=10)
            pdf.ln(3)
            pdf.cell(200, 10, txt=f"Conversion Rate Used: 1 USD = {exchange_rate:.6f} EUR", ln=True)

        # Mitigation Options
        pdf.ln(5)
        pdf.set_font("Arial", size=11)
        pdf.cell(200, 10, txt="--- Mitigation Options ---", ln=True)

        mitigation_with_price = [row for row in mitigation_rows if row.get("Price (USD/t)", 0) > 0]

        if mitigation_with_price:
            pdf.set_font("Arial", size=10)
            for row in mitigation_with_price:
                line = (f"{row['Fuel']}: {row['Required Amount (t)']:,.0f} t @ "
                        f"{row['Price (USD/t)']:,.2f} USD/t | "
                        f"{row['Estimated Cost (Eur)']:,.2f} Eur")
                pdf.cell(200, 10, txt=line, ln=True)

            mitigation_total_cost = sum(row.get("Estimated Cost (Eur)", 0) for row in mitigation_rows)
            total_with_mitigation = total_cost + mitigation_total_cost
            total_with_penalty = total_cost + penalty
            total_with_pooling = total_cost + pooling_cost
        
        else:
            mitigation_rows_sorted = sorted(mitigation_rows, key=lambda x: x["Required Amount (t)"])
            for row in mitigation_rows_sorted:
                mit_line = f"{row['Fuel']}: {row['Required Amount (t)']:,.0f} t"
                pdf.cell(200, 10, txt=mit_line, ln=True)
            pdf.ln(5)
            pdf.set_font("Arial", "B", size=12)
            pdf.cell(200, 10, txt="No mitigation fuel prices provided - quantities only report", ln=True)

        # Pooling Option
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt="--- Pooling Option ---", ln=True)
        
        if show_pooling_option and pooling_price > 0:
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt=f"CO₂ Deficit: {co2_balance_gco2eq:,.0f} gCO₂eq", ln=True)
            pdf.cell(200, 10, txt=f"Pooling Price: {pooling_price:,.2f} €/gCO₂eq", ln=True)
            pdf.cell(200, 10, txt=f"Pooling Cost: {pooling_cost:,.2f} Eur", ln=True)
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", size=12)
            pdf.cell(200, 10, txt=f"Scenario 1 (Initial fuels + Penalty): {total_with_penalty:,.2f} Eur", ln=True)
            pdf.cell(200, 10, txt=f"Scenario 2 (Initial fuels + Pooling, no Penalty): {total_with_pooling:,.2f} Eur", ln=True)
            pdf.cell(200, 10, txt=f"Scenario 3 (Initial fuels + Mitigation fuels, no Penalty): {total_with_mitigation:,.2f} Eur", ln=True)
            
                            
        # Export
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            tmp_pdf_path = tmp_pdf.name

        st.success(f"PDF exported: {os.path.basename(tmp_pdf_path)}")
        st.download_button("Download PDF", data=open(tmp_pdf_path, "rb"),
                           file_name="ghg_report.pdf",
                           mime="application/pdf")
