# backend/tests/test_financial_metrics.py

import unittest
from services.analysis.financial_metrics import FinancialMetrics

class TestFinancialMetrics(unittest.TestCase):
    def setUp(self):
        self.property_data = {
            'price': 200000,
            'bedrooms': 3,
            'bathrooms': 2,
            'sqft': 1500
        }
        self.market_data = {
            'property_tax_rate': 0.01,
            'price_to_rent_ratio': 15,
            'vacancy_rate': 0.08
        }
    
    def test_estimate_rental_income(self):
        metrics = FinancialMetrics(self.property_data, self.market_data)
        monthly_rent = metrics.estimate_rental_income()
        self.assertGreater(monthly_rent, 0)
        self.assertEqual(monthly_rent, round(200000 / 15 / 12, 2))