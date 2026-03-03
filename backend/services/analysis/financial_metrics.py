class FinancialMetrics:
    def __init__(self, property_data, market_data):
        self.property = property_data
        self.market = market_data

    def estimate_rental_income(self):
        """Estimate monthly rental income based on property characteristics and market data"""
        price_to_rent_ratio = self.market.get('price_to_rent_ratio', 15)
        annual_rent = self.property.price / price_to_rent_ratio
        monthly_rent = annual_rent / 12
        return round(monthly_rent, 2)

    def estimate_expenses(self, monthly_rent):
        """Estimate monthly expenses"""
        property_tax_rate = self.market.get('property_tax_rate', 0.01)
        annual_property_tax = self.property.price * property_tax_rate
        monthly_property_tax = annual_property_tax / 12

        insurance_rate = 0.0035
        annual_insurance = self.property.price * insurance_rate
        monthly_insurance = annual_insurance / 12

        maintenance_rate = 0.01
        annual_maintenance = self.property.price * maintenance_rate
        monthly_maintenance = annual_maintenance / 12

        vacancy_rate = self.market.get('vacancy_rate', 0.08)
        monthly_vacancy_cost = monthly_rent * vacancy_rate

        management_rate = 0.1
        monthly_management = monthly_rent * management_rate

        monthly_hoa = self.market.get('avg_hoa_fee', 0)

        total_monthly_expenses = (
            monthly_property_tax +
            monthly_insurance +
            monthly_maintenance +
            monthly_vacancy_cost +
            monthly_management +
            monthly_hoa
        )

        return {
            'total': round(total_monthly_expenses, 2),
            'property_tax': round(monthly_property_tax, 2),
            'insurance': round(monthly_insurance, 2),
            'maintenance': round(monthly_maintenance, 2),
            'vacancy': round(monthly_vacancy_cost, 2),
            'management': round(monthly_management, 2),
            'hoa': round(monthly_hoa, 2)
        }

    def calculate_mortgage_payment(self, down_payment_percentage=0.20, interest_rate=0.045, term_years=30):
        """Calculate monthly mortgage payment"""
        loan_amount = self.property.price * (1 - down_payment_percentage)
        monthly_rate = interest_rate / 12
        num_payments = term_years * 12

        if monthly_rate == 0:
            return loan_amount / num_payments

        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        return round(monthly_payment, 2)

    def calculate_cash_flow(self, monthly_rent, monthly_expenses, mortgage_payment):
        """Calculate monthly cash flow"""
        cash_flow = monthly_rent - monthly_expenses - mortgage_payment
        return round(cash_flow, 2)

    def calculate_cap_rate(self, annual_rental_income, annual_expenses):
        """Calculate capitalization rate"""
        noi = annual_rental_income - annual_expenses
        cap_rate = (noi / self.property.price) * 100
        return round(cap_rate, 2)

    def calculate_cash_on_cash_return(self, annual_cash_flow, down_payment, closing_costs):
        """Calculate cash-on-cash return"""
        total_investment = down_payment + closing_costs
        coc_return = (annual_cash_flow / total_investment) * 100
        return round(coc_return, 2)

    def calculate_roi(self, annual_cash_flow, down_payment, closing_costs, holding_period=5, appreciation_rate=0.03):
        """Calculate return on investment over a holding period"""
        initial_investment = down_payment + closing_costs
        future_property_value = self.property.price * ((1 + appreciation_rate) ** holding_period)
        total_cash_flow = annual_cash_flow * holding_period
        appreciation_profit = future_property_value - self.property.price
        total_profit = total_cash_flow + appreciation_profit
        roi = (total_profit / initial_investment) * 100
        base = 1 + roi / 100
        if base > 0:
            annualized_roi = (base ** (1 / holding_period) - 1) * 100
        else:
            annualized_roi = -100.0

        return {
            'total_roi': round(roi, 2),
            'annualized_roi': round(annualized_roi, 2),
            'future_value': round(future_property_value, 2),
            'total_cash_flow': round(total_cash_flow, 2),
            'appreciation_profit': round(appreciation_profit, 2)
        }

    def calculate_break_even_point(self, monthly_rent, monthly_expenses, mortgage_payment):
        """Calculate the break-even point in years"""
        monthly_cash_flow = monthly_rent - monthly_expenses - mortgage_payment

        if monthly_cash_flow >= 0:
            return 0

        down_payment = self.property.price * 0.20
        closing_costs = self.property.price * 0.03
        total_investment = down_payment + closing_costs

        annual_appreciation_rate = self.market.get('appreciation_rate', 0.03)
        monthly_appreciation = (self.property.price * annual_appreciation_rate) / 12

        total_monthly_benefit = monthly_cash_flow + monthly_appreciation

        if total_monthly_benefit <= 0:
            return 99

        months_to_break_even = total_investment / total_monthly_benefit
        years_to_break_even = months_to_break_even / 12

        return round(years_to_break_even, 2)

    def analyze_property(self, down_payment_percentage=0.20, interest_rate=0.045, term_years=30,
                         holding_period=5, appreciation_rate=0.03):
        """Perform complete financial analysis of a property"""
        monthly_rent = self.estimate_rental_income()
        annual_rental_income = monthly_rent * 12

        monthly_expenses = self.estimate_expenses(monthly_rent)
        annual_expenses = monthly_expenses['total'] * 12

        mortgage_payment = self.calculate_mortgage_payment(
            down_payment_percentage=down_payment_percentage,
            interest_rate=interest_rate,
            term_years=term_years
        )

        down_payment = self.property.price * down_payment_percentage
        closing_costs = self.property.price * 0.03
        monthly_cash_flow = self.calculate_cash_flow(
            monthly_rent=monthly_rent,
            monthly_expenses=monthly_expenses['total'],
            mortgage_payment=mortgage_payment
        )
        annual_cash_flow = monthly_cash_flow * 12

        cap_rate = self.calculate_cap_rate(
            annual_rental_income=annual_rental_income,
            annual_expenses=annual_expenses
        )

        cash_on_cash = self.calculate_cash_on_cash_return(
            annual_cash_flow=annual_cash_flow,
            down_payment=down_payment,
            closing_costs=closing_costs
        )

        roi = self.calculate_roi(
            annual_cash_flow=annual_cash_flow,
            down_payment=down_payment,
            closing_costs=closing_costs,
            holding_period=holding_period,
            appreciation_rate=appreciation_rate
        )

        break_even = self.calculate_break_even_point(
            monthly_rent=monthly_rent,
            monthly_expenses=monthly_expenses['total'],
            mortgage_payment=mortgage_payment
        )

        return {
            'monthly_rent': monthly_rent,
            'monthly_expenses': monthly_expenses,
            'mortgage_payment': mortgage_payment,
            'monthly_cash_flow': monthly_cash_flow,
            'annual_cash_flow': annual_cash_flow,
            'cap_rate': cap_rate,
            'cash_on_cash_return': cash_on_cash,
            'roi': roi,
            'break_even_point': break_even,
            'price_to_rent_ratio': round(self.property.price / annual_rental_income, 2),
            'gross_yield': round((annual_rental_income / self.property.price) * 100, 2),
            'total_investment': round(down_payment + closing_costs, 2)
        }
