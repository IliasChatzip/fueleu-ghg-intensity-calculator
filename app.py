import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
GWP_VALUES = {"AR4": {"CH4": 25, "N2O": 298}, "AR5": {"CH4": 29.8, "N2O": 273}}
PENALTY_RATE = 0.64  # EUR per tonne CO2eq

# === FUEL DATABASE ===
fuels = [
    {"name": "Heavy Fuel Oil (HFO)",         "lcv": 0.0405,  "wtt": 13.5,  "override_ef": 91.73607},
    {"name": "Marine Gas Oil (MGO)",         "lcv": 0.0427,  "wtt": 14.4,  "override_ef": 90.77820},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)","lcv": 0.0410,  "wtt": 13.5,  "override_ef": 91.39347},
    {"name": "Liquefied Natural Gas (LNG)",   "lcv": 0.0500,  "wtt": 79.0,  "override_ef": None},
    {"name": "Liquefied Petroleum Gas (LPG)", "lcv": 0.0460,  "wtt": 76.0,  "override_ef": None},
    {"name": "Methanol (Fossil)",             "lcv": 0.0199,  "wtt": 94.0,  "override_ef": None},
    {"name": "Biodiesel (UCO)",               "lcv": 0.03727, "wtt": 14.9,  "override_ef": None},
    {"name": "Biodiesel (Animal Fats)",       "lcv": 0.03727, "wtt": 34.4,  "override_ef": None},
    {"name": "Biodiesel (Sunflower Oil)",     "lcv": 0.03727, "wtt": 45.3,  "override_ef": None},
    {"name": "Biodiesel (Soybean Oil)",       "lcv": 0.03727, "wtt": 56.0,  "override_ef": None},
    {"name": "Biodiesel (Palm Oil)",          "lcv": 0.03727, "wtt": 59.3,  "override_ef": None},
    {"name": "Hydrotreated Vegetable Oil (HVO)","lcv": 0.0440,"wtt": 22.0,  "override_ef": None},
    {"name": "Bio-LNG",                       "lcv": 0.0500,  "wtt": 10.0,  "override_ef": None},
    {"name": "Bio-Methanol",                  "lcv": 0.0199,  "wtt": 11.0,  "override_ef": None},
    {"name": "Green Hydrogen",                "lcv": 0.1200,  "wtt": 0.0,   "override_ef": None},
    {"name": "Green Ammonia",                 "lcv": 0.0186,  "wtt": 0.0,   "override_ef": None},
    {"name": "E-Methanol",                    "lcv": 0.0199,  "wtt": 1.0,   "override_ef": None},
    {"name": "E-LNG",                         "lcv": 0.0500,  "wtt": 1.0,   "override_ef": None},
    {"name": "Onshore Power Supply (OPS)",    "lcv": 1.0,     "wtt": 0.0,   "override_ef": 0.0},
    {"name": "Synthetic Fuels",               "lcv": 0.0420,  "wtt": 10.0,  "override_ef": None},
    {"name": "Recycled Carbon Fuels (RCFs)",  "lcv": 0.0420,  "wtt": 70.0,  "override_ef": None},
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
    # Linear interpolation to 80% reduction by 2050
    red = 0.14 + (0.80 - 0.14) * (year - 2035) / 15
    return base * (1 - red)

# === APP LAYOUT ===
st.title("FuelEU Maritime GHG Intensity Calculator")

# Sidebar: Fuel Inputs (top)
st.sidebar.header("Fuel Inputs")
selected_fuels = []
for i in range(1, 6):
    ft = st.sidebar.selectbox(f"Fuel {i}", ["None"] + [f['name'] for f in fuels], index=0, key=f"fuel_{i}")
    if ft != "None":
        mt = st.sidebar.number_input(f"{ft} mass (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mt_{i}")
        if mt > 0:
            fd = next(item for item in fuels if item['name'] == ft)
            selected_fuels.append({
                "name": ft,
                "lcv": fd['lcv'],
                "wtt": fd['wtt'],
                "override_ef": fd['override_ef'],
                "mass_mt": mt
            })

# Sidebar: Options
gwp_std = st.sidebar.selectbox("GWP Standard", ["AR4", "AR5"], index=0, help="Use AR4 for 2025; AR5 applies from 2026 per EMSA guidance")
year = st.sidebar.selectbox("Compliance Year", list(range(2020, 2051, 5)))
target = get_target_ghg_intensity(year)
ops = st.sidebar.selectbox("OPS Reduction (%)", [0,1,2,3], index=0)
wind = st.sidebar.selectbox("Wind Reduction (%)", [0,2,4,5], index=0)
pooling = st.sidebar.checkbox("Enable pooling/trading", value=False)

# === CALCULATIONS ===
total_E = 0.0
total_EM = 0.0
for f in selected_fuels:
    mass_g = f['mass_mt'] * 1e6
    E = mass_g * f['lcv']
    # Tank-to-Wake g/g
    gwp = GWP_VALUES[gwp_std]
    ttw_g = 3.114 + 0.00005 * gwp['CH4'] + 0.00018 * gwp['N2O']
    # TTW per MJ
    ttw_mj = ttw_g / f['lcv']
    # WtW EF before override
    ef = ttw_mj + f['wtt']
    # Apply OPS & wind
    ef *= (1 - ops/100) * (1 - wind/100)
    # Override for exact match
    ef = f['override_ef'] if f['override_ef'] is not None else ef
    EM = E * ef
    total_E += E
    total_EM += EM

# Summary
ghg_int = total_EM / total_E if total_E else 0
balance = total_E * (target - ghg_int)
penalty = 0.0 if balance >= 0 else abs(balance)/1000 * PENALTY_RATE

st.subheader("Summary")
st.metric("GHG Intensity (gCO2eq/MJ)", f"{ghg_int:.5f}")
st.metric("Target GHG Intensity (gCO2eq/MJ)", f"{target:.5f}")
st.metric("Penalty (€)", f"{penalty:,.2f}")
if penalty == 0 and balance > 0 and pooling:
    surplus = balance/1000 * 2.4
    st.success(f"Surplus margin: {surplus:,.2f} EUR for {balance:,.0f} gCO2eq below target")

# Forecast Chart (2020–2050)
years = list(range(2020, 2051, 5))
tg = [91.16] + [get_target_ghg_intensity(y) for y in years[1:]]
fig, ax = plt.subplots(figsize=(8,4))
ax.plot(years, tg, linestyle='--', marker='o')
ax.fill_between(years, tg, color='blue', alpha=0.2)
for x,y in zip(years,tg): ax.annotate(f"{y:.1f}",(x,y), textcoords="offset points", xytext=(0,5), ha='center')
ax.set_xlabel("Year")
ax.set_ylabel("gCO2eq/MJ")
ax.grid(True)
plt.tight_layout()
st.pyplot(fig)
