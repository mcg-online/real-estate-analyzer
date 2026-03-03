"""Opportunity scoring module for real estate investment analysis.

Produces a composite 0-100 investment score across four weighted categories:
financial metrics (40%), market fundamentals (30%), risk factors (20%),
and tax/financing advantages (10%).
"""

import logging
from datetime import datetime
from typing import Any

from services.analysis.financial_metrics import FinancialMetrics

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1.0)
# ---------------------------------------------------------------------------
WEIGHT_FINANCIAL: float = 0.40
WEIGHT_MARKET: float = 0.30
WEIGHT_RISK: float = 0.20
WEIGHT_TAX_FINANCING: float = 0.10

# ---------------------------------------------------------------------------
# Grade thresholds (inclusive lower bound)
# ---------------------------------------------------------------------------
_GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (90.0, "A+"),
    (80.0, "A"),
    (70.0, "B"),
    (60.0, "C"),
    (50.0, "D"),
    (0.0, "F"),
]

# ---------------------------------------------------------------------------
# Default analysis parameters
# ---------------------------------------------------------------------------
_DEFAULT_DOWN_PAYMENT: float = 0.20
_DEFAULT_INTEREST_RATE: float = 0.045
_DEFAULT_TERM_YEARS: int = 30
_DEFAULT_HOLDING_PERIOD: int = 5
_DEFAULT_TAX_BRACKET: float = 0.22

# ---------------------------------------------------------------------------
# Reference benchmarks used in normalisation
# ---------------------------------------------------------------------------
_BENCHMARK_CAP_RATE_EXCELLENT: float = 10.0   # % – anything at or above scores 100
_BENCHMARK_CAP_RATE_POOR: float = 2.0         # % – anything at or below scores 0

_BENCHMARK_CASH_FLOW_EXCELLENT: float = 500.0  # $/month – positive cash flow ceiling
_BENCHMARK_CASH_FLOW_POOR: float = -500.0      # $/month – deeply negative floor

_BENCHMARK_COC_EXCELLENT: float = 12.0         # % cash-on-cash return
_BENCHMARK_COC_POOR: float = -5.0

_BENCHMARK_ANNUALIZED_ROI_EXCELLENT: float = 15.0  # %
_BENCHMARK_ANNUALIZED_ROI_POOR: float = 0.0

_BENCHMARK_APPRECIATION_EXCELLENT: float = 0.06   # 6 % annual appreciation
_BENCHMARK_APPRECIATION_POOR: float = 0.00

_BENCHMARK_VACANCY_EXCELLENT: float = 0.03    # 3 % vacancy rate is excellent
_BENCHMARK_VACANCY_POOR: float = 0.15         # 15 % vacancy rate is poor

_BENCHMARK_RENT_GROWTH_EXCELLENT: float = 0.05   # 5 % annual rent growth
_BENCHMARK_RENT_GROWTH_POOR: float = 0.00

_BENCHMARK_DOM_EXCELLENT: float = 15.0   # days on market – low = healthy demand
_BENCHMARK_DOM_POOR: float = 90.0

_BENCHMARK_PRICE_TO_RENT_EXCELLENT: float = 10.0  # lower ratio = better rental value
_BENCHMARK_PRICE_TO_RENT_POOR: float = 25.0

_BENCHMARK_PROPERTY_AGE_EXCELLENT: float = 5.0    # years old
_BENCHMARK_PROPERTY_AGE_POOR: float = 60.0

_BENCHMARK_WALK_SCORE_EXCELLENT: float = 90.0
_BENCHMARK_WALK_SCORE_POOR: float = 20.0

_BENCHMARK_SCHOOL_RATING_EXCELLENT: float = 9.0   # out of 10
_BENCHMARK_SCHOOL_RATING_POOR: float = 3.0

_BENCHMARK_CRIME_RATING_EXCELLENT: float = 9.0    # higher = safer
_BENCHMARK_CRIME_RATING_POOR: float = 3.0

_BENCHMARK_ANNUAL_TAX_SAVINGS_EXCELLENT: float = 8000.0   # $
_BENCHMARK_ANNUAL_TAX_SAVINGS_POOR: float = 0.0

