from flask import request
from flask_restful import Resource
from bson import ObjectId
from bson.errors import InvalidId
from models.property import Property
from models.market import Market
from services.analysis.financial_metrics import FinancialMetrics
from services.analysis.tax_benefits import TaxBenefits
from services.analysis.financing_options import FinancingOptions
from services.analysis.opportunity_scoring import OpportunityScoring
from services.geographic.market_aggregator import MarketAggregator
from utils.database import get_db
from utils.errors import error_response
import logging

logger = logging.getLogger(__name__)


def _is_valid_objectid(value):
    """Check if value is a valid 24-character hex ObjectId string."""
    try:
        ObjectId(value)
        return True
    except (InvalidId, TypeError):
        return False


# Default market data used when no market is found in the database
DEFAULT_MARKET_DATA = {
    'property_tax_rate': 0.01,
    'price_to_rent_ratio': 15,
    'vacancy_rate': 0.08,
    'appreciation_rate': 0.03,
    'avg_hoa_fee': 0,
    'tax_benefits': {},
    'financing_programs': [],
}


def _get_market_dict(property_obj):
    """Look up market data for a property, returning a dict suitable for analysis services."""
    market = None

    if property_obj.zip_code:
        market = Market.find_by_location('zip_code', property_obj.zip_code)

    if not market and property_obj.city and property_obj.state:
        market = Market.find_by_location('city', property_obj.city)

    if not market and property_obj.state:
        market = Market.find_by_location('state', property_obj.state)

    if market:
        # Convert Market object to dict so analysis services can use .get()
        return market.to_dict()

    return dict(DEFAULT_MARKET_DATA)


class PropertyAnalysisResource(Resource):
    def get(self, property_id):
        """Get comprehensive analysis for a single property"""
        try:
            if not _is_valid_objectid(property_id):
                return error_response('Invalid property ID format', 'VALIDATION_ERROR', 400)
            property_obj = Property.find_by_id(property_id)
            if not property_obj:
                return error_response('Property not found', 'NOT_FOUND', 404)

            market_data = _get_market_dict(property_obj)

            # Financial analysis
            financial_metrics = FinancialMetrics(property_obj, market_data)
            analysis = financial_metrics.analyze_property()

            # Tax benefits analysis
            tax_benefits = TaxBenefits(property_obj, market_data)
            tax_analysis = tax_benefits.analyze_tax_benefits()

            # Financing options
            financing = FinancingOptions(property_obj, market_data)
            financing_analysis = financing.analyze_financing_options()

            result = {
                'property_id': str(property_obj._id),
                'financial_analysis': analysis,
                'tax_benefits': tax_analysis,
                'financing_options': financing_analysis,
                'market_data': market_data
            }

            return result, 200

        except Exception as e:
            logger.exception("Failed to analyze property %s", property_id)
            return error_response(str(e), 'INTERNAL_ERROR', 500)

    def post(self, property_id):
        """Run custom analysis with user-defined parameters"""
        try:
            if not _is_valid_objectid(property_id):
                return error_response('Invalid property ID format', 'VALIDATION_ERROR', 400)
            property_obj = Property.find_by_id(property_id)
            if not property_obj:
                return error_response('Property not found', 'NOT_FOUND', 404)

            data = request.get_json()
            market_data = _get_market_dict(property_obj)

            # Custom financial analysis
            financial_metrics = FinancialMetrics(property_obj, market_data)
            analysis = financial_metrics.analyze_property(
                down_payment_percentage=data.get('down_payment_percentage', 0.20),
                interest_rate=data.get('interest_rate', 0.045),
                term_years=data.get('term_years', 30),
                holding_period=data.get('holding_period', 5),
                appreciation_rate=data.get('appreciation_rate', 0.03)
            )

            # Custom tax analysis
            tax_benefits = TaxBenefits(property_obj, market_data)
            tax_analysis = tax_benefits.analyze_tax_benefits(
                tax_bracket=data.get('tax_bracket', 0.22),
                down_payment_percentage=data.get('down_payment_percentage', 0.20),
                interest_rate=data.get('interest_rate', 0.045),
                term_years=data.get('term_years', 30)
            )

            # Custom financing analysis
            financing = FinancingOptions(property_obj, market_data)
            financing_analysis = financing.analyze_financing_options(
                credit_score=data.get('credit_score', 720),
                veteran=data.get('veteran', False),
                first_time_va=data.get('first_time_va', True)
            )

            result = {
                'property_id': str(property_obj._id),
                'parameters': data,
                'financial_analysis': analysis,
                'tax_benefits': tax_analysis,
                'financing_options': financing_analysis,
                'market_data': market_data
            }

            return result, 200

        except Exception as e:
            logger.exception("Failed custom analysis for property %s", property_id)
            return error_response(str(e), 'INTERNAL_ERROR', 500)


