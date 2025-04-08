class FinancingOptions:
    def __init__(self, property_data, market_data):
        self.property = property_data
        self.market = market_data
        
    def get_conventional_loan(self, down_payment_percentage=0.20, interest_rate=0.045, term_years=30, credit_score=720):
        """Calculate conventional loan scenario"""
        # Adjust interest rate based on credit score and down payment
        adjusted_rate = interest_rate
        if credit_score < 700:
            adjusted_rate += 0.005  # Higher rate for lower credit
        if down_payment_percentage < 0.20:
            adjusted_rate += 0.0025  # Higher rate for lower down payment
            
        loan_amount = self.property.price * (1 - down_payment_percentage)
        monthly_rate = adjusted_rate / 12
        num_payments = term_years * 12
        
        # Calculate monthly payment
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        
        # Calculate PMI if down payment less than 20%
        monthly_pmi = 0
        if down_payment_percentage < 0.20:
            pmi_rate = 0.005  # 0.5% annual PMI rate
            monthly_pmi = (loan_amount * pmi_rate) / 12
            
        # Calculate total monthly payment
        total_monthly_payment = monthly_payment + monthly_pmi
        
        # Calculate total cost over loan term
        total_cost = total_monthly_payment * num_payments
        total_interest = total_cost - loan_amount
        
        return {
            'type': 'Conventional',
            'loan_amount': round(loan_amount, 2),
            'down_payment': round(self.property.price * down_payment_percentage, 2),
            'down_payment_percentage': down_payment_percentage * 100,
            'interest_rate': adjusted_rate * 100,
            'term_years': term_years,
            'monthly_payment': round(monthly_payment, 2),
            'monthly_pmi': round(monthly_pmi, 2),
            'total_monthly_payment': round(total_monthly_payment, 2),
            'total_cost': round(total_cost, 2),
            'total_interest': round(total_interest, 2)
        }
        
    def get_fha_loan(self, down_payment_percentage=0.035, interest_rate=0.043, term_years=30, credit_score=660):
        """Calculate FHA loan scenario"""
        # FHA loans have specific requirements
        # Minimum down payment 3.5%, includes upfront and monthly MIP
        
        if down_payment_percentage < 0.035:
            down_payment_percentage = 0.035  # FHA minimum
            
        loan_amount = self.property.price * (1 - down_payment_percentage)
        monthly_rate = interest_rate / 12
        num_payments = term_years * 12
        
        # Calculate monthly payment
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        
        # FHA requires both upfront and monthly mortgage insurance
        upfront_mip = loan_amount * 0.0175  # 1.75% upfront MIP
        monthly_mip = (loan_amount * 0.0055) / 12  # 0.55% annual MIP rate
        
        # Calculate total monthly payment
        total_monthly_payment = monthly_payment + monthly_mip
        
        # Calculate total cost over loan term
        total_cost = (total_monthly_payment * num_payments) + upfront_mip
        total_interest = total_cost - loan_amount
        
        return {
            'type': 'FHA',
            'loan_amount': round(loan_amount, 2),
            'down_payment': round(self.property.price * down_payment_percentage, 2),
            'down_payment_percentage': down_payment_percentage * 100,
            'interest_rate': interest_rate * 100,
            'term_years': term_years,
            'monthly_payment': round(monthly_payment, 2),
            'upfront_mip': round(upfront_mip, 2),
            'monthly_mip': round(monthly_mip, 2),
            'total_monthly_payment': round(total_monthly_payment, 2),
            'total_cost': round(total_cost, 2),
            'total_interest': round(total_interest, 2)
        }
        
    def get_va_loan(self, funding_fee_percentage=0.0215, interest_rate=0.04, term_years=30, first_time=True):
        """Calculate VA loan scenario for eligible veterans"""
        # VA loans offer 0% down payment option with a funding fee
        down_payment_percentage = 0.0
        
        # Adjust funding fee based on first time use and down payment
        if not first_time:
            funding_fee_percentage = 0.0315  # 3.15% for subsequent use
            
        loan_amount = self.property.price * (1 - down_payment_percentage)
        funding_fee = loan_amount * funding_fee_percentage
        financed_amount = loan_amount + funding_fee
        
        monthly_rate = interest_rate / 12
        num_payments = term_years * 12
        
        # Calculate monthly payment
        monthly_payment = financed_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        
        # Calculate total cost over loan term
        total_cost = monthly_payment * num_payments
        total_interest = total_cost - loan_amount
        
        return {
            'type': 'VA',
            'loan_amount': round(loan_amount, 2),
            'down_payment': round(self.property.price * down_payment_percentage, 2),
            'down_payment_percentage': down_payment_percentage * 100,
            'interest_rate': interest_rate * 100,
            'term_years': term_years,
            'funding_fee': round(funding_fee, 2),
            'funding_fee_percentage': funding_fee_percentage * 100,
            'financed_amount': round(financed_amount, 2),
            'monthly_payment': round(monthly_payment, 2),
            'total_cost': round(total_cost, 2),
            'total_interest': round(total_interest, 2)
        }
        
    def get_local_financing_programs(self):
        """Get location-specific financing programs"""
        # In a real implementation, this would query a database of local financing programs
        # based on the property's location (city, county, state)
        
        # Example: First-time homebuyer programs, renovation loans, etc.
        return self.market.get('financing_programs', [])
        
    def analyze_financing_options(self, credit_score=720, veteran=False, first_time_va=True):
        """Analyze all financing options for this property"""
        financing_options = []
        
        # Conventional options (20% down and 10% down)
        financing_options.append(self.get_conventional_loan(
            down_payment_percentage=0.20,
            credit_score=credit_score
        ))
        
        financing_options.append(self.get_conventional_loan(
            down_payment_percentage=0.10,
            credit_score=credit_score
        ))
        
        # FHA option
        financing_options.append(self.get_fha_loan(
            credit_score=credit_score
        ))
        
        # VA option if eligible
        if veteran:
            financing_options.append(self.get_va_loan(
                first_time=first_time_va
            ))
            
        # Get local programs
        local_programs = self.get_local_financing_programs()
        
        return {
            'options': financing_options,
            'local_programs': local_programs,
            'recommended': self._recommend_financing(financing_options)
        }
        
    def _recommend_financing(self, options):
        """Recommend the best financing option based on cost and flexibility"""
        if not options:
            return None
            
        # Sort by total monthly payment (lowest first)
        sorted_by_payment = sorted(options, key=lambda x: x['total_monthly_payment'])
        
        # The cheapest option is usually best, but could add more logic here
        return sorted_by_payment[0]['type']