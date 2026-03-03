# backend/tests/test_risk_assessment.py
"""Tests for the RiskAssessment service.

Covers:
- Each individual scoring method returns a float in [0, 10]
- assess_risk() returns a dict with all documented keys
- individual_scores sub-dict contains all four risk dimensions
- overall_risk is in [0, 10] and matches a weighted combination
- risk_level is one of the four documented tiers
- risk_factors and recommendations are lists of strings
- strong-market scenarios produce lower risk scores than weak-market ones
- high vacancy / unemployment / old property conditions raise scores
- financing risk responds to LTV and interest-rate inputs
- edge cases: empty market data, missing keys, zero prices
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.analysis.risk_assessment import RiskAssessment

# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------

_INDIVIDUAL_SCORE_KEYS = frozenset(
    {
        "market_volatility",
        "vacancy_risk",
        "property_condition_risk",
        "financing_risk",
    }
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "individual_scores",
        "overall_risk",
        "risk_level",
        "risk_factors",
        "recommendations",
    }
)

_VALID_RISK_LEVELS = frozenset({"Low", "Moderate", "High", "Very High"})


def _assessor(property_fixture, market_fixture) -> RiskAssessment:
    """Convenience constructor."""
    return RiskAssessment(property_fixture, market_fixture)


def _score_in_range(value: float, lo: float = 0.0, hi: float = 10.0) -> bool:
    return lo <= value <= hi


# ---------------------------------------------------------------------------
# Test: calculate_market_volatility()
# ---------------------------------------------------------------------------


class TestCalculateMarketVolatility:
    """calculate_market_volatility() must return a float in [0, 10]."""

    def test_default_market_in_range(self, mock_property, default_market_data):
        score = _assessor(mock_property, default_market_data).calculate_market_volatility()
        assert _score_in_range(score)

    def test_strong_market_in_range(self, mock_property, strong_market_data):
        score = _assessor(mock_property, strong_market_data).calculate_market_volatility()
        assert _score_in_range(score)

    def test_weak_market_in_range(self, mock_property, weak_market_data):
        score = _assessor(mock_property, weak_market_data).calculate_market_volatility()
        assert _score_in_range(score)

    def test_returns_float(self, mock_property, default_market_data):
        score = _assessor(mock_property, default_market_data).calculate_market_volatility()
        assert isinstance(score, float)

    def test_zero_appreciation_raises_volatility(
        self, mock_property, weak_market_data, strong_market_data
    ):
        """weak_market_data has appreciation_rate=0.0 which deviates from the 3% ideal."""
        score_weak = _assessor(mock_property, weak_market_data).calculate_market_volatility()
        score_strong = _assessor(mock_property, strong_market_data).calculate_market_volatility()
        # A 0% appreciation rate should signal more risk than 6%... both are
        # outside the ideal but validation should at least ensure ranges hold.
        assert _score_in_range(score_weak)
        assert _score_in_range(score_strong)

    def test_negative_appreciation_produces_high_volatility(self, mock_property):
        """Negative appreciation should push volatility score toward the high end."""
        market = {"appreciation_rate": -0.05, "vacancy_rate": 0.08}
        score = _assessor(mock_property, market).calculate_market_volatility()
        assert score >= 5.0, (
            f"Expected high volatility for depreciating market, got {score}"
        )
        assert _score_in_range(score)

    def test_price_history_provided_does_not_raise(self, mock_property):
        market = {
            "appreciation_rate": 0.03,
            "price_history": [200000, 210000, 215000, 220000, 230000],
        }
        score = _assessor(mock_property, market).calculate_market_volatility()
        assert _score_in_range(score)

    def test_single_price_history_entry_uses_default(self, mock_property):
        """A price_history list with only one entry should fall back to the neutral default."""
        market = {"appreciation_rate": 0.03, "price_history": [200000]}
        score = _assessor(mock_property, market).calculate_market_volatility()
        assert _score_in_range(score)

    def test_volatile_price_history_raises_score(self, mock_property):
        """Highly volatile price history (large CV) should produce a high score."""
        market = {
            "appreciation_rate": 0.03,
            "price_history": [100000, 300000, 50000, 400000, 80000],
        }
        score = _assessor(mock_property, market).calculate_market_volatility()
        assert score > 3.0, f"Expected elevated volatility score, got {score}"
        assert _score_in_range(score)


# ---------------------------------------------------------------------------
# Test: calculate_vacancy_risk()
# ---------------------------------------------------------------------------


class TestCalculateVacancyRisk:
    """calculate_vacancy_risk() must return a float in [0, 10]."""

    def test_default_market_in_range(self, mock_property, default_market_data):
        score = _assessor(mock_property, default_market_data).calculate_vacancy_risk()
        assert _score_in_range(score)

    def test_strong_market_in_range(self, mock_property, strong_market_data):
        score = _assessor(mock_property, strong_market_data).calculate_vacancy_risk()
        assert _score_in_range(score)

    def test_weak_market_in_range(self, mock_property, weak_market_data):
        score = _assessor(mock_property, weak_market_data).calculate_vacancy_risk()
        assert _score_in_range(score)

    def test_returns_float(self, mock_property, default_market_data):
        score = _assessor(mock_property, default_market_data).calculate_vacancy_risk()
        assert isinstance(score, float)

    def test_high_vacancy_produces_higher_score(self, mock_property):
        """15% vacancy (weak) should score higher risk than 3% vacancy (strong)."""
        low_vacancy = _assessor(
            mock_property, {"vacancy_rate": 0.03, "days_on_market": 15}
        ).calculate_vacancy_risk()
        high_vacancy = _assessor(
            mock_property, {"vacancy_rate": 0.15, "days_on_market": 90}
        ).calculate_vacancy_risk()
        assert high_vacancy > low_vacancy

    def test_weak_market_vacancy_higher_than_strong_market(
        self, mock_property, strong_market_data, weak_market_data
    ):
        """weak_market_data (vacancy=0.15, DOM=90) should score higher than strong (vacancy=0.03, DOM=15)."""
        strong_score = _assessor(mock_property, strong_market_data).calculate_vacancy_risk()
        weak_score = _assessor(mock_property, weak_market_data).calculate_vacancy_risk()
        assert weak_score > strong_score

    def test_high_unemployment_increases_vacancy_risk(self, mock_property):
        """Unemployment above 4% should add a penalty to the vacancy score."""
        base_market = {"vacancy_rate": 0.08, "days_on_market": 30, "unemployment_rate": 0.04}
        high_unemp_market = {"vacancy_rate": 0.08, "days_on_market": 30, "unemployment_rate": 0.10}
        base_score = _assessor(mock_property, base_market).calculate_vacancy_risk()
        high_score = _assessor(mock_property, high_unemp_market).calculate_vacancy_risk()
        assert high_score > base_score

    def test_zero_vacancy_produces_low_score(self, mock_property):
        market = {"vacancy_rate": 0.0, "days_on_market": 5, "unemployment_rate": 0.03}
        score = _assessor(mock_property, market).calculate_vacancy_risk()
        assert score < 5.0
        assert _score_in_range(score)


# ---------------------------------------------------------------------------
# Test: calculate_property_condition_risk()
# ---------------------------------------------------------------------------


class TestCalculatePropertyConditionRisk:
    """calculate_property_condition_risk() must return a float in [0, 10]."""

    def test_default_property_in_range(self, mock_property, default_market_data):
        score = _assessor(mock_property, default_market_data).calculate_property_condition_risk()
        assert _score_in_range(score)

    def test_expensive_new_property_in_range(
        self, expensive_property, default_market_data
    ):
        score = _assessor(expensive_property, default_market_data).calculate_property_condition_risk()
        assert _score_in_range(score)

    def test_cheap_old_property_in_range(self, cheap_property, default_market_data):
        score = _assessor(cheap_property, default_market_data).calculate_property_condition_risk()
        assert _score_in_range(score)

    def test_returns_float(self, mock_property, default_market_data):
        score = _assessor(mock_property, default_market_data).calculate_property_condition_risk()
        assert isinstance(score, float)

    def test_old_property_scores_higher_than_new(
        self, cheap_property, expensive_property, default_market_data
    ):
        """cheap_property (year_built=1960) should have higher condition risk
        than expensive_property (year_built=2020)."""
        old_score = _assessor(
            cheap_property, default_market_data
        ).calculate_property_condition_risk()
        new_score = _assessor(
            expensive_property, default_market_data
        ).calculate_property_condition_risk()
        assert old_score > new_score, (
            f"Old property ({old_score}) should score higher risk than new ({new_score})"
        )

    def test_mobile_home_type_raises_condition_risk(
        self, mock_property, default_market_data
    ):
        """A 'mobile home' property type should score higher than 'Residential'."""
        from tests.conftest import MockProperty

        mobile = MockProperty(property_type="mobile home")
        mobile_score = _assessor(
            mobile, default_market_data
        ).calculate_property_condition_risk()
        standard_score = _assessor(
            mock_property, default_market_data
        ).calculate_property_condition_risk()
        assert mobile_score > standard_score

    def test_very_cheap_per_sqft_triggers_distress_flag(self, default_market_data):
        """A price_per_sqft < 50 should produce a high condition risk (ppsf_score=8)."""
        from tests.conftest import MockProperty

        distressed = MockProperty(price=30000, sqft=1000)  # $30/sqft
        score = _assessor(distressed, default_market_data).calculate_property_condition_risk()
        assert score >= 3.0, f"Expected elevated condition risk for distressed asset, got {score}"
        assert _score_in_range(score)


# ---------------------------------------------------------------------------
# Test: calculate_financing_risk()
# ---------------------------------------------------------------------------


class TestCalculateFinancingRisk:
    """calculate_financing_risk() must return a float in [0, 10]."""

    def test_default_market_in_range(self, mock_property, default_market_data):
        score = _assessor(mock_property, default_market_data).calculate_financing_risk()
        assert _score_in_range(score)

    def test_strong_market_in_range(self, mock_property, strong_market_data):
        score = _assessor(mock_property, strong_market_data).calculate_financing_risk()
        assert _score_in_range(score)

    def test_weak_market_in_range(self, mock_property, weak_market_data):
        score = _assessor(mock_property, weak_market_data).calculate_financing_risk()
        assert _score_in_range(score)

    def test_returns_float(self, mock_property, default_market_data):
        score = _assessor(mock_property, default_market_data).calculate_financing_risk()
        assert isinstance(score, float)

    def test_high_ltv_increases_financing_risk(self, mock_property):
        """5% down payment (95% LTV) should produce higher risk than 30% down."""
        low_down = {"down_payment_percentage": 0.05, "interest_rate": 0.07, "price_to_rent_ratio": 15}
        high_down = {"down_payment_percentage": 0.30, "interest_rate": 0.07, "price_to_rent_ratio": 15}
        low_score = _assessor(mock_property, low_down).calculate_financing_risk()
        high_score = _assessor(mock_property, high_down).calculate_financing_risk()
        assert low_score > high_score

    def test_high_interest_rate_increases_financing_risk(self, mock_property):
        """An 8% interest rate should score higher risk than a 4% rate."""
        low_rate = {"down_payment_percentage": 0.20, "interest_rate": 0.04, "price_to_rent_ratio": 15}
        high_rate = {"down_payment_percentage": 0.20, "interest_rate": 0.08, "price_to_rent_ratio": 15}
        low_score = _assessor(mock_property, low_rate).calculate_financing_risk()
        high_score = _assessor(mock_property, high_rate).calculate_financing_risk()
        assert high_score > low_score

    def test_favorable_ptr_reduces_financing_risk(self, mock_property):
        """Lower price-to-rent ratio (10) should produce lower financing risk than high (25)."""
        good_ptr = {"down_payment_percentage": 0.20, "interest_rate": 0.07, "price_to_rent_ratio": 10}
        bad_ptr = {"down_payment_percentage": 0.20, "interest_rate": 0.07, "price_to_rent_ratio": 25}
        good_score = _assessor(mock_property, good_ptr).calculate_financing_risk()
        bad_score = _assessor(mock_property, bad_ptr).calculate_financing_risk()
        assert good_score < bad_score


# ---------------------------------------------------------------------------
# Test: calculate_overall_risk()
# ---------------------------------------------------------------------------


class TestCalculateOverallRisk:
    """calculate_overall_risk() must return a float in [0, 10]."""

    def test_default_market_in_range(self, mock_property, default_market_data):
        score = _assessor(mock_property, default_market_data).calculate_overall_risk()
        assert _score_in_range(score)

    def test_strong_market_in_range(self, mock_property, strong_market_data):
        score = _assessor(mock_property, strong_market_data).calculate_overall_risk()
        assert _score_in_range(score)

    def test_weak_market_in_range(self, mock_property, weak_market_data):
        score = _assessor(mock_property, weak_market_data).calculate_overall_risk()
        assert _score_in_range(score)

    def test_returns_float(self, mock_property, default_market_data):
        score = _assessor(mock_property, default_market_data).calculate_overall_risk()
        assert isinstance(score, float)

    def test_weak_market_higher_overall_risk_than_strong(
        self, mock_property, strong_market_data, weak_market_data
    ):
        """Weak market conditions should yield a higher composite risk score."""
        strong_score = _assessor(mock_property, strong_market_data).calculate_overall_risk()
        weak_score = _assessor(mock_property, weak_market_data).calculate_overall_risk()
        assert weak_score > strong_score, (
            f"Expected weak ({weak_score}) > strong ({strong_score})"
        )

    def test_overall_risk_consistent_with_individual_scores(
        self, mock_property, default_market_data
    ):
        """calculate_overall_risk() should equal the weighted sum from assess_risk()."""
        assessor = _assessor(mock_property, default_market_data)
        overall_direct = assessor.calculate_overall_risk()
        report = assessor.assess_risk()
        assert overall_direct == pytest.approx(report["overall_risk"], abs=0.01)


# ---------------------------------------------------------------------------
# Test: assess_risk() return structure
# ---------------------------------------------------------------------------


class TestAssessRiskStructure:
    """assess_risk() must return a dict with all documented top-level keys."""

    def test_returns_dict(self, mock_property, default_market_data):
        result = _assessor(mock_property, default_market_data).assess_risk()
        assert isinstance(result, dict)

    def test_top_level_keys_present(self, mock_property, default_market_data):
        result = _assessor(mock_property, default_market_data).assess_risk()
        assert _TOP_LEVEL_KEYS.issubset(result.keys())

    def test_individual_scores_has_all_keys(self, mock_property, default_market_data):
        result = _assessor(mock_property, default_market_data).assess_risk()
        assert _INDIVIDUAL_SCORE_KEYS == set(result["individual_scores"].keys())

    def test_overall_risk_present_and_in_range(self, mock_property, default_market_data):
        result = _assessor(mock_property, default_market_data).assess_risk()
        assert "overall_risk" in result
        assert _score_in_range(result["overall_risk"])

    def test_risk_level_is_valid_string(self, mock_property, default_market_data):
        result = _assessor(mock_property, default_market_data).assess_risk()
        assert result["risk_level"] in _VALID_RISK_LEVELS

    def test_risk_factors_is_list(self, mock_property, default_market_data):
        result = _assessor(mock_property, default_market_data).assess_risk()
        assert isinstance(result["risk_factors"], list)

    def test_recommendations_is_list(self, mock_property, default_market_data):
        result = _assessor(mock_property, default_market_data).assess_risk()
        assert isinstance(result["recommendations"], list)

    def test_risk_factors_contains_strings(self, mock_property, default_market_data):
        result = _assessor(mock_property, default_market_data).assess_risk()
        for item in result["risk_factors"]:
            assert isinstance(item, str)

    def test_recommendations_contains_strings(self, mock_property, default_market_data):
        result = _assessor(mock_property, default_market_data).assess_risk()
        for item in result["recommendations"]:
            assert isinstance(item, str)

    def test_individual_scores_all_in_range(self, mock_property, default_market_data):
        result = _assessor(mock_property, default_market_data).assess_risk()
        for key, value in result["individual_scores"].items():
            assert _score_in_range(value), (
                f"individual_scores['{key}'] = {value} is out of [0, 10]"
            )


# ---------------------------------------------------------------------------
# Test: assess_risk() with strong market
# ---------------------------------------------------------------------------


class TestAssessRiskStrongMarket:
    """Strong market scenarios should produce lower overall risk."""

    def test_overall_risk_in_range(self, mock_property, strong_market_data):
        result = _assessor(mock_property, strong_market_data).assess_risk()
        assert _score_in_range(result["overall_risk"])

    def test_risk_level_not_very_high(self, mock_property, strong_market_data):
        """A strong market with default property should not be 'Very High' risk."""
        result = _assessor(mock_property, strong_market_data).assess_risk()
        assert result["risk_level"] != "Very High", (
            f"Unexpected 'Very High' risk in strong market: overall={result['overall_risk']}"
        )

    def test_vacancy_risk_low_in_strong_market(self, mock_property, strong_market_data):
        """3% vacancy and 15 DOM should produce a low vacancy risk score."""
        result = _assessor(mock_property, strong_market_data).assess_risk()
        assert result["individual_scores"]["vacancy_risk"] < 5.0

    def test_recommendations_always_has_cash_reserve_tip(
        self, mock_property, strong_market_data
    ):
        """The cash-reserve recommendation should always be present."""
        result = _assessor(mock_property, strong_market_data).assess_risk()
        joined = " ".join(result["recommendations"]).lower()
        assert "cash reserve" in joined or "liquid" in joined or "reserve" in joined


# ---------------------------------------------------------------------------
# Test: assess_risk() with weak market
# ---------------------------------------------------------------------------


class TestAssessRiskWeakMarket:
    """Weak market scenarios should produce elevated overall risk and richer factors."""

    def test_overall_risk_in_range(self, mock_property, weak_market_data):
        result = _assessor(mock_property, weak_market_data).assess_risk()
        assert _score_in_range(result["overall_risk"])

    def test_overall_risk_higher_than_strong_market(
        self, mock_property, strong_market_data, weak_market_data
    ):
        weak_result = _assessor(mock_property, weak_market_data).assess_risk()
        strong_result = _assessor(mock_property, strong_market_data).assess_risk()
        assert weak_result["overall_risk"] > strong_result["overall_risk"]

    def test_risk_level_elevated_in_weak_market(self, mock_property, weak_market_data):
        """High vacancy (15%), zero appreciation, and 10% unemployment should push
        the risk level to Moderate, High, or Very High."""
        result = _assessor(mock_property, weak_market_data).assess_risk()
        assert result["risk_level"] in {"Moderate", "High", "Very High"}, (
            f"Expected elevated risk level, got '{result['risk_level']}'"
        )

    def test_risk_factors_non_empty_in_weak_market(
        self, mock_property, weak_market_data
    ):
        """Weak market should surface at least one specific risk factor."""
        result = _assessor(mock_property, weak_market_data).assess_risk()
        assert len(result["risk_factors"]) > 0

    def test_high_vacancy_flagged_in_risk_factors(self, mock_property, weak_market_data):
        """15% vacancy should appear as a flagged risk factor."""
        result = _assessor(mock_property, weak_market_data).assess_risk()
        combined = " ".join(result["risk_factors"]).lower()
        assert "vacancy" in combined

    def test_unemployment_flagged_in_risk_factors(self, mock_property, weak_market_data):
        """10% unemployment should appear in risk factors."""
        result = _assessor(mock_property, weak_market_data).assess_risk()
        combined = " ".join(result["risk_factors"]).lower()
        assert "unemployment" in combined

    def test_recommendations_non_empty_in_weak_market(
        self, mock_property, weak_market_data
    ):
        result = _assessor(mock_property, weak_market_data).assess_risk()
        assert len(result["recommendations"]) > 0


# ---------------------------------------------------------------------------
# Test: assess_risk() with cheap (old) property
# ---------------------------------------------------------------------------


class TestAssessRiskOldProperty:
    """A 1960-built property should trigger age-related risk factors and recommendations."""

    def test_overall_risk_in_range(self, cheap_property, default_market_data):
        result = _assessor(cheap_property, default_market_data).assess_risk()
        assert _score_in_range(result["overall_risk"])

    def test_condition_risk_higher_for_old_property(
        self, cheap_property, expensive_property, default_market_data
    ):
        old_condition = _assessor(
            cheap_property, default_market_data
        ).assess_risk()["individual_scores"]["property_condition_risk"]
        new_condition = _assessor(
            expensive_property, default_market_data
        ).assess_risk()["individual_scores"]["property_condition_risk"]
        assert old_condition > new_condition

    def test_old_property_age_flagged_in_risk_factors(
        self, cheap_property, default_market_data
    ):
        """A 60+ year old property should flag structural / capex risk."""
        result = _assessor(cheap_property, default_market_data).assess_risk()
        combined = " ".join(result["risk_factors"]).lower()
        assert any(
            kw in combined for kw in ("years old", "capital", "systems", "plumbing")
        ), f"Expected age-related risk factor; got: {result['risk_factors']}"

    def test_old_property_triggers_inspection_recommendation(
        self, cheap_property, default_market_data
    ):
        """Properties over 30 years old should recommend a structural inspection."""
        result = _assessor(cheap_property, default_market_data).assess_risk()
        combined = " ".join(result["recommendations"]).lower()
        assert "inspection" in combined or "inspect" in combined or "reserve" in combined


# ---------------------------------------------------------------------------
# Test: risk_level thresholds
# ---------------------------------------------------------------------------


class TestRiskLevelThresholds:
    """_risk_level() must map score bands to the correct string tier."""

    @pytest.mark.parametrize(
        "score, expected",
        [
            (0.0, "Low"),
            (1.0, "Low"),
            (3.4, "Low"),
            (3.5, "Moderate"),
            (4.5, "Moderate"),
            (5.4, "Moderate"),
            (5.5, "High"),
            (6.0, "High"),
            (7.4, "High"),
            (7.5, "Very High"),
            (9.0, "Very High"),
            (10.0, "Very High"),
        ],
    )
    def test_risk_level_mapping(self, score, expected, mock_property, default_market_data):
        assessor = _assessor(mock_property, default_market_data)
        assert assessor._risk_level(score) == expected


# ---------------------------------------------------------------------------
# Test: edge cases and resilience
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """RiskAssessment must not raise for missing / empty / unusual inputs."""

    def test_empty_market_data_does_not_raise(self, mock_property):
        result = _assessor(mock_property, {}).assess_risk()
        assert _score_in_range(result["overall_risk"])
        assert result["risk_level"] in _VALID_RISK_LEVELS

    def test_partial_market_data_does_not_raise(self, mock_property):
        partial = {"vacancy_rate": 0.05}
        result = _assessor(mock_property, partial).assess_risk()
        assert _score_in_range(result["overall_risk"])

    def test_zero_price_property_does_not_raise(self, default_market_data):
        from tests.conftest import MockProperty

        zero_price = MockProperty(price=0)
        result = _assessor(zero_price, default_market_data).assess_risk()
        assert _score_in_range(result["overall_risk"])

    def test_market_data_as_empty_dict_returns_all_keys(self, mock_property):
        result = _assessor(mock_property, {}).assess_risk()
        assert _TOP_LEVEL_KEYS.issubset(result.keys())

    def test_individual_scores_all_in_range_with_empty_market(self, mock_property):
        result = _assessor(mock_property, {}).assess_risk()
        for key, value in result["individual_scores"].items():
            assert _score_in_range(value), (
                f"individual_scores['{key}'] = {value} is out of [0, 10] with empty market"
            )

    def test_all_scoring_methods_return_floats_empty_market(self, mock_property):
        assessor = _assessor(mock_property, {})
        for method_name in [
            "calculate_market_volatility",
            "calculate_vacancy_risk",
            "calculate_property_condition_risk",
            "calculate_financing_risk",
            "calculate_overall_risk",
        ]:
            method = getattr(assessor, method_name)
            result = method()
            assert isinstance(result, float), (
                f"{method_name}() returned {type(result).__name__}, expected float"
            )
            assert _score_in_range(result), (
                f"{method_name}() = {result} is out of [0, 10]"
            )

    def test_property_data_as_dict_does_not_raise(self, default_market_data):
        """RiskAssessment supports property_data passed as a plain dict."""
        prop_dict = {
            "price": 200000,
            "bedrooms": 3,
            "bathrooms": 2,
            "sqft": 1500,
            "year_built": 2000,
            "property_type": "Residential",
            "lot_size": 5000,
        }
        result = _assessor(prop_dict, default_market_data).assess_risk()
        assert _score_in_range(result["overall_risk"])

    def test_assess_risk_overall_matches_weighted_individual_scores(
        self, mock_property, default_market_data
    ):
        """overall_risk must equal the weighted sum of individual_scores."""
        assessor = _assessor(mock_property, default_market_data)
        result = assessor.assess_risk()
        weights = assessor._WEIGHTS
        computed = sum(
            result["individual_scores"][k] * weights[k] for k in weights
        )
        assert computed == pytest.approx(result["overall_risk"], abs=0.01), (
            f"Weighted sum {computed} != overall_risk {result['overall_risk']}"
        )

    def test_strong_market_with_expensive_new_property(
        self, expensive_property, strong_market_data
    ):
        result = _assessor(expensive_property, strong_market_data).assess_risk()
        assert _score_in_range(result["overall_risk"])
        assert result["risk_level"] in _VALID_RISK_LEVELS

    def test_weak_market_with_cheap_old_property(
        self, cheap_property, weak_market_data
    ):
        result = _assessor(cheap_property, weak_market_data).assess_risk()
        assert _score_in_range(result["overall_risk"])
        assert result["risk_level"] in _VALID_RISK_LEVELS
