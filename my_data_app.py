# streamlit_app.py
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, MetaData, Table
import re

st.set_page_config(page_title="Coinafrica Scraper", layout="wide")

# =========================
# DATABASE SETUP (SQLite)
# =========================
DB_URI = "sqlite:///coinafrica.db"
engine = create_engine(DB_URI, echo=False)
metadata = MetaData()

listings = Table(
    "listings", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("category", String(100)),   # vetements-homme, etc
    Column("type", String(200)),       # clothes / shoes
    Column("raw_price", String(100)),
    Column("price", Float, nullable=True),
    Column("address", String(255)),
    Column("image_link", Text),
    Column("source_url", Text)
)

metadata.create_all(engine)

def insert_rows(df: pd.DataFrame):
    # --- Fix KeyError : assurer toutes les colonnes attendues ---
    expected_cols = ["category","type","raw_price","address","image_link","source_url"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    df = df[expected_cols]  # réorganiser colonnes
    df.to_sql("listings", engine, if_exists="append", index=False)

def read_all():
    return pd.read_sql_table("listings", engine)

# =========================
# DATA CLEANING FUNCTIONS
# =========================
def parse_price(raw: str):
    if pd.isna(raw): 
        return None
    s = str(raw).replace('\xa0', ' ')
    m = re.search(r'(\d{1,3}(?:[ ,.\']\d{3})*(?:[.,]\d+)?)', s)
    if not m: return None
    num = m.group(1).replace(" ", "").replace("'", "").replace(",", ".")
    try:
        return float(num)
    except:
        return None

def normalize_type(text: str):
    t = str(text).lower()
    if "chauss" in t: return "shoes"
    if "vetem" in t or "vêt" in t or "t-shirt" in t or "pantalon" in t: return "clothes"
    return t

def clean_dataframe(df: pd.DataFrame):
    df = df.copy()
    df['price'] = df['raw_price'].apply(parse_price)
    df['type_norm'] = df['type'].apply(normalize_type)
    df['address'] = df['address'].fillna('').str.strip()
    df['image_link'] = df['image_link'].fillna('')
    return df

# =========================
# SCRAPER (BeautifulSoup)
# =========================
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CoinafricaScraper/1.0)"}
BASE_DELAY = 1.0

CATEGORIES = {
    "vetements-homme": "https://sn.coinafrique.com/categorie/vetements-homme",
    "chaussures-homme": "https://sn.coinafrique.com/categorie/chaussures-homme",
    "vetements-enfants": "https://sn.coinafrique.com/categorie/vetements-enfants",
    "chaussures-enfants": "https://sn.coinafrique.com/categorie/chaussures-enfants",
}

def parse_listing(card, category, page_url):
    title = card.select_one(".listing-title")
    price = card.select_one(".listing-price")
    address = card.select_one(".listing-address")
    img = card.select_one("img")
    return {
        "category": category,
        "type": title.get_text(strip=True) if title else "",
        "raw_price": price.get_text(strip=True) if price else "",
        "address": address.get_text(strip=True) if address else "",
        "image_link": urljoin(page_url, img['src']) if img and img.get('src') else "",
        "source_url": page_url
    }

