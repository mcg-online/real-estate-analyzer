from flask import request, jsonify
from flask_restful import Resource
from models.property import Property
from services.analysis.financial_metrics import FinancialMetrics
from services.analysis.opportunity_scoring import OpportunityScoring
from services.analysis.tax_benefits import TaxBenefits
from services.analysis.financing_options import FinancingOptions
from bson import ObjectId
import traceback
import json
from bson import ObjectId

class PropertyListResource(Resource):
    def get(self):
        """Get list of properties with filtering options"""
        try:
            # Parse query parameters
            filters = {}
            price_min = request.args.get('minPrice')
            price_max = request.args.get('maxPrice')
            if price_min or price_max:
                filters['price'] = {}
                if price_min:
                    filters['price']['$gte'] = int(price_min)
                if price_max:
                    filters['price']['$lte'] = int(price_max)
            
            bedrooms_min = request.args.get('minBedrooms')
            if bedrooms_min:
                filters['bedrooms'] = {'$gte': float(bedrooms_min)}
                
            bathrooms_min = request.args.get('minBathrooms')
            if bathrooms_min:
                filters['bathrooms'] = {'$gte': float(bathrooms_min)}
                
            property_type = request.args.get('propertyType')
            if property_type:
                filters['property_type'] = property_type
                
            city = request.args.get('city')
            if city:
                filters['city'] = city
                
            state = request.args.get('state')
            if state:
                filters['state'] = state
                
            zip_code = request.args.get('zipCode')
            if zip_code:
                filters['zip_code'] = zip_code
                
            score_min = request.args.get('minScore')
            if score_min:
                filters['score'] = {'$gte': float(score_min)}
                
            # Pagination
            limit = int(request.args.get('limit', 50))
            page = int(request.args.get('page', 1))
            skip = (page - 1) * limit
            
            # Sorting
            sort_by = request.args.get('sortBy', 'price')
            sort_order = 1 if request.args.get('sortOrder', 'asc') == 'asc' else -1
            
            # Get properties
            properties = Property.find_all(
                filters=filters,
                limit=limit,
                skip=skip,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            # Convert to JSON
            properties_json = [p.to_dict() for p in properties]
            for p in properties_json:
                if '_id' in p and isinstance(p['_id'], ObjectId):
                    p['_id'] = str(p['_id'])
                    
            return properties_json, 200
            
        except Exception as e:
            traceback.print_exc()
            return {'error': str(e)}, 500

    def post(self):
        """Create a new property"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['address', 'price', 'bedrooms', 'bathrooms', 'sqft', 
                             'year_built', 'property_type', 'lot_size', 'listing_url', 'source']
            for field in required_fields:
                if field not in data:
                    return {'error': f'Missing required field: {field}'}, 400
                    
            # Create property
            property = Property(
                address=data['address'],
                city=data.get('city', ''),
                state=data.get('state', ''),
                zip_code=data.get('zip_code', ''),
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
            
            # Save to database
            property.save()
            
            # Return created property
            result = property.to_dict()
            if '_id' in result and isinstance(result['_id'], ObjectId):
                result['_id'] = str(result['_id'])
                
            return result, 201
            
        except Exception as e:
            traceback.print_exc()
            return {'error': str(e)}, 500


class PropertyResource(Resource):
    def get(self, property_id):
        """Get a single property by ID"""
        try:
            property = Property.find_by_id(property_id)
            if not property:
                return {'error': 'Property not found'}, 404
                
            # Convert to JSON
            result = property.to_dict()
            if '_id' in result and isinstance(result['_id'], ObjectId):
                result['_id'] = str(result['_id'])
                
            return result, 200
            
        except Exception as e:
            traceback.print_exc()
            return {'error': str(e)}, 500

    def put(self, property_id):
        """Update a property"""
        try:
            property = Property.find_by_id(property_id)
            if not property:
                return {'error': 'Property not found'}, 404
                
            data = request.get_json()
            
            # Update fields
            for key, value in data.items():
                if key != '_id' and hasattr(property, key):
                    setattr(property, key, value)
                    
            # Save changes
            property.save()
            
            # Return updated property
            result = property.to_dict()
            if '_id' in result and isinstance(result['_id'], ObjectId):
                result['_id'] = str(result['_id'])
                
            return result, 200
            
        except Exception as e:
            traceback.print_exc()
            return {'error': str(e)}, 500

    def delete(self, property_id):
        """Delete a property"""
        try:
            property = Property.find_by_id(property_id)
            if not property:
                return {'error': 'Property not found'}, 404
                
            # Delete from database
            db = get_db()
            db[Property.collection_name].delete_one({'_id': ObjectId(property_id)})
            
            return {'message': 'Property deleted successfully'}, 200
            
        except Exception as e:
            traceback.print_exc()
            return {'error': str(e)}, 500