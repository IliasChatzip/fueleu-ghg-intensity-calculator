import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
# Global Warming Potentials
GWP_VALUES = {
    "AR4": {"CH4": 25, "N2O": 298},
    "AR5": {"CH4": 29.8, "N2O": 273}
}

# Fuel database: default WtT emission factors (gCO2eq/MJ)
FUEL_DATABASE = {
    "Heavy Fuel Oil (HFO)": {"lcv": 0.0405, "wtt": 13.5},
    "Marine Gas Oil (MGO)": {"lcv": 0.0427, "wtt": 14.4},
    "VLSFO": {"lcv": 0.0410, "wtt": 11.2},
    "LNG": {"lcv": 0.0500, "wtt": 79.0},
    "LPG": {"lcv": 0.0460, "wtt": 76.0},
    "Methanol (fossil)": {"lcv": 0.0199, "wtt": 94.0},
    "Biodiesel (UCO)": {"lcv": 0.0373, "wtt": 14.9},
    # ... add other fuels as needed
}

# FuelEU GHG Intensity targets
def get_target(year):
    base = 91.16
    if 2025 <= year <= 2029:
        return base * 0.98
    if 2030 <= year <= 2034:
        return base * 0.94
    if year == 2035:
        return base * 0.86
    # Linear interpolation 2036-2050 to 20% of base at 2050
    if year > 2035:
        return base * (1 - 0.14 - (0.66 * (year - 2035) / 15))
    return base

st.title("FuelEU Maritime GHG Intensity Calculator")

# === SIDEBAR INPUTS ===
st.sidebar.header("Input Parameters")
# Fuel selection
fuel_inputs = []
for i in range(1, 6):
    name = st.sidebar.selectbox(f"Fuel {i}", ["None"] + list(FUEL_DATABASE), key=f"fuel{i}")
    if name != "None":
        amount = st.sidebar.number_input(f"Amount (MT) of {name}", min_value=0.0, value=0.0, step=1.0, key=f"amt{i}")
        if amount > 0:
            fuel_inputs.append((name, amount))
# GWP standard
gwp_choice = st.sidebar.radio("GWP Standard", ["AR4", "AR5"], index=0,
    help="Use AR4 for 2025 per regulation; switch to AR5 from 2026 on.")
# Year selector
year = st.sidebar.slider("Compliance Year", 2025, 2035, 2025)
# OPS and wind
ops_pct = st.sidebar.selectbox("OPS reduction (%)", [0, 1, 2, 3], index=0)
wind_pct = st.sidebar.selectbox("Wind reduction (%)", [0, 2, 4, 5], index=0)
# Penalty rate matching BetterSea
penalty_rate = st.sidebar.number_input("Penalty rate (€ per tonne CO2eq)", min_value=0.0, value=0.6675, step=0.01)

# === CALCULATIONS ===
total_energy = 0.0
total_emissions = 0.0
rows = []
gwp = GWP_VALUES[gwp_choice]
for name, mt in fuel_inputs:
    data = FUEL_DATABASE[name]
    mass_g = mt * 1e6
    lcv = data['lcv']
    energy = mass_g * lcv
    # TTW factor g/g
    ttw = 3.114 + 0.00005 * gwp['CH4'] + 0.00018 * gwp['N2O']
    # EF per MJ
    ef = ttw / lcv + data['wtt']
    emis = energy * ef
    # accumulate
    total_energy += energy
    total_emissions += emis
    rows.append((name, mt, energy, emis, ef))
# Apply OPS and wind
factor = (1 - ops_pct/100) * (1 - wind_pct/100)
adjusted_emissions = total_emissions * factor
# GHG intensity
ghg_int = adjusted_emissions / total_energy if total_energy else 0
# Targets and compliance
target = get_target(year)
balance = total_energy * (target - ghg_int)
penalty = 0 if balance >= 0 else abs(balance)/1000 * penalty_rate

# === OUTPUTS ===
st.subheader("Fuel Breakdown")
df = pd.DataFrame(rows, columns=["Fuel","Amount (MT)","Energy (MJ)","Emissions (gCO2eq)","EF (gCO2eq/MJ)"])
st.dataframe(df)

st.subheader("Results")
col1, col2 = st.columns(2)
col1.metric("GHG Intensity (gCO2eq/MJ)", f"{ghg_int:.4f}")
col1.metric("Target Intensity (gCO2eq/MJ)", f"{target:.4f}")
col2.metric("Penalty (€)", f"{penalty:,.2f}")

# 5-year forecast chart
years = [2020] + list(range(2025, 2051, 5))
targ = [91.16] + [get_target(y) for y in years[1:]]
fig, ax = plt.subplots(figsize=(6,3))
ax.plot(years, targ, '--o')
ax.set_title("GHG Target Forecast 2020-2050 (5yr intervals)")
ax.set_xlabel("Year")
ax.set_ylabel("gCO2eq/MJ")
st.pyplot(fig)
