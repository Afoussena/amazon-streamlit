import requests
from bs4 import BeautifulSoup
import random
import streamlit as st

HEADERS_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
]

BASE_URL = "https://www.amazon.{domain}/dp/{asin}"
SEARCH_URL = "https://www.amazon.{domain}/s?k={query}"

def get_soup(url):
    headers = {'User-Agent': random.choice(HEADERS_LIST)}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Erreur de requête ({response.status_code}) pour l'URL: {url}")
    return BeautifulSoup(response.text, 'html.parser')

def get_asin_from_query(query, domain="fr"):
    domain = domain.lower().strip().replace("https://", "").replace("http://", "").replace("www.amazon.", "")
    url = SEARCH_URL.format(domain=domain, query=query.replace(" ", "+"))
    soup = get_soup(url)
    result = soup.select_one("div.s-result-item[data-asin]")
    if result and result['data-asin']:
        return result['data-asin']
    raise Exception("Aucun produit trouvé pour la requête.")

def extract_product_data(asin, domain="fr"):
    domain = domain.lower().strip().replace("https://", "").replace("http://", "").replace("www.amazon.", "")
    url = BASE_URL.format(domain=domain, asin=asin)
    soup = get_soup(url)
    data = {
        'title': soup.select_one('#productTitle').get_text(strip=True) if soup.select_one('#productTitle') else 'N/A',
        'features': [li.get_text(strip=True) for li in soup.select('#feature-bullets li') if li.get_text(strip=True)],
        'technical_details': {},
        'customer_reviews': []
    }
    for table in soup.select("table#productDetails_techSpec_section_1, table#productDetails_detailBullets_sections1"):
        for row in table.select("tr"):
            th = row.select_one("th")
            td = row.select_one("td")
            if th and td:
                data['technical_details'][th.get_text(strip=True)] = td.get_text(strip=True)
    for review in soup.select(".review-text-content span"):
        text = review.get_text(strip=True)
        if text:
            data['customer_reviews'].append(text)
    return data

def main():
    st.title("🛒 Extracteur de données Amazon")
    mode = st.radio("Méthode de recherche", ["ASIN", "Nom du produit"])
    domain = st.text_input("Domaine Amazon (ex: fr, com, de)", "fr")

    user_input = ""
    if mode == "ASIN":
        user_input = st.text_input("Entrez l'ASIN du produit")
    else:
        user_input = st.text_input("Entrez le nom du produit")

    if st.button("Extraire les données") and user_input:
        try:
            asin = user_input
            if mode != "ASIN":
                asin = get_asin_from_query(user_input, domain)
                st.success(f"ASIN trouvé : {asin}")
            data = extract_product_data(asin, domain)
            st.subheader("Titre")
            st.write(data['title'])

            st.subheader("Caractéristiques")
            for f in data['features']:
                st.markdown(f"- {f}")

            st.subheader("Détails techniques")
            for k, v in data['technical_details'].items():
                st.markdown(f"**{k}** : {v}")

            st.subheader("Avis clients")
            for i, review in enumerate(data['customer_reviews'], 1):
                st.markdown(f"{i}. {review}")

        except Exception as e:
            st.error(str(e))

if __name__ == "__main__":
    main()
