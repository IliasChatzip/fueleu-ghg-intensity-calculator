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
]
