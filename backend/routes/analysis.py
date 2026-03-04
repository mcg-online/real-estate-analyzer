from flask import request
from flask_restful import Resource
from models.property import Property
from models.market import Market
from services.analysis.financial_metrics import FinancialMetrics
from services.analysis.tax_benefits import TaxBenefits
from services.analysis.financing_options import FinancingOptions
from services.analysis.opportunity_scoring import OpportunityScoring
from services.geographic.market_aggregator import MarketAggregator
from utils.database import get_db
from utils.errors import error_response
from utils.request_validators import require_json_body, require_entity
import logging

logger = logging.getLogger(__name__)


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
    @require_entity(Property, 'property_id', inject_as='property_obj')
    def get(self, property_id, property_obj):
        """Get comprehensive analysis for a single property"""
        try:
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

    @require_entity(Property, 'property_id', inject_as='property_obj')
    @require_json_body
    def post(self, property_id, property_obj, data):
        """Run custom analysis with user-defined parameters"""
        try:
            market_data = _get_market_dict(property_obj)

            # Validate and bound user-supplied parameters
            try:
                down_pct = max(0.01, min(0.99, float(data.get('down_payment_percentage', 0.20))))
                interest = max(0.001, min(0.30, float(data.get('interest_rate', 0.045))))
                term = max(1, min(40, int(data.get('term_years', 30))))
                holding = max(1, min(30, int(data.get('holding_period', 5))))
                appreciation = max(-0.10, min(0.20, float(data.get('appreciation_rate', 0.03))))
                tax_bracket = max(0.0, min(0.50, float(data.get('tax_bracket', 0.22))))
            except (ValueError, TypeError):
                return error_response('Invalid numeric parameter', 'VALIDATION_ERROR', 400)

            # Custom financial analysis
            financial_metrics = FinancialMetrics(property_obj, market_data)
            analysis = financial_metrics.analyze_property(
                down_payment_percentage=down_pct,
                interest_rate=interest,
                term_years=term,
                holding_period=holding,
                appreciation_rate=appreciation
            )

            # Custom tax analysis
            tax_benefits = TaxBenefits(property_obj, market_data)
            tax_analysis = tax_benefits.analyze_tax_benefits(
                tax_bracket=tax_bracket,
                down_payment_percentage=down_pct,
                interest_rate=interest,
                term_years=term
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
    @require_entity(Market, 'market_id', inject_as='market_obj')
    def get(self, market_id, market_obj):
        """Get market analysis for a specific market area"""
        try:
            db = get_db()
            aggregator = MarketAggregator(db)

            if market_obj.market_type == 'state':
                aggregate_data = aggregator.aggregate_by_state(market_obj.state)
            elif market_obj.market_type == 'city':
                aggregate_data = aggregator.aggregate_by_city(market_obj.state, market_obj.city)
            elif market_obj.market_type == 'zip_code':
                aggregate_data = aggregator.aggregate_by_zip_code(market_obj.zip_code)
            else:
                return error_response('Invalid market type', 'INVALID_MARKET_TYPE', 400)

            result = {
                'market_id': str(market_obj._id),
                'market_name': market_obj.name,
                'market_type': market_obj.market_type,
                'aggregate_data': aggregate_data,
                'market_metrics': market_obj.metrics
            }

            return result, 200

        except Exception as e:
            logger.exception("Failed to get market analysis for %s", market_id)
            return error_response(str(e), 'INTERNAL_ERROR', 500)

    @require_entity(Market, 'market_id', inject_as='market_obj')
    def post(self, market_id, market_obj):
        """Run custom market analysis with user-defined parameters"""
        try:
            db = get_db()
            aggregator = MarketAggregator(db)

            if market_obj.market_type == 'state':
                aggregate_data = aggregator.aggregate_by_state(market_obj.state)
            elif market_obj.market_type == 'city':
                aggregate_data = aggregator.aggregate_by_city(market_obj.state, market_obj.city)
            elif market_obj.market_type == 'zip_code':
                aggregate_data = aggregator.aggregate_by_zip_code(market_obj.zip_code)
            else:
                return error_response('Invalid market type', 'INVALID_MARKET_TYPE', 400)

            result = {
                'market_id': str(market_obj._id),
                'market_name': market_obj.name,
                'market_type': market_obj.market_type,
                'aggregate_data': aggregate_data,
                'market_metrics': market_obj.metrics
            }

            return result, 200

        except Exception as e:
            logger.exception("Failed custom market analysis for %s", market_id)
            return error_response(str(e), 'INTERNAL_ERROR', 500)


class OpportunityScoringResource(Resource):
    @require_entity(Property, 'property_id', inject_as='property_obj')
    def get(self, property_id, property_obj):
        """Get investment opportunity score for a property"""
        try:
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
            try:
                limit = max(1, min(int(request.args.get('limit', 10)), 100))
            except (ValueError, TypeError):
                return error_response('Invalid limit parameter', 'VALIDATION_ERROR', 400)
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
