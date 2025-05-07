import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from fpdf import FPDF
from datetime import datetime

# === CONFIGURATION ===
BASE_TARGET = 91.16
REDUCTIONS = {2025: 0.02, 2030: 0.06, 2035: 0.14, 2050: 0.80}
PENALTY_RATE = 2400
VLSFO_ENERGY_CONTENT = 41_000
RFNBO_MULTIPLIER = 2
GWP_VALUES = {
    "AR4": {"CH4": 25, "N2O": 298},
    "AR5": {"CH4": 29.8, "N2O": 273},
}

# === FALLBACK PRICES ===
DEFAULT_PRICES = {
    "Heavy Fuel Oil (HFO)": 469,
    "Marine Gas Oil (MGO)": 900,
    "Liquefied Natural Gas (LNG)": 780,
    "Methanol (Fossil)": 380,
    "Biodiesel (UCO)": 1175,
    "Green Hydrogen": 4200,
    "E-Methanol": 1700,
    "E-LNG": 1500,
}

# === FUEL DATABASE ===
FUELS = [
    {"name": "Heavy Fuel Oil (HFO)",             "lcv": 0.0405, "wtt": 13.5, "ttw_co2": 3.114, "ttw_ch4": 0.00005, "ttw_n20": 0.00018, "rfnbo": False},
    {"name": "Low Fuel Oil (LFO)",               "lcv": 0.0410, "wtt": 13.2, "ttw_co2": 3.151, "ttw_ch4": 0.00005, "ttw_n20": 0.00018, "rfnbo": False},
    {"name": "Marine Gas Oil (MGO)",             "lcv": 0.0427, "wtt": 14.4, "ttw_co2": 3.206, "ttw_ch4": 0.00005, "ttw_n20": 0.00018, "rfnbo": False},
    {"name": "Liquefied Natural Gas (LNG)",      "lcv": 0.0491, "wtt": 18.5, "ttw_co2": 2.750, "ttw_ch4": 0.001276, "ttw_n20": 0.00011, "rfnbo": False},
    {"name": "Liquefied Petroleum Gas (LPG)",    "lcv": 0.0460, "wtt": 7.8,  "ttw_co2": 3.015, "ttw_ch4": 0.007,   "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Methanol (Fossil)",                "lcv": 0.0199, "wtt": 31.3, "ttw_co2": 1.375, "ttw_ch4": 0.003,   "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (Rapeseed Oil)",         "lcv": 0.0430, "wtt": 1.5, "ttw_co2": 2.834,  "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (Corn Oil)",             "lcv": 0.0430, "wtt": 31.6, "ttw_co2": 2.834,  "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (Wheat Straw)",          "lcv": 0.0430, "wtt": 15.7, "ttw_co2": 0.0,    "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Bioethanol (Sugar Beet)",          "lcv": 0.027,  "wtt": 35.0, "ttw_co2": 0.0,    "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Bioethanol (Maize)",               "lcv": 0.027,  "wtt": 38.2, "ttw_co2": 0.0,    "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Bioethanol (Wheat)",               "lcv": 0.027,  "wtt": 41.0, "ttw_co2": 0.0,    "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (UCO)",                  "lcv": 0.0430, "wtt": 14.9, "ttw_co2": 0.0,    "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (Animal Fats)",          "lcv": 0.0430, "wtt": 20.8, "ttw_co2": 0.0,    "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (Sunflower Oil)",        "lcv": 0.0430, "wtt": 44.7, "ttw_co2": 2.834,  "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (Soybean Oil)",          "lcv": 0.0430, "wtt": 47.0, "ttw_co2": 2.834,  "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (Palm Oil)",             "lcv": 0.0430, "wtt": 75.7, "ttw_co2": 2.834,  "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Hydrotreated Vegetable Oil (HVO)", "lcv": 0.0440, "wtt": 50.1, "ttw_co2": 3.115,  "ttw_ch4": 0.00005,"ttw_n20": 0.00018, "rfnbo": False},  
    {"name": "Fossil Hydrogen",                  "lcv": 0.1200, "wtt": 132.7, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "Fossil Ammonia",                   "lcv": 0.0186, "wtt": 118.6, "ttw_co2": 0.0, "ttw_ch4": 0.0, "ttw_n20": 0.0, "rfnbo": False},
    {"name": "E-Methanol",                       "lcv": 0.0199, "wtt": 1.0,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,   "ttw_n20": 0.0,     "rfnbo": True},
    {"name": "E-LNG",                            "lcv": 0.0491, "wtt": 1.0,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,   "ttw_n20": 0.0,     "rfnbo": True},
    {"name": "Green Hydrogen",                   "lcv": 0.1200, "wtt": 0.0,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,   "ttw_n20": 0.0,     "rfnbo": True},
    {"name": "Green Ammonia",                    "lcv": 0.0186, "wtt": 0.0,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,   "ttw_n20": 0.0,     "rfnbo": True},
    {"name": "Bio-LNG",                          "lcv": 0.0491, "wtt": 14.1, "ttw_co2": 2.75,   "ttw_ch4": 0.14,  "ttw_n20": 0.00011, "rfnbo": False},
    {"name": "Bio-Methanol",                     "lcv": 0.0199, "wtt": 13.5, "ttw_co2": 0.0,    "ttw_ch4": 0.003, "ttw_n20": 0.0,     "rfnbo": False},  
]

