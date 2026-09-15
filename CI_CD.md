# CI/CD with GitHub

## Continuous integration

The repository's `.github/workflows/ci.yml` workflow runs for pushes and pull
requests targeting `main`. It installs the development dependencies, compiles
the engine modules, and runs the full test suite on supported Python versions.
Coverage is measured across the engine modules and must remain at or above the
configured threshold.

Recommended GitHub repository settings:

1. Protect `main` and require pull requests.
2. Require both Python matrix checks to pass before merging.
3. Require branches to be current with `main` before merging.
4. Block force pushes and branch deletion on `main`.
5. Enable Dependabot for Python dependencies and GitHub Actions.
6. Use CODEOWNERS when more contributors join.

The normal workflow is:

```text
feature branch -> pull request -> CI -> review -> merge to main
```

## Continuous delivery and deployment

Deployment should begin in Phase 9, after a runnable FastAPI application and a
hosting target exist. Keep deployment in a separate workflow so ordinary tests
cannot accidentally deploy an incomplete service.

Recommended release flow:

```text
merge to main -> CI -> build immutable container -> staging -> smoke test
              -> protected production environment -> deploy -> health check
```

- Build one versioned container image per commit and promote that exact image.
- Store credentials in GitHub environment secrets, not repository files.
- Use a `staging` environment automatically and a protected `production`
  environment with required approval.
- Give workflow jobs only the permissions they need.
- Run database migrations as a separate, observable deployment step.
- Keep the prior container version available for rollback.
- Add health and smoke tests before directing production traffic to a release.

The eventual deployment workflow needs decisions that cannot be encoded yet:
the cloud/container host, image registry, production URL, database provider,
and migration tool. Until those are chosen, CI is complete while CD remains a
documented Phase 9 task.
