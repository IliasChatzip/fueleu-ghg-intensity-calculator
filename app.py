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
st.set_page_config(page_title="Fuel EU GHG Calculator", layout="wide")

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
REDUCTIONS = {2025: 0.02, 2030: 0.06, 2035: 0.145, 2040: 0.31, 2045: 0.62, 2050: 0.80}
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
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)",                       "lcv": 0.041,   "wtt": 13.2,  "ttw_co2": 3.206,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},
    {"name": "Ultra Low Sulphur Fuel Oil (ULSFO)",                      "lcv": 0.0405,  "wtt": 13.2,  "ttw_co2": 3.114,  "ttw_ch4": 0.00005,  "ttw_n20": 0.00018,  "rfnbo": False},
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
    if year <= 2039:
        return BASE_TARGET * (1 - REDUCTIONS[2035])
    if year <= 2044:
        return BASE_TARGET * (1 - REDUCTIONS[2040])
    if year <= 2049:
        return BASE_TARGET * (1 - REDUCTIONS[2045])
    if year == 2050:
        return BASE_TARGET * (1 - REDUCTIONS[2050])
      
# === USER INPUT ===
st.title("Fuel EU - GHG Intensity & Penalty Calculator")
st.sidebar.markdown("### Fuel Price Settings")
st.sidebar.info("Enter fuel prices in USD & provide exchange rate.")
st.sidebar.subheader("Fuel Inputs")
fuel_inputs = {}
fuel_price_inputs = {}
initial_fuels = [f["name"] for f in FUELS if not f["rfnbo"] and "Bio" not in f["name"] and "Biodiesel" not in f["name"] and "E-" not in f["name"] and "Vegetable" not in f["name"]]
mitigation_fuels = [f["name"] for f in FUELS if "Bio" in f["name"] or "Biodiesel" in f["name"] or "Vegetable" in f["name"] or f["rfnbo"] or "E-" in f["name"]]

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
       
if compliance_balance >= 0:
     penalty = 0
else:
     penalty = (abs(compliance_balance) / (ghg_intensity * VLSFO_ENERGY_CONTENT)) * PENALTY_RATE

mitigation_total_cost = 0.0
substitution_cost = None
total_substitution_cost = None
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

total_cost = 0.0

st.subheader("Fuel Breakdown")
if rows:
    df_raw = pd.DataFrame(rows).sort_values("Emissions (gCO2eq)", ascending=False).reset_index(drop=True)
    df_formatted = df_raw.style.format({
        "Quantity (t)": "{:,.0f}",
        "Price per Tonne (USD)": "{:,.2f}",
        "Cost (Eur)": "{:,.2f}",
        "Emissions (gCO2eq)": "{:,.0f}",
        "Energy (MJ)": "{:,.0f}",
        "GHG Intensity (gCO2eq/MJ)": "{:,.2f}"
    })
    st.dataframe(df_formatted)
    total_cost = sum(row["Cost (Eur)"] for row in rows)
    st.metric("Total Fuel Cost (Eur)", f"{total_cost:,.2f}")
    user_entered_prices = any(
        fuel_price_inputs.get(row["Fuel"], 0.0) > 0.0 for row in rows)
else:
    st.info("No fuel data provided yet.")

st.subheader("Summary")
st.metric("GHG Intensity (gCO2eq/MJ)", f"{ghg_intensity:.2f}")
balance_label = "Surplus" if compliance_balance >= 0 else "Deficit"
st.metric("Compliance Balance (gCO2eq)", f"{compliance_balance:,.0f}")
st.metric("Estimated Penalty (Eur)", f"{penalty:,.2f}")
if rows and user_entered_prices:
    conservative_total = total_cost + penalty
    st.metric("Total Cost of Selected Fuels + Penalty", f"{conservative_total:,.2f} Eur")

