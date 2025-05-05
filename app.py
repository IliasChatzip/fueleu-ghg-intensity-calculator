# Streamlit Web App: Advanced FuelEU Maritime GHG Intensity Calculator

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === EMISSION FACTORS DATABASE (Expanded) ===
default_fuels = [
    # Fossil Fuels
    {"name": "Heavy Fuel Oil (HFO)", "lcv_mj_per_g": 0.0405, "wtw_gco2_per_mj": (3.114 + 0.00005*29.8 + 0.00018*273)/0.0405 + 13.5},
    {"name": "Marine Gas Oil (MGO)", "lcv_mj_per_g": 0.0427, "wtw_gco2_per_mj": (3.206 + 0.00005*29.8 + 0.00018*273)/0.0427 + 14.4},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)", "lcv_mj_per_g": 0.041, "wtw_gco2_per_mj": 91.0},
    {"name": "Liquefied Natural Gas (LNG)", "lcv_mj_per_g": 0.050, "wtw_gco2_per_mj": 79.0},
    {"name": "Liquefied Petroleum Gas (LPG)", "lcv_mj_per_g": 0.046, "wtw_gco2_per_mj": 76.0},
    {"name": "Methanol (Fossil)", "lcv_mj_per_g": 0.0199, "wtw_gco2_per_mj": 94.0},

    # Biofuels
    {"name": "Biodiesel (UCO)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 14.9},
    {"name": "Biodiesel (Animal Fats)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 34.4},
    {"name": "Biodiesel (Sunflower Oil)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 45.3},
    {"name": "Biodiesel (Soybean Oil)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 56.0},
    {"name": "Biodiesel (Palm Oil - Certified)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 59.3},
    {"name": "Hydrotreated Vegetable Oil (HVO)", "lcv_mj_per_g": 0.044, "wtw_gco2_per_mj": 22.0},
    {"name": "Bio-LNG", "lcv_mj_per_g": 0.050, "wtw_gco2_per_mj": 10.0},
    {"name": "Bio-Methanol", "lcv_mj_per_g": 0.0199, "wtw_gco2_per_mj": 11.0},

    # RFNBOs
    {"name": "Green Hydrogen", "lcv_mj_per_g": 0.120, "wtw_gco2_per_mj": 0.0},
    {"name": "Green Ammonia", "lcv_mj_per_g": 0.0186, "wtw_gco2_per_mj": 0.0},
    {"name": "E-Methanol", "lcv_mj_per_g": 0.0199, "wtw_gco2_per_mj": 1.0},
    {"name": "E-LNG", "lcv_mj_per_g": 0.050, "wtw_gco2_per_mj": 1.0},

    # Others
    {"name": "Onshore Power Supply (OPS)", "lcv_mj_per_g": 1.0, "wtw_gco2_per_mj": 0.0},
    {"name": "Synthetic Fuels", "lcv_mj_per_g": 0.042, "wtw_gco2_per_mj": 10.0},
    {"name": "Recycled Carbon Fuels (RCFs)", "lcv_mj_per_g": 0.042, "wtw_gco2_per_mj": 70.0},
]

def get_target_ghg_intensity(year):
    base = 91.16
    reduction = {
        2025: 0.02, 2026: 0.02, 2027: 0.02, 2028: 0.02, 2029: 0.02,
        2030: 0.06, 2031: 0.06, 2032: 0.06, 2033: 0.06, 2034: 0.06,
        2035: 0.14
    }
    return base * (1 - reduction.get(year, 0.0))

st.title("FuelEU Maritime GHG Intensity Calculator")

# === USER INPUTS ===
st.sidebar.header("Fuel Input")
fuel_defaults = pd.DataFrame(default_fuels)
selected_fuels = []

for i in range(1, 6):
    fuel_type = st.sidebar.selectbox(f"Fuel {i} type", ["None"] + list(fuel_defaults["name"]), index=0, key=f"fuel_{i}_type")
    if fuel_type != "None":
        mode = st.sidebar.radio(f"Use default or custom values for {fuel_type}?", ["Default", "Custom"], key=f"mode_{i}")
        mass = st.sidebar.number_input(f"{fuel_type} mass (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mass_{i}")
        if mass > 0:
            if mode == "Custom":
                lcv = st.sidebar.number_input(f"LCV for {fuel_type} (MJ/g)", value=0.04, key=f"lcv_{i}")
                ef = st.sidebar.number_input(f"WtW EF for {fuel_type} (gCO₂eq/MJ)", value=90.0, key=f"ef_{i}")
            else:
                entry = fuel_defaults[fuel_defaults.name == fuel_type].iloc[0]
                lcv, ef = entry['lcv_mj_per_g'], entry['wtw_gco2_per_mj']
            selected_fuels.append({"name": fuel_type, "mass_mt": mass, "lcv": lcv, "ef": ef})

st.sidebar.markdown("---")
# GWP standard selector
gwp_scope = st.sidebar.radio(
    "GWP Standard",
    ["AR4 (25/298)", "AR5 (29.8/273)"],
    index=0,
    help="Use AR4 for 2025 and AR5 from 2026 as per EMSA guidance"
)
# Compliance year selector
year = st.sidebar.selectbox("Compliance Year", list(range(2025, 2036)))
target_ghg_intensity = get_target_ghg_intensity(year)

# OPS and wind rewards
ops_discount = st.sidebar.selectbox("OPS Reduction (%)", [0, 1, 2, 3], index=0)
wind_discount = st.sidebar.selectbox("Wind-Assisted Reduction (%)", [0, 2, 4, 5], index=0)

# === CALCULATIONS ===
total_energy = 0.0
total_emissions = 0.0
fuel_rows = []
penalty_per_mj = 0.64 / 1000  # €0.64 per tonne CO2eq
gwp_vals = {"AR4 (25/298)": (25, 298), "AR5 (29.8/273)": (29.8, 273)}
CH4_gwp, N2O_gwp = gwp_vals[gwp_scope]

for fuel in selected_fuels:
    mass_g = fuel['mass_mt'] * 1_000_000
    energy = mass_g * fuel['lcv']
    # Tank-to-Wake emissions per gram
    ttw_per_g = 3.114 + 0.00005 * CH4_gwp + 0.00018 * N2O_gwp
    # EF per MJ
    ef_per_mj = ttw_per_g / fuel['lcv'] + fuel['ef']
    emissions = energy * ef_per_mj
    total_energy += energy
    total_emissions += emissions
    fuel_rows.append({
        "Fuel": fuel['name'],
        "Mass (MT)": f"{fuel['mass_mt']:.2f}",
        "Energy (MJ)": f"{energy:,.2f}",
        "Emissions (gCO₂eq)": f"{emissions:,.2f}"})

# Apply OPS and wind multiplicative rewards
reward_factor = (1 - ops_discount/100) * (1 - wind_discount/100)
total_emissions *= reward_factor

# === OUTPUT ===
st.subheader("Fuel Breakdown")
st.dataframe(pd.DataFrame(fuel_rows))

ghg_intensity = total_emissions / total_energy if total_energy > 0 else 0
balance = total_energy * (target_ghg_intensity - ghg_intensity)
penalty = 0.0 if balance >= 0 else abs(balance) * penalty_per_mj

col1, col2 = st.columns(2)
col1.metric("GHG Intensity (gCO₂eq/MJ)", f"{ghg_intensity:.5f}")
col1.metric("Target Intensity (gCO₂eq/MJ)", f"{target_ghg_intensity:.5f}")
col2.metric("Compliance Balance (gCO₂eq)", f"{balance:,.0f}")
col2.metric("Penalty (€)", f"{penalty:,.2f}")

# Forecast chart
years = list(range(2020, 2051, 5))
targets = [91.16] + [get_target_ghg_intensity(y) for y in years if y >= 2025]
fig, ax = plt.subplots()
ax.plot(years, targets, '--o')
ax.set_title("GHG Target Forecast 2020-2050 (5-year intervals)")
ax.set_xlabel("Year")
ax.set_ylabel("gCO₂eq/MJ")
st.pyplot(fig)
