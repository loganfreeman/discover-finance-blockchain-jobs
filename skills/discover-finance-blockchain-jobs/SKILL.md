---
name: discover-finance-blockchain-jobs
description: Find and rank current software engineering jobs in finance, fintech, trading, crypto, DeFi, and blockchain for a user's target profile.
metadata:
  short-description: Discover ranked finance and blockchain engineering jobs
---

# Discover Finance and Blockchain Jobs

Use this skill when a user wants current engineering job opportunities in finance, fintech, trading, quant finance, crypto, DeFi, or blockchain infrastructure.

The output should be a concise, source-linked job discovery report with ranked roles and practical application guidance. Use `scripts/discover_jobs.py` for repeatable discovery from configured Greenhouse, Lever, and Ashby job boards. Job data is time-sensitive: execute the script at request time and retain retrieval dates. If network access is unavailable, say so clearly and use user-provided job data or fixtures only.

## Execute Discovery

Convert the user's request into an input JSON document matching `schemas/input.schema.json`, then run:

```bash
python scripts/discover_jobs.py --input <profile.json> --format markdown --output <report.md>
```

Use `--format json` for automation. The default source catalog is `sources.json`; pass `--sources <catalog.json>` to use a custom catalog. A catalog entry needs `company`, `industry_category`, `provider`, and the public ATS board `token`.

The script uses public, read-only ATS APIs and requires no credentials. It continues when one source fails and records failures in `source_errors`. Treat its score as triage: inspect the posting before making strong claims, especially for location, work authorization, compensation, and seniority.

## Inputs To Gather

Use what the user provides and make reasonable assumptions for missing details:

- Target role family, such as backend, platform, smart contract, protocol, quant dev, security, or full-stack.
- Location and remote preference.
- Seniority and years of experience.
- Core stack and domain experience.
- Industry preference: fintech, trading, quant finance, crypto exchange, blockchain infra, DeFi, or web3 security.
- Constraints such as visa sponsorship, compensation floor, excluded companies, or preferred company size.

## Research Guidance

Prefer the script's official ATS results. Use web search to discover additional company board tokens or roles that are not on a supported ATS, and confirm those roles on an official company page before adding them to the report.

For each role, capture:

- Company and role title.
- Official job URL.
- Location or remote policy.
- Role family and industry category.
- Seniority.
- Required or preferred stack.
- Why it matches the user's profile.
- Gaps or watchouts.
- Application priority.

Use `references/domain-taxonomy.md` from the repository root when assigning categories.

## Ranking

Rank roles by:

1. Match to target role, stack, seniority, and location.
2. Evidence that the posting is current and official.
3. Strength of finance/blockchain relevance.
4. Hiring signal quality.
5. User constraints such as compensation, visa, or remote.

Use a 0-100 match score. Scores should be explained in plain language, not treated as objective truth.

## Output

Follow `templates/report.md` unless the user asks for a different format. Include:

- Search assumptions.
- Top ranked roles table.
- Short notes on strongest matches.
- Skill gaps or resume keywords to add.
- Suggested next actions.
- Source links with retrieval date.