# === API PRICING WITH 24-HOUR CACHE ===
@st.cache_data(ttl=86400)
def get_live_prices():
    prices = DEFAULT_PRICES.copy()
    try:
        # This is a placeholder for actual API integration
        # Example simulated fetch:
        response = requests.get("https://api.mockfuels.com/prices")  # Replace with real API
        if response.status_code == 200:
            data = response.json()
            for item in data:
                name = item.get("name")
                price = item.get("eur_per_ton")
                if name and price:
                    prices[name] = price
    except Exception as e:
        st.warning("⚠️ Fuel price API fetch failed, using default prices.")
    return prices

def fetch_price(fuel_name):
    prices = get_live_prices()
    return prices.get(fuel_name, 1000)

# === TARGET FUNCTION ===
def target_intensity(year: int) -> float:
    if year <= 2020:
        return BASE_TARGET
    if year <= 2029:
        return BASE_TARGET * (1 - REDUCTIONS[2025])
    if year <= 2034:
        return BASE_TARGET * (1 - REDUCTIONS[2030])
    if year == 2035:
        return BASE_TARGET * (1 - REDUCTIONS[2035])
    frac = (year - 2035) / (2050 - 2035)
    red = REDUCTIONS[2035] + frac * (REDUCTIONS[2050] - REDUCTIONS[2035])
    return BASE_TARGET * (1 - red)

# === USER INPUT ===
st.title("FuelEU Maritime - GHG Intensity & Penalty Calculator")
st.sidebar.header("Input Parameters")
year = st.sidebar.selectbox(
    "Select Compliance Year",
    [2020, 2025, 2030, 2035, 2040, 2045, 2050],
    index=1,
    help="Select the year for GHG compliance benchmarking."
)
gwp_choice = st.sidebar.radio(
    "GWP Standard",
    ["AR4", "AR5"],
    index=0,
    help="Select Global Warming Potential values to apply: AR4 (CH₄: 25, N₂O: 298) or AR5 (CH₄: 29.8, N₂O: 273)."
)
gwp = GWP_VALUES[gwp_choice]

if st.sidebar.button("🔁 Reset Calculator"):
    st.cache_data.clear()
    st.experimental_rerun()

