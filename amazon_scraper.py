import requests
from bs4 import BeautifulSoup
import streamlit as st
import re
from urllib.parse import urlparse, quote_plus
import pandas as pd
import io

API_KEY = "9490822339bbc53376b0590110af80297706150008607ce1cfed5083865b4a74"

def get_serpapi_data(params):
    url = "https://serpapi.com/search"
    params["api_key"] = API_KEY
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

def extract_product_data(asin, domain, include_reviews=True, review_counts=None):
    product_data = {
        'title': f"Données extraites via l'ASIN {asin}.",
        'features': [],
        'technical_details': {},
        'customer_reviews': []
    }

    if include_reviews and review_counts:
        for stars, count in review_counts.items():
            reviews_params = {
                "engine": "amazon_reviews",
                "amazon_domain": f"amazon.{domain}",
                "asin": asin,
                "review_type": "ratings",
                "filter_by_star": f"{stars}_star",
                "sort_by": "recent"
            }
            reviews_data = get_serpapi_data(reviews_params)
            for r in reviews_data.get("reviews", [])[:count]:
                product_data['customer_reviews'].append(f"[{stars}⭐] {r.get('body', '')}")

    return product_data

def main():
    st.title("🛒 Extracteur de données Amazon - SerpAPI")

    mode = st.radio("Méthode de recherche", ["Nom du produit", "ASIN", "URL du produit"])
    domain = st.text_input("Domaine Amazon (ex: fr, com, de)", "fr")
    include_reviews = st.checkbox("Inclure les avis clients", value=True)

    review_counts = {}
    if include_reviews:
        st.markdown("**Nombre d'avis à extraire par type :**")
        for star in range(5, 0, -1):
            review_counts[star] = st.number_input(f"{star} étoile(s)", min_value=0, max_value=50, value=0)

    user_input = ""
    if mode == "Nom du produit":
        user_input = st.text_input("Entrez le nom du produit")
    elif mode == "ASIN":
        user_input = st.text_input("Entrez l'ASIN du produit")
    else:
        user_input = st.text_input("Entrez l'URL du produit Amazon")

    if st.button("Extraire les données") and user_input:
        try:
            if mode == "Nom du produit":
                search_params = {
                    "engine": "amazon",
                    "amazon_domain": f"amazon.{domain}",
                    "search_term": user_input
                }
                result = get_serpapi_data(search_params)
                asin = result.get("organic_results", [{}])[0].get("asin", "")
                if not asin:
                    raise Exception("ASIN introuvable pour ce produit.")
            elif mode == "URL du produit":
                _, domain, asin = clean_amazon_url(user_input.strip())
            else:
                asin = user_input.strip()

            data = extract_product_data(asin, domain, include_reviews, review_counts)

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
