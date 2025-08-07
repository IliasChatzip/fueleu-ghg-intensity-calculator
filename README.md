# FuelEU Maritime GHG Intensity & Penalty Calculator

This is a Streamlit app for calculating fuel GHG intensity, and compliance balance and penalties according to the FuelEU Maritime regulation.

## Features

- Calculates total and per-MJ GHG emissions for multiple fuel types, including biofuels and Renewable Fuels of Non-Biological Origin as well as EU ETS cost.
- Supports custom fuel quantities, price and compliance with year selection.
- Includes mitigation scenarios to offset/mitigate the penalty: pooling, biofuel addition and fuel replacement.
- Visualizes sector targets and user performance with interactive charts.
- Generates a PDF report summarizing inputs, results and mitigation options.

## How to Use

1. **Install dependencies:**
pip install -r requirements.txt

2. **Run the app:**
streamlit run app.py

3. **Open the app in your broswer:**
After running, Streamlit will give you a local link (usually http://localhost:8501)—open this in your browser

4. **Export results:**
Use the “Export to PDF” button in the web interface to download your results as a report
