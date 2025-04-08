from datetime import datetime
from utils.database import get_db
import logging
from bson import ObjectId   # Import ObjectId for MongoDB document IDs

logger = logging.getLogger(__name__)

class Property:
    collection_name = 'properties'

    def __init__(self, address, price, bedrooms, bathrooms, sqft, year_built,
                 property_type, lot_size, listing_url, source, latitude=None,
                 longitude=None, images=None, description=None):
        self.address = address
        self.price = price
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.sqft = sqft
        self.year_built = year_built
        self.property_type = property_type
        self.lot_size = lot_size
        self.listing_url = listing_url
        self.source = source
        self.latitude = latitude
        self.longitude = longitude
        self.images = images or []
        self.description = description
        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at
        self.metrics = {}
        self.score = None

    def save(self):
        db = get_db()
        try:
            if not hasattr(self, '_id'):
                # Check for existing property by listing_url
                existing = db[self.collection_name].find_one({'listing_url': self.listing_url})
                if existing:
                    self._id = existing['_id']
                    self.updated_at = datetime.utcnow()
                    db[self.collection_name].update_one(
                        {'_id': self._id},
                        {'$set': self.to_dict()}
                    )
                else:
                    result = db[self.collection_name].insert_one(self.to_dict())
                    self._id = result.inserted_id
            else:
                self.updated_at = datetime.utcnow()
                db[self.collection_name].update_one(
                    {'_id': self._id},
                    {'$set': self.to_dict()}
                )
            return self
        except Exception as e:
            logger.error(f"Error saving property {self.listing_url}: {e}")
            raise

    @classmethod
    def find_by_id(cls, property_id):
        db = get_db()
        if isinstance(property_id, str):
            property_id = ObjectId(property_id)  # Convert string ID to ObjectId if necessary
        property_data = db[cls.collection_name].find_one({'_id': property_id})
        if property_data:
            return cls.from_dict(property_data)
        return None  

    @classmethod
    def find_all(cls, filters=None, limit=100, skip=0):
        db = get_db()
        cursor = db[cls.collection_name].find(filters or {}).limit(limit).skip(skip)
        return [cls.from_dict(p) for p in cursor]

    def to_dict(self):
        return {
            'address': self.address,
            'price': self.price,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'sqft': self.sqft,
            'year_built': self.year_built,
            'property_type': self.property_type,
            'lot_size': self.lot_size,
            'listing_url': self.listing_url,
            'source': self.source,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'images': self.images,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metrics': self.metrics,
            'score': self.score
        }

    @classmethod
    def from_dict(cls, data):
        instance = cls(
            address=data['address'],
            price=data['price'],
            bedrooms=data['bedrooms'],
            bathrooms=data['bathrooms'],
            sqft=data['sqft'],
            year_built=data['year_built'],
            property_type=data['property_type'],
            lot_size=data['lot_size'],
            listing_url=data['listing_url'],
            source=data['source'],
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            images=data.get('images', []),
            description=data.get('description')
        )
        instance._id = data.get('_id')
        instance.created_at = data.get('created_at', instance.created_at)
        instance.updated_at = data.get('updated_at', instance.updated_at)
        instance.metrics = data.get('metrics', {})
        instance.score = data.get('score')
        return instance