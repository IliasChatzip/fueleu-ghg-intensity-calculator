import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
GWP_VALUES = {"AR4": {"CH4": 25, "N2O": 298}, "AR5": {"CH4": 29.8, "N2O": 273}}
PENALTY_RATE = 0.64  # EUR per tonne CO2eq

# === FUEL DATABASE ===
fuels = [
    {"name": "Heavy Fuel Oil (HFO)", "lcv": 0.0405, "wtt": 13.5},
    {"name": "Marine Gas Oil (MGO)", "lcv": 0.0427, "wtt": 14.4},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)", "lcv": 0.041, "wtt": 13.5},
    {"name": "Liquefied Natural Gas (LNG)", "lcv": 0.050, "wtt": 79.0},
    {"name": "Liquefied Petroleum Gas (LPG)", "lcv": 0.046, "wtt": 76.0},
    {"name": "Methanol (Fossil)", "lcv": 0.0199, "wtt": 94.0},
    {"name": "Biodiesel (UCO)", "lcv": 0.03727, "wtt": 14.9},
    {"name": "Biodiesel (Animal Fats)", "lcv": 0.03727, "wtt": 34.4},
    {"name": "Biodiesel (Sunflower Oil)", "lcv": 0.03727, "wtt": 45.3},
    {"name": "Biodiesel (Soybean Oil)", "lcv": 0.03727, "wtt": 56.0},
    {"name": "Biodiesel (Palm Oil - Certified)", "lcv": 0.03727, "wtt": 59.3},
    {"name": "Hydrotreated Vegetable Oil (HVO)", "lcv": 0.044, "wtt": 22.0},
    {"name": "Bio-LNG", "lcv": 0.050, "wtt": 10.0},
    {"name": "Bio-Methanol", "lcv": 0.0199, "wtt": 11.0},
    {"name": "Green Hydrogen", "lcv": 0.120, "wtt": 0.0},
    {"name": "Green Ammonia", "lcv": 0.0186, "wtt": 0.0},
    {"name": "E-Methanol", "lcv": 0.0199, "wtt": 1.0},
    {"name": "E-LNG", "lcv": 0.050, "wtt": 1.0},
    {"name": "Onshore Power Supply (OPS)", "lcv": 1.0, "wtt": 0.0},
    {"name": "Synthetic Fuels", "lcv": 0.042, "wtt": 10.0},
    {"name": "Recycled Carbon Fuels (RCFs)", "lcv": 0.042, "wtt": 70.0},
]

# === HELPERS ===
def get_target_ghg_intensity(year):
    base = 91.16
    if year < 2025:
        return base
    if year <= 2029:
        return base * 0.98
    if year <= 2034:
        return base * 0.94
    if year == 2035:
        return base * 0.86
    reduction = 0.14 + (0.80 - 0.14) * (year - 2035) / 15
    return base * (1 - reduction)

# === APP LAYOUT ===
st.title("FuelEU Maritime GHG Intensity Calculator")

# Sidebar: Fuel Inputs first
st.sidebar.header("Fuel Inputs")
selected_fuels = []
for i in range(1, 6):
    fuel_opt = st.sidebar.selectbox(
        f"Fuel {i}", ["None"] + [f['name'] for f in fuels], index=0, key=f"fuel_{i}"
    )
    if fuel_opt != "None":
        mass_mt = st.sidebar.number_input(
            f"{fuel_opt} mass (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mt_{i}"
        )
        if mass_mt > 0:
            fd = next(f for f in fuels if f['name'] == fuel_opt)
            selected_fuels.append({"name": fuel_opt, "lcv": fd['lcv'], "wtt": fd['wtt'], "mt": mass_mt})

# Sidebar: Other Options
st.sidebar.header("Options")
gwp_standard = st.sidebar.selectbox(
    "GWP Standard", ["AR4", "AR5"], index=0,
    help="Use AR4 for 2025; AR5 applies from 2026 per EMSA guidance"
)
year = st.sidebar.selectbox("Compliance Year", list(range(2020, 2051, 5)))
target = get_target_ghg_intensity(year)
ops = st.sidebar.selectbox("OPS Reduction (%)", [0, 1, 2, 3], index=0)
wind = st.sidebar.selectbox("Wind Reduction (%)", [0, 2, 4, 5], index=0)
pooling = st.sidebar.checkbox("Enable pooling", value=False)

# === CALCULATIONS ===
total_E = 0.0
total_em = 0.0
for fuel in selected_fuels:
    mass_g = fuel['mt'] * 1e6
    E = mass_g * fuel['lcv']
    gwp = GWP_VALUES[gwp_standard]
    ttw_g = 3.114 + 0.00005 * gwp['CH4'] + 0.00018 * gwp['N2O']
    ttw_mj = ttw_g / fuel['lcv']
    ef = ttw_mj + fuel['wtt']
    ef *= (1 - ops/100) * (1 - wind/100)
    em = E * ef
    total_E += E
    total_em += em

# Metrics
ghg_int = total_em / total_E if total_E > 0 else 0
bal = total_E * (target - ghg_int)
pen = 0 if bal >= 0 else abs(bal) / 1000 * PENALTY_RATE

# Display Summary
st.subheader("Summary")
st.metric("GHG Intensity (gCO2eq/MJ)", f"{ghg_int:.5f}")
st.metric("Target (gCO2eq/MJ)", f"{target:.2f}")
st.metric("Penalty (€)", f"{pen:.2f}")
if pen == 0 and bal > 0 and pooling:
    surplus = bal / 1000 * 2.4
    st.success(f"Surplus margin: {surplus:.2f} EUR equivalent for {bal:.0f} gCO2eq below target.")

# Forecast Chart
years = list(range(2020, 2051, 5))
tg = [91.16] + [get_target_ghg_intensity(y) for y in years[1:]]
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(years, tg, linestyle='--', marker='o')
ax.fill_between(years, tg, alpha=0.2)
for x, y in zip(years, tg): ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0,5), ha='center')
ax.set_xlabel("Year")
ax.set_ylabel("gCO2eq/MJ")
ax.grid(True)
plt.tight_layout()
st.pyplot(fig)
