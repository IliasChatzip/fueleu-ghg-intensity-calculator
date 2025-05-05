import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt



# === FUEL DATABASE ===
default_fuels = [
    {"name": "Heavy Fuel Oil (HFO)", "lcv_mj_per_g": 0.0405, "wtw_gco2_per_mj": (3.114 + 0.00005*29.8 + 0.00018*273)/0.0405 + 13.5},
    {"name": "Marine Gas Oil (MGO)", "lcv_mj_per_g": 0.0427, "wtw_gco2_per_mj": (3.206 + 0.00005*29.8 + 0.00018*273)/0.0427 + 14.4},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)", "lcv_mj_per_g": 0.041, "wtw_gco2_per_mj": 91.0},
    {"name": "Liquefied Natural Gas (LNG)", "lcv_mj_per_g": 0.050, "wtw_gco2_per_mj": 79.0},
    {"name": "Liquefied Petroleum Gas (LPG)", "lcv_mj_per_g": 0.046, "wtw_gco2_per_mj": 76.0},
    {"name": "Methanol (Fossil)", "lcv_mj_per_g": 0.0199, "wtw_gco2_per_mj": 94.0},
    {"name": "Biodiesel (UCO)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 14.9},
    {"name": "Biodiesel (Animal Fats)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 34.4},
    {"name": "Biodiesel (Sunflower Oil)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 45.3},
    {"name": "Biodiesel (Soybean Oil)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 56.0},
    {"name": "Biodiesel (Palm Oil - Certified)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 59.3},
    {"name": "Hydrotreated Vegetable Oil (HVO)", "lcv_mj_per_g": 0.044, "wtw_gco2_per_mj": 22.0},
    {"name": "Bio-LNG", "lcv_mj_per_g": 0.050, "wtw_gco2_per_mj": 10.0},
    {"name": "Bio-Methanol", "lcv_mj_per_g": 0.0199, "wtw_gco2_per_mj": 11.0},
    {"name": "Green Hydrogen", "lcv_mj_per_g": 0.120, "wtw_gco2_per_mj": 0.0},
    {"name": "Green Ammonia", "lcv_mj_per_g": 0.0186, "wtw_gco2_per_mj": 0.0},
    {"name": "E-Methanol", "lcv_mj_per_g": 0.0199, "wtw_gco2_per_mj": 1.0},
    {"name": "E-LNG", "lcv_mj_per_g": 0.050, "wtw_gco2_per_mj": 1.0},
    {"name": "Onshore Power Supply (OPS)", "lcv_mj_per_g": 1.0, "wtw_gco2_per_mj": 0.0},
    {"name": "Synthetic Fuels", "lcv_mj_per_g": 0.042, "wtw_gco2_per_mj": 10.0},
    {"name": "Recycled Carbon Fuels (RCFs)", "lcv_mj_per_g": 0.042, "wtw_gco2_per_mj": 70.0},
]

# === TARGET METHOD ===
def get_target_ghg_intensity(year):
    base = 91.16
    if year <= 2029:
        reduction = 0.02
    elif year <= 2034:
        reduction = 0.06
    elif year == 2035:
        reduction = 0.14
    elif year <= 2050:
        reduction = 0.14 + (0.80 - 0.14) * (year - 2035) / 15
    else:
        reduction = 0.80
    return base * (1 - reduction)

# === APP TITLE ===
st.title("FuelEU Maritime GHG Intensity Calculator")

# === SIDEBAR ===
st.sidebar.header("Inputs & Options")
fuel_defaults = pd.DataFrame(default_fuels)
selected_fuels = []
for i in range(1, 6):
    ft = st.sidebar.selectbox(f"Fuel {i}", ["None"] + fuel_defaults["name"].tolist(), key=f"fuel_{i}")
    if ft != "None":
        mode = st.sidebar.radio(f"{ft} values", ["Default", "Custom"], key=f"mode_{i}")
        mass = st.sidebar.number_input(
            f"{ft} mass (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mass_{i}"
        )
        if mass > 0:
            if mode == "Custom":
                lcv = st.sidebar.number_input(f"LCV {ft}", 0.04, key=f"lcv_{i}")
                ef = st.sidebar.number_input(f"EF {ft}", 90.0, key=f"ef_{i}")
            else:
                row = fuel_defaults[fuel_defaults.name == ft].iloc[0]
                lcv, ef = row.lcv_mj_per_g, row.wtw_gco2_per_mj
            selected_fuels.append({"name": ft, "mass_mt": mass, "lcv": lcv, "ef": ef})

st.sidebar.markdown("---")
# GHG scope
ghg_scope = st.sidebar.radio(
    "GHG Scope",
    ["CO2 only", "Full (CO2 + CH4 + N2O)"],
    index=1,
    help="Include CH4 and N2O for full scope or CO2 only for simplified mode."
)
# Pooling option
pooling = st.sidebar.checkbox(
    "Simulate pooling/trading of surplus",
    value=False,
    help="When selected, displays surplus margin that could be pooled or traded."
)
# Compliance year
year = st.sidebar.selectbox(
    "Compliance Year",
    list(range(2025, 2036)),
    index=0,
    help="Select the reporting year for target GHG intensity."
)
target = get_target_ghg_intensity(year)
# Rewards
ops = st.sidebar.selectbox("OPS Reduction (%)", [0, 1, 2, 3], index=0)
wind = st.sidebar.selectbox("Wind-Assisted Reduction (%)", [0, 2, 4, 5], index=0)
st.sidebar.markdown("---")
# GWP standard
gwp_standard = st.sidebar.selectbox(
    "GWP Standard",
    ["AR5 (29.8/273)", "AR4 (25/298)"],
    index=1,
    help="Select GWP for CH4/N2O: AR4 for 2025; AR5 applies from 2026+ per EMSA."
)
if gwp_standard.startswith("AR5"):
    gwp_ch4, gwp_n2o = 29.8, 273
else:
    gwp_ch4, gwp_n2o = 25, 298

# === CALCULATIONS ===
total_energy = 0.0
total_emissions = 0.0
fuel_rows = []
penalty_rate = 0.64  # EUR per tonne CO2eq (matches BetterSea/Zero44 defaults)
