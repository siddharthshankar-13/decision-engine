# Decision Intelligence Engine

Python engine for modeling decisions, running reproducible Monte Carlo
simulations, propagating graph values, evaluating constraints, comparing
scenarios, analyzing sensitivity, and exchanging structured data with future
finance, sales, and operations critics. The critique contracts are
provider-independent and do not call an LLM yet.

## Implemented engine modules

- `graph.py`: nodes, fields, dependencies, propagation, and constraints
- `simulation.py`: typed, seeded Monte Carlo simulation and percentiles
- `scenarios.py`: named assumption overrides and scenario comparisons
- `sensitivity.py`: correlation-based assumption ranking
- `critique.py`: structured critique contracts and domain interfaces
- `critique_adapters.py`: compact provider payloads and response validation
- `critique_aggregation.py`: multi-domain critique validation and aggregation
- `report.py`: unified decision report and derived outcome summaries

## Local development

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
```

GitHub Actions runs compilation and tests on Python 3.11 and 3.13 for every
push and pull request targeting `main`. See `CI_CD.md` for branch protection,
release, environment, and deployment recommendations.
