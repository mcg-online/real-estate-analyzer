from datetime import datetime, timezone
from utils.database import get_db
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)


class Property:
    collection_name = 'properties'

    def __init__(self, address, price, bedrooms, bathrooms, sqft, year_built,
                 property_type, lot_size, listing_url, source, latitude=None,
                 longitude=None, images=None, description=None, city='',
                 state='', zip_code='', user_id=None):
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code
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
        self.user_id = user_id
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at
        self.metrics = {}
        self.score = None

    def save(self):
        db = get_db()
        try:
            if not hasattr(self, '_id'):
                existing = db[self.collection_name].find_one({'listing_url': self.listing_url})
                if existing:
                    self._id = existing['_id']
                    self.updated_at = datetime.now(timezone.utc)
                    db[self.collection_name].update_one(
                        {'_id': self._id},
                        {'$set': self.to_dict()}
                    )
                else:
                    result = db[self.collection_name].insert_one(self.to_dict())
                    self._id = result.inserted_id
            else:
                self.updated_at = datetime.now(timezone.utc)
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
            property_id = ObjectId(property_id)
        property_data = db[cls.collection_name].find_one({'_id': property_id})
        if property_data:
            return cls.from_dict(property_data)
        return None

    def to_dict(self):
        return {
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
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
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'metrics': self.metrics,
            'score': self.score
        }

    @classmethod
    def from_dict(cls, data):
        try:
            instance = cls(
                address=data.get('address', 'Unknown'),
                price=data.get('price', 0),
                bedrooms=data.get('bedrooms', 0),
                bathrooms=data.get('bathrooms', 0),
                sqft=data.get('sqft', 0),
                year_built=data.get('year_built', 0),
                property_type=data.get('property_type', 'Unknown'),
                lot_size=data.get('lot_size', 0),
                listing_url=data.get('listing_url', ''),
                source=data.get('source', 'Unknown'),
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                images=data.get('images', []),
                description=data.get('description'),
                city=data.get('city', ''),
                state=data.get('state', ''),
                zip_code=data.get('zip_code', '')
            )
            instance._id = data.get('_id')
            instance.user_id = data.get('user_id')
            instance.created_at = data.get('created_at', instance.created_at)
            instance.updated_at = data.get('updated_at', instance.updated_at)
            instance.metrics = data.get('metrics', {})
            instance.score = data.get('score')
            return instance
        except Exception as e:
            logger.error(f"Failed to deserialize property document {data.get('_id')}: {e}")
            return None

    @classmethod
    def find_all(cls, filters=None, limit=100, skip=0, sort_by='price', sort_order=1,
                 cursor=None):
        """Fetch properties from MongoDB.

        When *cursor* (an ObjectId) is provided the method switches to
        cursor-based pagination: results are filtered to documents whose
        ``_id`` is strictly greater than the cursor value and are always
        sorted by ``_id`` ascending so the ordering is stable and
        consistent with subsequent cursor advances.

        When *cursor* is None the method uses traditional offset/limit
        pagination controlled by *skip*, *sort_by*, and *sort_order*.
        """
        db = get_db()
        query = dict(filters or {})

        if cursor is not None:
            # Merge the _id lower-bound into the existing query filters.
            # If the caller already has an _id filter (unusual) we wrap both
            # conditions in an $and clause to preserve them.
            id_filter = {'_id': {'$gt': cursor}}
            if '_id' in query:
                query = {'$and': [query, id_filter]}
            else:
                query['_id'] = {'$gt': cursor}

            # Cursor pagination requires a stable sort on _id.
            mongo_cursor = (
                db[cls.collection_name]
                .find(query)
                .sort('_id', 1)
                .limit(limit)
            )
        else:
            mongo_cursor = (
                db[cls.collection_name]
                .find(query)
                .sort(sort_by, sort_order)
                .skip(skip)
                .limit(limit)
            )

        return [p for p in (cls.from_dict(doc) for doc in mongo_cursor) if p is not None]