with st.expander("**Mitigation Strategies**", expanded=False):
    
    # === POOLING OPTION ===
    with st.expander("**Pooling**", expanded=False):
        show_pooling_option = False
        pooling_price_usd_per_tonne = 0.0
        pooling_cost_usd = 0.0
        pooling_cost_eur = 0.0
        total_with_pooling = 0.0
        deficit_tonnes = compliance_balance / 1_000_000
        
        if deficit_tonnes < 0:
            show_pooling_option = True
            st.subheader("Pooling Option")
            st.info(f"CO2 Deficit: {deficit_tonnes:,.2f} tCO2eq. You may offset this via pooling if you have access to external credits.")
        
            pooling_price_usd_per_tonne = st.number_input(
                "Enter Pooling Price (USD/tCO2eq)",
                min_value=0.0, value=0.0, step=0.01,
                help="The cost per tCO2eq to buy compliance credits from the pool. If 0, pooling will not be applied.")
        
            if pooling_price_usd_per_tonne > 0:
               pooling_cost_usd = pooling_price_usd_per_tonne * abs(deficit_tonnes)
               pooling_cost_eur = pooling_cost_usd * exchange_rate
               total_with_pooling = total_cost + pooling_cost_eur
        
            else:
               st.info("Enter a non-zero pooling price to activate Pooling Scenario.")
    
    
    # === BIO-FUELS OPTIONS ===
    with st.expander("**Add Bio Fuel**", expanded=False):
        getcontext().prec = 12
        user_entered_mitigation_price = False
        if penalty > 0:
            st.subheader("Bio Fuel Options")
            st.info(" This strategy **increases total fuel consumption** by **supplementing** the initial fuels with bio fuels to help achieve compliance.")
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
                selected_fuel = st.selectbox("Select Bio Fuel for Price Input",fuel_names,index=default_index)
                price_usd = st.number_input(f"{selected_fuel} - Price (USD/t)", min_value=0.0, value=0.0, step=10.0, key="mitigation_price_input")
        
                if price_usd > 0:
                    user_entered_mitigation_price = True
                    for row in mitigation_rows:
                        row["Price (USD/t)"] = price_usd if row["Fuel"] == selected_fuel else 0.0
                        row["Estimated Cost (Eur)"] = row["Price (USD/t)"] * exchange_rate * row["Required Amount (t)"]
                    mitigation_total_cost = sum(row.get("Estimated Cost (Eur)", 0) for row in mitigation_rows)
                
                else:
                    mitigation_rows = sorted(mitigation_rows, key=lambda x: x["Required Amount (t)"])
                    df_mit = pd.DataFrame(mitigation_rows)
                    st.markdown("#### Bio Fuel Options")
                    st.dataframe(df_mit.style.format({
                        "Required Amount (t)": "{:,.0f}"}))
    
    # === SUBSTITUTION SCENARIO ===
    with st.expander("**Replace with Bio Fuel**", expanded=False):
        if penalty > 0:
            st.subheader("Replacement Options (Compliance via Fuel Replacement)")
            default_substitute_fuel = "Biodiesel (UCO,B20)"
            default_substitute_index = mitigation_fuels.index(default_substitute_fuel) if default_substitute_fuel in mitigation_fuels else 0
        
            initial_fuel = st.selectbox("Select Fuel to Replace", initial_fuels, key="sub_initial")
            substitute_fuel = st.selectbox("Select Bio Fuel to Use", mitigation_fuels, index=default_substitute_index, key="sub_mitigation")
        
            qty_initial = fuel_inputs.get(initial_fuel, 0.0)
            price_initial = fuel_price_inputs.get(initial_fuel, 0.0) * exchange_rate
            substitution_price_usd = st.number_input(
                f"{substitute_fuel} - Price for Mitigation fuel (USD/t)",
                min_value=0.0, value=0.0, step=10.0, key="substitution_price_input"
                )
            substitution_price_eur = substitution_price_usd * exchange_rate
        
            additional_substitution_cost = None
            replaced_mass = None
        
            if qty_initial > 0:
                st.markdown("Estimate compliance by replacing the smallest possible fraction of a high-emission fuel with a bio fuel, ensuring GHG intensity is just below the FuelEU target.")
                
                initial_props = next(f for f in FUELS if f["name"] == initial_fuel)
                sub_props = next(f for f in FUELS if f["name"] == substitute_fuel)
                
                co2_initial = initial_props["ttw_co2"] * (1 - ops / 100) * wind
                ch4_initial = initial_props["ttw_ch4"] * gwp["CH4"]
                n2o_initial = initial_props["ttw_n20"] * gwp["N2O"]
                ghg_initial = co2_initial + ch4_initial + n2o_initial + initial_props["wtt"]
                co2_sub = sub_props["ttw_co2"] * (1 - ops / 100) * wind
                ch4_sub = sub_props["ttw_ch4"] * gwp["CH4"]
                n2o_sub = sub_props["ttw_n20"] * gwp["N2O"]
                ghg_sub = co2_sub + ch4_sub + sub_props["wtt"]
                
                target = target_intensity(year)
                precision = 1e-5
                low, high = 0.0, 1.0
                best_x = None
                for _ in range(100):
                    mid = (low + high) / 2
                    
                    initial_mass_g = qty_initial * 1_000_000
                    sub_mass_g = initial_mass_g * mid
                    remain_mass_g = initial_mass_g * (1 - mid)
        
                    energy_initial = remain_mass_g * initial_props["lcv"]
                    energy_sub = sub_mass_g * sub_props["lcv"]
                    if sub_props["rfnbo"] and year <= 2033:
                        energy_sub *= REWARD_FACTOR_RFNBO_MULTIPLIER
        
                    total_energy_blend = energy_initial + energy_sub + (total_energy - (initial_mass_g * initial_props["lcv"]))
        
                    # Emissions
                    ttw_initial = remain_mass_g * (co2_initial + ch4_initial + n2o_initial)
                    ttw_sub = sub_mass_g * (co2_sub + ch4_sub + n2o_sub)
                    wtt_initial = energy_initial * initial_props["wtt"]
                    wtt_sub = energy_sub * sub_props["wtt"]
        
                    total_emissions_blend = emissions - (initial_mass_g * (co2_initial + ch4_initial + n2o_initial) + initial_mass_g * initial_props["lcv"] * initial_props["wtt"]) + ttw_initial + ttw_sub + wtt_initial + wtt_sub
        
                    blended_ghg = total_emissions_blend / total_energy_blend if total_energy_blend > 0 else 99999
        
                    if blended_ghg <= target + precision:
                        best_x = mid
                        high = mid
                    else:
                        low = mid
        
                    if high - low < precision:
                        break
        
                if best_x is None or best_x > 1.0:
                    st.warning("⚠️ Consider alternative fuel.")
                    total_substitution_cost = None
                else:
                    replaced_mass = best_x * qty_initial
        
                    if price_initial > 0.0 and substitution_price_usd > 0.0:
                        mitigation_fuel_cost = replaced_mass * substitution_price_eur
                        remaining_fuel_cost = (qty_initial - replaced_mass) * price_initial
                        additional_substitution_cost = (replaced_mass * (substitution_price_eur - price_initial))
                        substitution_total_cost = mitigation_fuel_cost + remaining_fuel_cost
                        other_fuel_costs = sum(
                            fuel_inputs.get(f["name"], 0.0) * fuel_price_inputs.get(f["name"], 0.0) * exchange_rate
                            for f in FUELS if f["name"] not in [initial_fuel]
                            )
                        total_substitution_cost = substitution_total_cost + other_fuel_costs
                    else:
                        mitigation_fuel_cost = None
                        additional_substitution_cost = None
                        total_substitution_cost = None
        
                    st.success(f"To comply with the FuelEU target of {target:.2f} gCO2eq/MJ, you need to replace at least **{best_x*100:.2f}%** of {initial_fuel} with {substitute_fuel}.")
                    st.markdown(f"**Replaced {initial_fuel} mass**: {replaced_mass:,.1f} tonnes")
                    st.markdown(f"**Added {substitute_fuel} mass**: {replaced_mass:,.1f} tonnes")
                    if additional_substitution_cost is not None:
                        st.markdown(f"**Additional cost**: {additional_substitution_cost:,.2f} EUR")
                    else:
                        st.markdown(f"**Additional cost**: N/A (missing prices)")
           
            if mitigation_rows:
                st.markdown("### Total Cost Scenarios")
                scenario1 = total_cost + penalty if total_cost > 0 or penalty > 0 else None
                scenario2 = total_with_pooling if total_cost > 0 and pooling_price_usd_per_tonne > 0 else None
                scenario3 = total_cost + mitigation_total_cost if mitigation_total_cost > 0 else None
                scenario4 = total_substitution_cost if substitution_price_usd > 0 else None
                st.metric("Initial Fuels + Penalty", f"{scenario1:,.2f} Eur" if scenario1 is not None else "N/A (missing prices)")
                st.metric("Initial Fuels + Pooling (No Penalty)", f"{scenario2:,.2f} Eur" if scenario2 is not None else "N/A (missing prices)")
                st.metric("Initial Fuels + Bio Fuels (No Penalty)", f"{scenario3:,.2f} Eur" if scenario3 is not None else "N/A (missing prices)")
                st.metric("Replacement (No Penalty)", f"{scenario4:,.2f} Eur" if scenario4 is not None else "N/A (missing prices)")
            else:
                df_mit = pd.DataFrame(mitigation_rows)
                st.dataframe(df_mit.style.format({"Required Amount (t)": "{:,.0f}", "Price (USD/t)": "{:,.2f}", "Estimated Cost (Eur)": "{:,.2f}"}))

    else:
        if rows:
            st.info("✅ Compliance already achieved! No mitigation strategy required.")

