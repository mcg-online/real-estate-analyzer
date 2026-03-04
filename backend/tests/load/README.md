# Load Tests - Real Estate Analyzer API

Performance load tests for the Flask REST API using [Locust](https://locust.io).

---

## Prerequisites

The Flask backend must be running before you start Locust.  MongoDB must also
be available so property and market data exist for the analysis tasks to work
against.

### 1. Start the backend

```bash
# Using Docker Compose (recommended - starts Flask + MongoDB together)
docker-compose up -d

# OR run the backend directly
cd backend
source venv/bin/activate
python app.py
```

The API will be available at `http://localhost:5000`.

### 2. Install Locust

Install Locust into the backend virtual environment (or any Python 3.8+
environment):

```bash
pip install locust
```

Verify the installation:

```bash
locust --version
```

---

## Running the Tests

### Interactive Web UI (recommended for exploration)

```bash
cd backend
locust -f tests/load/locustfile.py --host http://localhost:5000
```

Open the Locust web UI at **http://localhost:8089**, enter your desired
user count and spawn rate, then click **Start swarming**.

The UI provides real-time charts for requests/second, response times, and
failure rates.

### Headless (CI / scripted) mode

Run a timed test without the browser UI:

```bash
cd backend
locust \
  -f tests/load/locustfile.py \
  --host http://localhost:5000 \
  --headless \
  --users 50 \
  --spawn-rate 5 \
  --run-time 60s
```

| Flag | Description |
|------|-------------|
| `--headless` | Disable the web UI; print results to stdout |
| `--users` / `-u` | Total number of concurrent virtual users |
| `--spawn-rate` / `-r` | Users added per second during ramp-up |
| `--run-time` / `-t` | How long to run (`60s`, `5m`, `1h`) |

### Recommended test progressions

| Scenario | Users | Spawn rate | Duration | Purpose |
|----------|-------|------------|----------|---------|
| Smoke | 5 | 1 | 30s | Verify locustfile runs without errors |
| Baseline | 20 | 2 | 2m | Establish normal-load metrics |
| Load | 50 | 5 | 5m | Typical peak traffic simulation |
| Stress | 100 | 10 | 5m | Find degradation threshold |
| Soak | 30 | 3 | 30m | Detect memory leaks / slow degradation |

### Exporting results to CSV

```bash
locust \
  -f tests/load/locustfile.py \
  --host http://localhost:5000 \
  --headless \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --csv=results/load_test
```

This writes three CSV files:

- `results/load_test_stats.csv` - aggregate per-endpoint stats
- `results/load_test_stats_history.csv` - time-series stats (1-second buckets)
- `results/load_test_failures.csv` - all recorded failures

---

## User Personas

The locustfile defines three `HttpUser` classes.  Locust spawns them in
proportion to their `weight` values.

### BrowsingUser (weight=3)

Simulates an unauthenticated visitor.  No login is required.

| Task | Weight | Endpoint |
|------|--------|----------|
| `browse_properties` | 5 | `GET /api/v1/properties` with random filters |
| `view_property` | 3 | `GET /api/v1/properties/<id>` |
| `top_markets` | 2 | `GET /api/v1/markets/top` |
| `health_check` | 1 | `GET /health` |

### AuthenticatedUser (weight=2)

Simulates a registered user.  A unique user is registered and logged in via
`on_start`.  The JWT token is refreshed automatically if a 401 is returned.

| Task | Weight | Endpoint |
|------|--------|----------|
| `browse_and_fetch` | 4 | `GET /api/v1/properties` then `GET /api/v1/properties/<id>` |
| `run_analysis` | 3 | `GET /api/v1/analysis/property/<id>` |
| `create_property` | 1 | `POST /api/v1/properties` |
| `logout_and_relogin` | 1 | `POST /api/v1/auth/logout` then `POST /api/v1/auth/login` |

### HeavyAnalysisUser (weight=1)

Simulates a power user (analyst / broker) who hammers the analysis engine.

| Task | Weight | Endpoint |
|------|--------|----------|
| `custom_analysis` | 5 | `POST /api/v1/analysis/property/<id>` with custom params |
| `standard_analysis` | 3 | `GET /api/v1/analysis/property/<id>` |
| `opportunity_score` | 2 | `GET /api/v1/analysis/score/<id>` |

---

## Performance Targets

These are the SLA thresholds to evaluate against test results.

| Endpoint category | p50 target | p95 target | p99 target |
|-------------------|-----------|-----------|-----------|
| Read (GET) | < 100 ms | < 500 ms | < 1000 ms |
| Write (POST/PUT) | < 200 ms | < 1000 ms | < 2000 ms |
| Analysis (GET/POST) | < 300 ms | < 1000 ms | < 2000 ms |
| Auth (login/register) | < 300 ms | < 800 ms | < 1500 ms |

Failure rate target: **< 1%** under normal load (50 users).

---

## Interpreting Results

After a headless run the summary table is printed to stdout.  Key columns:

| Column | Meaning |
|--------|---------|
| `# Requests` | Total requests sent |
| `# Failures` | Requests where `resp.failure()` was called or an exception occurred |
| `Median (ms)` | p50 response time |
| `95%ile (ms)` | p95 response time - primary SLA indicator |
| `99%ile (ms)` | p99 response time |
| `Avg (ms)` | Mean response time (can be skewed by outliers) |
| `Min (ms)` / `Max (ms)` | Absolute bounds |
| `Req/s` | Throughput |

A failure rate above 1% or p95 above the target values indicates the API is
saturated at that concurrency level.

---

## Rate Limiting

The Flask API enforces default limits of **200 requests per day** and
**50 requests per hour** per IP, plus a tighter **5 per minute** limit on
`/api/v1/auth/login` and **3 per hour** on `/api/v1/auth/register`.

When running Locust locally all virtual users share your machine's IP address,
so the per-IP limits will be hit quickly at higher user counts.

To work around this for load testing:

1. **Disable rate limiting** in the backend by setting
   `RATELIMIT_ENABLED=False` in the app config (do not do this in production).
2. **Use a Redis-backed limiter** with a higher threshold configured via
   environment variables.
3. **Distribute Locust workers** across multiple IPs using the Locust
   master/worker mode (see `locust --master` / `locust --worker`).

---

## Locust Worker Mode (distributed load generation)

To generate higher load from multiple machines:

```bash
# On the master node (coordinates workers, hosts the web UI)
locust -f tests/load/locustfile.py --master --host http://localhost:5000

# On each worker node (can be on separate machines)
locust -f tests/load/locustfile.py --worker --master-host <MASTER_IP>
```

---

## Troubleshooting

**All requests fail with connection errors**
Verify the backend is running: `curl http://localhost:5000/health`

**All analysis tasks skip ("No IDs in pool")**
The property collection is empty.  Seed it by calling
`POST /api/v1/properties` a few times, or import fixture data into MongoDB.

**401 errors on authenticated tasks**
The JWT expires after 1 hour (configurable via `JWT_EXPIRY_SECONDS`).  The
locustfile handles 401 by re-logging in automatically.  If every request
returns 401 check that `JWT_SECRET` is set and consistent between runs.

**Registration returning 409 (Conflict)**
Each virtual user generates a unique username with a random suffix so
duplicates should not occur across Locust runs.  If you do see 409 errors
consistently, check the MongoDB `users` collection for leftover test accounts.

**Rate-limit 429 errors**
See the Rate Limiting section above.
