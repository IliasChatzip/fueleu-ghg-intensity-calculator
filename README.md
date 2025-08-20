# FuelEU Maritime GHG Intensity & Penalty Calculator

This is a Streamlit app for calculating fuel GHG intensity, compliance balance and penalties according to the FuelEU Maritime regulation. It also lets you explore mitigation scenarios and export a tailored PDF report.

## Features

- **Per-fuel accounting**: Enter quantities (t), prices (USD/t), and compute energy, WtT/TtW splits, and blend GHG intensity.
- **EU ETS integration**:
  - **Simple** or **Advanced** coverage modes.
  - Phase-in selector and automatic inclusion of **CH₄/N₂O/slip from 2026+**.
  - Shows **ETS-eligible TtW (covered tCO₂e)** and **EU ETS cost**.
- **FuelEU target path**: Built-in sector targets (2025→2050) with 2024 baseline shown on the chart.
- **Mitigation tools**:
  - **Pooling** (buy credits).
  - **Add mitigation fuel** (Bio/RFNBO) with automatic quantity finder to reach target.
  - **Replace fossil with mitigation fuel** with a direct **additional fuel cost** approach.
- **Cost–Benefit analysis**:
  - Bullet-style scenarios with bold totals and a one-line breakdown underneath.
  - Skips scenarios gracefully if you didn’t enter the relevant inputs.
- **Charts**:
  - **Line chart**: Your blend vs sector target (2024–2050), no X-axis title in PDF if desired.
  - **Stacked columns**: **FuelEU vs EU ETS** dynamics across the timeline (coverage vs required reduction).
- **PDF export**:
  - Pick sections to include (summary, ETS, fuel table, WtT/TtW splits, mitigation, cost–benefit, charts).
  - Safe defaults; works even if mitigation inputs are missing.

## How to Use

1. **Install dependencies:**
pip install -r requirements.txt

2. **Run the app:**
streamlit run app.py

3. **Open the app in your broswer:**
After running, Streamlit will give you a local link in your browser

4. **Export results:**
Use the “Export to PDF” button in the web interface to download your results as a report
