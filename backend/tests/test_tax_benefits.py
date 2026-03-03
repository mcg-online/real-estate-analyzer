# backend/tests/test_tax_benefits.py
"""
Tests for the TaxBenefits analysis service.

Covers depreciation calculation, mortgage interest deduction,
property tax deduction, local tax incentives, and the full
analyze_tax_benefits orchestration method.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.analysis.tax_benefits import TaxBenefits


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tax_benefits(property_data, market_data):
    """Construct a TaxBenefits instance from fixtures."""
    return TaxBenefits(property_data, market_data)


def _first_year_interest(loan_amount: float, annual_rate: float, term_years: int = 30) -> float:
    """Replicate the first-year interest calculation used in TaxBenefits."""
    monthly_rate = annual_rate / 12
    n = term_years * 12
    monthly_payment = (
        loan_amount
        * (monthly_rate * (1 + monthly_rate) ** n)
        / ((1 + monthly_rate) ** n - 1)
    )
    interest_total = 0.0
    balance = loan_amount
    for _ in range(12):
        interest = balance * monthly_rate
        principal = monthly_payment - interest
        balance -= principal
        interest_total += interest
    return round(interest_total, 2)


# ---------------------------------------------------------------------------
# calculate_depreciation
# ---------------------------------------------------------------------------


class TestCalculateDepreciation:
    """Tests for TaxBenefits.calculate_depreciation."""

    def test_returns_required_keys(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000)
        assert set(result.keys()) == {
            "building_value",
            "land_value",
            "annual_depreciation",
            "monthly_depreciation",
        }

    def test_default_land_value_is_twenty_percent(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000)
        # Land defaults to 20 % of property value
        assert result["land_value"] == 40_000.00

    def test_building_value_is_property_minus_land(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000)
        assert result["building_value"] == 160_000.00

    def test_annual_depreciation_over_27_5_years(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000)
        # 160_000 / 27.5 = 5818.18...
        assert result["annual_depreciation"] == round(160_000 / 27.5, 2)

    def test_monthly_depreciation_is_annual_divided_by_12(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000)
        expected_monthly = round(result["annual_depreciation"] / 12, 2)
        assert result["monthly_depreciation"] == expected_monthly

    def test_explicit_land_value_used_when_provided(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000, land_value=50_000)
        assert result["land_value"] == 50_000.00
        assert result["building_value"] == 150_000.00

    def test_explicit_land_value_changes_annual_depreciation(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000, land_value=50_000)
        assert result["annual_depreciation"] == round(150_000 / 27.5, 2)

    def test_custom_depreciation_period(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000, depreciation_period=39)
        # Commercial property uses 39 years
        assert result["annual_depreciation"] == round(160_000 / 39, 2)

    def test_expensive_property_depreciation(self, expensive_property, default_market_data):
        tb = _make_tax_benefits(expensive_property, default_market_data)
        result = tb.calculate_depreciation(800_000)
        assert result["land_value"] == 160_000.00
        assert result["building_value"] == 640_000.00
        assert result["annual_depreciation"] == round(640_000 / 27.5, 2)

    def test_annual_depreciation_is_positive(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000)
        assert result["annual_depreciation"] > 0

    def test_monthly_depreciation_is_positive(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000)
        assert result["monthly_depreciation"] > 0

    def test_monthly_depreciation_less_than_annual(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000)
        assert result["monthly_depreciation"] < result["annual_depreciation"]

    def test_all_values_are_rounded_to_cents(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_depreciation(200_000)
        for key, value in result.items():
            assert isinstance(value, float), f"{key} should be a float"
            assert round(value, 2) == value, f"{key} should be rounded to 2 decimal places"


# ---------------------------------------------------------------------------
# calculate_mortgage_interest_deduction
# ---------------------------------------------------------------------------


class TestCalculateMortgageInterestDeduction:
    """Tests for TaxBenefits.calculate_mortgage_interest_deduction."""

    def test_returns_a_float(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_mortgage_interest_deduction(160_000, 0.045)
        assert isinstance(result, float)

    def test_first_year_interest_is_positive(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_mortgage_interest_deduction(160_000, 0.045)
        assert result > 0

    def test_first_year_interest_standard_loan(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_mortgage_interest_deduction(160_000, 0.045)
        expected = _first_year_interest(160_000, 0.045, 30)
        assert result == expected

    def test_higher_loan_produces_more_interest(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        small = tb.calculate_mortgage_interest_deduction(160_000, 0.045)
        large = tb.calculate_mortgage_interest_deduction(640_000, 0.045)
        assert large > small

    def test_higher_rate_produces_more_interest(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        low_rate = tb.calculate_mortgage_interest_deduction(160_000, 0.035)
        high_rate = tb.calculate_mortgage_interest_deduction(160_000, 0.065)
        assert high_rate > low_rate

    def test_zero_interest_rate_returns_zero(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_mortgage_interest_deduction(160_000, 0.0)
        assert result == 0

    def test_custom_term_years(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result_30 = tb.calculate_mortgage_interest_deduction(160_000, 0.045, term_years=30)
        result_15 = tb.calculate_mortgage_interest_deduction(160_000, 0.045, term_years=15)
        # 15-year loan has higher monthly payment, so first-year interest differs
        assert result_15 != result_30

    def test_interest_deduction_is_less_than_loan_amount(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        loan = 160_000
        result = tb.calculate_mortgage_interest_deduction(loan, 0.045)
        # First-year interest is always a fraction of the total loan
        assert result < loan

    def test_result_is_rounded_to_cents(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_mortgage_interest_deduction(160_000, 0.045)
        assert round(result, 2) == result

    def test_expensive_property_mortgage_interest(self, expensive_property, default_market_data):
        tb = _make_tax_benefits(expensive_property, default_market_data)
        loan = expensive_property.price * 0.80  # 640_000
        result = tb.calculate_mortgage_interest_deduction(loan, 0.045)
        expected = _first_year_interest(loan, 0.045, 30)
        assert result == expected


# ---------------------------------------------------------------------------
# calculate_property_tax_deduction
# ---------------------------------------------------------------------------


class TestCalculatePropertyTaxDeduction:
    """Tests for TaxBenefits.calculate_property_tax_deduction."""

    def test_returns_a_float(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_property_tax_deduction()
        assert isinstance(result, float)

    def test_standard_calculation(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_property_tax_deduction()
        # price=200_000, rate=0.01 -> 2_000.00
        assert result == 2_000.00

    def test_uses_market_property_tax_rate(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        expected = mock_property.price * default_market_data["property_tax_rate"]
        assert tb.calculate_property_tax_deduction() == round(expected, 2)

    def test_higher_tax_rate_yields_higher_deduction(self, mock_property):
        low_rate_market = {"property_tax_rate": 0.005}
        high_rate_market = {"property_tax_rate": 0.025}
        tb_low = _make_tax_benefits(mock_property, low_rate_market)
        tb_high = _make_tax_benefits(mock_property, high_rate_market)
        assert tb_high.calculate_property_tax_deduction() > tb_low.calculate_property_tax_deduction()

    def test_expensive_property_yields_larger_deduction(
        self, mock_property, expensive_property, default_market_data
    ):
        tb_cheap = _make_tax_benefits(mock_property, default_market_data)
        tb_exp = _make_tax_benefits(expensive_property, default_market_data)
        assert tb_exp.calculate_property_tax_deduction() > tb_cheap.calculate_property_tax_deduction()

    def test_expensive_property_standard_calculation(self, expensive_property, default_market_data):
        tb = _make_tax_benefits(expensive_property, default_market_data)
        # price=800_000, rate=0.01 -> 8_000.00
        assert tb.calculate_property_tax_deduction() == 8_000.00

    def test_defaults_to_one_percent_when_rate_missing(self, mock_property):
        market_without_rate = {}
        tb = _make_tax_benefits(mock_property, market_without_rate)
        # default rate = 0.01
        assert tb.calculate_property_tax_deduction() == round(mock_property.price * 0.01, 2)

    def test_result_is_rounded_to_cents(self, mock_property):
        market = {"property_tax_rate": 0.013}
        tb = _make_tax_benefits(mock_property, market)
        result = tb.calculate_property_tax_deduction()
        assert round(result, 2) == result

    def test_result_is_positive(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        assert tb.calculate_property_tax_deduction() > 0


# ---------------------------------------------------------------------------
# calculate_local_tax_incentives
# ---------------------------------------------------------------------------


class TestCalculateLocalTaxIncentives:
    """Tests for TaxBenefits.calculate_local_tax_incentives."""

    def test_returns_dict(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_local_tax_incentives()
        assert isinstance(result, dict)

    def test_default_incentives_when_market_has_no_tax_benefits(
        self, mock_property, default_market_data
    ):
        # default_market_data has no 'tax_benefits' key
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_local_tax_incentives()
        assert "has_opportunity_zone" in result
        assert "has_historic_tax_credits" in result
        assert "has_homestead_exemption" in result
        assert "has_renovation_incentives" in result
        assert "special_programs" in result

    def test_default_incentives_are_false(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_local_tax_incentives()
        assert result["has_opportunity_zone"] is False
        assert result["has_historic_tax_credits"] is False
        assert result["has_homestead_exemption"] is False
        assert result["has_renovation_incentives"] is False

    def test_default_special_programs_is_empty_list(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.calculate_local_tax_incentives()
        assert result["special_programs"] == []

    def test_returns_market_tax_benefits_when_present(self, mock_property):
        custom_incentives = {
            "has_opportunity_zone": True,
            "has_historic_tax_credits": True,
            "has_homestead_exemption": False,
            "has_renovation_incentives": True,
            "special_programs": ["First-Time Buyer Credit", "Green Building Rebate"],
        }
        market_with_benefits = {"property_tax_rate": 0.01, "tax_benefits": custom_incentives}
        tb = _make_tax_benefits(mock_property, market_with_benefits)
        result = tb.calculate_local_tax_incentives()
        assert result == custom_incentives

    def test_opportunity_zone_from_market(self, mock_property):
        market = {"tax_benefits": {"has_opportunity_zone": True, "special_programs": []}}
        tb = _make_tax_benefits(mock_property, market)
        result = tb.calculate_local_tax_incentives()
        assert result["has_opportunity_zone"] is True

    def test_empty_tax_benefits_dict_yields_defaults(self, mock_property):
        market = {"tax_benefits": {}}
        tb = _make_tax_benefits(mock_property, market)
        result = tb.calculate_local_tax_incentives()
        # An empty dict is falsy, so defaults should be applied
        assert "has_opportunity_zone" in result

    def test_special_programs_from_market(self, mock_property):
        programs = ["Historic Tax Credit Program", "Opportunity Zone Investment"]
        market = {
            "tax_benefits": {
                "has_opportunity_zone": True,
                "special_programs": programs,
            }
        }
        tb = _make_tax_benefits(mock_property, market)
        result = tb.calculate_local_tax_incentives()
        assert result["special_programs"] == programs


# ---------------------------------------------------------------------------
# analyze_tax_benefits
# ---------------------------------------------------------------------------


class TestAnalyzeTaxBenefits:
    """Tests for TaxBenefits.analyze_tax_benefits (full orchestration)."""

    def test_returns_required_keys(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.analyze_tax_benefits()
        assert set(result.keys()) == {
            "depreciation",
            "mortgage_interest_deduction",
            "property_tax_deduction",
            "local_tax_incentives",
            "total_deductions",
            "estimated_tax_savings",
            "monthly_tax_savings",
        }

    def test_depreciation_sub_dict_has_required_keys(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.analyze_tax_benefits()
        assert "annual_depreciation" in result["depreciation"]
        assert "building_value" in result["depreciation"]

    def test_total_deductions_is_sum_of_components(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.analyze_tax_benefits()
        dep = result["depreciation"]["annual_depreciation"]
        mid = result["mortgage_interest_deduction"]
        ptd = result["property_tax_deduction"]
        expected_total = round(dep + mid + ptd, 2)
        assert result["total_deductions"] == expected_total

    def test_estimated_tax_savings_uses_tax_bracket(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.analyze_tax_benefits(tax_bracket=0.22)
        expected_savings = round(result["total_deductions"] * 0.22, 2)
        assert result["estimated_tax_savings"] == expected_savings

    def test_monthly_tax_savings_is_annual_divided_by_12(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.analyze_tax_benefits()
        expected_monthly = round(result["estimated_tax_savings"] / 12, 2)
        assert result["monthly_tax_savings"] == expected_monthly

    def test_higher_tax_bracket_yields_higher_savings(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result_low = tb.analyze_tax_benefits(tax_bracket=0.12)
        result_high = tb.analyze_tax_benefits(tax_bracket=0.37)
        assert result_high["estimated_tax_savings"] > result_low["estimated_tax_savings"]

    def test_smaller_down_payment_yields_larger_loan_and_more_interest(
        self, mock_property, default_market_data
    ):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result_20 = tb.analyze_tax_benefits(down_payment_percentage=0.20)
        result_05 = tb.analyze_tax_benefits(down_payment_percentage=0.05)
        assert result_05["mortgage_interest_deduction"] > result_20["mortgage_interest_deduction"]

    def test_higher_interest_rate_yields_more_interest_deduction(
        self, mock_property, default_market_data
    ):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result_low = tb.analyze_tax_benefits(interest_rate=0.03)
        result_high = tb.analyze_tax_benefits(interest_rate=0.07)
        assert result_high["mortgage_interest_deduction"] > result_low["mortgage_interest_deduction"]

    def test_all_monetary_values_are_positive(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.analyze_tax_benefits()
        assert result["mortgage_interest_deduction"] > 0
        assert result["property_tax_deduction"] > 0
        assert result["total_deductions"] > 0
        assert result["estimated_tax_savings"] > 0
        assert result["monthly_tax_savings"] > 0

    def test_expensive_property_yields_larger_total_deductions(
        self, mock_property, expensive_property, default_market_data
    ):
        tb_cheap = _make_tax_benefits(mock_property, default_market_data)
        tb_exp = _make_tax_benefits(expensive_property, default_market_data)
        cheap_result = tb_cheap.analyze_tax_benefits()
        exp_result = tb_exp.analyze_tax_benefits()
        assert exp_result["total_deductions"] > cheap_result["total_deductions"]

    def test_local_tax_incentives_included_in_result(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result = tb.analyze_tax_benefits()
        # Should be a dict (either defaults or from market data)
        assert isinstance(result["local_tax_incentives"], dict)

    def test_default_parameters_match_22_percent_bracket(
        self, mock_property, default_market_data
    ):
        """Calling analyze_tax_benefits() with no args should use tax_bracket=0.22."""
        tb = _make_tax_benefits(mock_property, default_market_data)
        result_default = tb.analyze_tax_benefits()
        result_explicit = tb.analyze_tax_benefits(tax_bracket=0.22)
        assert result_default["estimated_tax_savings"] == result_explicit["estimated_tax_savings"]

    def test_fifteen_year_term_produces_different_results(self, mock_property, default_market_data):
        tb = _make_tax_benefits(mock_property, default_market_data)
        result_30 = tb.analyze_tax_benefits(term_years=30)
        result_15 = tb.analyze_tax_benefits(term_years=15)
        assert result_30["mortgage_interest_deduction"] != result_15["mortgage_interest_deduction"]
