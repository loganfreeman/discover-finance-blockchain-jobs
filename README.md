# Skills for Finance and Blockchain Careers

An open-source agentic skills repository for software engineers targeting roles in fintech, trading, quant finance, crypto, DeFi, and blockchain infrastructure.

This project is not a static job board. It is a set of executable Codex skills that help an end user produce ranked job lists, resume match reports, company hiring briefs, and weekly market reports.

## First Version

The initial skill set is:

- `discover-finance-blockchain-jobs`: find and rank current engineering jobs in finance, fintech, trading, crypto, and blockchain.
- `match-resume-to-jobs`: compare a resume against target job postings and produce fit scores plus resume gaps.
- `research-company-hiring-signal`: research one company and summarize whether it appears worth applying to now.
- `generate-weekly-market-report`: produce a current market report for a target role, stack, region, or niche.

Each skill lives in `skills/<skill-name>/` and includes:

- `SKILL.md`: agent instructions.
- `agents/openai.yaml`: UI metadata and default prompt.
- `schemas/input.schema.json`: expected structured input.
- `schemas/output.schema.json`: expected structured output.
- `templates/report.md`: report shape for human-readable output.
- `examples/`: sample input and output.

`discover-finance-blockchain-jobs` also includes an executable, dependency-free collector for public Greenhouse, Lever, and Ashby job boards:

```powershell
python skills/discover-finance-blockchain-jobs/scripts/discover_jobs.py `
  --input skills/discover-finance-blockchain-jobs/examples/input.json `
  --format markdown `
  --output jobs-report.md
```

Edit `skills/discover-finance-blockchain-jobs/sources.json` or pass a separate source catalog to search different companies.

## How End Users Run a Skill

Copy this repository, then invoke a skill by name in Codex:

```text
Use $discover-finance-blockchain-jobs to find remote US backend engineering jobs in blockchain infrastructure for a Go and TypeScript engineer with 4 years of experience.
```

Another example:

```text
Use $research-company-hiring-signal to research Coinbase for senior backend engineering roles. Focus on hiring momentum, engineering roles, business stability, and interview prep.
```

## Output Principles

Skills should produce useful artifacts, not just chat responses:

- Markdown reports for humans.
- Tables for scanning.
- JSON-compatible fields for automation.
- Clear source links and retrieval dates for time-sensitive claims.
- Explicit assumptions when user input is incomplete.

## Data Freshness

Job openings, compensation, funding, layoffs, and hiring signals change quickly. Skills that use current market data should verify with web sources at execution time and include source links. When web access is unavailable, the report must say so and avoid presenting stale claims as current.

## Repository Roadmap

Good next additions:

- `prepare-fintech-blockchain-interview`
- `build-role-roadmap`
- `track-applications`
- `research-compensation`
- `compare-offers`
- deterministic helper scripts for normalizing job exports from Lever, Greenhouse, Ashby, CSV, and JSON.
