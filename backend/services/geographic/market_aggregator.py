class MarketAggregator:
    def __init__(self, db):
        self.db = db
        
    def aggregate_by_state(self, state_code):
        """Aggregate property data at the state level"""
        pipeline = [
            {'$match': {'state': state_code}},
            {'$group': {
                '_id': '$state',
                'count': {'$sum': 1},
                'avg_price': {'$avg': '$price'},
                'avg_sqft': {'$avg': '$sqft'},
                'avg_price_per_sqft': {'$avg': {'$divide': ['$price', '$sqft']}},
                'median_bedrooms': {'$avg': '$bedrooms'},
                'median_bathrooms': {'$avg': '$bathrooms'},
                'min_price': {'$min': '$price'},
                'max_price': {'$max': '$price'},
            }},
            {'$project': {
                'state': '$_id',
                'count': 1,
                'avg_price': 1,
                'avg_sqft': 1,
                'avg_price_per_sqft': 1,
                'median_bedrooms': 1,
                'median_bathrooms': 1,
                'price_range': {
                    'min': '$min_price',
                    'max': '$max_price'
                },
                '_id': 0
            }}
        ]
        
        result = list(self.db.properties.aggregate(pipeline))
        return result[0] if result else None
        
    def aggregate_by_city(self, state_code, city):
        """Aggregate property data at the city level"""
        pipeline = [
            {'$match': {'state': state_code, 'city': city}},
            {'$group': {
                '_id': {'state': '$state', 'city': '$city'},
                'count': {'$sum': 1},
                'avg_price': {'$avg': '$price'},
                'avg_sqft': {'$avg': '$sqft'},
                'avg_price_per_sqft': {'$avg': {'$divide': ['$price', '$sqft']}},
                'median_bedrooms': {'$avg': '$bedrooms'},
                'median_bathrooms': {'$avg': '$bathrooms'},
                'min_price': {'$min': '$price'},
                'max_price': {'$max': '$price'},
            }},
            {'$project': {
                'state': '$_id.state',
                'city': '$_id.city',
                'count': 1,
                'avg_price': 1,
                'avg_sqft': 1,
                'avg_price_per_sqft': 1,
                'median_bedrooms': 1,
                'median_bathrooms': 1,
                'price_range': {
                    'min': '$min_price',
                    'max': '$max_price'
                },
                '_id': 0
            }}
        ]
        
        result = list(self.db.properties.aggregate(pipeline))
        return result[0] if result else None
        
    def aggregate_by_zip_code(self, zip_code):
        """Aggregate property data at the zip code level"""
        pipeline = [
            {'$match': {'zip_code': zip_code}},
            {'$group': {
                '_id': '$zip_code',
                'count': {'$sum': 1},
                'avg_price': {'$avg': '$price'},
                'avg_sqft': {'$avg': '$sqft'},
                'avg_price_per_sqft': {'$avg': {'$divide': ['$price', '$sqft']}},
                'median_bedrooms': {'$avg': '$bedrooms'},
                'median_bathrooms': {'$avg': '$bathrooms'},
                'min_price': {'$min': '$price'},
                'max_price': {'$max': '$price'},
            }},
            {'$project': {
                'zip_code': '$_id',
                'count': 1,
                'avg_price': 1,
                'avg_sqft': 1,
                'avg_price_per_sqft': 1,
                'median_bedrooms': 1,
                'median_bathrooms': 1,
                'price_range': {
                    'min': '$min_price',
                    'max': '$max_price'
                },
                '_id': 0
            }}
        ]
        
        result = list(self.db.properties.aggregate(pipeline))
        return result[0] if result else None
        
    def top_markets_by_roi(self, limit=10):
        """Find top markets ranked by ROI potential"""
        pipeline = [
            {'$match': {'metrics.cap_rate': {'$exists': True}}},
            {'$group': {
                '_id': {'state': '$state', 'city': '$city'},
                'count': {'$sum': 1},
                'avg_price': {'$avg': '$price'},
                'avg_cap_rate': {'$avg': '$metrics.cap_rate'},
                'avg_cash_flow': {'$avg': '$metrics.monthly_cash_flow'},
                'avg_roi': {'$avg': '$metrics.roi.annualized_roi'},
            }},
            {'$match': {'count': {'$gte': 5}}},  # Only include markets with enough data
            {'$sort': {'avg_roi': -1}},
            {'$limit': limit},
            {'$project': {
                'state': '$_id.state',
                'city': '$_id.city',
                'count': 1,
                'avg_price': 1,
                'avg_cap_rate': 1,
                'avg_cash_flow': 1,
                'avg_roi': 1,
                '_id': 0
            }}
        ]
        
        return list(self.db.properties.aggregate(pipeline))
        
    def compare_markets(self, markets, metrics=None):
        """Compare multiple markets across key metrics"""
        if not metrics:
            metrics = ['avg_price', 'avg_price_per_sqft', 'avg_cap_rate', 'avg_cash_flow', 'avg_roi']
            
        result = []
        
        for market in markets:
            if 'city' in market and 'state' in market:
                # City-level comparison
                data = self.aggregate_by_city(market['state'], market['city'])
            elif 'state' in market:
                # State-level comparison
                data = self.aggregate_by_state(market['state'])
            elif 'zip_code' in market:
                # Zip code-level comparison
                data = self.aggregate_by_zip_code(market['zip_code'])
            else:
                continue
                
            if data:
                result.append(data)
                
        return result