ops = st.sidebar.selectbox(
    "OPS Reduction (%)",
    [0, 1, 2],
    index=0,
    help="Onshore Power Supply usage: select 1–2% reduction if OPS is utilized while berthed."
)
wind = st.sidebar.selectbox(
    "Wind Reduction Factor",
    [1.00, 0.99, 0.97, 0.95],
    index=0,
    help="Applies wind-assisted propulsion correction factor: lower values imply higher wind assistance."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Fuel Inputs")
fuel_inputs = {}
for fuel in FUELS:
    qty = st.sidebar.number_input(f"{fuel['name']} (t)", min_value=0.0, step=1.0, value=0.0, key=f"qty_{fuel['name']}")
    fuel_inputs[fuel['name']] = qty
    st.session_state[f"qty_{fuel['name']}"] = qty

# === CALCULATIONS ===
total_energy = 0.0
emissions = 0.0
rows = []
for fuel in FUELS:
    qty = fuel_inputs[fuel["name"]]
    if qty > 0:
        mass_g = qty * 1_000_000
        lcv = fuel["lcv"]
        energy = mass_g * lcv
        co2_corr = fuel["ttw_co2"] * (1 - ops / 100) * wind
        ttw = co2_corr + fuel["ttw_ch4"] * gwp["CH4"] + fuel["ttw_n20"] * gwp["N2O"]
        total = energy * (ttw + fuel["wtt"])
        if fuel["rfnbo"] and year <= 2033:
            energy *= RFNBO_MULTIPLIER
        total_energy += energy
        emissions += total
        rows.append({
            "Fuel": fuel["name"],
            "Quantity (t)": qty,
            "Energy (MJ)": energy,
            "Emissions (gCO2eq)": total,
            "Price (€/t)": fetch_price(fuel["name"]),
        })

ghg_intensity = emissions / total_energy if total_energy else 0.0
st.session_state["computed_ghg"] = ghg_intensity
compliance_balance = total_energy * (target_intensity(year) - ghg_intensity)
penalty = 0 if compliance_balance >= 0 else abs(compliance_balance) * PENALTY_RATE / VLSFO_ENERGY_CONTENT

# === MITIGATION SUGGESTIONS ===
if penalty > 0:
    st.subheader("Mitigation Options: Biofuels & RFNBO")
    excess_emissions = abs(compliance_balance)
    mitigation_options = []
    for fuel in FUELS:
        if fuel["ttw_co2"] == 0.0 or fuel["rfnbo"]:
            price = fetch_price(fuel["name"])
            if fuel["wtt"] > 0:
                required_mj = excess_emissions / fuel["wtt"]
                required_tonnes = required_mj / (fuel["lcv"] * 1_000_000)
                total_cost = required_tonnes * price
                mitigation_options.append({
                    "Fuel": fuel["name"],
                    "Required (t)": required_tonnes,
                    "Total Cost (€)": total_cost
                })

    if mitigation_options:
        mitigation_df = pd.DataFrame(mitigation_options)
        mitigation_df.sort_values("Total Cost (€)", inplace=True)
        st.dataframe(mitigation_df.style.format({"Required (t)": "{:.2f}", "Total Cost (€)": "{:.2f}"}))

st.subheader("Fuel Breakdown")
st.dataframe(pd.DataFrame(rows))

st.subheader("Summary")
st.metric("Total Energy (MJ)", f"{total_energy:,.0f}")
st.metric("Total Emissions (gCO2eq)", f"{emissions:,.0f}")
st.metric("GHG Intensity (gCO2eq/MJ)", f"{ghg_intensity:.2f}")
st.metric("Compliance Balance (MJ)", f"{compliance_balance:,.0f}")
st.metric("Estimated Penalty (€)", f"{penalty:,.2f}")

# === COMPLIANCE CHART ===
years = list(range(2020, 2051, 5))
targets = [target_intensity(y) for y in years]

st.subheader("Sector-wide GHG Intensity Targets")
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(years, targets, linestyle='--', marker='o', label='EU Target')
ax.axhline(st.session_state["computed_ghg"], color='red', linestyle='-', label='Your GHG Intensity')
ax.set_xlabel("Year")
ax.set_ylabel("gCO2eq/MJ")
ax.set_title("Your Performance vs Sector Target")
ax.legend()
ax.grid(True)
st.pyplot(fig)

# === PDF EXPORT ===

if st.button("Export to PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="FuelEU Maritime GHG Report", ln=True, align="C")
    pdf.cell(200, 10, txt=f"Year: {year} | GWP: {gwp_choice}", ln=True)
    pdf.cell(200, 10, txt=f"GHG Intensity: {ghg_intensity:.2f} gCO2eq/MJ", ln=True)
    pdf.cell(200, 10, txt=f"Compliance Balance: {compliance_balance:,.2f} MJ", ln=True)
    pdf.cell(200, 10, txt=f"Penalty: €{penalty:,.2f}", ln=True)
    pdf.ln(10)
    for row in rows:
        pdf.cell(200, 10, txt=str(row), ln=True)
    if penalty > 0 and mitigation_options:
        pdf.ln(5)
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(200, 10, txt="Mitigation Options (sorted by cost):", ln=True)
        pdf.set_font("Arial", size=12)
        for opt in mitigation_options:
            pdf.cell(200, 10, txt=f"- {opt['Fuel']}: {opt['Required (t)']:,.2f} t, €{opt['Total Cost (€)']:,.2f}", ln=True)

    filename = f"ghg_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(f"/mnt/data/{filename}")
    st.success(f"PDF exported: {filename}")
    fig_path = f"/mnt/data/chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    fig.savefig(fig_path, dpi=150)
    pdf.image(fig_path, x=10, y=None, w=190)

    st.download_button("Download PDF", data=open(f"/mnt/data/{filename}", "rb"), file_name=filename, mime="application/pdf")
