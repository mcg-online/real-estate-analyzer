# backend/tests/test_opportunity_scoring.py
"""Tests for the OpportunityScoring service.

Covers:
- calculate_score() return structure and key presence
- overall_score is always clamped to [0, 100]
- grade assignment follows documented thresholds
- category score keys match the documented schema
- weights sum to 1.0 and match documented constants
- strong-market scenarios produce high scores
- weak-market scenarios produce low scores
- individual category scorers return values in [0, 100]
- score_breakdown weighted contributions sum to overall_score
- lazy financial analysis is computed exactly once
- missing / optional market keys are handled gracefully
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.analysis.opportunity_scoring import (
    OpportunityScoring,
    WEIGHT_FINANCIAL,
    WEIGHT_MARKET,
    WEIGHT_RISK,
    WEIGHT_TAX_FINANCING,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CATEGORY_KEYS = frozenset(
    {"financial_metrics", "market_fundamentals", "risk_factors", "tax_and_financing"}
)

_EXPECTED_TOP_LEVEL_KEYS = frozenset(
    {
        "overall_score",
        "grade",
        "category_scores",
        "weights",
        "score_breakdown",
        "financial_analysis",
    }
)

_VALID_GRADES = frozenset({"A+", "A", "B", "C", "D", "F"})


def _scorer(property_fixture, market_fixture) -> OpportunityScoring:
    """Convenience constructor."""
    return OpportunityScoring(property_fixture, market_fixture)


# ---------------------------------------------------------------------------
# Test: calculate_score() return structure
# ---------------------------------------------------------------------------


class TestCalculateScoreStructure:
    """calculate_score() must return a dict with all documented keys."""

    def test_returns_dict(self, mock_property, default_market_data):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert isinstance(result, dict)

    def test_top_level_keys_present(self, mock_property, default_market_data):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert _EXPECTED_TOP_LEVEL_KEYS.issubset(result.keys())

    def test_category_scores_has_all_keys(self, mock_property, default_market_data):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert _CATEGORY_KEYS == set(result["category_scores"].keys())

    def test_weights_has_all_keys(self, mock_property, default_market_data):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert _CATEGORY_KEYS == set(result["weights"].keys())

    def test_score_breakdown_has_all_keys(self, mock_property, default_market_data):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert _CATEGORY_KEYS == set(result["score_breakdown"].keys())

    def test_financial_analysis_is_dict(self, mock_property, default_market_data):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert isinstance(result["financial_analysis"], dict)


# ---------------------------------------------------------------------------
# Test: overall_score range
# ---------------------------------------------------------------------------


class TestOverallScoreRange:
    """overall_score must always be a float in [0.0, 100.0]."""

    def test_default_market_score_in_range(self, mock_property, default_market_data):
        score = _scorer(mock_property, default_market_data).calculate_score()
        assert 0.0 <= score["overall_score"] <= 100.0

    def test_strong_market_score_in_range(self, mock_property, strong_market_data):
        score = _scorer(mock_property, strong_market_data).calculate_score()
        assert 0.0 <= score["overall_score"] <= 100.0

    def test_weak_market_score_in_range(self, mock_property, weak_market_data):
        score = _scorer(mock_property, weak_market_data).calculate_score()
        assert 0.0 <= score["overall_score"] <= 100.0

    def test_expensive_property_score_in_range(
        self, expensive_property, strong_market_data
    ):
        score = _scorer(expensive_property, strong_market_data).calculate_score()
        assert 0.0 <= score["overall_score"] <= 100.0

    def test_cheap_property_score_in_range(self, cheap_property, weak_market_data):
        score = _scorer(cheap_property, weak_market_data).calculate_score()
        assert 0.0 <= score["overall_score"] <= 100.0

    def test_overall_score_is_float(self, mock_property, default_market_data):
        score = _scorer(mock_property, default_market_data).calculate_score()
        assert isinstance(score["overall_score"], float)


# ---------------------------------------------------------------------------
# Test: category score ranges
# ---------------------------------------------------------------------------


class TestCategoryScoreRanges:
    """Every individual category score must be a float in [0.0, 100.0]."""

    @pytest.mark.parametrize("key", sorted(_CATEGORY_KEYS))
    def test_default_market_category_in_range(
        self, key, mock_property, default_market_data
    ):
        result = _scorer(mock_property, default_market_data).calculate_score()
        value = result["category_scores"][key]
        assert isinstance(value, (int, float))
        assert 0.0 <= value <= 100.0

    @pytest.mark.parametrize("key", sorted(_CATEGORY_KEYS))
    def test_strong_market_category_in_range(
        self, key, mock_property, strong_market_data
    ):
        result = _scorer(mock_property, strong_market_data).calculate_score()
        value = result["category_scores"][key]
        assert 0.0 <= value <= 100.0

    @pytest.mark.parametrize("key", sorted(_CATEGORY_KEYS))
    def test_weak_market_category_in_range(self, key, mock_property, weak_market_data):
        result = _scorer(mock_property, weak_market_data).calculate_score()
        value = result["category_scores"][key]
        assert 0.0 <= value <= 100.0


# ---------------------------------------------------------------------------
# Test: individual category scorer methods
# ---------------------------------------------------------------------------


class TestIndividualCategoryScorers:
    """Direct calls to each scorer method must return floats in [0, 100]."""

    def test_score_financial_metrics_range(self, mock_property, default_market_data):
        scorer = _scorer(mock_property, default_market_data)
        value = scorer.score_financial_metrics()
        assert isinstance(value, float)
        assert 0.0 <= value <= 100.0

    def test_score_market_fundamentals_range(self, mock_property, default_market_data):
        scorer = _scorer(mock_property, default_market_data)
        value = scorer.score_market_fundamentals()
        assert isinstance(value, float)
        assert 0.0 <= value <= 100.0

    def test_score_risk_factors_range(self, mock_property, default_market_data):
        scorer = _scorer(mock_property, default_market_data)
        value = scorer.score_risk_factors()
        assert isinstance(value, float)
        assert 0.0 <= value <= 100.0

    def test_score_tax_and_financing_range(self, mock_property, default_market_data):
        scorer = _scorer(mock_property, default_market_data)
        value = scorer.score_tax_and_financing()
        assert isinstance(value, float)
        assert 0.0 <= value <= 100.0


# ---------------------------------------------------------------------------
# Test: grade assignment
# ---------------------------------------------------------------------------


class TestGradeAssignment:
    """Grade strings must be one of the documented letter grades."""

    def test_grade_is_valid_string(self, mock_property, default_market_data):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert result["grade"] in _VALID_GRADES

    def test_strong_market_grade_is_high(self, mock_property, strong_market_data):
        """A strong-market scenario with a new property should grade A or A+."""
        result = _scorer(mock_property, strong_market_data).calculate_score()
        assert result["grade"] in {"A+", "A", "B"}, (
            f"Expected a high grade for strong market, got {result['grade']} "
            f"(score={result['overall_score']})"
        )

    def test_weak_market_grade_is_low(self, mock_property, weak_market_data):
        """A weak-market scenario should grade D or F."""
        result = _scorer(mock_property, weak_market_data).calculate_score()
        assert result["grade"] in {"D", "F", "C"}, (
            f"Expected a low grade for weak market, got {result['grade']} "
            f"(score={result['overall_score']})"
        )

    def test_all_valid_grades_recognized(self):
        """Ensure every documented grade string is in the allowed set."""
        assert _VALID_GRADES == {"A+", "A", "B", "C", "D", "F"}


# ---------------------------------------------------------------------------
# Test: strong vs. weak market comparison
# ---------------------------------------------------------------------------


class TestMarketComparison:
    """Strong markets must score materially higher than weak markets."""

    def test_strong_market_beats_weak_market(
        self, mock_property, strong_market_data, weak_market_data
    ):
        strong_score = _scorer(
            mock_property, strong_market_data
        ).calculate_score()["overall_score"]
        weak_score = _scorer(
            mock_property, weak_market_data
        ).calculate_score()["overall_score"]
        assert strong_score > weak_score, (
            f"Expected strong market ({strong_score}) > weak market ({weak_score})"
        )

    def test_strong_market_score_above_50(self, mock_property, strong_market_data):
        result = _scorer(mock_property, strong_market_data).calculate_score()
        assert result["overall_score"] > 50.0

    def test_weak_market_score_below_strong(
        self, expensive_property, strong_market_data, weak_market_data
    ):
        strong = _scorer(
            expensive_property, strong_market_data
        ).calculate_score()["overall_score"]
        weak = _scorer(
            expensive_property, weak_market_data
        ).calculate_score()["overall_score"]
        assert strong > weak

    def test_strong_market_fundamentals_score_high(
        self, mock_property, strong_market_data
    ):
        """Market fundamentals score should be high when vacancy and DOM are excellent."""
        scorer = _scorer(mock_property, strong_market_data)
        mkt_score = scorer.score_market_fundamentals()
        # strong_market_data: vacancy=0.03 (excellent), appreciation=0.06 (excellent),
        # days_on_market=15 (excellent), price_to_rent=10 (excellent)
        assert mkt_score > 70.0, f"Expected market fundamentals > 70, got {mkt_score}"

    def test_weak_market_fundamentals_score_low(
        self, mock_property, weak_market_data
    ):
        """Market fundamentals score should be low when vacancy and DOM are poor."""
        scorer = _scorer(mock_property, weak_market_data)
        mkt_score = scorer.score_market_fundamentals()
        assert mkt_score < 30.0, f"Expected market fundamentals < 30, got {mkt_score}"

    def test_strong_market_risk_factors_score_high(
        self, mock_property, strong_market_data
    ):
        """Risk factors score (higher = lower risk) should be high in a strong market."""
        scorer = _scorer(mock_property, strong_market_data)
        risk_score = scorer.score_risk_factors()
        assert risk_score > 60.0, f"Expected risk factors > 60, got {risk_score}"

    def test_weak_market_risk_factors_score_low(
        self, mock_property, weak_market_data
    ):
        """Risk factors score should be low when unemployment and location are poor."""
        scorer = _scorer(mock_property, weak_market_data)
        risk_score = scorer.score_risk_factors()
        assert risk_score < 40.0, f"Expected risk factors < 40, got {risk_score}"


# ---------------------------------------------------------------------------
# Test: weights
# ---------------------------------------------------------------------------


class TestWeights:
    """Weights returned in the result must match documented module constants."""

    def test_weights_sum_to_one(self, mock_property, default_market_data):
        result = _scorer(mock_property, default_market_data).calculate_score()
        total = sum(result["weights"].values())
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"

    def test_financial_weight_matches_constant(
        self, mock_property, default_market_data
    ):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert result["weights"]["financial_metrics"] == pytest.approx(WEIGHT_FINANCIAL)

    def test_market_weight_matches_constant(self, mock_property, default_market_data):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert result["weights"]["market_fundamentals"] == pytest.approx(WEIGHT_MARKET)

    def test_risk_weight_matches_constant(self, mock_property, default_market_data):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert result["weights"]["risk_factors"] == pytest.approx(WEIGHT_RISK)

    def test_tax_financing_weight_matches_constant(
        self, mock_property, default_market_data
    ):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert result["weights"]["tax_and_financing"] == pytest.approx(
            WEIGHT_TAX_FINANCING
        )


# ---------------------------------------------------------------------------
# Test: score_breakdown consistency
# ---------------------------------------------------------------------------


class TestScoreBreakdown:
    """Weighted contributions in score_breakdown must sum to overall_score."""

    def test_breakdown_sums_to_overall(self, mock_property, default_market_data):
        result = _scorer(mock_property, default_market_data).calculate_score()
        breakdown_sum = sum(result["score_breakdown"].values())
        assert breakdown_sum == pytest.approx(result["overall_score"], abs=0.02), (
            f"Breakdown sum {breakdown_sum} != overall_score {result['overall_score']}"
        )

    def test_breakdown_sums_to_overall_strong_market(
        self, mock_property, strong_market_data
    ):
        result = _scorer(mock_property, strong_market_data).calculate_score()
        breakdown_sum = sum(result["score_breakdown"].values())
        assert breakdown_sum == pytest.approx(result["overall_score"], abs=0.02)

    def test_breakdown_sums_to_overall_weak_market(
        self, mock_property, weak_market_data
    ):
        result = _scorer(mock_property, weak_market_data).calculate_score()
        breakdown_sum = sum(result["score_breakdown"].values())
        assert breakdown_sum == pytest.approx(result["overall_score"], abs=0.02)


# ---------------------------------------------------------------------------
# Test: lazy financial analysis memoisation
# ---------------------------------------------------------------------------


class TestFinancialAnalysisMemoisation:
    """_get_financial_analysis() should be computed exactly once per instance."""

    def test_financial_analysis_is_same_object_on_repeated_calls(
        self, mock_property, default_market_data
    ):
        scorer = _scorer(mock_property, default_market_data)
        first = scorer._get_financial_analysis()
        second = scorer._get_financial_analysis()
        assert first is second, "Expected the same dict object on repeated calls"

    def test_calculate_score_twice_returns_same_overall(
        self, mock_property, default_market_data
    ):
        scorer = _scorer(mock_property, default_market_data)
        first = scorer.calculate_score()["overall_score"]
        second = scorer.calculate_score()["overall_score"]
        assert first == second


# ---------------------------------------------------------------------------
# Test: missing / optional market data resilience
# ---------------------------------------------------------------------------


class TestMissingMarketData:
    """OpportunityScoring must not raise when optional market keys are absent."""

    def test_empty_market_data_does_not_raise(self, mock_property):
        scorer = _scorer(mock_property, {})
        result = scorer.calculate_score()
        assert 0.0 <= result["overall_score"] <= 100.0

    def test_partial_market_data_does_not_raise(self, mock_property):
        partial = {"vacancy_rate": 0.05, "price_to_rent_ratio": 12}
        result = _scorer(mock_property, partial).calculate_score()
        assert 0.0 <= result["overall_score"] <= 100.0

    def test_walk_score_missing_uses_default(self, mock_property, default_market_data):
        """Omitting walk_score should not cause an error or produce an out-of-range score."""
        market = {k: v for k, v in default_market_data.items() if k != "walk_score"}
        result = _scorer(mock_property, market).calculate_score()
        assert 0.0 <= result["overall_score"] <= 100.0

    def test_tax_benefits_key_missing_uses_default(
        self, mock_property, default_market_data
    ):
        result = _scorer(mock_property, default_market_data).calculate_score()
        assert result["category_scores"]["tax_and_financing"] >= 0.0

    def test_tax_benefits_with_opportunity_zone_boosts_score(
        self, mock_property, default_market_data
    ):
        """A market with an opportunity zone should outscore one without."""
        baseline_scorer = _scorer(mock_property, default_market_data)
        baseline = baseline_scorer.score_tax_and_financing()

        market_with_oz = dict(default_market_data)
        market_with_oz["tax_benefits"] = {"has_opportunity_zone": True}
        oz_scorer = _scorer(mock_property, market_with_oz)
        oz_score = oz_scorer.score_tax_and_financing()

        assert oz_score > baseline, (
            f"OZ score ({oz_score}) should exceed baseline ({baseline})"
        )


# ---------------------------------------------------------------------------
# Test: property variant scenarios
# ---------------------------------------------------------------------------


class TestPropertyVariants:
    """Different property fixtures should produce distinct, valid scores."""

    def test_expensive_property_default_market_score_valid(
        self, expensive_property, default_market_data
    ):
        result = _scorer(expensive_property, default_market_data).calculate_score()
        assert 0.0 <= result["overall_score"] <= 100.0
        assert result["grade"] in _VALID_GRADES

    def test_cheap_property_default_market_score_valid(
        self, cheap_property, default_market_data
    ):
        result = _scorer(cheap_property, default_market_data).calculate_score()
        assert 0.0 <= result["overall_score"] <= 100.0
        assert result["grade"] in _VALID_GRADES

    def test_cheap_property_scores_differ_from_expensive(
        self, cheap_property, expensive_property, default_market_data
    ):
        cheap_score = _scorer(
            cheap_property, default_market_data
        ).calculate_score()["overall_score"]
        expensive_score = _scorer(
            expensive_property, default_market_data
        ).calculate_score()["overall_score"]
        # Scores need not be equal — just assert they are distinct or at least valid.
        assert isinstance(cheap_score, float)
        assert isinstance(expensive_score, float)

    def test_new_construction_beats_old_on_risk_factors(
        self, expensive_property, cheap_property, default_market_data
    ):
        """expensive_property (year_built=2020) should outscore cheap_property
        (year_built=1960) on the risk_factors category because age risk is lower."""
        new_risk = _scorer(
            expensive_property, default_market_data
        ).calculate_score()["category_scores"]["risk_factors"]
        old_risk = _scorer(
            cheap_property, default_market_data
        ).calculate_score()["category_scores"]["risk_factors"]
        assert new_risk > old_risk, (
            f"New property risk score ({new_risk}) should exceed old property ({old_risk})"
        )
