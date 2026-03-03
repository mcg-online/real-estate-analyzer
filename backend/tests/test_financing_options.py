# backend/tests/test_financing_options.py
"""
Tests for the FinancingOptions analysis service.

Covers conventional, FHA, and VA loan calculations, credit-score-based rate
adjustments, PMI logic, and the full analyze_financing_options orchestration
method (including veteran flag behaviour).
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.analysis.financing_options import FinancingOptions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_financing(property_data, market_data):
    """Construct a FinancingOptions instance from fixtures."""
    return FinancingOptions(property_data, market_data)


def _amortized_monthly_payment(loan: float, annual_rate: float, years: int) -> float:
    """Standard amortisation formula replicating the implementation."""
    monthly_rate = annual_rate / 12
    n = years * 12
    return loan * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)


# ---------------------------------------------------------------------------
# get_conventional_loan
# ---------------------------------------------------------------------------


class TestGetConventionalLoan:
    """Tests for FinancingOptions.get_conventional_loan."""

    def test_returns_required_keys(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan()
        assert set(result.keys()) == {
            "type",
            "loan_amount",
            "down_payment",
            "down_payment_percentage",
            "interest_rate",
            "term_years",
            "monthly_payment",
            "monthly_pmi",
            "total_monthly_payment",
            "total_cost",
            "total_interest",
        }

    def test_type_is_conventional(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        assert fo.get_conventional_loan()["type"] == "Conventional"

    def test_loan_amount_twenty_percent_down(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan(down_payment_percentage=0.20)
        assert result["loan_amount"] == round(mock_property.price * 0.80, 2)

    def test_down_payment_amount(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan(down_payment_percentage=0.20)
        assert result["down_payment"] == round(mock_property.price * 0.20, 2)

    def test_down_payment_percentage_stored_as_percent(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan(down_payment_percentage=0.20)
        assert result["down_payment_percentage"] == 20.0

    def test_no_pmi_when_twenty_percent_down(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan(down_payment_percentage=0.20, credit_score=720)
        assert result["monthly_pmi"] == 0.0

    def test_pmi_charged_when_less_than_twenty_percent_down(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan(down_payment_percentage=0.10, credit_score=720)
        assert result["monthly_pmi"] > 0

    def test_pmi_rate_is_half_percent_annual(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan(down_payment_percentage=0.10, credit_score=720)
        loan = mock_property.price * 0.90
        expected_pmi = round((loan * 0.005) / 12, 2)
        assert result["monthly_pmi"] == expected_pmi

    def test_total_monthly_payment_equals_payment_plus_pmi(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan(down_payment_percentage=0.10, credit_score=720)
        assert result["total_monthly_payment"] == round(
            result["monthly_payment"] + result["monthly_pmi"], 2
        )

    def test_no_credit_score_penalty_above_700(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan(down_payment_percentage=0.20, credit_score=720)
        # No adjustment -> reported rate should equal the default 4.5 %
        assert result["interest_rate"] == pytest.approx(4.5)

    def test_credit_score_below_700_increases_rate(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        high_score = fo.get_conventional_loan(down_payment_percentage=0.20, credit_score=750)
        low_score = fo.get_conventional_loan(down_payment_percentage=0.20, credit_score=650)
        assert low_score["interest_rate"] > high_score["interest_rate"]

    def test_credit_score_penalty_is_half_percent(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        high_score = fo.get_conventional_loan(down_payment_percentage=0.20, interest_rate=0.045, credit_score=750)
        low_score = fo.get_conventional_loan(down_payment_percentage=0.20, interest_rate=0.045, credit_score=650)
        # 0.5 % rate increase -> stored as percentage points
        assert low_score["interest_rate"] == pytest.approx(high_score["interest_rate"] + 0.5)

    def test_low_down_payment_rate_surcharge(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        full_down = fo.get_conventional_loan(down_payment_percentage=0.20, interest_rate=0.045, credit_score=750)
        low_down = fo.get_conventional_loan(down_payment_percentage=0.10, interest_rate=0.045, credit_score=750)
        # 0.25 % surcharge for < 20 % down
        assert low_down["interest_rate"] == pytest.approx(full_down["interest_rate"] + 0.25)

    def test_monthly_payment_greater_than_zero(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan()
        assert result["monthly_payment"] > 0

    def test_total_cost_equals_monthly_payment_times_periods(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan(down_payment_percentage=0.20, credit_score=720)
        expected_cost = result["total_monthly_payment"] * 360
        assert result["total_cost"] == pytest.approx(expected_cost, abs=2.0)

    def test_total_interest_is_total_cost_minus_loan(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan(down_payment_percentage=0.20, credit_score=720)
        expected_interest = round(result["total_cost"] - result["loan_amount"], 2)
        assert result["total_interest"] == expected_interest

    def test_expensive_property_loan_amount(self, expensive_property, default_market_data):
        fo = _make_financing(expensive_property, default_market_data)
        result = fo.get_conventional_loan(down_payment_percentage=0.20)
        assert result["loan_amount"] == round(expensive_property.price * 0.80, 2)

    def test_term_years_stored_correctly(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan(term_years=15)
        assert result["term_years"] == 15

    def test_fifteen_year_monthly_payment_higher_than_thirty(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result_30 = fo.get_conventional_loan(term_years=30, credit_score=720)
        result_15 = fo.get_conventional_loan(term_years=15, credit_score=720)
        assert result_15["monthly_payment"] > result_30["monthly_payment"]

    def test_all_monetary_values_are_positive(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_conventional_loan()
        assert result["loan_amount"] > 0
        assert result["down_payment"] > 0
        assert result["monthly_payment"] > 0
        assert result["total_cost"] > 0
        assert result["total_interest"] > 0


# ---------------------------------------------------------------------------
# get_fha_loan
# ---------------------------------------------------------------------------


class TestGetFhaLoan:
    """Tests for FinancingOptions.get_fha_loan."""

    def test_returns_required_keys(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_fha_loan()
        assert set(result.keys()) == {
            "type",
            "loan_amount",
            "down_payment",
            "down_payment_percentage",
            "interest_rate",
            "term_years",
            "monthly_payment",
            "upfront_mip",
            "monthly_mip",
            "total_monthly_payment",
            "total_cost",
            "total_interest",
        }

    def test_type_is_fha(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        assert fo.get_fha_loan()["type"] == "FHA"

    def test_default_down_payment_is_3_5_percent(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_fha_loan()
        assert result["down_payment_percentage"] == pytest.approx(3.5)

    def test_loan_amount_at_3_5_percent_down(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_fha_loan()
        expected_loan = round(mock_property.price * (1 - 0.035), 2)
        assert result["loan_amount"] == expected_loan

    def test_minimum_down_payment_enforced(self, mock_property, default_market_data):
        """A down payment below 3.5 % should be raised to the FHA minimum."""
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_fha_loan(down_payment_percentage=0.01)
        assert result["down_payment_percentage"] == pytest.approx(3.5)

    def test_upfront_mip_is_1_75_percent_of_loan(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_fha_loan()
        expected_upfront = round(result["loan_amount"] * 0.0175, 2)
        assert result["upfront_mip"] == expected_upfront

    def test_monthly_mip_rate_is_0_55_percent_annual(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_fha_loan()
        expected_monthly_mip = round((result["loan_amount"] * 0.0055) / 12, 2)
        assert result["monthly_mip"] == expected_monthly_mip

    def test_total_monthly_payment_includes_mip(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_fha_loan()
        assert result["total_monthly_payment"] == round(
            result["monthly_payment"] + result["monthly_mip"], 2
        )

    def test_total_cost_includes_upfront_mip(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_fha_loan()
        expected_cost = result["total_monthly_payment"] * 360 + result["upfront_mip"]
        assert result["total_cost"] == pytest.approx(expected_cost, abs=2.0)

    def test_total_interest_is_total_cost_minus_loan(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_fha_loan()
        expected_interest = round(result["total_cost"] - result["loan_amount"], 2)
        assert result["total_interest"] == expected_interest

    def test_monthly_payment_is_positive(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        assert fo.get_fha_loan()["monthly_payment"] > 0

    def test_upfront_mip_is_positive(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        assert fo.get_fha_loan()["upfront_mip"] > 0

    def test_monthly_mip_is_positive(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        assert fo.get_fha_loan()["monthly_mip"] > 0

    def test_interest_rate_stored_as_percentage(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_fha_loan(interest_rate=0.043)
        assert result["interest_rate"] == pytest.approx(4.3)

    def test_expensive_property_larger_upfront_mip(
        self, mock_property, expensive_property, default_market_data
    ):
        fo_cheap = _make_financing(mock_property, default_market_data)
        fo_exp = _make_financing(expensive_property, default_market_data)
        assert fo_exp.get_fha_loan()["upfront_mip"] > fo_cheap.get_fha_loan()["upfront_mip"]

    def test_term_years_stored_correctly(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_fha_loan(term_years=30)
        assert result["term_years"] == 30


# ---------------------------------------------------------------------------
# get_va_loan
# ---------------------------------------------------------------------------


class TestGetVaLoan:
    """Tests for FinancingOptions.get_va_loan."""

    def test_returns_required_keys(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan()
        assert set(result.keys()) == {
            "type",
            "loan_amount",
            "down_payment",
            "down_payment_percentage",
            "interest_rate",
            "term_years",
            "funding_fee",
            "funding_fee_percentage",
            "financed_amount",
            "monthly_payment",
            "total_monthly_payment",
            "total_cost",
            "total_interest",
        }

    def test_type_is_va(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        assert fo.get_va_loan()["type"] == "VA"

    def test_down_payment_is_zero(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan()
        assert result["down_payment"] == 0.0
        assert result["down_payment_percentage"] == 0.0

    def test_loan_amount_equals_full_price(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan()
        assert result["loan_amount"] == mock_property.price

    def test_first_time_funding_fee_is_2_15_percent(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan(funding_fee_percentage=0.0215, first_time=True)
        expected_fee = round(mock_property.price * 0.0215, 2)
        assert result["funding_fee"] == expected_fee

    def test_funding_fee_percentage_stored_as_percent(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan(funding_fee_percentage=0.0215, first_time=True)
        assert result["funding_fee_percentage"] == pytest.approx(2.15)

    def test_subsequent_use_increases_funding_fee(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        first_use = fo.get_va_loan(first_time=True)
        subsequent = fo.get_va_loan(first_time=False)
        assert subsequent["funding_fee"] > first_use["funding_fee"]

    def test_subsequent_use_funding_fee_is_3_15_percent(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan(first_time=False)
        expected_fee = round(mock_property.price * 0.0315, 2)
        assert result["funding_fee"] == expected_fee

    def test_financed_amount_is_loan_plus_funding_fee(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan()
        expected_financed = round(result["loan_amount"] + result["funding_fee"], 2)
        assert result["financed_amount"] == expected_financed

    def test_monthly_payment_based_on_financed_amount(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan(interest_rate=0.04, term_years=30, first_time=True)
        expected_payment = round(
            _amortized_monthly_payment(result["financed_amount"], 0.04, 30), 2
        )
        assert result["monthly_payment"] == expected_payment

    def test_total_cost_equals_monthly_payment_times_periods(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan()
        expected_cost = result["monthly_payment"] * 360
        assert result["total_cost"] == pytest.approx(expected_cost, abs=2.0)

    def test_total_interest_is_total_cost_minus_loan(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan()
        expected_interest = round(result["total_cost"] - result["loan_amount"], 2)
        assert result["total_interest"] == expected_interest

    def test_interest_rate_stored_as_percentage(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan(interest_rate=0.04)
        assert result["interest_rate"] == pytest.approx(4.0)

    def test_monthly_payment_is_positive(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        assert fo.get_va_loan()["monthly_payment"] > 0

    def test_expensive_property_has_larger_loan_and_fee(
        self, expensive_property, default_market_data
    ):
        fo = _make_financing(expensive_property, default_market_data)
        result = fo.get_va_loan()
        assert result["loan_amount"] == expensive_property.price
        assert result["funding_fee"] == round(expensive_property.price * 0.0215, 2)

    def test_term_years_stored_correctly(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.get_va_loan(term_years=30)
        assert result["term_years"] == 30


# ---------------------------------------------------------------------------
# analyze_financing_options
# ---------------------------------------------------------------------------


class TestAnalyzeFinancingOptions:
    """Tests for FinancingOptions.analyze_financing_options."""

    def test_returns_required_keys(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options()
        assert "options" in result
        assert "recommended" in result
        assert "local_programs" in result

    def test_options_is_a_list(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options()
        assert isinstance(result["options"], list)

    def test_non_veteran_yields_three_options(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options(credit_score=720, veteran=False)
        # Conventional 20%, Conventional 10%, FHA
        assert len(result["options"]) == 3

    def test_veteran_yields_four_options(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options(credit_score=720, veteran=True)
        # Conventional 20%, Conventional 10%, FHA, VA
        assert len(result["options"]) == 4

    def test_va_option_absent_when_not_veteran(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options(veteran=False)
        types = [opt["type"] for opt in result["options"]]
        assert "VA" not in types

    def test_va_option_present_when_veteran(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options(veteran=True)
        types = [opt["type"] for opt in result["options"]]
        assert "VA" in types

    def test_conventional_options_always_present(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options(veteran=False)
        types = [opt["type"] for opt in result["options"]]
        # Both 20 % and 10 % conventional options have type "Conventional"
        assert types.count("Conventional") == 2

    def test_fha_option_always_present(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options(veteran=False)
        types = [opt["type"] for opt in result["options"]]
        assert "FHA" in types

    def test_recommended_is_a_string(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options()
        assert isinstance(result["recommended"], str)

    def test_recommended_is_one_of_the_option_types(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options()
        valid_types = {opt["type"] for opt in result["options"]}
        assert result["recommended"] in valid_types

    def test_recommended_has_lowest_monthly_payment(self, mock_property, default_market_data):
        """The recommended option should be the one with the lowest total monthly payment."""
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options(veteran=False, credit_score=720)
        min_payment = min(opt["total_monthly_payment"] for opt in result["options"])
        recommended_option = next(
            opt for opt in result["options"] if opt["type"] == result["recommended"]
        )
        assert recommended_option["total_monthly_payment"] == min_payment

    def test_credit_score_below_700_adjusts_conventional_rate(
        self, mock_property, default_market_data
    ):
        fo = _make_financing(mock_property, default_market_data)
        result_high = fo.analyze_financing_options(credit_score=750, veteran=False)
        result_low = fo.analyze_financing_options(credit_score=650, veteran=False)
        conv_high = next(o for o in result_high["options"] if o["type"] == "Conventional" and o["down_payment_percentage"] == 20.0)
        conv_low = next(o for o in result_low["options"] if o["type"] == "Conventional" and o["down_payment_percentage"] == 20.0)
        assert conv_low["interest_rate"] > conv_high["interest_rate"]

    def test_veteran_flag_true_includes_va_with_first_time_fee(
        self, mock_property, default_market_data
    ):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options(veteran=True, first_time_va=True)
        va_option = next(opt for opt in result["options"] if opt["type"] == "VA")
        # first_time=True -> 2.15 % funding fee
        assert va_option["funding_fee_percentage"] == pytest.approx(2.15)

    def test_veteran_flag_true_subsequent_va_use(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options(veteran=True, first_time_va=False)
        va_option = next(opt for opt in result["options"] if opt["type"] == "VA")
        # first_time=False -> 3.15 % funding fee
        assert va_option["funding_fee_percentage"] == pytest.approx(3.15)

    def test_all_options_have_positive_monthly_payment(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options(veteran=True)
        for opt in result["options"]:
            assert opt["total_monthly_payment"] > 0, (
                f"Option '{opt['type']}' has non-positive monthly payment"
            )

    def test_local_programs_is_a_list(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options()
        assert isinstance(result["local_programs"], list)

    def test_local_programs_from_market_data(self, mock_property):
        programs = ["First-Time Buyer Assistance", "Down Payment Grant"]
        market_with_programs = {
            "property_tax_rate": 0.01,
            "financing_programs": programs,
        }
        fo = _make_financing(mock_property, market_with_programs)
        result = fo.analyze_financing_options()
        assert result["local_programs"] == programs

    def test_no_local_programs_when_absent_from_market(self, mock_property, default_market_data):
        # default_market_data has no 'financing_programs' key
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options()
        assert result["local_programs"] == []

    def test_expensive_property_options_have_larger_loan_amounts(
        self, expensive_property, default_market_data
    ):
        fo = _make_financing(expensive_property, default_market_data)
        result = fo.analyze_financing_options(veteran=False, credit_score=720)
        for opt in result["options"]:
            assert opt["loan_amount"] > 400_000, (
                f"Expected loan > 400k for $800k property, got {opt['loan_amount']} for {opt['type']}"
            )

    def test_each_option_has_type_key(self, mock_property, default_market_data):
        fo = _make_financing(mock_property, default_market_data)
        result = fo.analyze_financing_options(veteran=True)
        for opt in result["options"]:
            assert "type" in opt
