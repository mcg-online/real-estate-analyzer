"""
Locust load test suite for the Real Estate Analyzer Flask API.

User personas
-------------
BrowsingUser (weight=3)
    Simulates an unauthenticated visitor paging through property listings,
    viewing individual properties, and checking top markets.  The heaviest
    user class, representing the majority of traffic.

AuthenticatedUser (weight=2)
    Simulates a registered user who logs in, browses properties, runs a
    standard analysis on a property they find, and occasionally creates a
    new listing.

HeavyAnalysisUser (weight=1)
    Simulates a power user (e.g. an analyst or broker) who logs in and
    immediately starts running repeated property analyses with varied custom
    parameters.

Running
-------
    locust -f tests/load/locustfile.py --host http://localhost:5000

See README.md in this directory for full usage instructions.
"""

from __future__ import annotations

import logging
import random
import string
import time
from typing import Optional

from locust import HttpUser, between, task

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared test data constants
# ---------------------------------------------------------------------------

# Property IDs that the load test will exercise.  At runtime the browsing
# users also collect real IDs from the listing endpoint and store them in
# the class-level pool below so that subsequent single-property GETs and
# analysis requests hit real documents rather than always 404-ing.
_PROPERTY_ID_POOL: list[str] = []
_PROPERTY_ID_POOL_MAX = 50  # cap so the list does not grow unbounded

# Realistic filter combinations applied randomly by browsing tasks.
_FILTER_SETS: list[dict] = [
    {},
    {"state": "CA"},
    {"state": "TX"},
    {"state": "FL"},
    {"state": "WA"},
    {"minPrice": "200000", "maxPrice": "500000"},
    {"minPrice": "500000", "maxPrice": "1000000"},
    {"minBedrooms": "3"},
    {"minBedrooms": "4", "minBathrooms": "2"},
    {"propertyType": "single_family"},
    {"propertyType": "condo"},
    {"propertyType": "multi_family"},
    {"state": "CA", "minPrice": "300000", "maxPrice": "800000"},
    {"state": "TX", "minBedrooms": "3", "propertyType": "single_family"},
    {"minScore": "70"},
    {"sortBy": "price", "sortOrder": "desc", "limit": "10"},
    {"sortBy": "price", "sortOrder": "asc", "limit": "20", "page": "2"},
]

# Realistic custom analysis parameters cycled through by HeavyAnalysisUser.
_ANALYSIS_PARAM_SETS: list[dict] = [
    {
        "down_payment_percentage": 0.20,
        "interest_rate": 0.065,
        "term_years": 30,
        "holding_period": 5,
        "appreciation_rate": 0.03,
        "tax_bracket": 0.22,
    },
    {
        "down_payment_percentage": 0.25,
        "interest_rate": 0.055,
        "term_years": 15,
        "holding_period": 10,
        "appreciation_rate": 0.04,
        "tax_bracket": 0.32,
    },
    {
        "down_payment_percentage": 0.10,
        "interest_rate": 0.075,
        "term_years": 30,
        "holding_period": 3,
        "appreciation_rate": 0.02,
        "tax_bracket": 0.24,
        "credit_score": 680,
        "veteran": False,
        "first_time_va": False,
    },
    {
        "down_payment_percentage": 0.05,
        "interest_rate": 0.07,
        "term_years": 30,
        "holding_period": 7,
        "appreciation_rate": 0.035,
        "tax_bracket": 0.12,
        "credit_score": 750,
        "veteran": True,
        "first_time_va": True,
    },
    {
        "down_payment_percentage": 0.30,
        "interest_rate": 0.06,
        "term_years": 20,
        "holding_period": 15,
        "appreciation_rate": 0.05,
        "tax_bracket": 0.37,
        "credit_score": 800,
    },
]

