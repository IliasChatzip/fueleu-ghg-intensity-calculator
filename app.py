import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === FUEL DATABASE ===
default_fuels = [
    {"name": "Heavy Fuel Oil (HFO)", "lcv_mj_per_g": 0.0405},
    {"name": "Marine Gas Oil (MGO)", "lcv_mj_per_g": 0.0427},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)", "lcv_mj_per_g": 0.041},
    {"name": "Liquefied Natural Gas (LNG)", "lcv_mj_per_g": 0.050},
    {"name": "Onshore Power Supply (OPS)", "lcv_mj_per_g": 1.0, "ef_static": 0.0},
]

# Default static EF for fuels (WtT included)
static_efs = {
    "HFO": (3.114 + 0.00005 * 25 + 0.00018 * 298) / 0.0405 + 13.5,  # AR4 + WtT
    "MGO": (3.206 + 0.00005 * 25 + 0.00018 * 298) / 0.0427 + 14.4,
    "VLSFO": 91.0,
    "LNG": 79.0,
    "OPS": 0.0
}

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

# === STREAMLIT APP ===
st.title("FuelEU Maritime GHG Intensity Calculator")

# Sidebar Inputs
st.sidebar.header("Fuel Mix & Options")
fuel_defaults = pd.DataFrame(default_fuels)
selected = []
for i in range(1, 6):
    ft = st.sidebar.selectbox(f"Fuel {i}", ["None"] + fuel_defaults["name"].tolist(), key=f"fuel{i}")
    if ft != "None":
        mass = st.sidebar.number_input(f"{ft} mass (MT)", 0.0, 1e6, 0.0, step=100.0, key=f"mass{i}")
        if mass > 0:
            selected.append({"name": ft, "mass": mass, "lcv": fuel_defaults.query("name==@ft")["lcv_mj_per_g"].iloc[0]})

year = st.sidebar.selectbox("Compliance Year", list(range(2025, 2036)), index=0)
target = get_target_ghg_intensity(year)

ops = st.sidebar.selectbox("OPS Reduction (%)", [0,1,2,3], index=0)
wind = st.sidebar.selectbox("Wind-Assisted Reduction (%)", [0,2,4,5], index=0)

# GWP standard default AR4
gwp_ch4, gwp_n2o = 25, 298
st.sidebar.markdown("*Using AR4 values for 2025 as per FuelEU; AR5 applies from 2026*")

# Penalty rate per tonne
penalty_rate = st.sidebar.number_input("Penalty rate (EUR/tonne CO2)", 0.01, 10.0, value=2.4, step=0.1)

# === CALCULATIONS ===
total_energy = 0.0
total_emissions = 0.0
rows = []
for f in selected:
    mass_g = f["mass"] * 1e6
    energy = mass_g * f["lcv"]
    # compute dynamic EF for fuel
    base_co2 = 3.114 if f["name"] in ["HFO","MGO","VLSFO","LNG"] else 0.0
    ttw = base_co2 + 0.00005 * gwp_ch4 + 0.00018 * gwp_n2o
    wtt = 0.0
    if f["name"] == "Heavy Fuel Oil (HFO)": wtt = 13.5
    if f["name"] == "Marine Gas Oil (MGO)": wtt = 14.4
    ef_dyn = ttw / f["lcv"] + wtt
    emissions = energy * ef_dyn
    # apply rewards
    emissions *= (1-ops/100)*(1-wind/100)

    total_energy += energy
    total_emissions += emissions
    rows.append({"Fuel": f["name"], "Mass (MT)": f["mass"], "Energy (MJ)": energy, "Emissions (gCO2eq)": emissions})

# === OUTPUT ===
if rows:
    df_out = pd.DataFrame(rows)
    st.subheader("Fuel Breakdown")
    st.dataframe(df_out)

    gi = total_emissions/total_energy if total_energy else 0
    balance = total_energy*(target-gi)
    penalty = 0 if balance>=0 else abs(balance)/1e6*penalty_rate  # balance in g -> tonnes

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("GHG Intensity (g/MJ)", f"{gi:.3f}")
    c2.metric("Target (g/MJ)", f"{target:.3f}")
    c3.metric("Compliance Balance (g)", f"{balance:,.0f}")
    c4.metric("Penalty (EUR)", f"{penalty:,.2f}")

    # Forecast chart 2020-2050
    yrs = [2020] + list(range(2025,2051,5))
    vals = [91.16]+[get_target_ghg_intensity(y) for y in yrs[1:]]
    fig, ax = plt.subplots(figsize=(6,3))
    ax.plot(yrs,vals,'--o')
    ax.fill_between(yrs,vals,alpha=0.2)
    ax.set_title("GHG Target Forecast 2020-2050")
    ax.set_xlabel("Year")
    ax.set_ylabel("gCO2eq/MJ")
    st.pyplot(fig)
else:
    st.info("Enter fuel masses to see results.")
