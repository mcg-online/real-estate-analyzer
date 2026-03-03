import pytest
import sys
import os

# Add backend directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class MockProperty:
    """Mock property object for testing"""
    def __init__(self, price=200000, bedrooms=3, bathrooms=2, sqft=1500,
                 year_built=2000, property_type='Residential', lot_size=5000,
                 listing_url='http://example.com/property', source='Test',
                 city='Seattle', state='WA', zip_code='98101'):
        self.price = price
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.sqft = sqft
        self.year_built = year_built
        self.property_type = property_type
        self.lot_size = lot_size
        self.listing_url = listing_url
        self.source = source
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self._id = 'test_id_123'
        self.latitude = 47.6062
        self.longitude = -122.3321
        self.images = []
        self.description = 'Test property'
        self.metrics = {}
        self.score = None


@pytest.fixture
def mock_property():
    return MockProperty()


@pytest.fixture
def expensive_property():
    return MockProperty(price=800000, bedrooms=5, bathrooms=4, sqft=4000,
                        year_built=2020, property_type='Residential', lot_size=10000)


@pytest.fixture
def cheap_property():
    return MockProperty(price=80000, bedrooms=2, bathrooms=1, sqft=800,
                        year_built=1960, property_type='Residential', lot_size=3000)


@pytest.fixture
def default_market_data():
    return {
        'property_tax_rate': 0.01,
        'price_to_rent_ratio': 15,
        'vacancy_rate': 0.08,
        'appreciation_rate': 0.03,
        'days_on_market': 30,
        'avg_hoa_fee': 0,
    }


@pytest.fixture
def strong_market_data():
    return {
        'property_tax_rate': 0.008,
        'price_to_rent_ratio': 10,
        'vacancy_rate': 0.03,
        'appreciation_rate': 0.06,
        'days_on_market': 15,
        'avg_hoa_fee': 0,
        'rent_growth_rate': 0.05,
        'walk_score': 90,
        'school_rating': 9,
        'crime_rating': 9,
    }


@pytest.fixture
def weak_market_data():
    return {
        'property_tax_rate': 0.02,
        'price_to_rent_ratio': 25,
        'vacancy_rate': 0.15,
        'appreciation_rate': 0.00,
        'days_on_market': 90,
        'avg_hoa_fee': 200,
        'rent_growth_rate': 0.0,
        'unemployment_rate': 0.10,
        'walk_score': 20,
        'school_rating': 3,
        'crime_rating': 3,
    }
