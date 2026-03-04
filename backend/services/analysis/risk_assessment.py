"""Real estate investment risk assessment service.

Evaluates investment risk across four dimensions—market volatility, vacancy,
property condition, and financing—then synthesises them into a weighted
composite score and human-readable report.
"""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Custom exception hierarchy
# ---------------------------------------------------------------------------

class RiskAssessmentError(Exception):
    """Base exception for all risk assessment failures."""


class InsufficientDataError(RiskAssessmentError):
    """Raised when required data fields are missing or unusable."""


# ---------------------------------------------------------------------------
# Score helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    """Clamp *value* to the closed interval [*lo*, *hi*]."""
    return max(lo, min(hi, value))


def _coefficient_of_variation(values: list[float]) -> float:
    """Return the coefficient of variation (std / mean) for *values*.

    Returns 0.0 when the mean is zero or *values* has fewer than two
    elements so callers never receive a division-by-zero error.
    """
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    if mean == 0.0:
        return 0.0
    return statistics.stdev(values) / mean


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class RiskAssessment:
    """Assess investment risk for a single real estate property.

    All scoring methods return a float on the 0-10 scale where **10 is the
    highest risk**.  The :meth:`assess_risk` method returns a complete report
    dictionary suitable for direct serialisation to JSON.

    Args:
        property_data: A :class:`~models.property.Property` instance **or**
            any object that exposes the following attributes: ``price``,
            ``bedrooms``, ``bathrooms``, ``sqft``, ``year_built``,
            ``property_type``, ``lot_size``.
        market_data: A ``dict`` (or dict-like object) with any subset of the
            following keys: ``vacancy_rate``, ``days_on_market``,
            ``appreciation_rate``, ``property_tax_rate``,
            ``price_history`` (``list[float]``), ``price_to_rent_ratio``,
            ``unemployment_rate``, ``median_income``, ``crime_rating``,
            ``school_rating``.
    """

    # ------------------------------------------------------------------
    # Weight configuration for the overall composite score.
    # Values must sum to 1.0.
    # ------------------------------------------------------------------
    _WEIGHTS: dict[str, float] = {
        "market_volatility": 0.30,
        "vacancy_risk": 0.25,
        "property_condition_risk": 0.20,
        "financing_risk": 0.25,
    }

    # Property types treated as higher-risk (older construction norms,
    # narrower buyer / renter pools, elevated maintenance complexity).
    _HIGHER_RISK_PROPERTY_TYPES: frozenset[str] = frozenset(
        {"mobile home", "manufactured", "co-op", "land", "farm", "commercial"}
    )

    @staticmethod
    def _current_year() -> int:
        """Return the current calendar year (evaluated at call time)."""
        return datetime.now().year

    def __init__(self, property_data: Any, market_data: dict[str, Any]) -> None:
        self.property = property_data
        self.market = market_data

    # ------------------------------------------------------------------
    # Private attribute-access helpers
    # ------------------------------------------------------------------

    def _prop(self, attr: str, default: Any = None) -> Any:
        """Return *property_data* attribute, falling back to *default*."""
        if isinstance(self.property, dict):
            return self.property.get(attr, default)
        return getattr(self.property, attr, default)

    def _mkt(self, key: str, default: Any = None) -> Any:
        """Return *market_data* value for *key*, falling back to *default*."""
        if isinstance(self.market, dict):
            return self.market.get(key, default)
        return getattr(self.market, key, default)

    # ------------------------------------------------------------------
    # Individual risk factor methods
    # ------------------------------------------------------------------

    def calculate_market_volatility(self) -> float:
        """Calculate market price-history volatility risk.

        Two independent signals are combined with equal weight:

        1. **Price-history CV** – the coefficient of variation of the
           ``price_history`` list.  A CV above 0.30 maps to the maximum
           score of 10.
        2. **Appreciation-rate deviation** – how far ``appreciation_rate``
           departs from a healthy 3 % annual norm.  Negative appreciation
           (depreciation) or rates above 10 % both indicate elevated risk
           (overheating markets reverse sharply).

        Returns:
            Risk score in [0, 10].  Higher means more volatile / risky.
        """
        price_history: list[float] = self._mkt("price_history", [])
        appreciation_rate: float = float(self._mkt("appreciation_rate", 0.03) or 0.03)

        # --- Signal 1: price history coefficient of variation ----------
        if price_history and len(price_history) >= 2:
            cv = _coefficient_of_variation([float(p) for p in price_history])
            # CV of 0.30 or more → score 10; CV of 0 → score 0.
            cv_score = _clamp(cv / 0.30 * 10.0)
        else:
            # No history available: assign a neutral-high default (5.0).
            cv_score = 5.0

        # --- Signal 2: appreciation rate deviation ----------------------
        # Ideal band: 2 %–5 %.  Penalty grows outside that band.
        ideal_rate = 0.03
        deviation = abs(appreciation_rate - ideal_rate)

        if appreciation_rate < 0:
            # Depreciation: strong negative signal — score jumps to at least 7.
            appreciation_score = _clamp(7.0 + abs(appreciation_rate) * 30.0)
        elif appreciation_rate > 0.10:
            # Overheating market: elevated reversal risk.
            appreciation_score = _clamp(6.0 + (appreciation_rate - 0.10) * 40.0)
        else:
            # Within reasonable range: scale deviation linearly.
            appreciation_score = _clamp(deviation / 0.05 * 5.0)

        combined = (cv_score + appreciation_score) / 2.0
        return round(_clamp(combined), 2)

    def calculate_vacancy_risk(self) -> float:
        """Calculate risk based on local vacancy and days-on-market trends.

        Two signals are combined with equal weight:

        1. **Vacancy rate** – national average is roughly 7–8 %.
           Rates above 15 % indicate a structurally weak rental market.
        2. **Days on market** – properties sitting longer than 60 days
           signal weak demand.

        Returns:
            Risk score in [0, 10].
        """
        vacancy_rate: float = float(self._mkt("vacancy_rate", 0.08) or 0.08)
        days_on_market: float = float(self._mkt("days_on_market", 30) or 30)

        # Vacancy rate: 0 % → 0, 15 %+ → 10
        vacancy_score = _clamp(vacancy_rate / 0.15 * 10.0)

        # Days on market: 0 days → 0, 90+ days → 10
        dom_score = _clamp(days_on_market / 90.0 * 10.0)

        # Unemployment rate lifts vacancy risk further when elevated.
        unemployment_rate: float = float(self._mkt("unemployment_rate", 0.04) or 0.04)
        # National "full employment" threshold ≈ 4 %.  Each extra percentage
        # point above 4 % adds 0.5 to the score.
        unemployment_penalty = _clamp(max(0.0, unemployment_rate - 0.04) * 50.0, 0.0, 2.0)

        combined = (vacancy_score + dom_score) / 2.0 + unemployment_penalty
        return round(_clamp(combined), 2)

    def calculate_property_condition_risk(self) -> float:
        """Calculate risk from property age, type, and structural indicators.

        Three signals are combined:

        1. **Property age** – older buildings carry higher maintenance
           burden and code-compliance exposure.
        2. **Property type** – certain asset classes (mobile/manufactured,
           land, co-ops) carry structurally higher risk.
        3. **Price-per-square-foot outlier** – extreme deviation from a
           typical range signals either a distressed asset (very low) or
           an overpriced listing (very high).

        Returns:
            Risk score in [0, 10].
        """
        year_built: int | None = self._prop("year_built")
        property_type: str = str(self._prop("property_type", "single family") or "single family").lower()
        price: float = float(self._prop("price", 0) or 0)
        sqft: float = float(self._prop("sqft", 0) or 0)

        # --- Signal 1: age risk -----------------------------------------
        if year_built:
            age = max(0, self._current_year() - int(year_built))
            # Properties up to 10 years old: minimal risk (0–1).
            # 10–30 years: low-moderate (1–4).
            # 30–60 years: moderate-high (4–7).
            # 60+ years: high (7–10).
            if age <= 10:
                age_score = age / 10.0
            elif age <= 30:
                age_score = 1.0 + (age - 10) / 20.0 * 3.0
            elif age <= 60:
                age_score = 4.0 + (age - 30) / 30.0 * 3.0
            else:
                age_score = _clamp(7.0 + (age - 60) / 40.0 * 3.0)
        else:
            # Unknown age: assign a conservative default.
            age_score = 5.0

        # --- Signal 2: property type risk --------------------------------
        type_score = (
            7.0
            if any(hrt in property_type for hrt in self._HIGHER_RISK_PROPERTY_TYPES)
            else 3.0
            if property_type in {"condo", "townhouse", "multi-family", "duplex", "triplex"}
            else 2.0  # single-family, house — baseline
        )

        # --- Signal 3: price-per-sqft outlier ---------------------------
        if price > 0 and sqft > 0:
            price_per_sqft = price / sqft
            # Typical range for US residential: $80–$500 / sqft.
            # Outside this range → possible distress or overvaluation.
            if price_per_sqft < 50:
                ppsf_score = 8.0  # Very cheap — likely distress.
            elif price_per_sqft < 80:
                ppsf_score = 5.0
            elif price_per_sqft <= 500:
                ppsf_score = 1.0  # Normal range.
            elif price_per_sqft <= 800:
                ppsf_score = 4.0
            else:
                ppsf_score = 7.0  # Very expensive — liquidity risk.
        else:
            ppsf_score = 5.0  # Unknown — neutral-high default.

        # Weighted combination: age carries most weight.
        combined = age_score * 0.50 + type_score * 0.35 + ppsf_score * 0.15
        return round(_clamp(combined), 2)

    def calculate_financing_risk(self) -> float:
        """Calculate risk related to financing, leverage, and interest rates.

        Three signals are combined:

        1. **Loan-to-value (LTV)** derived from ``down_payment_percentage``
           in market data (defaults to 20 %).  Higher LTV = more leverage =
           more risk.
        2. **Interest rate sensitivity** – rates above 7 % materially
           compress cash flows and buyer pools.
        3. **Debt-service coverage ratio (DSCR)** – estimated from the
           market's price-to-rent ratio.  A DSCR below 1.0 means the
           property cannot service its own debt from rental income.

        Returns:
            Risk score in [0, 10].
        """
        down_payment_pct: float = float(
            self._mkt("down_payment_percentage", 0.20) or 0.20
        )
        interest_rate: float = float(
            self._mkt("interest_rate", 0.07) or 0.07
        )
        price_to_rent_ratio: float = float(
            self._mkt("price_to_rent_ratio", 15) or 15
        )
        property_price: float = float(self._prop("price", 0) or 0)

        # --- Signal 1: LTV risk ------------------------------------------
        # LTV = 1 - down_payment_pct.
        # LTV ≤ 60 % → score 1; LTV = 80 % (standard) → score 4;
        # LTV = 95 %+ → score 10.
        ltv = 1.0 - down_payment_pct
        if ltv <= 0.60:
            ltv_score = 1.0
        elif ltv <= 0.80:
            ltv_score = 1.0 + (ltv - 0.60) / 0.20 * 3.0
        elif ltv <= 0.95:
            ltv_score = 4.0 + (ltv - 0.80) / 0.15 * 5.0
        else:
            ltv_score = 10.0

        # --- Signal 2: interest rate risk --------------------------------
        # 3–4 % → minimal risk; 7 %+ → significant cash-flow pressure.
        if interest_rate <= 0.04:
            rate_score = 1.0
        elif interest_rate <= 0.06:
            rate_score = 1.0 + (interest_rate - 0.04) / 0.02 * 3.0
        elif interest_rate <= 0.08:
            rate_score = 4.0 + (interest_rate - 0.06) / 0.02 * 4.0
        else:
            rate_score = _clamp(8.0 + (interest_rate - 0.08) / 0.02 * 2.0)

        # --- Signal 3: DSCR estimate ------------------------------------
        # Gross rent yield ≈ 1 / price_to_rent_ratio (annual).
        # Simplified DSCR = gross rent yield / mortgage constant.
        # Mortgage constant for 30-yr loan ≈ interest_rate * 1.15 (rough).
        if property_price > 0 and price_to_rent_ratio > 0:
            annual_rent_yield = 1.0 / price_to_rent_ratio
            # Effective expense ratio (tax, insurance, mgmt, vacancy) ≈ 40 %.
            noi_yield = annual_rent_yield * 0.60
            mortgage_constant = interest_rate * 1.15 * ltv  # annual debt / price
            if mortgage_constant > 0:
                dscr = noi_yield / mortgage_constant
            else:
                dscr = 99.0  # all-cash — no debt risk
        else:
            dscr = 1.0  # unknown — neutral

        # DSCR ≥ 1.25 → low risk (score 1); < 1.0 → high risk (score 8+).
        if dscr >= 1.25:
            dscr_score = 1.0
        elif dscr >= 1.0:
            dscr_score = 1.0 + (1.25 - dscr) / 0.25 * 4.0
        elif dscr >= 0.75:
            dscr_score = 5.0 + (1.0 - dscr) / 0.25 * 3.0
        else:
            dscr_score = _clamp(8.0 + (0.75 - dscr) / 0.75 * 2.0)

        combined = ltv_score * 0.35 + rate_score * 0.35 + dscr_score * 0.30
        return round(_clamp(combined), 2)

    def calculate_overall_risk(self) -> float:
        """Compute weighted composite risk score across all four dimensions.

        Weights are defined in :attr:`_WEIGHTS` and sum to 1.0.

        Returns:
            Composite risk score in [0, 10].
        """
        scores = {
            "market_volatility": self.calculate_market_volatility(),
            "vacancy_risk": self.calculate_vacancy_risk(),
            "property_condition_risk": self.calculate_property_condition_risk(),
            "financing_risk": self.calculate_financing_risk(),
        }
        overall = sum(
            scores[factor] * weight for factor, weight in self._WEIGHTS.items()
        )
        return round(_clamp(overall), 2)

    # ------------------------------------------------------------------
    # Internal helpers for the report
    # ------------------------------------------------------------------

    @staticmethod
    def _risk_level(score: float) -> str:
        """Map a numeric score to a human-readable risk tier.

        Args:
            score: A value in [0, 10].

        Returns:
            One of ``'Low'``, ``'Moderate'``, ``'High'``, or ``'Very High'``.
        """
        if score < 3.5:
            return "Low"
        if score < 5.5:
            return "Moderate"
        if score < 7.5:
            return "High"
        return "Very High"

    def _build_risk_factors(
        self,
        market_vol: float,
        vacancy: float,
        condition: float,
        financing: float,
    ) -> list[str]:
        """Collect plain-language descriptions of elevated risk signals.

        Args:
            market_vol: Market volatility score.
            vacancy: Vacancy risk score.
            condition: Property condition risk score.
            financing: Financing risk score.

        Returns:
            List of concern strings, empty when all scores are low.
        """
        factors: list[str] = []

        # --- Market volatility factors ----------------------------------
        appreciation_rate: float = float(self._mkt("appreciation_rate", 0.03) or 0.03)
        price_history: list = self._mkt("price_history", [])

        if market_vol >= 7.0:
            factors.append(
                "Market exhibits high price volatility — recent price history "
                "shows wide swings that increase exit-price uncertainty."
            )
        if appreciation_rate < 0:
            factors.append(
                f"Market is currently depreciating "
                f"({appreciation_rate:.1%} annual rate), eroding equity."
            )
        elif appreciation_rate > 0.10:
            factors.append(
                f"Appreciation rate ({appreciation_rate:.1%}) may indicate an "
                "overheating market susceptible to a sharp correction."
            )
        if len(price_history) < 2:
            factors.append(
                "Insufficient price-history data to assess market trend "
                "reliably; volatility score uses a conservative default."
            )

        # --- Vacancy risk factors ---------------------------------------
        vacancy_rate: float = float(self._mkt("vacancy_rate", 0.08) or 0.08)
        days_on_market: float = float(self._mkt("days_on_market", 30) or 30)
        unemployment_rate: float = float(self._mkt("unemployment_rate", 0.04) or 0.04)

        if vacancy_rate > 0.12:
            factors.append(
                f"Local vacancy rate ({vacancy_rate:.1%}) is well above the "
                "national average, indicating weak rental demand."
            )
        if days_on_market > 60:
            factors.append(
                f"Properties are sitting on the market for {days_on_market:.0f} days "
                "on average, signalling a buyer's or renter's market."
            )
        if unemployment_rate > 0.06:
            factors.append(
                f"Elevated local unemployment ({unemployment_rate:.1%}) may "
                "increase tenant default and vacancy risk."
            )

        # --- Property condition factors ---------------------------------
        year_built: int | None = self._prop("year_built")
        property_type: str = str(
            self._prop("property_type", "single family") or "single family"
        ).lower()

        if year_built:
            age = max(0, self._current_year() - int(year_built))
            if age > 60:
                factors.append(
                    f"Property is {age} years old — expect elevated capital "
                    "expenditure risk for plumbing, electrical, and structural systems."
                )
            elif age > 30:
                factors.append(
                    f"Property age ({age} years) suggests major systems "
                    "(HVAC, roof) may be approaching end-of-life."
                )
        else:
            factors.append(
                "Year built is unknown; condition risk uses a conservative default."
            )

        if any(hrt in property_type for hrt in self._HIGHER_RISK_PROPERTY_TYPES):
            factors.append(
                f"Property type '{property_type}' typically carries a narrower "
                "buyer/renter pool and higher financing restrictions."
            )

        # --- Financing risk factors -------------------------------------
        down_payment_pct: float = float(
            self._mkt("down_payment_percentage", 0.20) or 0.20
        )
        interest_rate: float = float(self._mkt("interest_rate", 0.07) or 0.07)
        ltv = 1.0 - down_payment_pct

        if ltv > 0.90:
            factors.append(
                f"High loan-to-value ratio ({ltv:.0%}) leaves minimal equity "
                "buffer against market downturns."
            )
        elif ltv > 0.80:
            factors.append(
                f"LTV of {ltv:.0%} likely requires private mortgage insurance, "
                "increasing effective carrying costs."
            )
        if interest_rate > 0.07:
            factors.append(
                f"Current interest rate ({interest_rate:.2%}) materially "
                "compresses cash flow and limits the buyer pool on exit."
            )

        return factors

    def _build_recommendations(
        self,
        market_vol: float,
        vacancy: float,
        condition: float,
        financing: float,
        overall: float,
    ) -> list[str]:
        """Generate actionable recommendations based on risk scores.

        Args:
            market_vol: Market volatility score.
            vacancy: Vacancy risk score.
            condition: Property condition risk score.
            financing: Financing risk score.
            overall: Overall composite score.

        Returns:
            Prioritised list of recommendation strings.
        """
        recs: list[str] = []

        if overall >= 7.5:
            recs.append(
                "Consider passing on this investment unless deeply discounted — "
                "the composite risk profile is in the 'Very High' tier."
            )
        elif overall >= 5.5:
            recs.append(
                "Proceed cautiously: negotiate a price reduction to create an "
                "adequate margin of safety for the elevated risk identified."
            )

        # Market volatility recommendations
        if market_vol >= 6.0:
            recs.append(
                "Shorten your target holding period or use options/insurance "
                "strategies to hedge against market price swings."
            )
        appreciation_rate: float = float(self._mkt("appreciation_rate", 0.03) or 0.03)
        if appreciation_rate < 0:
            recs.append(
                "Avoid appreciation-dependent underwriting in a depreciating "
                "market; base return projections on cash flow only."
            )

        # Vacancy risk recommendations
        vacancy_rate: float = float(self._mkt("vacancy_rate", 0.08) or 0.08)
        if vacancy >= 5.0:
            recs.append(
                "Budget for extended vacancy (at least 12–15 % of gross rents) "
                "and stress-test cash flow at 20 % vacancy before committing."
            )
        if vacancy_rate > 0.10:
            recs.append(
                "Research the drivers of local vacancy — structural decline, "
                "oversupply, or seasonal patterns each require a different strategy."
            )

        # Property condition recommendations
        year_built: int | None = self._prop("year_built")
        if year_built:
            age = max(0, self._current_year() - int(year_built))
            if age > 30:
                recs.append(
                    "Commission a full structural inspection and obtain quotes "
                    "for roof, HVAC, and plumbing/electrical upgrades before closing."
                )
            if age > 60:
                recs.append(
                    "Reserve at least 2 % of purchase price annually for capital "
                    "expenditures on a property of this age."
                )

        if condition >= 6.0:
            recs.append(
                "Factor a 10–15 % rehab contingency into your acquisition model "
                "to account for deferred maintenance."
            )

        # Financing risk recommendations
        interest_rate: float = float(self._mkt("interest_rate", 0.07) or 0.07)
        down_payment_pct: float = float(
            self._mkt("down_payment_percentage", 0.20) or 0.20
        )
        if interest_rate > 0.07:
            recs.append(
                "Model a rate buy-down or seller financing structure to improve "
                "DSCR; alternatively, increase the down payment to reduce debt service."
            )
        if down_payment_pct < 0.20:
            recs.append(
                "Increasing the down payment to at least 20 % eliminates PMI "
                "and reduces monthly debt service, improving cash flow resilience."
            )
        if financing >= 6.0:
            recs.append(
                "Ensure the property meets minimum DSCR requirements (≥ 1.25) "
                "for the lender; if not, re-evaluate the purchase price."
            )

        # Always-present best practices
        recs.append(
            "Maintain a liquid cash reserve equal to at least six months of "
            "total monthly expenses (PITI + operating costs) for this property."
        )

        return recs

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def assess_risk(self) -> dict[str, Any]:
        """Produce a complete risk assessment report for the property.

        Computes all individual risk scores, the weighted composite, and
        assembles a structured report with plain-English risk factors and
        prioritised recommendations.

        Returns:
            A dictionary with the following keys:

            - ``individual_scores`` – ``dict[str, float]``: one entry per
              risk dimension, each in [0, 10].
            - ``overall_risk`` – ``float``: weighted composite score in [0, 10].
            - ``risk_level`` – ``str``: one of ``'Low'``, ``'Moderate'``,
              ``'High'``, or ``'Very High'``.
            - ``risk_factors`` – ``list[str]``: specific concerns identified.
            - ``recommendations`` – ``list[str]``: actionable mitigations.

        Raises:
            RiskAssessmentError: If an unexpected calculation error occurs.
        """
        try:
            market_vol = self.calculate_market_volatility()
            vacancy = self.calculate_vacancy_risk()
            condition = self.calculate_property_condition_risk()
            financing = self.calculate_financing_risk()

            overall = round(
                _clamp(
                    market_vol * self._WEIGHTS["market_volatility"]
                    + vacancy * self._WEIGHTS["vacancy_risk"]
                    + condition * self._WEIGHTS["property_condition_risk"]
                    + financing * self._WEIGHTS["financing_risk"]
                ),
                2,
            )

            return {
                "individual_scores": {
                    "market_volatility": market_vol,
                    "vacancy_risk": vacancy,
                    "property_condition_risk": condition,
                    "financing_risk": financing,
                },
                "overall_risk": overall,
                "risk_level": self._risk_level(overall),
                "risk_factors": self._build_risk_factors(
                    market_vol, vacancy, condition, financing
                ),
                "recommendations": self._build_recommendations(
                    market_vol, vacancy, condition, financing, overall
                ),
            }
        except RiskAssessmentError:
            raise
        except Exception as exc:
            raise RiskAssessmentError(
                f"Unexpected error during risk assessment: {exc}"
            ) from exc
