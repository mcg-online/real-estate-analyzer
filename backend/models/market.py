from datetime import datetime
from utils.database import get_db
from bson import ObjectId

class Market:
    collection_name = 'markets'

    def __init__(self, name, market_type, state=None, county=None, 
                 city=None, zip_code=None, population=None, 
                 median_income=None, unemployment_rate=None):
        self.name = name
        self.market_type = market_type  # state, county, city, zip_code
        self.state = state
        self.county = county
        self.city = city
        self.zip_code = zip_code
        self.population = population
        self.median_income = median_income
        self.unemployment_rate = unemployment_rate
        self.metrics = {}
        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at
        
        # Market-specific metrics
        self.property_tax_rate = None
        self.price_to_rent_ratio = None
        self.vacancy_rate = None
        self.appreciation_rate = None
        self.median_home_price = None
        self.median_rent = None
        self.price_per_sqft = None
        self.days_on_market = None
        self.school_rating = None
        self.crime_rating = None
        self.walk_score = None
        self.transit_score = None
        self.avg_hoa_fee = None
        
        # Tax benefits specific to this location
        self.tax_benefits = {}
        # Financing programs available in this location
        self.financing_programs = []

    def save(self):
        db = get_db()
        if not hasattr(self, '_id'):
            result = db[self.collection_name].insert_one(self.to_dict())
            self._id = result.inserted_id
        else:
            self.updated_at = datetime.utcnow()
            db[self.collection_name].update_one(
                {'_id': self._id}, 
                {'$set': self.to_dict()}
            )
        return self

    @classmethod
    def find_by_id(cls, market_id):
        db = get_db()
        market_data = db[cls.collection_name].find_one({'_id': ObjectId(market_id)})
        if market_data:
            return cls.from_dict(market_data)
        return None

    @classmethod
    def find_by_location(cls, location_type, location_value):
        db = get_db()
        query = {location_type: location_value}
        market_data = db[cls.collection_name].find_one(query)
        if market_data:
            return cls.from_dict(market_data)
        return None

    @classmethod
    def find_all(cls, filters=None, limit=100, skip=0):
        db = get_db()
        cursor = db[cls.collection_name].find(filters or {}).limit(limit).skip(skip)
        return [cls.from_dict(m) for m in cursor]

    def to_dict(self):
        return {
            'name': self.name,
            'market_type': self.market_type,
            'state': self.state,
            'county': self.county,
            'city': self.city,
            'zip_code': self.zip_code,
            'population': self.population,
            'median_income': self.median_income,
            'unemployment_rate': self.unemployment_rate,
            'metrics': self.metrics,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'property_tax_rate': self.property_tax_rate,
            'price_to_rent_ratio': self.price_to_rent_ratio,
            'vacancy_rate': self.vacancy_rate,
            'appreciation_rate': self.appreciation_rate,
            'median_home_price': self.median_home_price,
            'median_rent': self.median_rent,
            'price_per_sqft': self.price_per_sqft,
            'days_on_market': self.days_on_market,
            'school_rating': self.school_rating,
            'crime_rating': self.crime_rating,
            'walk_score': self.walk_score,
            'transit_score': self.transit_score,
            'avg_hoa_fee': self.avg_hoa_fee,
            'tax_benefits': self.tax_benefits,
            'financing_programs': self.financing_programs
        }

    @classmethod
    def from_dict(cls, data):
        if '_id' in data:
            data['_id'] = str(data['_id']) if isinstance(data['_id'], ObjectId) else data['_id']
            
        instance = cls(
            name=data['name'],
            market_type=data['market_type'],
            state=data.get('state'),
            county=data.get('county'),
            city=data.get('city'),
            zip_code=data.get('zip_code'),
            population=data.get('population'),
            median_income=data.get('median_income'),
            unemployment_rate=data.get('unemployment_rate')
        )
        
        if '_id' in data:
            instance._id = data['_id']
        
        instance.metrics = data.get('metrics', {})
        instance.created_at = data.get('created_at', instance.created_at)
        instance.updated_at = data.get('updated_at', instance.updated_at)
        
        # Set market-specific metrics
        instance.property_tax_rate = data.get('property_tax_rate')
        instance.price_to_rent_ratio = data.get('price_to_rent_ratio')
        instance.vacancy_rate = data.get('vacancy_rate')
        instance.appreciation_rate = data.get('appreciation_rate')
        instance.median_home_price = data.get('median_home_price')
        instance.median_rent = data.get('median_rent')
        instance.price_per_sqft = data.get('price_per_sqft')
        instance.days_on_market = data.get('days_on_market')
        instance.school_rating = data.get('school_rating')
        instance.crime_rating = data.get('crime_rating')
        instance.walk_score = data.get('walk_score')
        instance.transit_score = data.get('transit_score')
        instance.avg_hoa_fee = data.get('avg_hoa_fee')
        
        instance.tax_benefits = data.get('tax_benefits', {})
        instance.financing_programs = data.get('financing_programs', [])
        
        return instance