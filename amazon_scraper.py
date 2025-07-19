import requests
from bs4 import BeautifulSoup
import random
import streamlit as st
import re
from urllib.parse import urlparse

HEADERS_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
]

def get_soup(url):
    headers = {'User-Agent': random.choice(HEADERS_LIST)}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Erreur de requête ({response.status_code}) pour l'URL: {url}")
    return BeautifulSoup(response.text, 'html.parser')

def clean_amazon_url(url):
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    if not match:
        raise ValueError("URL Amazon invalide ou ASIN non trouvé.")
    asin = match.group(1)
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.amazon.", "")
    return f"https://www.amazon.{domain}/dp/{asin}", domain, asin

def extract_product_data_from_url(url, domain):
    soup = get_soup(url)

    data = {
        'title': soup.select_one('#productTitle').get_text(strip=True) if soup.select_one('#productTitle') else 'N/A',
        'features': [li.get_text(strip=True) for li in soup.select('#feature-bullets li') if li.get_text(strip=True)],
        'technical_details': {},
    }
    for table in soup.select("table#productDetails_techSpec_section_1, table#productDetails_detailBullets_sections1"):
        for row in table.select("tr"):
            th = row.select_one("th")
            td = row.select_one("td")
            if th and td:
                data['technical_details'][th.get_text(strip=True)] = td.get_text(strip=True)

    return data

def main():
    st.title("🛒 Extracteur de données Amazon - V2")
    mode = st.radio("Méthode de recherche", ["ASIN", "Nom du produit", "URL du produit"])
    domain = st.text_input("Domaine Amazon (ex: fr, com, de)", "fr")

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
                clean_url, domain, asin = clean_amazon_url(user_input.strip())
                data = extract_product_data_from_url(clean_url, domain)
            else:
                domain = domain.lower().strip().replace("https://", "").replace("http://", "").replace("www.amazon.", "")
                asin = user_input
                if mode == "Nom du produit":
                    query = user_input.replace(" ", "+")
                    search_url = f"https://www.amazon.{domain}/s?k={query}"
                    soup = get_soup(search_url)
                    result = soup.select_one("div.s-result-item[data-asin]")
                    if result and result['data-asin']:
                        asin = result['data-asin']
                        st.success(f"ASIN trouvé : {asin}")
                    else:
                        raise Exception("Aucun produit trouvé pour la requête.")
                url = f"https://www.amazon.{domain}/dp/{asin}"
                data = extract_product_data_from_url(url, domain)

            st.subheader("Titre")
            st.write(data['title'])

            st.subheader("Caractéristiques")
            for f in data['features']:
                st.markdown(f"- {f}")

            st.subheader("Détails techniques")
            for k, v in data['technical_details'].items():
                st.markdown(f"**{k}** : {v}")

        except Exception as e:
            st.error(str(e))

if __name__ == "__main__":
    main()
