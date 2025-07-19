import requests
from bs4 import BeautifulSoup
import streamlit as st
import re
from urllib.parse import urlparse, quote_plus
import pandas as pd
import io

def get_serpapi_data(params, api_key):
    url = "https://serpapi.com/search"
    params["api_key"] = api_key
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Erreur {response.status_code} depuis SerpApi: {response.text}")
    return response.json()

def clean_amazon_url(url):
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    if not match:
        raise ValueError("URL Amazon invalide ou ASIN non trouvé.")
    asin = match.group(1)
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.amazon.", "")
    return f"https://www.amazon.{domain}/dp/{asin}", domain, asin

def extract_product_data(asin, domain, api_key, include_reviews=True):
    params = {
        "engine": "amazon_product",
        "amazon_domain": f"amazon.{domain}",
        "asin": asin
    }
    data = get_serpapi_data(params, api_key)

    product_data = {
        'title': data.get("title", "N/A"),
        'features': data.get("feature_bullets", []),
        'technical_details': data.get("specifications", {}),
        'customer_reviews': []
    }

    if include_reviews:
        reviews_params = {
            "engine": "amazon_reviews",
            "amazon_domain": f"amazon.{domain}",
            "asin": asin,
            "review_type": "all",
            "sort_by": "recent"
        }
        reviews_data = get_serpapi_data(reviews_params, api_key)
        for r in reviews_data.get("reviews", [])[:10]:
            product_data['customer_reviews'].append(r.get("body", ""))

    return product_data

def main():
    st.title("🛒 Extracteur de données Amazon - SerpAPI")
    api_key = st.text_input("Entrez votre clé API SerpApi", type="password")
    if not api_key:
        st.warning("Veuillez entrer votre clé API SerpApi pour commencer.")
        return

    mode = st.radio("Méthode de recherche", ["ASIN", "Nom du produit", "URL du produit"])
    domain = st.text_input("Domaine Amazon (ex: fr, com, de)", "fr")
    include_reviews = st.checkbox("Inclure les avis clients", value=True)

    user_input = ""
    if mode == "ASIN":
        user_input = st.text_input("Entrez l'ASIN du produit")
    elif mode == "Nom du produit":
        user_input = st.text_input("Entrez le nom du produit")
    else:
        user_input = st.text_input("Entrez l'URL du produit Amazon")

    if st.button("Extraire les données") and user_input:
        try:
            if mode == "URL du produit":
                _, domain, asin = clean_amazon_url(user_input.strip())
            elif mode == "Nom du produit":
                search_params = {
                    "engine": "amazon",
                    "amazon_domain": f"amazon.{domain}",
                    "search_term": user_input
                }
                result = get_serpapi_data(search_params, api_key)
                asin = result.get("organic_results", [{}])[0].get("asin", "")
                if not asin:
                    raise Exception("Produit non trouvé.")
            else:
                asin = user_input.strip()

            data = extract_product_data(asin, domain, api_key, include_reviews)

            st.subheader("Titre")
            st.write(data['title'])

            st.subheader("Caractéristiques")
            for f in data['features']:
                st.markdown(f"- {f}")

            st.subheader("Détails techniques")
            for k, v in data['technical_details'].items():
                st.markdown(f"**{k}** : {v}")

            if data['customer_reviews']:
                st.subheader("Avis clients")
                for i, review in enumerate(data['customer_reviews'], 1):
                    st.markdown(f"{i}. {review}")

            # Export CSV
            export_data = {
                "Titre": [data['title']],
                "Caractéristiques": [" | ".join(data['features'])],
                "Détails techniques": [" | ".join([f"{k}: {v}" for k, v in data['technical_details'].items()])],
                "Avis clients": [" | ".join(data['customer_reviews'])]
            }
            df_export = pd.DataFrame(export_data)
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Télécharger les données en CSV",
                data=csv,
                file_name=f"amazon_{asin}.csv",
                mime='text/csv'
            )

        except Exception as e:
            st.error(str(e))

if __name__ == "__main__":
    main()
