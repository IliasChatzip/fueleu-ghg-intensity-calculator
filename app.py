# Streamlit Web App: Advanced FuelEU Maritime GHG Intensity Calculator

import streamlit as st
import pandas as pd

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
ghg_scope = st.sidebar.radio(
    "GHG Scope",
    ["CO₂ only", "Full (CO₂ + CH₄ + N₂O)"],
    index=1,
    help="Choose whether to include only CO₂ or also CH₄ and N₂O in Tank-to-Wake calculations."
)
pooling_option = st.sidebar.checkbox("Simulate pooling/trading of surplus", value=False, help="Toggle to simulate the use of surplus GHG savings via FuelEU pooling or credit transfer provisions.")
year = st.sidebar.selectbox("Compliance Year", list(range(2025, 2036)))
target_ghg_intensity = get_target_ghg_intensity(year)

ops_discount = st.sidebar.selectbox(
    "OPS Reduction (%)",
    [0, 1, 2, 3],
    index=0,
    help="Reward for use of Onshore Power Supply (OPS) during port stays. Max 3% emissions reduction allowed."
)
wind_discount = st.sidebar.selectbox(
    "Wind-Assisted Reduction (%)",
    [0, 2, 4, 5],
    index=0,
    help="Reward for using wind propulsion assistance. Reduction reflects certified propulsion effectiveness."
)

gwp_standard = st.sidebar.selectbox(
    "GWP Standard",
    ["AR5 (29.8/273)", "AR4 (25/298)"],
    index=1,
    help="Select the GWP standard for CH₄ and N₂O: AR5 or AR4"
),
    help="Select the GWP standard for CH₄ and N₂O: AR5 or AR4"
)
if gwp_standard.startswith("AR5"):
    gwp_ch4, gwp_n2o = 29.8, 273
else:
    gwp_ch4, gwp_n2o = 25, 298


# === CALCULATIONS ===
total_energy = 0.0
total_emissions = 0.0
fuel_rows = []
penalty_per_mj = 2.4 / 1000

for fuel in selected_fuels:
    mass_g = fuel['mass_mt'] * 1_000_000
    energy = mass_g * fuel['lcv']
    # Determine emissions based on GHG scope and GWP standard
    if ghg_scope == "CO₂ only":
        # CO₂-only: only CO₂ emissions
        co2_ttw_per_g = 3.114
        # Well-to-Tank default: only for major fossil fuels
        wtt = 0.0
        if fuel['name'] == "Heavy Fuel Oil (HFO)":
            wtt = 13.5
        elif fuel['name'] == "Marine Gas Oil (MGO)":
            wtt = 14.4
        co2_ef_dynamic = co2_ttw_per_g / fuel['lcv'] + wtt
        emissions = energy * co2_ef_dynamic
    else:
        # Full scope: include CH₄ and N₂O with selected GWP
        if fuel['name'] in ["Heavy Fuel Oil (HFO)", "Marine Gas Oil (MGO)"]:
            ttw_per_g = 3.114 + (0.00005 * gwp_ch4) + (0.00018 * gwp_n2o)
            wtt = 13.5 if fuel['name'] == "Heavy Fuel Oil (HFO)" else 14.4
            ef_dynamic = ttw_per_g / fuel['lcv'] + wtt
            emissions = energy * ef_dynamic
        else:
            emissions = energy * fuel['ef']
        total_energy += energy
    total_emissions += emissions

    fuel_rows.append({
        "Fuel": fuel['name'],
        "Mass (MT)": f"{fuel['mass_mt']:.2f}",
        "Energy (MJ)": f"{energy:,.2f}",
        "Emissions (gCO₂eq)": f"{emissions:,.2f}"
    })

# === APPLY OPS AND WIND ASSISTANCE CORRECTLY ===
reward_factor = (1 - ops_discount / 100) * (1 - wind_discount / 100)  # Applied multiplicatively per EU regulation
total_emissions *= reward_factor
st.caption("OPS and Wind rewards applied according to FuelEU Maritime Regulation Article 5(6) — multiplicative discount on WtW emissions.")

# === OUTPUT ===
import io

if fuel_rows:
    st.subheader("Fuel Breakdown")
    df_fuel = pd.DataFrame(fuel_rows)
    st.dataframe(df_fuel)

    ghg_intensity = total_emissions / total_energy if total_energy > 0 else 0
    balance = total_energy * (target_ghg_intensity - ghg_intensity)
    penalty = 0.0 if balance >= 0 else abs(balance) / 1000 * 0.64

    st.subheader("Summary")
    st.metric("Total Energy (MJ)", f"{total_energy:,.0f}")
    st.metric("Total Emissions (gCO₂eq)", f"{total_emissions:,.0f}")
    st.metric("GHG Intensity (gCO₂eq/MJ)", f"{ghg_intensity:.5f}")
    st.metric("Compliance Balance (gCO₂eq)", f"{balance:,.0f}")
    st.metric("Penalty (€)", f"{penalty:,.2f}")

    if penalty == 0 and balance > 0 and pooling_option:
        surplus_eur = (balance / 1000) * 2.4
        st.success(f"Surplus margin: {surplus_eur:,.2f} EUR equivalent for {balance:,.0f} gCO2eq below target. May be used in pooling or trading as per FuelEU provisions.")

    
    
    

    
else:
    st.info("Please enter fuel inputs in the sidebar to see results.")
