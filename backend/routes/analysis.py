from flask import request, jsonify
from flask_restful import Resource
from models.property import Property
from models.market import Market
from services.analysis.financial_metrics import FinancialMetrics
from services.analysis.tax_benefits import TaxBenefits
from services.analysis.financing_options import FinancingOptions
from services.analysis.opportunity_scoring import OpportunityScoring
from services.geographic.market_aggregator import MarketAggregator
from utils.database import get_db
from bson import ObjectId
import traceback

class PropertyAnalysisResource(Resource):
    def get(self, property_id):
        """Get comprehensive analysis for a single property"""
        try:
            property = Property.find_by_id(property_id)
            if not property:
                return {'error': 'Property not found'}, 404
                
            # Get market data for the property's location
            market = None
            
            if property.zip_code:
                market = Market.find_by_location('zip_code', property.zip_code)
            
            if not market and property.city and property.state:
                market = Market.find_by_location('city', property.city)
                
            if not market and property.state:
                market = Market.find_by_location('state', property.state)
                
            if not market:
                # Create default market data
                market = {
                    'property_tax_rate': 0.01,
                    'price_to_rent_ratio': 15,
                    'vacancy_rate': 0.08,
                    'appreciation_rate': 0.03
                }

            # Financial analysis
            financial_metrics = FinancialMetrics(property, market)
            analysis = financial_metrics.analyze_property()
            
            # Tax benefits analysis
            tax_benefits = TaxBenefits(property, market)
            tax_analysis = tax_benefits.analyze_tax_benefits()
            
            # Financing options
            financing = FinancingOptions(property, market)
            financing_analysis = financing.analyze_financing_options()
            
            # Return comprehensive analysis
            result = {
                'property_id': str(property._id),
                'financial_analysis': analysis,
                'tax_benefits': tax_analysis,
                'financing_options': financing_analysis,
                'market_data': market
            }
            
            return result, 200
            
        except Exception as e:
            traceback.print_exc()
            return {'error': str(e)}, 500
            
    def post(self, property_id):
        """Run custom analysis with user-defined parameters"""
        try:
            property = Property.find_by_id(property_id)
            if not property:
                return {'error': 'Property not found'}, 404
                
            # Get analysis parameters from request
            data = request.get_json()
            
            # Get market data
            market = None
            
            if property.zip_code:
                market = Market.find_by_location('zip_code', property.zip_code)
            
            if not market and property.city and property.state:
                market = Market.find_by_location('city', property.city)
                
            if not market and property.state:
                market = Market.find_by_location('state', property.state)
                
            if not market:
                # Create default market data
                market = {
                    'property_tax_rate': 0.01,
                    'price_to_rent_ratio': 15,
                    'vacancy_rate': 0.08,
                    'appreciation_rate': 0.03
                }
                
            # Custom financial analysis
            financial_metrics = FinancialMetrics(property, market)
            analysis = financial_metrics.analyze_property(
                down_payment_percentage=data.get('down_payment_percentage', 0.20),
                interest_rate=data.get('interest_rate', 0.045),
                term_years=data.get('term_years', 30),
                holding_period=data.get('holding_period', 5),
                appreciation_rate=data.get('appreciation_rate', 0.03)
            )
            
            # Custom tax analysis
            tax_benefits = TaxBenefits(property, market)
            tax_analysis = tax_benefits.analyze_tax_benefits(
                tax_bracket=data.get('tax_bracket', 0.22),
                down_payment_percentage=data.get('down_payment_percentage', 0.20),
                interest_rate=data.get('interest_rate', 0.045),
                term_years=data.get('term_years', 30)
            )
            
            # Custom financing analysis
            financing = FinancingOptions(property, market)
            financing_analysis = financing.analyze_financing_options(
                credit_score=data.get('credit_score', 720),
                veteran=data.get('veteran', False),
                first_time_va=data.get('first_time_va', True)
            )
            
            # Return custom analysis
            result = {
                'property_id': str(property._id),
                'parameters': data,
                'financial_analysis': analysis,
                'tax_benefits': tax_analysis,
                'financing_options': financing_analysis,
                'market_data': market
            }
            
            return result, 200
            
        except Exception as e:
            traceback.print_exc()
            return {'error': str(e)}, 500


class MarketAnalysisResource(Resource):
    def get(self, market_id):
        """Get market analysis for a specific market area"""
        try:
            market = Market.find_by_id(market_id)
            if not market:
                return {'error': 'Market not found'}, 404
                
            # Aggregate property data for this market
            db = get_db()
            aggregator = MarketAggregator(db)
            
            if market.market_type == 'state':
                aggregate_data = aggregator.aggregate_by_state(market.state)
            elif market.market_type == 'city':
                aggregate_data = aggregator.aggregate_by_city(market.state, market.city)
            elif market.market_type == 'zip_code':
                aggregate_data = aggregator.aggregate_by_zip_code(market.zip_code)
            else:
                return {'error': 'Invalid market type'}, 400
                
            # Return market analysis
            result = {
                'market_id': str(market._id),
                'market_name': market.name,
                'market_type': market.market_type,
                'aggregate_data': aggregate_data,
                'market_metrics': market.metrics
            }
            
            return result, 200
            
        except Exception as e:
            traceback.print_exc()
            return {'error': str(e)}, 500
            
    def post(self, market_id):
        """Run custom market analysis with user-defined parameters"""
        try:
            market = Market.find_by_id(market_id)
            if not market:
                return {'error': 'Market not found'}, 404
                
            # Get analysis parameters from request
            data = request.get_json()
            
            # Aggregate property data based on custom filters
            db = get_db()
            aggregator = MarketAggregator(db)
            
            filters = data.get('filters', {})
            metrics = data.get('metrics', [])
            
            # Run appropriate aggregation
            if market.market_type == 'state':
                aggregate_data = aggregator.aggregate_by_state(market.state)
            elif market.market_type == 'city':
                aggregate_data = aggregator.aggregate_by_city(market.state, market.city)
            elif market.market_type == 'zip_code':
                aggregate_data = aggregator.aggregate_by_zip_code(market.zip_code)
            else:
                return {'error': 'Invalid market type'}, 400
                
            # Return custom market analysis
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
            traceback.print_exc()
            return {'error': str(e)}, 500

class TopMarketsResource(Resource):
    def get(self):
        """Get top performing markets based on investment metrics"""
        try:
            # Get query parameters
            limit = int(request.args.get('limit', 10))
            metric = request.args.get('metric', 'roi')  # default to ROI
            
            # Get database connection
            db = get_db()
            aggregator = MarketAggregator(db)
            
            # Get top markets
            if metric == 'roi':
                top_markets = aggregator.top_markets_by_roi(limit=limit)
            elif metric == 'cap_rate':
                # Would implement other metrics like this
                top_markets = aggregator.top_markets_by_roi(limit=limit)
            else:
                return {'error': 'Invalid metric'}, 400
                
            return top_markets, 200
            
        except Exception as e:
            traceback.print_exc()
            return {'error': str(e)}, 500