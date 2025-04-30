# Streamlit Web App: FuelEU Maritime GHG Intensity Calculator (Expanded)

import streamlit as st
import pandas as pd

# === EMISSION FACTORS DATABASE (Expanded) ===
fuel_defaults = pd.DataFrame([
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
])

st.title("FuelEU Maritime GHG Intensity Calculator")

st.markdown("""
Enter the fuel mix below. The calculator will compute the total energy, total emissions, and GHG intensity (gCO₂eq/MJ).
""")

# === USER INPUT ===
selected_fuels = []
st.sidebar.header("Fuel Input")
for i in range(1, 6):
    fuel_type = st.sidebar.selectbox(f"Fuel {i} type", ["None"] + list(fuel_defaults["name"]), index=0, key=f"fuel_{i}_type")
    if fuel_type != "None":
        mass = st.sidebar.number_input(f"{fuel_type} mass (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mass_{i}")
        if mass > 0:
            selected_fuels.append({"name": fuel_type, "mass_mt": mass})

# === CALCULATIONS ===
total_energy = 0.0
total_emissions = 0.0
fuel_rows = []

target_ghg_intensity = 89.33680  # FuelEU GHG intensity target
penalty_per_mj = 2.4 / 1000  # EUR/gCO2eq excess per MJ

for fuel in selected_fuels:
    entry = fuel_defaults[fuel_defaults.name == fuel['name']].iloc[0]
    lcv = entry['lcv_mj_per_g']
    ef = entry['wtw_gco2_per_mj']
    mass_g = fuel['mass_mt'] * 1_000_000
    energy = mass_g * lcv
    emissions = energy * ef

    total_energy += energy
    total_emissions += emissions

    fuel_rows.append({
        "Fuel": fuel['name'],
        "Mass (MT)": fuel['mass_mt'],
        "Energy (MJ)": round(energy, 0),
        "Emissions (gCO₂eq)": round(emissions, 0)
    })

# === OUTPUT ===
if fuel_rows:
    st.subheader("Fuel Breakdown")
    st.dataframe(pd.DataFrame(fuel_rows))

    ghg_intensity = total_emissions / total_energy if total_energy > 0 else 0
    balance = total_energy * (target_ghg_intensity - ghg_intensity)
    penalty = 0.0 if balance >= 0 else abs(balance) * penalty_per_mj

    st.subheader("Summary")
    st.metric("Total Energy (MJ)", f"{total_energy:,.0f}")
    st.metric("Total Emissions (gCO₂eq)", f"{total_emissions:,.0f}")
    st.metric("GHG Intensity (gCO₂eq/MJ)", f"{ghg_intensity:.5f}")
    st.metric("Compliance Balance (gCO₂eq)", f"{balance:,.0f}")
    st.metric("Penalty (€)", f"{penalty:,.2f}")
else:
    st.info("Please enter fuel inputs in the sidebar to see results.")
