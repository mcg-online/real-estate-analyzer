"""
Centralized request validation decorators for Flask-RESTful Resource handlers.

Usage examples
--------------
from utils.request_validators import require_json_body, validate_objectid, require_entity
from models.property import Property

class MyResource(Resource):

    @validate_objectid('property_id')
    def get(self, property_id):
        # property_id is already validated as a well-formed ObjectId string
        ...

    @require_json_body
    def post(self, data):
        # ``data`` is guaranteed to be a non-empty dict parsed from the JSON body
        ...

    @require_entity(Property, 'property_id', inject_as='property_obj')
    def delete(self, property_id, property_obj):
        # property_id validated; property_obj is the loaded Property instance
        ...

Decorator stacking order
------------------------
Because each decorator wraps the function independently, stacking order matters
when you combine them.  Apply decorators from innermost (closest to the function)
to outermost:

    @validate_objectid('property_id')   # runs second
    @require_json_body                   # runs first (innermost)
    def put(self, property_id, data):
        ...

    # Execution order: validate_objectid -> require_json_body -> put
    # (Python applies decorators bottom-up)

Notes
-----
- All decorators are compatible with ``flask_restful.Resource`` methods.
- ``require_entity`` subsumes ``validate_objectid``; do not stack both for
  the same parameter.
- Python 3.9 compatible (no use of 3.10+ syntax).
"""

import functools
import logging

from flask import request

from utils.errors import error_response
from utils.validation import is_valid_objectid

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# require_json_body
# ---------------------------------------------------------------------------

def require_json_body(fn):
    """Decorator that parses and validates the JSON request body.

    Ensures the incoming request carries a non-empty JSON object (dict).
    On success the parsed dict is injected as the keyword argument ``data``
    into the decorated function.

    Responses on failure:

    - 400 VALIDATION_ERROR — body is missing, not valid JSON, or not a dict.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        body = request.get_json(silent=True)
        if not body or not isinstance(body, dict):
            return error_response(
                'Request body must be JSON',
                'VALIDATION_ERROR',
                400,
            )
        return fn(*args, data=body, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# validate_objectid
# ---------------------------------------------------------------------------

def validate_objectid(param_name):
    """Decorator factory that validates a URL parameter as a MongoDB ObjectId.

    Parameters
    ----------
    param_name:
        Name of the keyword argument in the decorated function that holds the
        raw ObjectId string (e.g. ``'property_id'``, ``'market_id'``).

    Responses on failure:

    - 400 VALIDATION_ERROR — the value is not a valid 24-character hex string.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            raw_id = kwargs.get(param_name)
            if not is_valid_objectid(raw_id):
                # Build a human-readable error using the parameter name so the
                # caller can tell which ID failed (e.g. "Invalid property_id format").
                label = param_name.replace('_', ' ')
                return error_response(
                    f'Invalid {label} format',
                    'VALIDATION_ERROR',
                    400,
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# require_entity
# ---------------------------------------------------------------------------

def require_entity(model_class, param_name, inject_as):
    """Decorator factory that validates an ObjectId and loads the entity.

    Combines ObjectId validation with the database lookup, so route handlers
    do not need to repeat the ``find_by_id`` / 404-guard pattern.

    Parameters
    ----------
    model_class:
        The model class to load from (must expose ``find_by_id(id_str)``).
    param_name:
        Name of the URL keyword argument containing the raw ObjectId string.
    inject_as:
        Name of the keyword argument under which the loaded entity is injected
        into the decorated function.

    Responses on failure:

    - 400 VALIDATION_ERROR — the value is not a valid 24-character hex string.
    - 404 NOT_FOUND        — no document with that ID exists in the collection.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            raw_id = kwargs.get(param_name)

            # Step 1: ObjectId format check.
            if not is_valid_objectid(raw_id):
                label = param_name.replace('_', ' ')
                return error_response(
                    f'Invalid {label} format',
                    'VALIDATION_ERROR',
                    400,
                )

            # Step 2: Database lookup.
            try:
                entity = model_class.find_by_id(raw_id)
            except Exception:
                logger.exception(
                    "require_entity: unexpected error looking up %s id=%s",
                    model_class.__name__,
                    raw_id,
                )
                return error_response(
                    'Internal server error during entity lookup',
                    'INTERNAL_ERROR',
                    500,
                )

            if entity is None:
                # Derive a friendly resource name from the model class name,
                # e.g. "Property" -> "Property not found".
                resource_name = model_class.__name__
                return error_response(
                    f'{resource_name} not found',
                    'NOT_FOUND',
                    404,
                )

            kwargs[inject_as] = entity
            return fn(*args, **kwargs)
        return wrapper
    return decorator