class MarketAnalysisResource(Resource):
    def get(self, market_id):
        """Get market analysis for a specific market area"""
        try:
            if not _is_valid_objectid(market_id):
                return error_response('Invalid market ID format', 'VALIDATION_ERROR', 400)
            market = Market.find_by_id(market_id)
            if not market:
                return error_response('Market not found', 'NOT_FOUND', 404)

            db = get_db()
            aggregator = MarketAggregator(db)

            if market.market_type == 'state':
                aggregate_data = aggregator.aggregate_by_state(market.state)
            elif market.market_type == 'city':
                aggregate_data = aggregator.aggregate_by_city(market.state, market.city)
            elif market.market_type == 'zip_code':
                aggregate_data = aggregator.aggregate_by_zip_code(market.zip_code)
            else:
                return error_response('Invalid market type', 'INVALID_MARKET_TYPE', 400)

            result = {
                'market_id': str(market._id),
                'market_name': market.name,
                'market_type': market.market_type,
                'aggregate_data': aggregate_data,
                'market_metrics': market.metrics
            }

            return result, 200

        except Exception as e:
            logger.exception("Failed to get market analysis for %s", market_id)
            return error_response(str(e), 'INTERNAL_ERROR', 500)

    def post(self, market_id):
        """Run custom market analysis with user-defined parameters"""
        try:
            if not _is_valid_objectid(market_id):
                return error_response('Invalid market ID format', 'VALIDATION_ERROR', 400)
            market = Market.find_by_id(market_id)
            if not market:
                return error_response('Market not found', 'NOT_FOUND', 404)

            data = request.get_json()
            db = get_db()
            aggregator = MarketAggregator(db)

            if market.market_type == 'state':
                aggregate_data = aggregator.aggregate_by_state(market.state)
            elif market.market_type == 'city':
                aggregate_data = aggregator.aggregate_by_city(market.state, market.city)
            elif market.market_type == 'zip_code':
                aggregate_data = aggregator.aggregate_by_zip_code(market.zip_code)
            else:
                return error_response('Invalid market type', 'INVALID_MARKET_TYPE', 400)

            result = {
                'market_id': str(market._id),
                'market_name': market.name,
                'market_type': market.market_type,
                'parameters': data,
                'aggregate_data': aggregate_data,
                'market_metrics': market.metrics
            }

            return result, 200

        except Exception as e:
            logger.exception("Failed custom market analysis for %s", market_id)
            return error_response(str(e), 'INTERNAL_ERROR', 500)

class OpportunityScoringResource(Resource):
    def get(self, property_id):
        """Get investment opportunity score for a property"""
        try:
            if not _is_valid_objectid(property_id):
                return error_response('Invalid property ID format', 'VALIDATION_ERROR', 400)
            property_obj = Property.find_by_id(property_id)
            if not property_obj:
                return error_response('Property not found', 'NOT_FOUND', 404)

            market_data = _get_market_dict(property_obj)
            scorer = OpportunityScoring(property_obj, market_data)
            result = scorer.calculate_score()
            result['property_id'] = str(property_obj._id)
            return result, 200

        except Exception as e:
            logger.exception("Failed to score opportunity for property %s", property_id)
            return error_response(str(e), 'INTERNAL_ERROR', 500)


class TopMarketsResource(Resource):
    def get(self):
        """Get top performing markets based on investment metrics"""
        try:
            limit = min(int(request.args.get('limit', 10)), 100)
            metric = request.args.get('metric', 'roi')

            db = get_db()
            aggregator = MarketAggregator(db)

            if metric == 'roi':
                top_markets = aggregator.top_markets_by_roi(limit=limit, sort_field='avg_roi')
            elif metric == 'cap_rate':
                top_markets = aggregator.top_markets_by_roi(limit=limit, sort_field='avg_cap_rate')
            else:
                return error_response('Invalid metric', 'INVALID_METRIC', 400)

            return top_markets, 200

        except Exception as e:
            logger.exception("Failed to get top markets")
            return error_response(str(e), 'INTERNAL_ERROR', 500)
