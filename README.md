# Decision Intelligence Engine

Python engine for modeling decisions, running reproducible Monte Carlo
simulations, propagating graph values, evaluating constraints, comparing
scenarios, and analyzing sensitivity.

## Local development

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
```

GitHub Actions runs compilation and tests on Python 3.11 and 3.13 for every
push and pull request.
