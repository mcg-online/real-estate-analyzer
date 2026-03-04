from datetime import datetime
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.property import Property
from utils.database import get_db
from utils.errors import error_response
from utils.request_validators import require_json_body, require_entity
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

ALLOWED_PROPERTY_TYPES = ['single_family', 'condo', 'townhouse', 'multi_family', 'land', 'commercial']


def validate_property_data(data, require_all=True):
    """Validate property fields. Returns (is_valid, error_message).

    When require_all=True, all required fields must be present.
    When require_all=False (for PUT), only validates fields that are present.
    """
    errors = []

    def field_present(field):
        return field in data and data[field] is not None

    # address
    if require_all or field_present('address'):
        address = data.get('address', '')
        if not isinstance(address, str) or not address.strip():
            errors.append("'address' must be a non-empty string")

    # price
    if require_all or field_present('price'):
        price = data.get('price')
        try:
            if float(price) <= 0:
                errors.append("'price' must be greater than 0")
        except (TypeError, ValueError):
            errors.append("'price' must be a positive number")

    # sqft
    if require_all or field_present('sqft'):
        sqft = data.get('sqft')
        try:
            if float(sqft) <= 0:
                errors.append("'sqft' must be greater than 0")
        except (TypeError, ValueError):
            errors.append("'sqft' must be a positive number")

    # bedrooms
    if require_all or field_present('bedrooms'):
        bedrooms = data.get('bedrooms')
        try:
            if float(bedrooms) < 0:
                errors.append("'bedrooms' must be >= 0")
        except (TypeError, ValueError):
            errors.append("'bedrooms' must be a non-negative number")

    # bathrooms
    if require_all or field_present('bathrooms'):
        bathrooms = data.get('bathrooms')
        try:
            if float(bathrooms) < 0:
                errors.append("'bathrooms' must be >= 0")
        except (TypeError, ValueError):
            errors.append("'bathrooms' must be a non-negative number")

    # year_built
    if require_all or field_present('year_built'):
        year_built = data.get('year_built')
        try:
            year_int = int(year_built)
            current_year = datetime.now().year
            if year_int < 1800 or year_int > current_year + 1:
                errors.append(f"'year_built' must be between 1800 and {current_year + 1}")
        except (TypeError, ValueError):
            errors.append("'year_built' must be a valid year integer")

    # property_type
    if require_all or field_present('property_type'):
        property_type = data.get('property_type')
        if property_type not in ALLOWED_PROPERTY_TYPES:
            errors.append(
                f"'property_type' must be one of: {', '.join(ALLOWED_PROPERTY_TYPES)}"
            )

    # state (optional field, validated only if provided)
    if field_present('state'):
        state = data.get('state', '')
        if not (isinstance(state, str) and len(state) == 2 and state.isupper()):
            errors.append("'state' must be a 2-character uppercase string (e.g. 'CA')")

    if errors:
        return False, '; '.join(errors)
    return True, None


