import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === EMISSION FACTORS DATABASE ===
default_fuels = [
    {"name": "Heavy Fuel Oil (HFO)", "lcv": 0.0405, "wtt": 13.5},
    {"name": "Marine Gas Oil (MGO)", "lcv": 0.0427, "wtt": 14.4},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)", "lcv": 0.041, "wtt": 13.5},
    {"name": "Liquefied Natural Gas (LNG)", "lcv": 0.050, "wtt": 11.2},
    {"name": "Liquefied Petroleum Gas (LPG)", "lcv": 0.046, "wtt": 11.2},
]

# GWP standards
GWP = {
    "AR4": {"CH4": 25, "N2O": 298},
    "AR5": {"CH4": 29.8, "N2O": 273}
}

# Sidebar inputs
st.sidebar.header("Settings")
gwp_std = st.sidebar.selectbox("GWP Standard", ["AR4", "AR5"], index=0)
scope = st.sidebar.selectbox("GHG Scope", ["CO2 only", "Full (CO2+CH4+N2O)"], index=1)
year = st.sidebar.selectbox("Compliance Year", list(range(2025, 2051)), index=0)
target = 91.16 * (1 - (0.02 if year<2030 else 0.06 if year<2035 else 0.14 if year==2035 else (0.14 + (year-2035)*(0.80-0.14)/15)))
ops = st.sidebar.selectbox("OPS reduction (%)", [0,1,2,3], index=0)
wind = st.sidebar.selectbox("Wind reduction (%)", [0,2,4,5], index=0)
pooling = st.sidebar.checkbox("Enable pooling", value=False)

# Input fuels
st.sidebar.header("Fuel Inputs")
inputs=[]
for fuel in default_fuels:
    mt = st.sidebar.number_input(fuel['name']+" (MT)", min_value=0.0, value=0.0, step=100.0, key=fuel['name'])
    if mt>0:
        inputs.append({"name": fuel['name'],"lcv":fuel['lcv'],"wtt":fuel['wtt'],"mass":mt})

# Main logic
if inputs:
    total_E=0
    total_em=0
    rows=[]
    for f in inputs:
        m_g = f['mass']*1e6
        E = m_g * f['lcv']
        if scope=="CO2 only":
            ttw_g = 3.114
            ef = ttw_g/f['lcv'] + f['wtt']
        else:
            G = GWP[gwp_std]
            ttw_g = 3.114 + 0.00005*G['CH4'] + 0.00018*G['N2O']
            ef = ttw_g/f['lcv'] + f['wtt']
        em = E * ef
        total_E += E
        total_em += em
        rows.append({"Fuel":f['name'],"Energy_MJ":E,"Emissions_g":em})
    # rewards
    total_em *= (1-ops/100)*(1-wind/100)
    intensity = total_em/total_E
    balance = total_E*(target - intensity)
    penalty = 0 if balance>=0 else abs(balance)/1000*0.64
    st.subheader("Fuel breakdown")
    st.dataframe(pd.DataFrame(rows))
    st.subheader("Summary")
    st.metric("Intensity (g/MJ)",f"{intensity:.5f}")
    st.metric("Target (g/MJ)",f"{target:.5f}")
    st.metric("Balance (g)",f"{balance:,.0f}")
    st.metric("Penalty (€)",f"{penalty:,.2f}")
    # forecast chart
    yrs = [2020]+list(range(2025,2051,5))
    vals = [91.16]+[91.16*(1-0.02) if y<2030 else 91.16*(1-0.06) if y<2035 else 91.16*(1-0.14) if y==2035 else 91.16*(1-0.80) for y in yrs[1:]]
    fig,ax=plt.subplots()
    ax.plot(yrs,vals,marker='o')
    ax.set_xlabel('Year')
    ax.set_ylabel('Target (g/MJ)')
    st.pyplot(fig)
else:
    st.info("Enter fuel inputs to calculate.")
