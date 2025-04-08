# Add to backend/services/analysis/risk_assessment.py

class RiskAssessment:
    def __init__(self, property_data, market_data):
        self.property = property_data
        self.market = market_data
    
    def calculate_market_volatility(self):
        """Calculate historical price volatility in the market"""
        # Implementation needed
        
    def calculate_vacancy_risk(self):
        """Calculate risk based on local vacancy trends"""
        vacancy_rate = self.market.get('vacancy_rate', 0.08)
        avg_days_on_market = self.market.get('days_on_market', 30)
        
        # Higher vacancy rate and days on market = higher risk
        vacancy_risk = (vacancy_rate * 10) + (avg_days_on_market / 30)
        return min(10, vacancy_risk)
    
    # Add more risk factors...