class PropertyListResource(Resource):
    def get(self):
        """Get list of properties with filtering options.

        Supports two mutually exclusive pagination modes:

        **Offset/limit pagination** (default, backward-compatible):
            ?page=1&limit=50
            Response: {data, total, page, limit, pages}

        **Cursor-based pagination** (opt-in via ``cursor`` query param):
            ?cursor=<objectid>&limit=50
            The cursor must be the ``_id`` value of the last item returned
            by the previous page.  Pass an empty string or omit the
            parameter entirely for the first page.
            Response: {data, next_cursor, has_more, limit}
        """
        try:
            # Parse and validate common filter query parameters
            filters = {}
            try:
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

                score_min = request.args.get('minScore')
                if score_min:
                    filters['score'] = {'$gte': float(score_min)}
            except (ValueError, TypeError):
                return error_response(
                    'Invalid numeric filter parameter', 'VALIDATION_ERROR', 400
                )

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

            # Validate and clamp the limit parameter (shared by both modes).
            try:
                limit = max(1, min(100, int(request.args.get('limit', 50))))
            except (ValueError, TypeError):
                return error_response(
                    'Invalid pagination parameter', 'VALIDATION_ERROR', 400
                )

            # ------------------------------------------------------------------
            # Cursor-based pagination branch
            # ------------------------------------------------------------------
            cursor_param = request.args.get('cursor')
            if cursor_param is not None:
                # An empty string means "first page" — no lower bound needed.
                cursor_oid = None
                if cursor_param != '':
                    from utils.validation import is_valid_objectid as _is_valid_objectid
                    if not _is_valid_objectid(cursor_param):
                        return error_response(
                            'Invalid cursor format: must be a valid ObjectId string',
                            'VALIDATION_ERROR',
                            400,
                        )
                    cursor_oid = ObjectId(cursor_param)

                properties = Property.find_all(
                    filters=filters,
                    limit=limit,
                    cursor=cursor_oid,
                )

                # Serialize and capture the _id of each result for next_cursor.
                properties_json = []
                last_id = None
                for prop in properties:
                    prop_dict = prop.to_dict()
                    raw_id = getattr(prop, '_id', None)
                    if raw_id is not None:
                        str_id = str(raw_id)
                        prop_dict['_id'] = str_id
                        last_id = str_id
                    elif '_id' in prop_dict and isinstance(prop_dict['_id'], ObjectId):
                        str_id = str(prop_dict['_id'])
                        prop_dict['_id'] = str_id
                        last_id = str_id
                    properties_json.append(prop_dict)

                has_more = len(properties_json) == limit
                return {
                    'data': properties_json,
                    'next_cursor': last_id if has_more else None,
                    'has_more': has_more,
                    'limit': limit,
                }, 200

            # ------------------------------------------------------------------
            # Offset/limit pagination branch (original, backward-compatible)
            # ------------------------------------------------------------------
            try:
                page = max(1, int(request.args.get('page', 1)))
            except (ValueError, TypeError):
                return error_response(
                    'Invalid pagination parameter', 'VALIDATION_ERROR', 400
                )
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

            # Count total matching documents for pagination metadata
            db = get_db()
            total = db[Property.collection_name].count_documents(filters)

            return {
                'data': properties_json,
                'total': total,
                'page': page,
                'limit': limit,
                'pages': -(-total // limit)  # ceiling division
            }, 200

        except Exception as e:
            logger.exception("Failed to list properties")
            return error_response(str(e), 'INTERNAL_ERROR', 500)

    @jwt_required()
    @require_json_body
    def post(self, data):
        """Create a new property"""
        try:
            # Validate required fields presence
            required_fields = ['address', 'price', 'bedrooms', 'bathrooms', 'sqft',
                             'year_built', 'property_type', 'lot_size', 'listing_url', 'source']
            for field in required_fields:
                if field not in data:
                    return error_response(f'Missing required field: {field}', 'VALIDATION_ERROR', 400)

            # Validate field values
            is_valid, error_msg = validate_property_data(data, require_all=True)
            if not is_valid:
                return error_response(error_msg, 'VALIDATION_ERROR', 400)

            # Create property
            user_id = get_jwt_identity()
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
                description=data.get('description'),
                user_id=user_id
            )

            # Save to database
            property.save()

            # Return created property
            result = property.to_dict()
            if '_id' in result and isinstance(result['_id'], ObjectId):
                result['_id'] = str(result['_id'])

            return result, 201

        except Exception as e:
            logger.exception("Failed to create property")
            return error_response(str(e), 'INTERNAL_ERROR', 500)


class PropertyResource(Resource):
    @require_entity(Property, 'property_id', inject_as='property_obj')
    def get(self, property_id, property_obj):
        """Get a single property by ID"""
        try:
            # Convert to JSON
            result = property_obj.to_dict()
            if '_id' in result and isinstance(result['_id'], ObjectId):
                result['_id'] = str(result['_id'])

            return result, 200

        except Exception as e:
            logger.exception("Failed to get property %s", property_id)
            return error_response(str(e), 'INTERNAL_ERROR', 500)

    @jwt_required()
    @require_entity(Property, 'property_id', inject_as='property_obj')
    @require_json_body
    def put(self, property_id, property_obj, data):
        """Update a property"""
        try:
            # Ownership check: only the creator may update (legacy properties with no
            # user_id are allowed through for backward compatibility)
            property_owner = getattr(property_obj, 'user_id', None)
            if property_owner is not None and property_owner != get_jwt_identity():
                return error_response('You do not own this property', 'FORBIDDEN', 403)

            # Validate only the fields being updated
            is_valid, error_msg = validate_property_data(data, require_all=False)
            if not is_valid:
                return error_response(error_msg, 'VALIDATION_ERROR', 400)

            # Update only whitelisted fields
            UPDATABLE_FIELDS = {
                'address', 'city', 'state', 'zip_code', 'price', 'bedrooms',
                'bathrooms', 'sqft', 'year_built', 'property_type', 'lot_size',
                'listing_url', 'source', 'latitude', 'longitude', 'images',
                'description'
            }
            for key, value in data.items():
                if key in UPDATABLE_FIELDS:
                    setattr(property_obj, key, value)

            # Save changes
            property_obj.save()

            # Return updated property
            result = property_obj.to_dict()
            if '_id' in result and isinstance(result['_id'], ObjectId):
                result['_id'] = str(result['_id'])

            return result, 200

        except Exception as e:
            logger.exception("Failed to update property %s", property_id)
            return error_response(str(e), 'INTERNAL_ERROR', 500)

    @jwt_required()
    @require_entity(Property, 'property_id', inject_as='property_obj')
    def delete(self, property_id, property_obj):
        """Delete a property"""
        try:
            # Ownership check: only the creator may delete (legacy properties with no
            # user_id are allowed through for backward compatibility)
            property_owner = getattr(property_obj, 'user_id', None)
            if property_owner is not None and property_owner != get_jwt_identity():
                return error_response('You do not own this property', 'FORBIDDEN', 403)

            # Delete from database
            db = get_db()
            db[Property.collection_name].delete_one({'_id': ObjectId(property_id)})

            return {'message': 'Property deleted successfully'}, 200

        except Exception as e:
            logger.exception("Failed to delete property %s", property_id)
            return error_response(str(e), 'INTERNAL_ERROR', 500)