_BENCHMARK_FINANCING_RATE_EXCELLENT: float = 0.03   # 3 % interest rate
_BENCHMARK_FINANCING_RATE_POOR: float = 0.08        # 8 % interest rate


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Return *value* clamped to [low, high]."""
    return max(low, min(high, float(value)))


def _linear_score(
    value: float,
    poor: float,
    excellent: float,
) -> float:
    """Map *value* linearly onto [0, 100] given *poor* and *excellent* anchors.

    Works whether excellent > poor (higher-is-better) or excellent < poor
    (lower-is-better), because the direction is derived automatically.

    Args:
        value: The raw metric value to score.
        poor: The anchor value that produces a score of 0.
        excellent: The anchor value that produces a score of 100.

    Returns:
        A float in [0.0, 100.0].
    """
    if excellent == poor:
        return 50.0
    raw = (value - poor) / (excellent - poor) * 100.0
    return _clamp(raw)


def _assign_grade(score: float) -> str:
    """Return a letter grade for a composite score in [0, 100].

    Args:
        score: Composite opportunity score.

    Returns:
        A letter grade string such as "A+", "A", "B", "C", "D", or "F".
    """
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


class OpportunityScoring:
    """Score a real estate investment opportunity on a 0-100 composite scale.

    The composite score is produced by weighting four independent category
    scores:

    - Financial metrics  – 40 %
    - Market fundamentals – 30 %
    - Risk factors        – 20 %
    - Tax / financing     – 10 %

    Each category returns a float in [0, 100].  The weighted sum is the
    ``overall_score`` returned by :meth:`calculate_score`.

    Example::

        scorer = OpportunityScoring(property_obj, market_dict)
        result = scorer.calculate_score()
        print(result["overall_score"], result["grade"])

    Args:
        property_data: A :class:`~models.property.Property` instance (or any
            object exposing ``price``, ``bedrooms``, ``bathrooms``, ``sqft``,
            ``year_built``, ``property_type``, and ``lot_size`` attributes).
        market_data: A ``dict`` containing market-level metrics.  All keys are
            optional; sensible defaults are applied when a key is absent.
    """

    def __init__(self, property_data: Any, market_data: dict[str, Any]) -> None:
        self.property = property_data
        self.market = market_data

        # Run financial analysis once so all scoring methods share the result.
        self._financial_metrics = FinancialMetrics(property_data, market_data)
        self._financial_analysis: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_financial_analysis(self) -> dict[str, Any]:
        """Return (and lazily compute) the full financial analysis result.

        Returns:
            The dict produced by :meth:`~FinancialMetrics.analyze_property`.
        """
        if self._financial_analysis is None:
            self._financial_analysis = self._financial_metrics.analyze_property(
                down_payment_percentage=_DEFAULT_DOWN_PAYMENT,
                interest_rate=_DEFAULT_INTEREST_RATE,
                term_years=_DEFAULT_TERM_YEARS,
                holding_period=_DEFAULT_HOLDING_PERIOD,
                appreciation_rate=self.market.get(
                    "appreciation_rate", 0.03
                ),
            )
        return self._financial_analysis

    def _current_year(self) -> int:
        """Return the current calendar year."""
        return datetime.now().year

    # ------------------------------------------------------------------
    # Category 1 – Financial metrics (weight: 40 %)
    # ------------------------------------------------------------------

    def score_financial_metrics(self) -> float:
        """Score the financial characteristics of the investment.

        Sub-metrics and their relative contribution within the category:

        - Cap rate            – 35 %
        - Monthly cash flow   – 30 %
        - Cash-on-cash return – 20 %
        - Annualised ROI      – 15 %

        Returns:
            A float in [0.0, 100.0] representing the financial score.
        """
        analysis = self._get_financial_analysis()

        cap_rate: float = analysis.get("cap_rate", 0.0)
        monthly_cash_flow: float = analysis.get("monthly_cash_flow", 0.0)
        cash_on_cash: float = analysis.get("cash_on_cash_return", 0.0)
        annualised_roi: float = analysis.get("roi", {}).get("annualized_roi", 0.0)

        cap_rate_score = _linear_score(
            cap_rate,
            poor=_BENCHMARK_CAP_RATE_POOR,
            excellent=_BENCHMARK_CAP_RATE_EXCELLENT,
        )
        cash_flow_score = _linear_score(
            monthly_cash_flow,
            poor=_BENCHMARK_CASH_FLOW_POOR,
            excellent=_BENCHMARK_CASH_FLOW_EXCELLENT,
        )
        coc_score = _linear_score(
            cash_on_cash,
            poor=_BENCHMARK_COC_POOR,
            excellent=_BENCHMARK_COC_EXCELLENT,
        )
        roi_score = _linear_score(
            annualised_roi,
            poor=_BENCHMARK_ANNUALIZED_ROI_POOR,
            excellent=_BENCHMARK_ANNUALIZED_ROI_EXCELLENT,
        )

        financial_score = (
            cap_rate_score * 0.35
            + cash_flow_score * 0.30
            + coc_score * 0.20
            + roi_score * 0.15
        )

        logger.debug(
            "Financial score breakdown – cap_rate=%.1f cash_flow=%.1f "
            "coc=%.1f roi=%.1f  -> composite=%.2f",
            cap_rate_score,
            cash_flow_score,
            coc_score,
            roi_score,
            financial_score,
        )
        return _clamp(financial_score)

    # ------------------------------------------------------------------
    # Category 2 – Market fundamentals (weight: 30 %)
    # ------------------------------------------------------------------

    def score_market_fundamentals(self) -> float:
        """Score the underlying market conditions for this investment.

        Sub-metrics and their relative contribution within the category:

        - Appreciation rate      – 30 %
        - Vacancy rate           – 25 %
        - Rent growth rate       – 20 %
        - Days on market         – 15 %
        - Price-to-rent ratio    – 10 %

        Returns:
            A float in [0.0, 100.0] representing the market fundamentals score.
        """
        appreciation_rate: float = self.market.get("appreciation_rate", 0.03)
        vacancy_rate: float = self.market.get("vacancy_rate", 0.08)
        rent_growth: float = self.market.get("rent_growth_rate", 0.03)
        days_on_market: float = self.market.get("days_on_market", 30.0)
        price_to_rent: float = self.market.get("price_to_rent_ratio", 15.0)

        appreciation_score = _linear_score(
            appreciation_rate,
            poor=_BENCHMARK_APPRECIATION_POOR,
            excellent=_BENCHMARK_APPRECIATION_EXCELLENT,
        )
        vacancy_score = _linear_score(
            vacancy_rate,
            # Lower vacancy is better, so poor/excellent are swapped
            poor=_BENCHMARK_VACANCY_POOR,
            excellent=_BENCHMARK_VACANCY_EXCELLENT,
        )
        rent_growth_score = _linear_score(
            rent_growth,
            poor=_BENCHMARK_RENT_GROWTH_POOR,
            excellent=_BENCHMARK_RENT_GROWTH_EXCELLENT,
        )
        dom_score = _linear_score(
            days_on_market,
            # Fewer days on market is better
            poor=_BENCHMARK_DOM_POOR,
            excellent=_BENCHMARK_DOM_EXCELLENT,
        )
        ptr_score = _linear_score(
            price_to_rent,
            # Lower price-to-rent ratio means stronger rental demand
            poor=_BENCHMARK_PRICE_TO_RENT_POOR,
            excellent=_BENCHMARK_PRICE_TO_RENT_EXCELLENT,
        )

        market_score = (
            appreciation_score * 0.30
            + vacancy_score * 0.25
            + rent_growth_score * 0.20
            + dom_score * 0.15
            + ptr_score * 0.10
        )

        logger.debug(
            "Market score breakdown – appreciation=%.1f vacancy=%.1f "
            "rent_growth=%.1f dom=%.1f ptr=%.1f  -> composite=%.2f",
            appreciation_score,
            vacancy_score,
            rent_growth_score,
            dom_score,
            ptr_score,
            market_score,
        )
        return _clamp(market_score)

    # ------------------------------------------------------------------
    # Category 3 – Risk factors (weight: 20 %)
    # ------------------------------------------------------------------

    def score_risk_factors(self) -> float:
        """Score the risk profile of the investment.

        Sub-metrics and their relative contribution within the category:

        - Market volatility (proxied by unemployment rate) – 30 %
        - Property age                                      – 25 %
        - Location quality (walk score, school, crime)     – 45 %
            - Walk score       – 15 %
            - School rating    – 15 %
            - Crime rating     – 15 %

        Returns:
            A float in [0.0, 100.0] where higher means *lower* risk (better).
        """
        # -- Market volatility proxy -----------------------------------------
        # A low unemployment rate signals a stable labour market and lower risk.
        unemployment_rate: float = self.market.get("unemployment_rate", 0.05)
        # Map 0 % → 100, 15 % → 0
        volatility_score = _linear_score(
            unemployment_rate,
            poor=0.15,
            excellent=0.00,
        )

        # -- Property age -------------------------------------------------------
        year_built: int | None = getattr(self.property, "year_built", None)
        if year_built and year_built > 0:
            property_age: float = float(self._current_year() - year_built)
        else:
            property_age = 20.0  # neutral assumption when unknown

        age_score = _linear_score(
            property_age,
            poor=_BENCHMARK_PROPERTY_AGE_POOR,
            excellent=_BENCHMARK_PROPERTY_AGE_EXCELLENT,
        )

        # -- Location quality ---------------------------------------------------
        walk_score: float = self.market.get("walk_score", 50.0) or 50.0
        school_rating: float = self.market.get("school_rating", 5.0) or 5.0
        crime_rating: float = self.market.get("crime_rating", 5.0) or 5.0

        walk_score_norm = _linear_score(
            walk_score,
            poor=_BENCHMARK_WALK_SCORE_POOR,
            excellent=_BENCHMARK_WALK_SCORE_EXCELLENT,
        )
        school_score_norm = _linear_score(
            school_rating,
            poor=_BENCHMARK_SCHOOL_RATING_POOR,
            excellent=_BENCHMARK_SCHOOL_RATING_EXCELLENT,
        )
        crime_score_norm = _linear_score(
            crime_rating,
            poor=_BENCHMARK_CRIME_RATING_POOR,
            excellent=_BENCHMARK_CRIME_RATING_EXCELLENT,
        )

        location_score = (
            walk_score_norm * (1 / 3)
            + school_score_norm * (1 / 3)
            + crime_score_norm * (1 / 3)
        )

        risk_score = (
            volatility_score * 0.30
            + age_score * 0.25
            + location_score * 0.45
        )

        logger.debug(
            "Risk score breakdown – volatility=%.1f age=%.1f location=%.1f "
            "(walk=%.1f school=%.1f crime=%.1f)  -> composite=%.2f",
            volatility_score,
            age_score,
            location_score,
            walk_score_norm,
            school_score_norm,
            crime_score_norm,
            risk_score,
        )
        return _clamp(risk_score)

    # ------------------------------------------------------------------
    # Category 4 – Tax benefits and financing advantages (weight: 10 %)
    # ------------------------------------------------------------------

    def score_tax_and_financing(self) -> float:
        """Score the tax and financing advantages of the investment.

        Sub-metrics and their relative contribution within the category:

        - Estimated annual tax savings – 50 %
        - Effective financing rate     – 30 %
        - Local tax incentives bonus   – 20 %

        Returns:
            A float in [0.0, 100.0] representing the tax/financing score.
        """
        # -- Tax savings --------------------------------------------------------
        # Approximate annual tax savings from depreciation + mortgage interest.
        # Use the same inputs as TaxBenefits.analyze_tax_benefits but without
        # importing that class to avoid circular dependencies.
        price: float = getattr(self.property, "price", 0.0)
        loan_amount: float = price * (1 - _DEFAULT_DOWN_PAYMENT)

        # Depreciation (residential: 27.5 years, 80 % building value)
        building_value: float = price * 0.80
        annual_depreciation: float = building_value / 27.5

        # First-year mortgage interest (rough approximation)
        monthly_rate: float = _DEFAULT_INTEREST_RATE / 12
        num_payments: int = _DEFAULT_TERM_YEARS * 12
        if monthly_rate > 0:
            monthly_payment: float = (
                loan_amount
                * (monthly_rate * (1 + monthly_rate) ** num_payments)
                / ((1 + monthly_rate) ** num_payments - 1)
            )
            # First payment is almost entirely interest; use first-year sum
            first_year_interest: float = 0.0
            balance: float = loan_amount
            for _ in range(12):
                interest_pmt: float = balance * monthly_rate
                principal_pmt: float = monthly_payment - interest_pmt
                balance -= principal_pmt
                first_year_interest += interest_pmt
        else:
            first_year_interest = 0.0

        property_tax_rate: float = self.market.get("property_tax_rate", 0.01)
        annual_property_tax: float = price * property_tax_rate

        total_deductions: float = (
            annual_depreciation + first_year_interest + annual_property_tax
        )
        estimated_tax_savings: float = total_deductions * _DEFAULT_TAX_BRACKET

        tax_savings_score = _linear_score(
            estimated_tax_savings,
            poor=_BENCHMARK_ANNUAL_TAX_SAVINGS_POOR,
            excellent=_BENCHMARK_ANNUAL_TAX_SAVINGS_EXCELLENT,
        )

        # -- Financing rate -----------------------------------------------------
        # Use market-supplied current rate if available, otherwise the default.
        current_rate: float = self.market.get(
            "current_mortgage_rate", _DEFAULT_INTEREST_RATE
        )
        financing_rate_score = _linear_score(
            current_rate,
            # Lower rate is better
            poor=_BENCHMARK_FINANCING_RATE_POOR,
            excellent=_BENCHMARK_FINANCING_RATE_EXCELLENT,
        )

        # -- Local tax incentive bonus ------------------------------------------
        tax_incentives: dict[str, Any] = self.market.get("tax_benefits", {})
        bonus: float = 0.0
        if tax_incentives.get("has_opportunity_zone"):
            bonus += 25.0
        if tax_incentives.get("has_historic_tax_credits"):
            bonus += 20.0
        if tax_incentives.get("has_renovation_incentives"):
            bonus += 15.0
        if tax_incentives.get("has_homestead_exemption"):
            bonus += 10.0
        special_programs: list = tax_incentives.get("special_programs", [])
        bonus += min(len(special_programs) * 5.0, 30.0)
        incentive_score: float = _clamp(bonus)

        tax_financing_score = (
            tax_savings_score * 0.50
            + financing_rate_score * 0.30
            + incentive_score * 0.20
        )

        logger.debug(
            "Tax/financing score breakdown – tax_savings=%.1f financing_rate=%.1f "
            "incentives=%.1f  -> composite=%.2f",
            tax_savings_score,
            financing_rate_score,
            incentive_score,
            tax_financing_score,
        )
        return _clamp(tax_financing_score)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_score(self) -> dict[str, Any]:
        """Calculate the composite investment opportunity score.

        Runs all four category scorers, applies their weights, and returns a
        structured result dict.

        Returns:
            A ``dict`` with the following keys:

            ``overall_score`` (float)
                Composite score in [0.0, 100.0].
            ``grade`` (str)
                Letter grade derived from the overall score
                (``"A+"``, ``"A"``, ``"B"``, ``"C"``, ``"D"``, or ``"F"``).
            ``category_scores`` (dict)
                Per-category raw scores (each in [0.0, 100.0]) under:
                ``financial_metrics``, ``market_fundamentals``,
                ``risk_factors``, ``tax_and_financing``.
            ``weights`` (dict)
                The weights applied to each category.
            ``financial_analysis`` (dict)
                The raw output from :class:`~FinancialMetrics` for reference.
            ``score_breakdown`` (dict)
                Weighted contribution from each category to the overall score.
        """
        try:
            financial_score: float = self.score_financial_metrics()
        except Exception:
            logger.exception("Financial metrics scoring failed; defaulting to 0")
            financial_score = 0.0

        try:
            market_score: float = self.score_market_fundamentals()
        except Exception:
            logger.exception("Market fundamentals scoring failed; defaulting to 0")
            market_score = 0.0

        try:
            risk_score: float = self.score_risk_factors()
        except Exception:
            logger.exception("Risk factor scoring failed; defaulting to 0")
            risk_score = 0.0

        try:
            tax_financing_score: float = self.score_tax_and_financing()
        except Exception:
            logger.exception("Tax/financing scoring failed; defaulting to 0")
            tax_financing_score = 0.0

        weighted_financial: float = financial_score * WEIGHT_FINANCIAL
        weighted_market: float = market_score * WEIGHT_MARKET
        weighted_risk: float = risk_score * WEIGHT_RISK
        weighted_tax_financing: float = tax_financing_score * WEIGHT_TAX_FINANCING

        overall_score: float = _clamp(
            weighted_financial
            + weighted_market
            + weighted_risk
            + weighted_tax_financing
        )

        grade: str = _assign_grade(overall_score)

        return {
            "overall_score": round(overall_score, 2),
            "grade": grade,
            "category_scores": {
                "financial_metrics": round(financial_score, 2),
                "market_fundamentals": round(market_score, 2),
                "risk_factors": round(risk_score, 2),
                "tax_and_financing": round(tax_financing_score, 2),
            },
            "weights": {
                "financial_metrics": WEIGHT_FINANCIAL,
                "market_fundamentals": WEIGHT_MARKET,
                "risk_factors": WEIGHT_RISK,
                "tax_and_financing": WEIGHT_TAX_FINANCING,
            },
            "score_breakdown": {
                "financial_metrics": round(weighted_financial, 2),
                "market_fundamentals": round(weighted_market, 2),
                "risk_factors": round(weighted_risk, 2),
                "tax_and_financing": round(weighted_tax_financing, 2),
            },
            "financial_analysis": self._get_financial_analysis(),
        }
