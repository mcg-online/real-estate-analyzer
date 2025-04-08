import logging
from datetime import datetime
from services.data_collection.zillow_scraper import ZillowScraper
from models.property import Property
from models.market import Market
from utils.database import get_db

logger = logging.getLogger(__name__)

def update_property_data():
    """
    Update property data by scraping new listings and refreshing existing ones.
    This function is called by the scheduler.
    """
    try:
        logger.info(f"Starting scheduled property data update at {datetime.now()}")
        
        # Get cities to scan
        cities_to_scan = [
            {"city": "Seattle", "state": "WA"},
            {"city": "Portland", "state": "OR"},
            {"city": "San Francisco", "state": "CA"},
            # Add more cities as needed
        ]
        
        # Initialize scraper
        scraper = ZillowScraper()
        
        # Scan each city
        for city_data in cities_to_scan:
            try:
                logger.info(f"Scanning {city_data['city']}, {city_data['state']}")
                properties = scraper.search_properties(
                    city=city_data['city'],
                    state=city_data['state'],
                    max_pages=2  # Limit pages to avoid overloading
                )
                
                # Save properties to database
                for prop in properties:
                    prop.save()
                    
                logger.info(f"Found {len(properties)} properties in {city_data['city']}")
            except Exception as e:
                logger.error(f"Error scanning {city_data['city']}: {str(e)}")
                
        logger.info("Property data update completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error in property data update: {str(e)}")
        return False

def update_market_data():
    """
    Update market data including tax rates, appreciation rates, and other metrics.
    This function is called by the scheduler.
    """
    try:
        logger.info(f"Starting scheduled market data update at {datetime.now()}")
        
        # Get database connection
        db = get_db()
        
        # Get all markets
        markets = Market.find_all()
        
        for market in markets:
            try:
                # Here you would add code to fetch updated market data
                # from external sources like Census API, economic data APIs, etc.
                
                # For now, we'll just update the timestamp
                market.updated_at = datetime.utcnow()
                market.save()
                
                logger.info(f"Updated market data for {market.name}")
            except Exception as e:
                logger.error(f"Error updating market {market.name}: {str(e)}")
        
        logger.info("Market data update completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error in market data update: {str(e)}")
        return False

