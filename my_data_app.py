# streamlit_app.py
import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="Coinafrica Scraper & Dashboard", layout="wide")

# =========================
# Scraper Functions
# =========================
def get_page(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        return BeautifulSoup(r.text, 'html.parser')
    except:
        return None

def clean_price(text):
    if not text:
        return 0
    num = ''.join(filter(str.isdigit, text))
    return int(num) if num else 0

def scrape_generic(url_pattern, pages, category_name):
    data = []
    for page in range(1, pages + 1):
        url = url_pattern.format(page=page)
        soup = get_page(url)
        if not soup:
            continue
        for card in soup.select('.ad__card'):
            try:
                name_tag = card.select_one('.ad__card-description')
                name = name_tag.get_text(strip=True) if name_tag else "No name"
                price_tag = card.select_one('.ad__card-price')
                price = clean_price(price_tag.get_text()) if price_tag else 0
                city_tag = card.select_one('.ad__card-location span')
                city = city_tag.get_text(strip=True) if city_tag else "Dakar"
                img = card.select_one('img')
                img_url = img['src'] if img and img.get('src') else ""
                data.append({
                    "category": category_name,
                    "type": name,
                    "price": price,
                    "address": city,
                    "image_link": img_url,
                    "source_url": url
                })
            except:
                continue
        time.sleep(1)
    df = pd.DataFrame(data)
    if not df.empty:
        df.drop_duplicates(inplace=True)
    return df

# =========================
# Dashboard Cleaning
# =========================
def normalize_type(text):
    t = str(text).lower()
    if "chauss" in t: return "shoes"
    if "vetem" in t or "vêt" in t: return "clothes"
    return t

def clean_dataframe(df):
    df = df.copy()
    df['type_norm'] = df['type'].apply(normalize_type)
    df['address'] = df['address'].fillna('').str.strip()
    df['image_link'] = df['image_link'].fillna('')
    return df

# =========================
# Streamlit App
# =========================
st.title("Coinafrica — Scraper, Dashboard & Téléchargement CSV")

tabs = st.tabs(["Scraper", "Télécharger CSV existants", "Dashboard", "Formulaires"])

# ---------- Onglet 1 : Scraper ----------
with tabs[0]:
    st.header("Lancer le scraping")
    pages = st.number_input("Nombre de pages par catégorie", min_value=1, max_value=20, value=2)

    if st.button("Scraper toutes les catégories"):
        st.info("Scraping en cours...")
        all_df = pd.DataFrame()
        urls = {
            "vetements-homme": "https://sn.coinafrique.com/categorie/vetements-homme?page={page}",
            "vetements-enfants": "https://sn.coinafrique.com/categorie/vetements-enfants?page={page}",
            "chaussures-homme": "https://sn.coinafrique.com/categorie/chaussures-homme?page={page}",
            "chaussures-enfants": "https://sn.coinafrique.com/categorie/chaussures-enfants?page={page}"
        }
        for cat, url in urls.items():
            df_cat = scrape_generic(url, pages, cat)
            all_df = pd.concat([all_df, df_cat], ignore_index=True)
        if not all_df.empty:
            st.success(f"{len(all_df)} annonces récupérées.")
            st.dataframe(all_df.head(50))
            # Sauvegarder CSV pour téléchargement
            if not os.path.exists("data"):
                os.makedirs("data")
            all_df.to_csv(f"data/coinafrica_scraped.csv", index=False)
            st.success("CSV sauvegardé dans le dossier 'data' pour téléchargement.")

# ---------- Onglet 2 : Télécharger CSV ----------
with tabs[1]:
    st.header("Télécharger les CSV existants")
    data_folder = "data"
    if not os.path.exists(data_folder):
        st.warning("Aucun dossier 'data' trouvé.")
    else:
        files = [f for f in os.listdir(data_folder) if f.endswith(".csv")]
        st.write("Fichiers disponibles :")
        for f in files:
            file_path = os.path.join(data_folder, f)
            with open(file_path, "rb") as file:
                st.download_button(label=f"Télécharger {f}", data=file, file_name=f, mime="text/csv")

# ---------- Onglet 3 : Dashboard ----------
with tabs[2]:
    st.header("Dashboard des données")
    csv_file = st.selectbox("Sélectionner un CSV pour le dashboard", options=os.listdir("data") if os.path.exists("data") else [])
    if csv_file:
        df = pd.read_csv(os.path.join("data", csv_file))
        df_clean = clean_dataframe(df)
        st.subheader("Aperçu des annonces")
        st.dataframe(df_clean.head(200))
        st.subheader("Statistiques")
        st.metric("Prix moyen", f"{df_clean['price'].mean():.2f}")
        st.write("Répartition par type")
        st.bar_chart(df_clean['type_norm'].value_counts())

# ---------- Onglet 4 : Formulaires ----------
with tabs[3]:
    st.header("Accéder aux formulaires")
    st.markdown("### Google Form")
    st.markdown("[Ouvrir le formulaire Google Form](https://docs.google.com/forms/d/e/1FAIpQLScyppuAhSkIxD0lXN9Gqcd9D7KfBnF6AlbID2eRxDaTtkmMog/viewform?usp=header)")
    
    st.markdown("### KoboToolbox Form")
    st.markdown("[Ouvrir le formulaire KoboToolbox](https://ee.kobotoolbox.org/x/Sa81fs4S)")
