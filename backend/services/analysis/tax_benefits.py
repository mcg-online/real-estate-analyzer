class TaxBenefits:
    def __init__(self, property_data, market_data):
        self.property = property_data
        self.market = market_data

    def calculate_depreciation(self, property_value, land_value=None, depreciation_period=27.5):
        """
        Calculate annual depreciation deduction
        
        The IRS allows depreciation of residential rental property over 27.5 years
        Only the building value (not land) can be depreciated
        """
        if land_value is None:
            # Estimate land value as 20% of property value if not provided
            land_value = property_value * 0.2
            
        building_value = property_value - land_value
        annual_depreciation = building_value / depreciation_period
        
        return {
            'building_value': round(building_value, 2),
            'land_value': round(land_value, 2),
            'annual_depreciation': round(annual_depreciation, 2),
            'monthly_depreciation': round(annual_depreciation / 12, 2)
        }
        
    def calculate_mortgage_interest_deduction(self, loan_amount, interest_rate, term_years=30):
        """Calculate first-year mortgage interest deduction"""
        # Calculate monthly payment
        monthly_rate = interest_rate / 12
        num_payments = term_years * 12
        
        if monthly_rate == 0:
            monthly_payment = loan_amount / num_payments
            return 0  # No interest if rate is 0
            
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        
        # Calculate first year interest (sum of interest payments for first 12 months)
        first_year_interest = 0
        remaining_balance = loan_amount
        
        for _ in range(12):
            interest_payment = remaining_balance * monthly_rate
            principal_payment = monthly_payment - interest_payment
            remaining_balance -= principal_payment
            first_year_interest += interest_payment
            
        return round(first_year_interest, 2)
        
    def calculate_property_tax_deduction(self):
        """Calculate property tax deduction"""
        property_tax_rate = self.market.get('property_tax_rate', 0.01)
        annual_property_tax = self.property.price * property_tax_rate
        
        return round(annual_property_tax, 2)
        
    def calculate_local_tax_incentives(self):
        """Calculate location-specific tax incentives"""
        # In a real implementation, this would query a database of local tax incentives
        # based on the property's location (city, county, state)
        
        # Example: Some locations offer tax abatements for improvements
        tax_incentives = self.market.get('tax_benefits', {})
        
        if not tax_incentives:
            # Default to empty dictionary if no special incentives
            tax_incentives = {
                'has_opportunity_zone': False,
                'has_historic_tax_credits': False,
                'has_homestead_exemption': False,
                'has_renovation_incentives': False,
                'special_programs': []
            }
            
        return tax_incentives
        
    def analyze_tax_benefits(self, tax_bracket=0.22, down_payment_percentage=0.20, interest_rate=0.045, term_years=30):
        """Perform comprehensive tax benefit analysis"""
        loan_amount = self.property.price * (1 - down_payment_percentage)
        
        # Calculate depreciation
        depreciation = self.calculate_depreciation(self.property.price)
        
        # Calculate mortgage interest deduction
        mortgage_interest = self.calculate_mortgage_interest_deduction(
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            term_years=term_years
        )
        
        # Calculate property tax deduction
        property_tax = self.calculate_property_tax_deduction()
        
        # Calculate local tax incentives
        local_incentives = self.calculate_local_tax_incentives()
        
        # Calculate tax savings
        deductions = depreciation['annual_depreciation'] + mortgage_interest + property_tax
        tax_savings = deductions * tax_bracket
        
        return {
            'depreciation': depreciation,
            'mortgage_interest_deduction': mortgage_interest,
            'property_tax_deduction': property_tax,
            'local_tax_incentives': local_incentives,
            'total_deductions': round(deductions, 2),
            'estimated_tax_savings': round(tax_savings, 2),
            'monthly_tax_savings': round(tax_savings / 12, 2)
        }