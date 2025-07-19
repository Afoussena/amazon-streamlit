import requests
from bs4 import BeautifulSoup
import random
import streamlit as st
import re

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

def extract_reviews_by_rating(domain, asin, star, max_count):
    reviews = []
    page = 1
    while len(reviews) < max_count:
        url = f"https://www.amazon.{domain}/product-reviews/{asin}/?filterByStar={star}_star&pageNumber={page}"
        soup = get_soup(url)
        review_elements = soup.select(".review")
        if not review_elements:
            break
        for review in review_elements:
            text_el = review.select_one(".review-text-content span")
            if text_el:
                text = text_el.get_text(strip=True)
                reviews.append(text)
                if len(reviews) >= max_count:
                    break
        page += 1
    return reviews

def extract_product_data_from_url(url, domain, review_limits):
    soup = get_soup(url)
    asin_match = re.search(r"/dp/([A-Z0-9]{10})", url)
    asin = asin_match.group(1) if asin_match else None

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

    if asin:
        for star in range(5, 0, -1):
            reviews = extract_reviews_by_rating(domain, asin, star, review_limits.get(star, 0))
            data['customer_reviews'].extend([f"{star}★: {rev}" for rev in reviews])

    return data

def main():
    st.title("🛒 Extracteur de données Amazon - V2")
    mode = st.radio("Méthode de recherche", ["ASIN", "Nom du produit", "URL du produit"])
    domain = st.text_input("Domaine Amazon (ex: fr, com, de)", "fr")

    review_limits = {}
    with st.expander("Nombre d'avis à extraire par note"):
        for i in range(5, 0, -1):
            review_limits[i] = st.number_input(f"Avis {i} étoiles", min_value=0, max_value=100, value=2, step=1)

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
                url = user_input.strip()
                data = extract_product_data_from_url(url, domain, review_limits)
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
                data = extract_product_data_from_url(url, domain, review_limits)

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
