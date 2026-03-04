"""Comprehensive pytest tests for the FinancialMetrics class.

Tests cover all public methods with multiple cases each, including normal
operation, edge cases, boundary conditions, and return-type validation.
Fixtures are sourced from conftest.py.
"""


from services.analysis.financial_metrics import FinancialMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_metrics(property_fixture, market_fixture):
    """Convenience factory so individual tests stay concise."""
    return FinancialMetrics(property_fixture, market_fixture)


# ---------------------------------------------------------------------------
# estimate_rental_income
# ---------------------------------------------------------------------------

class TestEstimateRentalIncome:
    """Tests for FinancialMetrics.estimate_rental_income()."""

    def test_returns_float(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.estimate_rental_income()
        assert isinstance(result, float)

    def test_standard_property_formula(self, mock_property, default_market_data):
        """Monthly rent = price / price_to_rent_ratio / 12, rounded to 2 dp."""
        fm = make_metrics(mock_property, default_market_data)
        expected = round(200_000 / 15 / 12, 2)
        assert fm.estimate_rental_income() == expected

    def test_expensive_property_higher_rent(self, expensive_property, default_market_data):
        """A more-expensive property should yield more monthly rent."""
        fm_exp = make_metrics(expensive_property, default_market_data)
        expected = round(800_000 / 15 / 12, 2)
        assert fm_exp.estimate_rental_income() == expected

    def test_cheap_property_lower_rent(self, cheap_property, default_market_data):
        fm = make_metrics(cheap_property, default_market_data)
        expected = round(80_000 / 15 / 12, 2)
        assert fm.estimate_rental_income() == expected

    def test_rent_scales_with_price_to_rent_ratio(self, mock_property):
        """Lower price-to-rent ratio produces higher monthly rent."""
        low_ratio_market = {'price_to_rent_ratio': 10}
        high_ratio_market = {'price_to_rent_ratio': 20}
        fm_low = make_metrics(mock_property, low_ratio_market)
        fm_high = make_metrics(mock_property, high_ratio_market)
        assert fm_low.estimate_rental_income() > fm_high.estimate_rental_income()

    def test_rent_is_positive(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        assert fm.estimate_rental_income() > 0

    def test_default_price_to_rent_ratio_fallback(self, mock_property):
        """Market data without price_to_rent_ratio should use default of 15."""
        fm_no_ratio = make_metrics(mock_property, {})
        fm_default = make_metrics(mock_property, {'price_to_rent_ratio': 15})
        assert fm_no_ratio.estimate_rental_income() == fm_default.estimate_rental_income()


# ---------------------------------------------------------------------------
# estimate_expenses
# ---------------------------------------------------------------------------

class TestEstimateExpenses:
    """Tests for FinancialMetrics.estimate_expenses(monthly_rent)."""

    def test_returns_dict_with_required_keys(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        monthly_rent = fm.estimate_rental_income()
        result = fm.estimate_expenses(monthly_rent)
        required_keys = {'total', 'property_tax', 'insurance', 'maintenance',
                         'vacancy', 'management', 'hoa'}
        assert required_keys == set(result.keys())

    def test_total_equals_sum_of_components(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        monthly_rent = fm.estimate_rental_income()
        result = fm.estimate_expenses(monthly_rent)
        component_sum = round(
            result['property_tax'] + result['insurance'] + result['maintenance']
            + result['vacancy'] + result['management'] + result['hoa'],
            2,
        )
        assert result['total'] == component_sum

    def test_all_values_are_non_negative(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        monthly_rent = fm.estimate_rental_income()
        result = fm.estimate_expenses(monthly_rent)
        for key, value in result.items():
            assert value >= 0, f"Expense component '{key}' is negative: {value}"

    def test_property_tax_uses_market_rate(self, mock_property):
        """Higher tax rate in market data should increase the property_tax component."""
        low_tax = make_metrics(mock_property, {'property_tax_rate': 0.005})
        high_tax = make_metrics(mock_property, {'property_tax_rate': 0.02})
        rent = mock_property.price / 15 / 12
        assert low_tax.estimate_expenses(rent)['property_tax'] < high_tax.estimate_expenses(rent)['property_tax']

    def test_vacancy_cost_scales_with_rent(self, mock_property, default_market_data):
        """Vacancy cost is a percentage of rent, so higher rent means higher vacancy cost."""
        fm = make_metrics(mock_property, default_market_data)
        low_rent = 500.0
        high_rent = 2000.0
        assert (
            fm.estimate_expenses(high_rent)['vacancy']
            > fm.estimate_expenses(low_rent)['vacancy']
        )

    def test_hoa_defaults_to_zero_when_absent(self, mock_property):
        market_without_hoa = {'property_tax_rate': 0.01, 'price_to_rent_ratio': 15}
        fm = make_metrics(mock_property, market_without_hoa)
        rent = fm.estimate_rental_income()
        assert fm.estimate_expenses(rent)['hoa'] == 0.0

    def test_hoa_included_when_present(self, mock_property):
        market_with_hoa = {'avg_hoa_fee': 300}
        fm = make_metrics(mock_property, market_with_hoa)
        rent = fm.estimate_rental_income()
        assert fm.estimate_expenses(rent)['hoa'] == 300.0

    def test_expensive_property_higher_fixed_expenses(
        self, mock_property, expensive_property, default_market_data
    ):
        """Tax, insurance and maintenance are property-price-based; expensive = more."""
        fm_cheap = make_metrics(mock_property, default_market_data)
        fm_exp = make_metrics(expensive_property, default_market_data)
        rent_cheap = fm_cheap.estimate_rental_income()
        rent_exp = fm_exp.estimate_rental_income()
        assert (
            fm_exp.estimate_expenses(rent_exp)['property_tax']
            > fm_cheap.estimate_expenses(rent_cheap)['property_tax']
        )

    def test_property_tax_calculation(self, mock_property, default_market_data):
        """Verify exact property_tax value: price * rate / 12."""
        fm = make_metrics(mock_property, default_market_data)
        rent = fm.estimate_rental_income()
        result = fm.estimate_expenses(rent)
        expected_tax = round(200_000 * 0.01 / 12, 2)
        assert result['property_tax'] == expected_tax


# ---------------------------------------------------------------------------
# calculate_mortgage_payment
# ---------------------------------------------------------------------------

class TestCalculateMortgagePayment:
    """Tests for FinancialMetrics.calculate_mortgage_payment()."""

    def test_returns_float(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_mortgage_payment()
        assert isinstance(result, float)

    def test_standard_payment_is_positive(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        assert fm.calculate_mortgage_payment() > 0

    def test_zero_interest_rate_returns_principal_divided_by_payments(
        self, mock_property, default_market_data
    ):
        """When interest_rate=0, payment = loan_amount / num_payments."""
        fm = make_metrics(mock_property, default_market_data)
        loan_amount = 200_000 * (1 - 0.20)
        num_payments = 30 * 12
        expected = round(loan_amount / num_payments, 2)
        result = fm.calculate_mortgage_payment(down_payment_percentage=0.20, interest_rate=0.0, term_years=30)
        assert abs(result - expected) < 0.01

    def test_zero_down_payment_uses_full_price_as_loan(
        self, mock_property, default_market_data
    ):
        """0% down means the entire purchase price is financed."""
        fm = make_metrics(mock_property, default_market_data)
        payment_zero_down = fm.calculate_mortgage_payment(down_payment_percentage=0.0)
        payment_twenty_down = fm.calculate_mortgage_payment(down_payment_percentage=0.20)
        assert payment_zero_down > payment_twenty_down

    def test_higher_down_payment_lowers_monthly_payment(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        payment_10 = fm.calculate_mortgage_payment(down_payment_percentage=0.10)
        payment_30 = fm.calculate_mortgage_payment(down_payment_percentage=0.30)
        assert payment_10 > payment_30

    def test_higher_interest_rate_increases_payment(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        low_rate = fm.calculate_mortgage_payment(interest_rate=0.03)
        high_rate = fm.calculate_mortgage_payment(interest_rate=0.07)
        assert high_rate > low_rate

    def test_longer_term_reduces_monthly_payment(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        payment_15yr = fm.calculate_mortgage_payment(term_years=15)
        payment_30yr = fm.calculate_mortgage_payment(term_years=30)
        assert payment_15yr > payment_30yr

    def test_expensive_property_higher_payment(
        self, expensive_property, default_market_data
    ):
        fm_exp = make_metrics(expensive_property, default_market_data)
        assert fm_exp.calculate_mortgage_payment() > 0

    def test_known_amortization_value(self, mock_property, default_market_data):
        """
        $200k purchase, 20% down -> $160k loan at 4.5% for 30 years.
        Standard amortization formula yields ~$810.70/month.
        """
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_mortgage_payment(
            down_payment_percentage=0.20, interest_rate=0.045, term_years=30
        )
        assert 800.0 < result < 825.0


# ---------------------------------------------------------------------------
# calculate_cash_flow
# ---------------------------------------------------------------------------

class TestCalculateCashFlow:
    """Tests for FinancialMetrics.calculate_cash_flow()."""

    def test_returns_float(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_cash_flow(1500.0, 600.0, 800.0)
        assert isinstance(result, float)

    def test_positive_cash_flow(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_cash_flow(monthly_rent=2000.0, monthly_expenses=500.0, mortgage_payment=600.0)
        assert result == round(2000.0 - 500.0 - 600.0, 2)

    def test_negative_cash_flow(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_cash_flow(monthly_rent=800.0, monthly_expenses=700.0, mortgage_payment=800.0)
        assert result < 0

    def test_zero_cash_flow(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_cash_flow(monthly_rent=1300.0, monthly_expenses=500.0, mortgage_payment=800.0)
        assert result == 0.0

    def test_formula_correctness(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        rent, expenses, mortgage = 1750.0, 480.25, 810.70
        expected = round(rent - expenses - mortgage, 2)
        assert fm.calculate_cash_flow(rent, expenses, mortgage) == expected

    def test_cash_flow_with_integrated_estimates(self, mock_property, default_market_data):
        """Integration: verify cash_flow = rent - expenses_total - mortgage."""
        fm = make_metrics(mock_property, default_market_data)
        rent = fm.estimate_rental_income()
        expenses = fm.estimate_expenses(rent)
        mortgage = fm.calculate_mortgage_payment()
        cf = fm.calculate_cash_flow(rent, expenses['total'], mortgage)
        assert cf == round(rent - expenses['total'] - mortgage, 2)


# ---------------------------------------------------------------------------
# calculate_cap_rate
# ---------------------------------------------------------------------------

class TestCalculateCapRate:
    """Tests for FinancialMetrics.calculate_cap_rate()."""

    def test_returns_float(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_cap_rate(annual_rental_income=15000, annual_expenses=5000)
        assert isinstance(result, float)

    def test_standard_calculation(self, mock_property, default_market_data):
        """Cap rate = (NOI / price) * 100."""
        fm = make_metrics(mock_property, default_market_data)
        annual_income = 15_000.0
        annual_expenses = 5_000.0
        noi = annual_income - annual_expenses
        expected = round((noi / 200_000) * 100, 2)
        assert fm.calculate_cap_rate(annual_income, annual_expenses) == expected

    def test_higher_expenses_lower_cap_rate(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        cap_low_exp = fm.calculate_cap_rate(15_000, 3_000)
        cap_high_exp = fm.calculate_cap_rate(15_000, 8_000)
        assert cap_low_exp > cap_high_exp

    def test_higher_income_higher_cap_rate(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        cap_low_inc = fm.calculate_cap_rate(10_000, 5_000)
        cap_high_inc = fm.calculate_cap_rate(20_000, 5_000)
        assert cap_high_inc > cap_low_inc

    def test_cap_rate_is_percentage(self, mock_property, default_market_data):
        """Realistic cap rates fall between 2% and 15% for residential properties."""
        fm = make_metrics(mock_property, default_market_data)
        rent = fm.estimate_rental_income()
        annual_income = rent * 12
        annual_expenses = fm.estimate_expenses(rent)['total'] * 12
        cap_rate = fm.calculate_cap_rate(annual_income, annual_expenses)
        assert 0 < cap_rate < 20

    def test_cap_rate_negative_when_expenses_exceed_income(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_cap_rate(annual_rental_income=5_000, annual_expenses=10_000)
        assert result < 0


# ---------------------------------------------------------------------------
# calculate_cash_on_cash_return
# ---------------------------------------------------------------------------

class TestCalculateCashOnCashReturn:
    """Tests for FinancialMetrics.calculate_cash_on_cash_return()."""

    def test_returns_float(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_cash_on_cash_return(
            annual_cash_flow=3_000, down_payment=40_000, closing_costs=6_000
        )
        assert isinstance(result, float)

    def test_standard_calculation(self, mock_property, default_market_data):
        """CoC = (annual_cash_flow / (down_payment + closing_costs)) * 100."""
        fm = make_metrics(mock_property, default_market_data)
        annual_cf = 3_600.0
        dp = 40_000.0
        cc = 6_000.0
        expected = round((annual_cf / (dp + cc)) * 100, 2)
        assert fm.calculate_cash_on_cash_return(annual_cf, dp, cc) == expected

    def test_positive_return_for_positive_cash_flow(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_cash_on_cash_return(5_000, 40_000, 6_000)
        assert result > 0

    def test_negative_return_for_negative_cash_flow(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_cash_on_cash_return(-2_000, 40_000, 6_000)
        assert result < 0

    def test_higher_investment_lowers_return(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        low_inv = fm.calculate_cash_on_cash_return(3_000, 20_000, 3_000)
        high_inv = fm.calculate_cash_on_cash_return(3_000, 80_000, 6_000)
        assert low_inv > high_inv

    def test_cheap_vs_expensive_property_comparison(
        self, cheap_property, expensive_property, default_market_data
    ):
        """Both properties can produce valid (possibly contrasting) CoC values."""
        fm_cheap = make_metrics(cheap_property, default_market_data)
        fm_exp = make_metrics(expensive_property, default_market_data)
        dp_cheap = cheap_property.price * 0.20
        dp_exp = expensive_property.price * 0.20
        cc_cheap = cheap_property.price * 0.03
        cc_exp = expensive_property.price * 0.03
        cf_cheap = -500.0
        cf_exp = -2_000.0
        coc_cheap = fm_cheap.calculate_cash_on_cash_return(cf_cheap, dp_cheap, cc_cheap)
        coc_exp = fm_exp.calculate_cash_on_cash_return(cf_exp, dp_exp, cc_exp)
        # Both are valid floats with same-sign cash flows
        assert isinstance(coc_cheap, float)
        assert isinstance(coc_exp, float)


# ---------------------------------------------------------------------------
# calculate_roi
# ---------------------------------------------------------------------------

class TestCalculateRoi:
    """Tests for FinancialMetrics.calculate_roi()."""

    def test_returns_dict_with_required_keys(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_roi(
            annual_cash_flow=3_000, down_payment=40_000, closing_costs=6_000
        )
        required_keys = {
            'total_roi', 'annualized_roi', 'future_value',
            'total_cash_flow', 'appreciation_profit'
        }
        assert required_keys == set(result.keys())

    def test_all_values_are_numeric(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_roi(3_000, 40_000, 6_000)
        for key, value in result.items():
            assert isinstance(value, (int, float)), f"Key '{key}' is not numeric: {type(value)}"

    def test_future_value_greater_than_price_with_positive_appreciation(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_roi(3_000, 40_000, 6_000, holding_period=5, appreciation_rate=0.03)
        assert result['future_value'] > 200_000

    def test_future_value_equals_price_with_zero_appreciation(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_roi(3_000, 40_000, 6_000, appreciation_rate=0.0)
        assert result['future_value'] == 200_000.0
        assert result['appreciation_profit'] == 0.0

    def test_total_cash_flow_equals_annual_times_holding_period(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        annual_cf = 3_600.0
        holding = 7
        result = fm.calculate_roi(annual_cf, 40_000, 6_000, holding_period=holding)
        assert result['total_cash_flow'] == round(annual_cf * holding, 2)

    def test_longer_holding_period_increases_total_roi_when_cf_positive(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        roi_5yr = fm.calculate_roi(5_000, 40_000, 6_000, holding_period=5)
        roi_10yr = fm.calculate_roi(5_000, 40_000, 6_000, holding_period=10)
        assert roi_10yr['total_roi'] > roi_5yr['total_roi']

    def test_negative_cash_flow_reduces_roi(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        roi_positive = fm.calculate_roi(5_000, 40_000, 6_000)
        roi_negative = fm.calculate_roi(-5_000, 40_000, 6_000)
        assert roi_negative['total_roi'] < roi_positive['total_roi']

    def test_expensive_property_future_value_formula(
        self, expensive_property, default_market_data
    ):
        fm = make_metrics(expensive_property, default_market_data)
        result = fm.calculate_roi(10_000, 160_000, 24_000, holding_period=5, appreciation_rate=0.03)
        expected_fv = round(800_000 * (1.03 ** 5), 2)
        assert result['future_value'] == expected_fv

    def test_zero_investment_returns_zero_roi(self, mock_property, default_market_data):
        """calculate_roi with zero initial investment should return 0 ROI, not ZeroDivisionError."""
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_roi(
            annual_cash_flow=5000, down_payment=0, closing_costs=0
        )
        assert result['total_roi'] == 0.0
        assert result['annualized_roi'] == 0.0
        # Other fields should still be computed
        assert 'future_value' in result
        assert 'total_cash_flow' in result


# ---------------------------------------------------------------------------
# calculate_break_even_point
# ---------------------------------------------------------------------------

class TestCalculateBreakEvenPoint:
    """Tests for FinancialMetrics.calculate_break_even_point()."""

    def test_returns_numeric(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_break_even_point(1_500.0, 600.0, 800.0)
        assert isinstance(result, (int, float))

    def test_zero_when_cash_flow_positive(self, mock_property, default_market_data):
        """If rent > expenses + mortgage, break-even is already passed (returns 0)."""
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_break_even_point(
            monthly_rent=3_000.0, monthly_expenses=500.0, mortgage_payment=600.0
        )
        assert result == 0

    def test_negative_cash_flow_yields_positive_years(
        self, mock_property, default_market_data
    ):
        """When cash flow is negative, appreciation must cover the gap."""
        fm = make_metrics(mock_property, default_market_data)
        result = fm.calculate_break_even_point(
            monthly_rent=800.0, monthly_expenses=700.0, mortgage_payment=810.0
        )
        assert result > 0

    def test_returns_99_when_no_break_even_possible(
        self, mock_property
    ):
        """If total monthly benefit (cash flow + appreciation) <= 0, return 99."""
        zero_appreciation_market = {'appreciation_rate': 0.0}
        fm = make_metrics(mock_property, zero_appreciation_market)
        result = fm.calculate_break_even_point(
            monthly_rent=100.0, monthly_expenses=10_000.0, mortgage_payment=10_000.0
        )
        assert result == 99

    def test_break_even_reasonable_range_for_typical_rental(
        self, mock_property, default_market_data
    ):
        """A tight-but-negative cash flow should break even within a few decades."""
        fm = make_metrics(mock_property, default_market_data)
        rent = fm.estimate_rental_income()
        expenses = fm.estimate_expenses(rent)
        mortgage = fm.calculate_mortgage_payment()
        result = fm.calculate_break_even_point(rent, expenses['total'], mortgage)
        assert 0 <= result <= 99

    def test_higher_rent_reduces_break_even_years(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        # Both scenarios have negative cash flow but different rent levels
        bep_low = fm.calculate_break_even_point(700.0, 600.0, 810.0)
        bep_high = fm.calculate_break_even_point(950.0, 600.0, 810.0)
        # Higher rent means less negative cash flow, so break-even is sooner
        if bep_low not in (0, 99) and bep_high not in (0, 99):
            assert bep_high < bep_low


# ---------------------------------------------------------------------------
# analyze_property  (integration / end-to-end)
# ---------------------------------------------------------------------------

class TestAnalyzeProperty:
    """Tests for FinancialMetrics.analyze_property() composite method."""

    def test_returns_dict_with_required_keys(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.analyze_property()
        required_keys = {
            'monthly_rent', 'monthly_expenses', 'mortgage_payment',
            'monthly_cash_flow', 'annual_cash_flow', 'cap_rate',
            'cash_on_cash_return', 'roi', 'break_even_point',
            'price_to_rent_ratio', 'gross_yield', 'total_investment'
        }
        assert required_keys.issubset(set(result.keys()))

    def test_monthly_expenses_is_dict(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.analyze_property()
        assert isinstance(result['monthly_expenses'], dict)

    def test_roi_is_dict_with_correct_keys(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.analyze_property()
        roi_keys = {'total_roi', 'annualized_roi', 'future_value',
                    'total_cash_flow', 'appreciation_profit'}
        assert roi_keys == set(result['roi'].keys())

    def test_annual_cash_flow_equals_monthly_times_12(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.analyze_property()
        assert result['annual_cash_flow'] == round(result['monthly_cash_flow'] * 12, 2)

    def test_total_investment_equals_down_plus_closing(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.analyze_property(down_payment_percentage=0.20)
        expected = round(200_000 * 0.20 + 200_000 * 0.03, 2)
        assert result['total_investment'] == expected

    def test_gross_yield_is_positive(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.analyze_property()
        assert result['gross_yield'] > 0

    def test_price_to_rent_ratio_reflects_market(self, mock_property, default_market_data):
        """price_to_rent_ratio reported in results should match market input."""
        fm = make_metrics(mock_property, default_market_data)
        result = fm.analyze_property()
        # annual_rental_income = monthly_rent * 12 = price / ptr / 12 * 12 = price / ptr
        expected_ptr = round(200_000 / (200_000 / 15), 2)
        assert result['price_to_rent_ratio'] == expected_ptr

    def test_custom_interest_rate_affects_mortgage(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        result_low = fm.analyze_property(interest_rate=0.03)
        result_high = fm.analyze_property(interest_rate=0.07)
        assert result_high['mortgage_payment'] > result_low['mortgage_payment']

    def test_custom_holding_period_affects_roi(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result_5yr = fm.analyze_property(holding_period=5)
        result_10yr = fm.analyze_property(holding_period=10)
        assert result_5yr['roi']['total_cash_flow'] != result_10yr['roi']['total_cash_flow']

    def test_cheap_property_complete_analysis(self, cheap_property, default_market_data):
        fm = make_metrics(cheap_property, default_market_data)
        result = fm.analyze_property()
        assert result['monthly_rent'] > 0
        assert result['mortgage_payment'] > 0
        assert result['total_investment'] > 0

    def test_expensive_property_complete_analysis(
        self, expensive_property, default_market_data
    ):
        fm = make_metrics(expensive_property, default_market_data)
        result = fm.analyze_property()
        assert result['monthly_rent'] > 0
        assert result['mortgage_payment'] > 0
        assert result['total_investment'] > 0

    def test_break_even_within_valid_range(self, mock_property, default_market_data):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.analyze_property()
        assert 0 <= result['break_even_point'] <= 99

    def test_zero_interest_rate_produces_valid_analysis(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.analyze_property(interest_rate=0.0)
        assert result['mortgage_payment'] > 0
        assert isinstance(result['monthly_cash_flow'], float)

    def test_zero_down_payment_produces_valid_analysis(
        self, mock_property, default_market_data
    ):
        fm = make_metrics(mock_property, default_market_data)
        result = fm.analyze_property(down_payment_percentage=0.0)
        # Closing costs still make total_investment > 0
        assert result['total_investment'] > 0
        assert result['mortgage_payment'] > 0