# Minimal valid property payload for POST /api/v1/properties.
_BASE_PROPERTY_PAYLOAD: dict = {
    "address": "100 Load Test Ave",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
    "price": 350000,
    "bedrooms": 3,
    "bathrooms": 2,
    "sqft": 1800,
    "year_built": 2010,
    "property_type": "single_family",
    "lot_size": 6000,
    "listing_url": "http://example.com/load-test-listing",
    "source": "load_test",
    "description": "Load test property - safe to delete",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_suffix(length: int = 8) -> str:
    """Return a short random alphanumeric string for unique usernames/addresses."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _pick_property_id() -> Optional[str]:
    """Return a random ID from the shared pool, or None if the pool is empty."""
    if _PROPERTY_ID_POOL:
        return random.choice(_PROPERTY_ID_POOL)
    return None


def _store_property_ids(response_json: dict) -> None:
    """Extract and cache property IDs returned by the listing endpoint."""
    items = response_json.get("data", [])
    for item in items:
        pid = item.get("_id")
        if pid and pid not in _PROPERTY_ID_POOL:
            _PROPERTY_ID_POOL.append(pid)
            if len(_PROPERTY_ID_POOL) > _PROPERTY_ID_POOL_MAX:
                _PROPERTY_ID_POOL.pop(0)


# ---------------------------------------------------------------------------
# User classes
# ---------------------------------------------------------------------------

class BrowsingUser(HttpUser):
    """Anonymous user browsing property listings and market data.

    Task weights (relative frequency within this user class):
        browse_properties  5  -- most common action
        view_property      3  -- detail page views
        top_markets        2  -- market overview page
        health_check       1  -- background keepalive / monitoring traffic
    """

    weight = 3
    wait_time = between(1, 5)

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    @task(5)
    def browse_properties(self):
        """GET /api/v1/properties with a random filter combination."""
        filters = random.choice(_FILTER_SETS)
        params = {"limit": random.choice([10, 20, 50]), "page": 1, **filters}

        with self.client.get(
            "/api/v1/properties",
            params=params,
            name="/api/v1/properties [browse]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    body = resp.json()
                    _store_property_ids(body)
                    resp.success()
                except (ValueError, KeyError):
                    resp.failure(f"Unexpected response body: {resp.text[:200]}")
            else:
                resp.failure(f"Expected 200, got {resp.status_code}: {resp.text[:200]}")

    @task(3)
    def view_property(self):
        """GET /api/v1/properties/<id> for a known property."""
        property_id = _pick_property_id()
        if not property_id:
            # Pool not yet populated; skip this iteration rather than fire a
            # guaranteed 404 with a bogus ID.
            return

        with self.client.get(
            f"/api/v1/properties/{property_id}",
            name="/api/v1/properties/[id]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                # 404 is acceptable: the property may have been deleted by an
                # AuthenticatedUser or simply not exist in this environment.
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}: {resp.text[:200]}")

    @task(2)
    def top_markets(self):
        """GET /api/v1/markets/top with varied metric and limit params."""
        metric = random.choice(["roi", "cap_rate"])
        limit = random.choice([5, 10, 20])

        with self.client.get(
            "/api/v1/markets/top",
            params={"metric": metric, "limit": limit},
            name="/api/v1/markets/top",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Expected 200, got {resp.status_code}: {resp.text[:200]}")

    @task(1)
    def health_check(self):
        """GET /health -- shallow liveness probe."""
        with self.client.get(
            "/health",
            name="/health",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health check failed: {resp.status_code}")


# ---------------------------------------------------------------------------

class AuthenticatedUser(HttpUser):
    """Registered user: login -> browse -> analyse -> occasionally create.

    Task weights:
        browse_and_fetch   4  -- list + detail views dominate
        run_analysis       3  -- standard analysis on a found property
        create_property    1  -- occasional new listing creation
        logout_and_relogin 1  -- session rotation
    """

    weight = 2
    wait_time = between(2, 5)

    # Populated in on_start; cleared in on_stop.
    token: Optional[str] = None
    username: str = ""
    password: str = ""

    def on_start(self):
        """Register a unique user then log in to obtain a JWT token."""
        self.username = f"loadtest_{_random_suffix()}"
        self.password = "LoadTest1!"  # meets: upper, lower, digit, 8+ chars

        # Register
        reg_resp = self.client.post(
            "/api/v1/auth/register",
            json={"username": self.username, "password": self.password},
            name="/api/v1/auth/register [setup]",
        )
        if reg_resp.status_code not in (201, 409):
            logger.warning(
                "Registration returned unexpected status %s for user %s",
                reg_resp.status_code,
                self.username,
            )

        self._do_login()

    def on_stop(self):
        """Log out cleanly so the token is added to the server-side blocklist."""
        if self.token:
            self.client.post(
                "/api/v1/auth/logout",
                headers=self._auth_headers(),
                name="/api/v1/auth/logout [teardown]",
            )
            self.token = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _do_login(self) -> bool:
        """POST /api/v1/auth/login and store the returned JWT.  Returns True on success."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": self.username, "password": self.password},
            name="/api/v1/auth/login",
        )
        if resp.status_code == 200:
            try:
                self.token = resp.json().get("access_token")
                return True
            except (ValueError, KeyError):
                logger.warning("Login response missing access_token for %s", self.username)
        else:
            logger.warning("Login failed (%s) for user %s", resp.status_code, self.username)
        return False

    def _auth_headers(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _pick_or_fetch_property_id(self) -> Optional[str]:
        """Return an ID from the shared pool, seeding the pool first if empty."""
        if not _PROPERTY_ID_POOL:
            resp = self.client.get(
                "/api/v1/properties",
                params={"limit": 20},
                name="/api/v1/properties [seed]",
            )
            if resp.status_code == 200:
                try:
                    _store_property_ids(resp.json())
                except ValueError:
                    pass
        return _pick_property_id()

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    @task(4)
    def browse_and_fetch(self):
        """List properties then fetch a detail page -- mimics normal UI navigation."""
        filters = random.choice(_FILTER_SETS)
        params = {"limit": random.choice([10, 20]), **filters}

        with self.client.get(
            "/api/v1/properties",
            params=params,
            name="/api/v1/properties [auth browse]",
            catch_response=True,
        ) as list_resp:
            if list_resp.status_code == 200:
                try:
                    body = list_resp.json()
                    _store_property_ids(body)
                    list_resp.success()
                except ValueError:
                    list_resp.failure("Non-JSON response on property list")
                    return
            else:
                list_resp.failure(
                    f"Property list returned {list_resp.status_code}: {list_resp.text[:200]}"
                )
                return

        # Brief pause simulating user reading the list before clicking a result.
        time.sleep(random.uniform(0.5, 1.5))

        property_id = _pick_property_id()
        if not property_id:
            return

        with self.client.get(
            f"/api/v1/properties/{property_id}",
            headers=self._auth_headers(),
            name="/api/v1/properties/[id] [auth view]",
            catch_response=True,
        ) as detail_resp:
            if detail_resp.status_code in (200, 404):
                detail_resp.success()
            else:
                detail_resp.failure(
                    f"Property detail returned {detail_resp.status_code}: {detail_resp.text[:200]}"
                )

    @task(3)
    def run_analysis(self):
        """GET /api/v1/analysis/property/<id> -- standard analysis for a found property."""
        if not self.token:
            return

        property_id = self._pick_or_fetch_property_id()
        if not property_id:
            return

        with self.client.get(
            f"/api/v1/analysis/property/{property_id}",
            headers=self._auth_headers(),
            name="/api/v1/analysis/property/[id] [GET]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                # 404 acceptable: property may have been deleted or not exist.
                resp.success()
            else:
                resp.failure(f"Analysis GET returned {resp.status_code}: {resp.text[:200]}")

    @task(1)
    def create_property(self):
        """POST /api/v1/properties -- create a new listing (JWT required)."""
        if not self.token:
            return

        payload = dict(_BASE_PROPERTY_PAYLOAD)
        payload["address"] = f"{random.randint(100, 9999)} Load Test St"
        payload["listing_url"] = f"http://example.com/load-test/{_random_suffix()}"

        with self.client.post(
            "/api/v1/properties",
            json=payload,
            headers=self._auth_headers(),
            name="/api/v1/properties [POST create]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                try:
                    new_id = resp.json().get("_id")
                    if new_id and new_id not in _PROPERTY_ID_POOL:
                        _PROPERTY_ID_POOL.append(new_id)
                    resp.success()
                except ValueError:
                    resp.failure("Non-JSON response on property creation")
            elif resp.status_code == 401:
                # Token may have expired -- attempt a re-login.
                self._do_login()
                resp.failure("Token expired during create, re-logging in")
            else:
                resp.failure(
                    f"Property creation returned {resp.status_code}: {resp.text[:200]}"
                )

    @task(1)
    def logout_and_relogin(self):
        """POST /api/v1/auth/logout then immediately log back in.

        Exercises the token-blocklist path and verifies that a fresh login
        always works under load.
        """
        if not self.token:
            self._do_login()
            return

        with self.client.post(
            "/api/v1/auth/logout",
            headers=self._auth_headers(),
            name="/api/v1/auth/logout [task]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                self.token = None
                resp.success()
            else:
                resp.failure(f"Logout returned {resp.status_code}: {resp.text[:200]}")

        time.sleep(random.uniform(0.3, 0.8))
        self._do_login()


# ---------------------------------------------------------------------------

class HeavyAnalysisUser(HttpUser):
    """Power user running repeated property analyses with custom parameters.

    Task weights:
        custom_analysis      5  -- POSTing custom params is the primary action
        standard_analysis    3  -- also runs default GET analysis
        opportunity_score    2  -- checks the opportunity score endpoint
        register_and_login   0  -- only in on_start; not a recurring task
    """

    weight = 1
    wait_time = between(1, 3)

    token: Optional[str] = None
    username: str = ""
    password: str = ""

    def on_start(self):
        """Register and log in so all analysis tasks have a valid token."""
        self.username = f"analyst_{_random_suffix()}"
        self.password = "Analyst99!"

        reg_resp = self.client.post(
            "/api/v1/auth/register",
            json={"username": self.username, "password": self.password},
            name="/api/v1/auth/register [setup]",
        )
        if reg_resp.status_code not in (201, 409):
            logger.warning(
                "Analyst registration returned %s for %s",
                reg_resp.status_code,
                self.username,
            )

        self._do_login()

        # Pre-seed the property pool so tasks do not immediately skip.
        if not _PROPERTY_ID_POOL:
            seed = self.client.get(
                "/api/v1/properties",
                params={"limit": 50},
                name="/api/v1/properties [analyst seed]",
            )
            if seed.status_code == 200:
                try:
                    _store_property_ids(seed.json())
                except ValueError:
                    pass

    def on_stop(self):
        if self.token:
            self.client.post(
                "/api/v1/auth/logout",
                headers=self._auth_headers(),
                name="/api/v1/auth/logout [teardown]",
            )
            self.token = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _do_login(self) -> bool:
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": self.username, "password": self.password},
            name="/api/v1/auth/login",
        )
        if resp.status_code == 200:
            try:
                self.token = resp.json().get("access_token")
                return True
            except (ValueError, KeyError):
                pass
        logger.warning("Analyst login failed (%s) for %s", resp.status_code, self.username)
        return False

    def _auth_headers(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _require_token(self) -> bool:
        """Ensure we have a valid token, refreshing if necessary.  Returns True if ready."""
        if self.token:
            return True
        return self._do_login()

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    @task(5)
    def custom_analysis(self):
        """POST /api/v1/analysis/property/<id> with varied custom parameters.

        Exercises the server-side financial calculation engine under sustained
        concurrent load, which is the most CPU-intensive path in the API.
        """
        if not self._require_token():
            return

        property_id = _pick_property_id()
        if not property_id:
            # No IDs in pool yet -- fetch a batch to fill it.
            seed = self.client.get(
                "/api/v1/properties",
                params={"limit": 50},
                name="/api/v1/properties [analyst seed]",
            )
            if seed.status_code == 200:
                try:
                    _store_property_ids(seed.json())
                except ValueError:
                    pass
            return

        params = random.choice(_ANALYSIS_PARAM_SETS)

        with self.client.post(
            f"/api/v1/analysis/property/{property_id}",
            json=params,
            headers=self._auth_headers(),
            name="/api/v1/analysis/property/[id] [POST custom]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    body = resp.json()
                    # Verify key sections are present in the response.
                    missing = [
                        k for k in ("financial_analysis", "tax_benefits", "financing_options")
                        if k not in body
                    ]
                    if missing:
                        resp.failure(f"Analysis response missing keys: {missing}")
                    else:
                        resp.success()
                except ValueError:
                    resp.failure(f"Non-JSON analysis response: {resp.text[:200]}")
            elif resp.status_code == 404:
                # Property was removed; purge it from the pool and move on.
                if property_id in _PROPERTY_ID_POOL:
                    _PROPERTY_ID_POOL.remove(property_id)
                resp.success()
            elif resp.status_code == 401:
                self.token = None
                self._do_login()
                resp.failure("Token expired during custom analysis, re-logging in")
            else:
                resp.failure(
                    f"Custom analysis returned {resp.status_code}: {resp.text[:200]}"
                )

    @task(3)
    def standard_analysis(self):
        """GET /api/v1/analysis/property/<id> -- default analysis parameters."""
        if not self._require_token():
            return

        property_id = _pick_property_id()
        if not property_id:
            return

        with self.client.get(
            f"/api/v1/analysis/property/{property_id}",
            headers=self._auth_headers(),
            name="/api/v1/analysis/property/[id] [GET standard]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    body = resp.json()
                    if "financial_analysis" not in body:
                        resp.failure("Standard analysis response missing financial_analysis key")
                    else:
                        resp.success()
                except ValueError:
                    resp.failure(f"Non-JSON standard analysis response: {resp.text[:200]}")
            elif resp.status_code == 404:
                if property_id in _PROPERTY_ID_POOL:
                    _PROPERTY_ID_POOL.remove(property_id)
                resp.success()
            elif resp.status_code == 401:
                self.token = None
                self._do_login()
                resp.failure("Token expired during standard analysis, re-logging in")
            else:
                resp.failure(
                    f"Standard analysis returned {resp.status_code}: {resp.text[:200]}"
                )

    @task(2)
    def opportunity_score(self):
        """GET /api/v1/analysis/score/<id> -- investment opportunity scoring."""
        if not self._require_token():
            return

        property_id = _pick_property_id()
        if not property_id:
            return

        with self.client.get(
            f"/api/v1/analysis/score/{property_id}",
            headers=self._auth_headers(),
            name="/api/v1/analysis/score/[id]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    body = resp.json()
                    if "property_id" not in body:
                        resp.failure("Score response missing property_id key")
                    else:
                        resp.success()
                except ValueError:
                    resp.failure(f"Non-JSON score response: {resp.text[:200]}")
            elif resp.status_code == 404:
                if property_id in _PROPERTY_ID_POOL:
                    _PROPERTY_ID_POOL.remove(property_id)
                resp.success()
            elif resp.status_code == 401:
                self.token = None
                self._do_login()
                resp.failure("Token expired during score request, re-logging in")
            else:
                resp.failure(
                    f"Opportunity score returned {resp.status_code}: {resp.text[:200]}"
                )
