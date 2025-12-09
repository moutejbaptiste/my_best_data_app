# streamlit_app.py
import streamlit as st
import pandas as pd
from db import init_db, insert_rows, read_all
from scraping import scrape_all  # si tu appelles scraper en module, sinon importe fonctions
from cleaning import clean_dataframe
import io

st.set_page_config(page_title="Coinafrica Scraper", layout="wide")

init_db()

st.title("Coinafrica — Scraper & Dashboard")

tabs = st.tabs(["Scrape", "Importer WebScraper CSV (unclean)", "Dashboard (cleaned)", "Formulaire d'évaluation"])

with tabs[0]:
    st.header("Scraper multi-pages")
    st.write("Lancer le scraper (BeautifulSoup). Attention : vérifie les sélecteurs.")
    max_pages = st.number_input("Max pages par catégorie", min_value=1, max_value=100, value=5)
    if st.button("Lancer le scraping"):
        with st.spinner("Scraping en cours..."):
            df = scrape_all(max_pages=max_pages)
            st.success(f"{len(df)} lignes récupérées")
            st.dataframe(df.head(50))
            # insérer raw dans DB
            insert_rows(df[["category","type","raw_price","address","image_link","source_url"]])
            st.info("Données non nettoyées insérées dans la DB.")

with tabs[1]:
    st.header("Importer / Télécharger CSV exporté par Web Scraper (non nettoyé)")
    uploaded = st.file_uploader("Choisis le CSV exporté par Web Scraper", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        st.write("Aperçu du CSV uploadé")
        st.dataframe(df.head())
        if st.button("Insérer ce CSV dans la DB (non nettoyé)"):
            # map & insert (simple)
            df2 = df.rename(columns=lambda c: c.strip().lower())
            # heuristiques de mapping (comme dans webscraper_import)
            mapping, cols = {}, df2.columns
            for col in cols:
                if "price" in col: mapping[col] = "raw_price"
                if "image" in col: mapping[col] = "image_link"
                if "addr" in col or "location" in col: mapping[col] = "address"
                if "type" in col or "title" in col: mapping[col] = "type"
            df2 = df2.rename(columns=mapping)
            for c in ["category", "source_url"]:
                if c not in df2.columns:
                    df2[c] = "webscraper_import"
            insert_rows(df2[["category","type","raw_price","address","image_link","source_url"]])
            st.success("Inséré dans la DB.")

with tabs[2]:
    st.header("Dashboard (données nettoyées)")
    df = read_all()
    st.write(f"Données totales en base : {len(df)} lignes")
    if len(df) == 0:
        st.info("La base est vide. Scrape ou importe un CSV d'abord.")
    else:
        df_clean = clean_dataframe(df)
        st.subheader("Aperçu nettoyé")
        st.dataframe(df_clean.head(200))
        # Statistiques simples
        st.subheader("Stats")
        st.write("Prix: (en monnaie locale, normalisé si possible)")
        st.metric("Moyenne prix", f"{df_clean['price_clean'].mean():.2f}")
        st.write("Répartition par type")
        st.bar_chart(df_clean['type_norm'].value_counts())

        st.subheader("Filtrer par catégorie / type")
        cat = st.selectbox("Catégorie", options=["all"] + sorted(df_clean['category'].dropna().unique().tolist()))
        t = st.selectbox("Type", options=["all"] + sorted(df_clean['type_norm'].dropna().unique().tolist()))
        sub = df_clean.copy()
        if cat != "all":
            sub = sub[sub['category'] == cat]
        if t != "all":
            sub = sub[sub['type_norm'] == t]
        st.dataframe(sub)

with tabs[3]:
    st.header("Formulaire d'évaluation de l'app")
    name = st.text_input("Nom")
    rating = st.slider("Note globale", 1, 5, 3)
    comments = st.text_area("Commentaires")
    if st.button("Envoyer l'évaluation"):
        # tu peux stocker les évaluations dans la DB ou un fichier
        with open("data/evaluations.csv", "a", encoding="utf-8") as f:
            f.write(f"{name},{rating},{comments}\n")
        st.success("Merci pour ton retour !")
