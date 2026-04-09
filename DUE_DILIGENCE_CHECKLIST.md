# Due Diligence Checklist

This checklist is meant to be run by a technical buyer, security team, or platform evaluator who wants a reproducible view of the repository's current state.

## Scope

This checklist focuses on what can be verified directly from the repository:

- package installation
- CLI and API smoke paths
- static quality gates
- test collection and selected test execution
- container build path
- public security and release posture

## 1. Clone And Inspect Metadata

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
git status --short --branch
python --version
```

Review:

- [README.md](README.md)
- [ENTERPRISE_READINESS.md](ENTERPRISE_READINESS.md)
- [SECURITY.md](SECURITY.md)
- [SUPPORT.md](SUPPORT.md)
- [VERSION_SUPPORT.md](VERSION_SUPPORT.md)
- [RELEASE_PROCESS.md](RELEASE_PROCESS.md)

## 2. Install The Local-First Core

```bash
pip install -e ".[dev]"
python -m build
```

Expected outcome:

- package builds successfully
- local `cortex` CLI is available

## Optional: Enable The Self-Hosted API Beta

```bash
pip install -e ".[dev,api]"
```

Use this only if you also want to evaluate the self-hosted beta API surface from the same source checkout.

## 3. Run A Minimal CLI Smoke Test

Use an isolated database path so the evaluation does not touch a personal local database.

```bash
export CORTEX_DB_PATH=/tmp/cortex-diligence.db
rm -f "$CORTEX_DB_PATH"

cortex init
cortex store diligence "Technical diligence smoke test" --type decision --source diligence
# capture the returned fact id from the previous command
cortex verify <FACT_ID_FROM_STORE>
cortex trust-ledger verify --full
cortex export --project diligence --format json --out /tmp/cortex-diligence.json
```

Expected outcome:

- initialization succeeds
- storing a fact returns a created fact id
- fact verification succeeds for the stored record
- ledger verification reports the fact set as valid
- export produces a portable JSON artifact without command-surface surprises

## 4. Run The Same Static Gates Used By CI

```bash
ruff check cortex/ tests/
ruff format --check cortex/ tests/
pyright cortex/
python -m pytest tests/ --collect-only -q
```

If you want a closer CI-equivalent test run:

```bash
timeout --signal=TERM 20m \
python -X faulthandler -m pytest tests/ -vv -s --tb=short -x \
  --durations=20 \
  --timeout=300 \
  --timeout-method=thread \
  --cov=cortex \
  --cov-report=xml \
  --cov-report=term-missing
```

## 5. Run A Security-Focused Pass

The public CI currently runs dependency audit, SAST-oriented Ruff checks, SBOM generation, and container scanning.

Reproduce the dependency audit command:

```bash
pip install pip-audit
pip-audit . --desc on \
  --ignore-vuln GHSA-qmgc-5h2g-mvrw \
  --ignore-vuln GHSA-j842-xgm4-wf88 \
  --ignore-vuln GHSA-w6vg-jg77-2qg6 \
  --ignore-vuln GHSA-f83h-ghpp-7wcc \
  --ignore-vuln GHSA-jr27-m4p2-rc6r
```

Then review:

- [.github/workflows/ci.yml](.github/workflows/ci.yml)
- [.github/workflows/codeql.yml](.github/workflows/codeql.yml)
- [.github/workflows/release.yml](.github/workflows/release.yml)

## Optional: Evaluate The Self-Hosted API Beta Container Path

```bash
docker build -t cortex:diligence .
docker run --rm -d --name cortex-diligence -p 8484:8484 cortex:diligence
sleep 5
curl -f http://127.0.0.1:8484/health
docker stop cortex-diligence
```

For a more realistic review, repeat with explicit production-like environment variables:

```bash
docker run --rm -d \
  --name cortex-diligence \
  -p 8484:8484 \
  -e CORTEX_DEPLOY=cloud \
  -e CORTEX_DB_PATH=/data/cortex.db \
  -e CORTEX_ALLOWED_ORIGINS=https://example.com \
  -e CORTEX_MASTER_KEY=BASE64_32_BYTE_AES_KEY \
  -v cortex-diligence-data:/data \
  cortex:diligence
```

## 7. Review The Trust-Critical Code Paths

Read these directories with extra scrutiny:

- `cortex/engine`
- `cortex/memory`
- `cortex/guards`
- `cortex/ledger`
- `cortex/routes`

Cross-check them against:

- [docs/SECURITY_TRUST_MODEL.md](docs/SECURITY_TRUST_MODEL.md)
- [docs/architecture.md](docs/architecture.md)
- [DEPLOYMENT_HARDENING.md](DEPLOYMENT_HARDENING.md)

## 8. Capture Evaluation Notes

At the end of the review, record:

- which commands passed unchanged
- which docs matched reality
- which claims needed qualification
- whether the buyer is evaluating a core product subset or the full repo surface
- what additional operational evidence is still required

## Bottom Line

If this checklist passes cleanly, the repository has crossed the line from “interesting codebase” to “credible technical diligence target.” It still remains a beta trust platform, so the outcome should be “validated for deeper review,” not “all procurement questions answered.”
