import requests
from bs4 import BeautifulSoup
import streamlit as st
import re
from urllib.parse import urlparse, quote_plus
import pandas as pd
import io

API_KEY = "9490822339bbc53376b0590110af80297706150008607ce1cfed5083865b4a74"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9"
}

def get_serpapi_data(params):
    url = "https://serpapi.com/search"
    params["api_key"] = API_KEY
    if not params.get("search_term") and not params.get("asin") and params.get("engine") != "amazon_reviews":
        raise ValueError("Paramètre 'search_term', 'asin' ou un engine valide requis pour l'appel à SerpApi.")
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Erreur {response.status_code} depuis SerpApi: {response.text}")
    return response.json()

def extract_asin_from_url(url):
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    if not match:
        raise ValueError("ASIN introuvable dans l'URL.")
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.amazon.", "")
    return match.group(1), domain

def extract_asin_from_name(name, domain):
    if not name.strip():
        raise ValueError("Le nom du produit est vide.")
    params = {
        "engine": "amazon",
        "amazon_domain": f"amazon.{domain}",
        "search_term": name
    }
    data = get_serpapi_data(params)
    asin = data.get("organic_results", [{}])[0].get("asin", "")
    return asin

def extract_amazon_data_via_serpapi(asin, domain):
    params = {
        "engine": "amazon",
        "amazon_domain": f"amazon.{domain}",
        "asin": asin
    }
    data = get_serpapi_data(params)
    result = data.get("product_results", {})
    return {
        'title': result.get("title", "N/A"),
        'features': result.get("feature_bullets", []),
        'technical_details': result.get("technical_specifications", {}),
        'customer_reviews': []
    }

def extract_reviews_from_serpapi(asin, domain, review_counts):
    reviews = []
    for stars, count in review_counts.items():
        if count == 0:
            continue
        params = {
            "engine": "amazon_reviews",
            "amazon_domain": f"amazon.{domain}",
            "asin": asin,
            "review_type": "ratings",
            "filter_by_star": f"{stars}_star",
            "sort_by": "recent"
        }
        try:
            data = get_serpapi_data(params)
            reviews.extend([f"[{stars}⭐] {r.get('body', '')}" for r in data.get("reviews", [])[:count]])
        except:
            continue
    return reviews

def main():
    st.title("🛒 Extracteur Amazon - Version SerpAPI")

    mode = st.radio("Méthode de recherche", ["URL du produit", "Nom du produit"])
    user_input = st.text_input("Entrez l'URL ou le nom du produit Amazon")
    domain = st.text_input("Domaine Amazon (ex: fr, com, de)", value="fr")
    include_reviews = st.checkbox("Inclure les avis clients", value=True)

    review_counts = {}
    if include_reviews:
        st.markdown("**Nombre d'avis à extraire par type :**")
        for star in range(5, 0, -1):
            review_counts[star] = st.number_input(f"{star} étoile(s)", min_value=0, max_value=10, value=0)

    if st.button("Extraire les données") and user_input:
        try:
            if mode == "URL du produit":
                asin, domain = extract_asin_from_url(user_input)
            else:
                asin = extract_asin_from_name(user_input, domain)
                if not asin:
                    raise Exception("ASIN introuvable pour ce nom de produit.")

            data = extract_amazon_data_via_serpapi(asin, domain)

            if include_reviews:
                data['customer_reviews'] = extract_reviews_from_serpapi(asin, domain, review_counts)

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