def scrape_category(url, category, max_pages=5):
    rows = []
    page = 1
    next_url = url
    while next_url and page <= max_pages:
        r = requests.get(next_url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            st.warning(f"Erreur {r.status_code} pour {next_url}")
            break
        soup = BeautifulSoup(r.text, "lxml")
        cards = soup.select(".listing-card")
        if not cards:
            cards = soup.select(".product, .post, .annonce")
        for c in cards:
            rows.append(parse_listing(c, category, next_url))
        nxt = soup.select_one("a.next, a.pagination-next")
        if nxt and nxt.get('href'):
            next_url = nxt['href'] if nxt['href'].startswith("http") else urljoin(next_url, nxt['href'])
        else:
            next_url = None
        page += 1
        time.sleep(BASE_DELAY)
    return rows

def scrape_all(max_pages=5):
    all_rows = []
    for cat, url in CATEGORIES.items():
        st.info(f"Scraping {cat} ...")
        rows = scrape_category(url, cat, max_pages=max_pages)
        all_rows.extend(rows)
    df = pd.DataFrame(all_rows)
    df.to_csv("scraped_unclean.csv", index=False)
    return df

# =========================
# STREAMLIT APP
# =========================
st.title("Coinafrica — Scraper & Dashboard")

tabs = st.tabs(["Scrape", "Importer CSV WebScraper", "Dashboard nettoyé", "Formulaire d'évaluation"])

with tabs[0]:
    st.header("Scraper multi-pages")
    max_pages = st.number_input("Max pages par catégorie", min_value=1, max_value=50, value=3)
    if st.button("Lancer le scraping"):
        with st.spinner("Scraping en cours..."):
            df = scrape_all(max_pages=max_pages)
            st.success(f"{len(df)} annonces récupérées")
            st.dataframe(df.head(50))
            
            # --- Fix KeyError ---
            expected_cols = ["category","type","raw_price","address","image_link","source_url"]
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = ""
            insert_rows(df[expected_cols])
            st.info("Données non nettoyées insérées dans la DB.")

with tabs[1]:
    st.header("Importer CSV exporté par Web Scraper (non nettoyé)")
    uploaded = st.file_uploader("Choisir CSV", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df.head())
        if st.button("Insérer ce CSV dans la DB"):
            df2 = df.rename(columns=lambda c: c.strip().lower())
            mapping = {}
            for col in df2.columns:
                if "price" in col: mapping[col] = "raw_price"
                if "image" in col: mapping[col] = "image_link"
                if "addr" in col or "location" in col: mapping[col] = "address"
                if "type" in col or "title" in col: mapping[col] = "type"
            df2 = df2.rename(columns=mapping)
            expected_cols = ["category","type","raw_price","address","image_link","source_url"]
            for col in expected_cols:
                if col not in df2.columns:
                    df2[col] = ""
            insert_rows(df2[expected_cols])
            st.success("CSV inséré dans la DB.")

with tabs[2]:
    st.header("Dashboard (données nettoyées)")
    df = read_all()
    st.write(f"Données totales : {len(df)} lignes")
    if len(df) > 0:
        df_clean = clean_dataframe(df)
        st.subheader("Aperçu nettoyé")
        st.dataframe(df_clean.head(200))
        st.subheader("Stats")
        st.metric("Prix moyen", f"{df_clean['price'].mean():.2f}" if not df_clean['price'].isna().all() else "N/A")
        st.write("Répartition par type")
        st.bar_chart(df_clean['type_norm'].value_counts())
        st.subheader("Filtrer par catégorie / type")
        cat = st.selectbox("Catégorie", options=["all"] + sorted(df_clean['category'].dropna().unique().tolist()))
        t = st.selectbox("Type", options=["all"] + sorted(df_clean['type_norm'].dropna().unique().tolist()))
        sub = df_clean.copy()
        if cat != "all": sub = sub[sub['category']==cat]
        if t != "all": sub = sub[sub['type_norm']==t]
        st.dataframe(sub)

# ----- Onglet 3 : Formulaires -----
with tabs[2]:
    st.header("Accéder aux formulaires")
    st.markdown("### Google Form")
    st.markdown("[Ouvrir le formulaire Google Form](https://docs.google.com/forms/d/e/1FAIpQLScyppuAhSkIxD0lXN9Gqcd9D7KfBnF6AlbID2eRxDaTtkmMog/viewform?usp=header)")
    
    st.markdown("### KoboToolbox Form")
    st.markdown("[Ouvrir le formulaire KoboToolbox](https://ee.kobotoolbox.org/x/Sa81fs4S)")