# === COMPLIANCE CHART ===
years = sorted(REDUCTIONS.keys())
targets = [BASE_TARGET * (1 - REDUCTIONS[y]) for y in years]

st.subheader("Sector-wide GHG Intensity Targets")
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(years, targets, linestyle='--', marker='o', label='EU Target')
for x, y in zip(years, targets):
    ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)
computed_ghg = st.session_state.get("computed_ghg", ghg_intensity)
line_color = 'red' if computed_ghg > target_intensity(year) else 'green'
ax.axhline(computed_ghg, color=line_color, linestyle='-', label='Your GHG Intensity')
ax.annotate(f"{computed_ghg:.2f}",
            xy=(2050, computed_ghg),
            xytext=(0, -10),
            textcoords="offset points",
            ha="center", va="top",
            color="black", fontsize=10)
ax.set_xlabel("Year")
ax.set_ylabel("gCO2eq/MJ")
ax.set_title("Your Performance vs Sector Target")
ax.legend()
ax.grid(True)
st.pyplot(fig)

conservative_total = total_cost + penalty
total_with_mitigation = total_cost + mitigation_total_cost
total_with_pooling = total_cost + pooling_cost_eur

# === PDF EXPORT ===
if st.button("Export to PDF"):
    if not rows:
        st.warning("No data to export.")
    else:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        pdf.cell(200, 10, txt="Fuel EU Maritime GHG & Penalty Report", ln=True, align="C")
        pdf.cell(200, 10, txt=f"Year: {year} | GWP: {gwp_choice}", ln=True)
        pdf.cell(200, 10, txt=f"EU Target for {year}: {target_intensity(year):.2f} gCO2eq/MJ", ln=True)
        pdf.cell(200, 10, txt=f"GHG Intensity: {ghg_intensity:.2f} gCO2eq/MJ", ln=True)
        pdf.cell(200, 10, txt=f"Compliance Balance: {compliance_balance:,.0f} gCO2eq", ln=True)
        pdf.cell(200, 10, txt=f"Penalty: {penalty:,.2f} Eur", ln=True)
        pdf.ln(10)

        # Fuel Breakdown
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt="--- Fuel Breakdown ---", ln=True)
        user_entered_prices = any(fuel_price_inputs.get(f["name"], 0.0) > 0.0 for f in FUELS)
        for row in rows:
            fuel_name = row['Fuel']
            qty = row['Quantity (t)']
            price_usd = fuel_price_inputs.get(fuel_name, 0.0)
            cost = qty * price_usd * exchange_rate
            ghg_intensity = row['GHG Intensity (gCO2eq/MJ)']
            line = f"{fuel_name}: {qty:,.0f} t @ {price_usd:,.2f} USD/t | {cost:,.2f} Eur | GHG Intensity: {ghg_intensity:.2f} gCO2eq/MJ"
            pdf.cell(200, 10, txt=line, ln=True)

        # Total Cost
        pdf.ln(5)
        pdf.set_font("Arial", "B", size=11)
        pdf.cell(200, 10, txt=f"Total Fuel Cost: {total_cost:,.2f} Eur", ln=True)
        if user_entered_prices:
            pdf.set_font("Arial", size=10)
            pdf.ln(3)
            pdf.cell(200, 10, txt=f"Conversion Rate Used: 1 USD = {exchange_rate:.6f} EUR", ln=True)

        # Pooling Option
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt="--- Pooling Cost ---", ln=True)
        
        if show_pooling_option and pooling_price_usd_per_tonne > 0:
            pdf.set_font("Arial", size=10)
            pooling_line = (f"CO2 Deficit Offset: {abs(deficit_tonnes):,.2f} tCO2eq @ "
                    f"{pooling_price_usd_per_tonne:,.2f} USD/t | "
                    f"{pooling_cost_eur:,.2f} Eur")
            pdf.cell(200, 10, txt=pooling_line, ln=True)

        # Bio Fuel Option
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt="--- Mitigation Cost ---", ln=True)

        mitigation_with_price = [row for row in mitigation_rows if row.get("Price (USD/t)", 0) > 0]

        if mitigation_with_price:
            pdf.set_font("Arial", size=10)
            for row in mitigation_with_price:
                line = (f"{row['Fuel']}: {row['Required Amount (t)']:,.0f} t @ "
                        f"{row['Price (USD/t)']:,.2f} USD/t | "
                        f"{row['Estimated Cost (Eur)']:,.2f} Eur")
                pdf.cell(200, 10, txt=line, ln=True)        
        else:
            mitigation_rows_sorted = sorted(mitigation_rows, key=lambda x: x["Required Amount (t)"])
            for row in mitigation_rows_sorted:
                mit_line = f"{row['Fuel']}: {row['Required Amount (t)']:,.0f} t"
                pdf.cell(200, 10, txt=mit_line, ln=True)
            pdf.ln(5)
            pdf.set_font("Arial", "B", size=11)
            pdf.cell(200, 10, txt="No bio fuel prices provided - quantities only report", ln=True)

        
        # Replacemnet Option
        pdf.ln(5)
        pdf.set_font("Arial", size=11)
        pdf.cell(200, 10, txt="--- Substitution Cost ---", ln=True)

        if penalty > 0 and replaced_mass is not None and best_x is not None:
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt=f"Replaced {initial_fuel} with {substitute_fuel}: {replaced_mass:,.0f} tonnes", ln=True)
            pdf.cell(200, 10, txt=f"Substitution Ratio: {best_x*100:.1f}% of {initial_fuel} replaced by {substitute_fuel} for compliance.", ln=True)
            if additional_substitution_cost is not None:
                pdf.cell(200, 10, txt=f"Additional cost: {additional_substitution_cost:,.2f} EUR", ln=True)
                pdf.cell(200, 10, txt=f"Total Cost: {total_substitution_cost:,.2f} EUR", ln=True)
            else:
                pdf.cell(200, 10, txt="N/A (missing prices).", ln=True)
            
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", size=12)
        pdf.cell(200, 10, txt="--- Cost Analysis ---", ln=True)
        pdf.set_font("Arial", size=10)
        if total_cost > 0:
            pdf.set_font("Arial", style="B", size=11)
            pdf.cell(200, 10, txt=f"- Initial fuels + Penalty: {conservative_total:,.2f} Eur", ln=True)
        else:
            pdf.set_font("Arial", style="B", size=11)
            pdf.cell(200, 10, txt=f"- Initial fuels + Penalty: {penalty:,.2f} Eur", ln=True)
        
        if total_cost > 0:
            pdf.set_font("Arial", style="B", size=11)
            pdf.cell(200, 10, txt=f"- Initial fuels + Pooling, no Penalty: {total_with_pooling:,.2f} Eur", ln=True)
        else:
            pdf.set_font("Arial", style="B", size=11)
            pdf.cell(200, 10, txt=f"- Initial fuels + Pooling, no Penalty: N/A (missing prices)", ln=True)
        
        if total_cost > 0:
            pdf.set_font("Arial", style="B", size=11)
            pdf.cell(200, 10, txt=f"- Initial fuels + Bio fuels, no Penalty: {total_with_mitigation:,.2f} Eur", ln=True)                        
        else:
            pdf.set_font("Arial", style="B", size=11)
            pdf.cell(200, 10, txt=f"- Initial fuels + Bio fuels, no Penalty: N/A (missing prices)", ln=True)
        
        if total_substitution_cost is not None:
            pdf.set_font("Arial", style="B", size=11)
            pdf.cell(200, 10, txt=f"- Replacement, no Penalty: {total_substitution_cost:,.2f} Eur", ln=True)
        else:
            pdf.set_font("Arial", style="B", size=11)
            pdf.cell(200, 10, txt="- Replacement, no Penalty: N/A (missing prices)", ln=True)

                  
        # Export
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            tmp_pdf_path = tmp_pdf.name

        st.success(f"PDF exported: {os.path.basename(tmp_pdf_path)}")
        st.download_button("Download PDF", data=open(tmp_pdf_path, "rb"),
                           file_name="ghg_report.pdf",
                           mime="application/pdf")
