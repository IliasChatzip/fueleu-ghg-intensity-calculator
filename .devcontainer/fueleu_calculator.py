import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# Fuel database (imported from canvas)
import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
from datetime import datetime

FUELS = [
    {"name": "Heavy Fuel Oil (HFO)", "price": 469, "lcv": 0.0405, "wtt": 13.5, "ttw_co2": 3.114, "ttw_ch4": 0.00005, "ttw_n20": 0.00018, "rfnbo": False},
    {"name": "Low Fuel Oil (LFO)", "price": 750, "lcv": 0.0410, "wtt": 13.2, "ttw_co2": 3.151, "ttw_ch4": 0.00005, "ttw_n20": 0.00018, "rfnbo": False},
    {"name": "Marine Gas Oil (MGO)", "price": 900, "lcv": 0.0427, "wtt": 14.4, "ttw_co2": 3.206, "ttw_ch4": 0.00005, "ttw_n20": 0.00018, "rfnbo": False},
    {"name": "Liquefied Natural Gas (LNG)", "price": 780, "lcv": 0.0491, "wtt": 18.5, "ttw_co2": 2.750, "ttw_ch4": 0.001276, "ttw_n20": 0.00011, "rfnbo": False},
    {"name": "Liquefied Petroleum Gas (LPG)", "price": 600, "lcv": 0.0460, "wtt": 7.8, "ttw_co2": 3.015, "ttw_ch4": 0.007, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Methanol (Fossil)", "price": 380, "lcv": 0.0199, "wtt": 31.3, "ttw_co2": 1.375, "ttw_ch4": 0.003, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Biodiesel (Rapeseed Oil)", "price": 1175, "lcv": 0.0430, "wtt": 1.5, "ttw_co2": 2.834, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Biodiesel (Corn Oil)", "price": 1100, "lcv": 0.0430, "wtt": 31.6, "ttw_co2": 2.834, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Biodiesel (Wheat Straw)", "price": 900, "lcv": 0.0430, "wtt": 15.7, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Bioethanol (Sugar Beet)", "price": 650, "lcv": 0.0270, "wtt": 35.0, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Bioethanol (Maize)", "price": 700, "lcv": 0.0270, "wtt": 38.2, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Bioethanol (Wheat)", "price": 700, "lcv": 0.0270, "wtt": 41.0, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Biodiesel (UCO)", "price": 1175, "lcv": 0.0430, "wtt": 14.9, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Biodiesel (Animal Fats)", "price": 1150, "lcv": 0.0430, "wtt": 20.8, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Biodiesel (Sunflower Oil)", "price": 1175, "lcv": 0.0430, "wtt": 44.7, "ttw_co2": 2.834, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Biodiesel (Soybean Oil)", "price": 1175, "lcv": 0.0430, "wtt": 47.0, "ttw_co2": 2.834, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Biodiesel (Palm Oil)", "price": 1175, "lcv": 0.0430, "wtt": 75.7, "ttw_co2": 2.834, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Hydrotreated Vegetable Oil (HVO)", "price": 1700, "lcv": 0.0440, "wtt": 50.1, "ttw_co2": 3.115, "ttw_ch4": 0.00005, "ttw_n20": 0.00018, "rfnbo": False},
    {"name": "Fossil Hydrogen", "price": 344, "lcv": 0.1200, "wtt": 132.7, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Fossil Ammonia", "price": 500, "lcv": 0.0186, "wtt": 118.6, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "E-Methanol", "price": 1700, "lcv": 0.0199, "wtt": 1.0, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": True},
    {"name": "E-LNG", "price": 1500, "lcv": 0.0491, "wtt": 1.0, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": True},
    {"name": "Green Hydrogen", "price": 4200, "lcv": 0.1200, "wtt": 0.0, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": True},
    {"name": "Green Ammonia", "price": 900, "lcv": 0.0186, "wtt": 0.0, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": True},
    {"name": "Bio-LNG", "price": 1300, "lcv": 0.0491, "wtt": 14.1, "ttw_co2": 2.75, "ttw_ch4": 0.14, "ttw_n20": 0.00011, "rfnbo": False},
    {"name": "Bio-Methanol", "price": 1450, "lcv": 0.0199, "wtt": 13.5, "ttw_co2": 0.0, "ttw_ch4": 0.003, "ttw_n20": 0.0, "rfnbo": False}
]  # <-- truncated for brevity. In actual implementation, we’ll insert full FUELS list here

# Constants
BASE_TARGET = 91.16
REDUCTIONS = {2025: 0.02, 2030: 0.06, 2035: 0.14, 2050: 0.80}
PENALTY_RATE = 2400
VLSFO_ENERGY = 41000
RFNBO_MULTIPLIER = 2
GWP = {"CH4": 25, "N2O": 298}

# App UI
st.set_page_config(page_title="FuelEU Maritime Calculator", layout="wide")
st.title("FuelEU Maritime GHG Calculator")

year = st.selectbox("Compliance Year", sorted(REDUCTIONS.keys()), index=0)
gwp_version = st.radio("GWP Set", options=["AR4", "AR5"], index=0, help="Global Warming Potential version")
GWP = {"AR4": {"CH4": 25, "N2O": 298}, "AR5": {"CH4": 29.8, "N2O": 273}}[gwp_version]

selected_fuels = st.multiselect("Select Fuel Types", options=[f["name"] for f in FUELS])
quantities = {fuel: st.number_input(f"{fuel} (MT)", min_value=0.0, value=0.0, step=10.0) for fuel in selected_fuels}

# Calculations
total_energy, total_emissions = 0.0, 0.0
df_rows = []
for fuel_name in selected_fuels:
    fuel = next(f for f in FUELS if f["name"] == fuel_name)
    qty = quantities[fuel_name]
    lcv_mj = fuel["lcv"] * qty * 1e3
    wtt = fuel["wtt"]
    ttw = (
        fuel["ttw_co2"] +
        fuel["ttw_ch4"] * GWP["CH4"] +
        fuel["ttw_n20"] * GWP["N2O"]
    )
    emissions = lcv_mj * (wtt + ttw)
    if fuel["rfnbo"] and year <= 2033:
        lcv_mj *= RFNBO_MULTIPLIER
    total_energy += lcv_mj
    total_emissions += emissions
    df_rows.append({"Fuel": fuel_name, "Quantity (t)": qty, "Energy (MJ)": lcv_mj, "Emissions (gCO2eq)": emissions})

target = BASE_TARGET * (1 - REDUCTIONS.get(year, 0))
ghg_intensity = total_emissions / total_energy if total_energy else 0.0
compliance_balance = total_energy * (target - ghg_intensity)
penalty = 0 if compliance_balance >= 0 else abs(compliance_balance) * PENALTY_RATE / VLSFO_ENERGY

# Results
st.metric("GHG Intensity (gCO2eq/MJ)", f"{ghg_intensity:.2f}")
st.metric("Compliance Balance (MJ)", f"{compliance_balance:,.2f}")
st.metric("Estimated Penalty (€)", f"{penalty:,.2f}")

# Table
df = pd.DataFrame(df_rows)
st.dataframe(df)

# PDF export
if st.button("Export to PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="FuelEU Maritime GHG Report", ln=True, align="C")
    pdf.cell(200, 10, txt=f"Year: {year} | GWP: {gwp_version}", ln=True)
    pdf.cell(200, 10, txt=f"GHG Intensity: {ghg_intensity:.2f} gCO2eq/MJ", ln=True)
    pdf.cell(200, 10, txt=f"Compliance Balance: {compliance_balance:,.2f} MJ", ln=True)
    pdf.cell(200, 10, txt=f"Penalty: €{penalty:,.2f}", ln=True)
    pdf.ln(10)
    for row in df_rows:
        pdf.cell(200, 10, txt=str(row), ln=True)
    filename = f"ghg_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(f"/mnt/data/{filename}")
    st.success(f"PDF exported: {filename}")
