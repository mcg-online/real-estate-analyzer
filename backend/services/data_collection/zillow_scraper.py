import aiohttp
import asyncio
from bs4 import BeautifulSoup
import requests
import time
import random
import logging
from models.property import Property

logger = logging.getLogger(__name__)

class ZillowScraper:
    def __init__(self):
        self.base_url = "https://www.zillow.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    async def _fetch_page(self, session, url):
        async with session.get(url, headers=self.headers) as response:
            return await response.text()

    async def search_properties(self, city, state, max_pages=3):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for page in range(1, max_pages + 1):
                url = self._get_search_url(city, state, page)
                tasks.append(self._fetch_page(session, url))
            
            pages = await asyncio.gather(*tasks)
            properties = []
            for page_content in pages:
                soup = BeautifulSoup(page_content, 'html.parser')
                listings = self._extract_listings_from_page(soup)
                for listing in listings:
                    prop_data = self._parse_property_details(listing['url'])
                    if prop_data:
                        properties.append(Property(**prop_data))
            return properties

    def _get_search_url(self, city, state, page=1):
        city_state = f"{city}-{state}".lower().replace(' ', '-')
        if page == 1:
            return f"{self.base_url}/homes/{city_state}/for_sale/"
        return f"{self.base_url}/homes/{city_state}/for_sale/{page}_p/"

    def _extract_listings_from_page(self, soup):
        listings = []
        property_cards = soup.select('article.list-card')
        for card in property_cards:
            url_elem = card.select_one('a.list-card-link')
            if url_elem and url_elem['href'].startswith('http'):
                listings.append({'url': url_elem['href']})
        return listings

    def _parse_property_details(self, property_url):
        try:
            response = requests.get(property_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            address_elem = soup.select_one('.ds-address-container')
            address = address_elem.text.strip() if address_elem else "Unknown Address"

            price_elem = soup.select_one('[data-testid="price"]')
            price_str = price_elem.text.replace('$', '').replace(',', '') if price_elem else "0"
            price = int(price_str) if price_str.isdigit() else 0

            beds_elem = soup.select_one('[data-testid="bed-bath-beyond"] span:nth-child(1)')
            bedrooms = int(beds_elem.text.split()[0]) if beds_elem and beds_elem.text.split()[0].isdigit() else 0

            baths_elem = soup.select_one('[data-testid="bed-bath-beyond"] span:nth-child(2)')
            bathrooms = float(baths_elem.text.split()[0]) if baths_elem and baths_elem.text.split()[0].replace('.', '').isdigit() else 0

            sqft_elem = soup.select_one('[data-testid="bed-bath-beyond"] span:nth-child(3)')
            sqft = int(sqft_elem.text.split()[0].replace(',', '')) if sqft_elem and sqft_elem.text.split()[0].replace(',', '').isdigit() else 0

            return {
                'address': address,
                'price': price,
                'bedrooms': bedrooms,
                'bathrooms': bathrooms,
                'sqft': sqft,
                'year_built': 0,  # Placeholder; Zillow parsing may vary
                'property_type': 'Residential',
                'lot_size': 0,  # Placeholder
                'listing_url': property_url,
                'source': 'Zillow'
            }
        except requests.RequestException as e:
            logger.error(f"Network error for {property_url}: {e}")
            return None
        except (ValueError, AttributeError) as e:
            logger.error(f"Parsing error for {property_url}: {e}")
            return None