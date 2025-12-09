# streamlit_app.py
import streamlit as st
import pandas as pd
import os
import re
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, MetaData, Table

st.set_page_config(page_title="Coinafrica Scraper & Dashboard", layout="wide")

# =========================
# DATABASE SETUP (SQLite)
# =========================
DB_URI = "sqlite:///coinafrica.db"
engine = create_engine(DB_URI, echo=False)
metadata = MetaData()

listings = Table(
    "listings", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("category", String(100)),
    Column("type", String(200)),
    Column("raw_price", String(100)),
    Column("price", Float, nullable=True),
    Column("address", String(255)),
    Column("image_link", Text),
    Column("source_url", Text)
)

metadata.create_all(engine)

def insert_rows(df: pd.DataFrame):
    expected_cols = ["category","type","raw_price","address","image_link","source_url"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    df = df[expected_cols]
    df.to_sql("listings", engine, if_exists="append", index=False)

def read_all():
    return pd.read_sql_table("listings", engine)

# =========================
# DATA CLEANING
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
# STREAMLIT APP
# =========================
st.title("Coinafrica — Dashboard & Forms")

tabs = st.tabs(["Importer CSV existants", "Dashboard nettoyé", "Formulaires"])

# ----- Onglet 1 : Importer CSV existants -----
with tabs[0]:
    st.header("Importer CSV existants depuis le dossier 'data'")
    data_folder = "data"
    files = [f for f in os.listdir(data_folder) if f.endswith(".csv")]
    st.write("Fichiers détectés :", files)
    
    selected_files = st.multiselect("Sélectionner les fichiers à importer", options=files)
    
    if st.button("Importer dans la DB"):
        total_rows = 0
        for file in selected_files:
            path = os.path.join(data_folder, file)
            df = pd.read_csv(path)
            # Déterminer la catégorie depuis le nom de fichier si nécessaire
            if "vetements-homme" in file.lower():
                df["category"] = "vetements-homme"
            elif "chaussures-homme" in file.lower():
                df["category"] = "chaussures-homme"
            elif "vetements-enfants" in file.lower():
                df["category"] = "vetements-enfants"
            elif "chaussures-enfants" in file.lower():
                df["category"] = "chaussures-enfants"
            else:
                df["category"] = "unknown"
            # Assurer colonnes obligatoires
            for col in ["type","raw_price","address","image_link","source_url"]:
                if col not in df.columns:
                    df[col] = ""
            insert_rows(df[["category","type","raw_price","address","image_link","source_url"]])
            total_rows += len(df)
        st.success(f"{total_rows} lignes importées dans la DB.")

# ----- Onglet 2 : Dashboard -----
with tabs[1]:
    st.header("Dashboard des données nettoyées")
    df = read_all()
    st.write(f"Données totales : {len(df)} lignes")
    if len(df) > 0:
        df_clean = clean_dataframe(df)
        st.subheader("Aperçu nettoyé")
        st.dataframe(df_clean.head(200))
        st.subheader("Statistiques")
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
