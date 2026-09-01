---
name: match-resume-to-jobs
description: Compare a software engineering resume to finance, fintech, trading, crypto, DeFi, or blockchain job postings and produce fit scores, gaps, and tailoring guidance.
metadata:
  short-description: Match a resume to target finance and blockchain jobs
---

# Match Resume To Jobs

Use this skill when a user provides a resume, profile summary, LinkedIn-style experience, or job postings and wants to know which finance or blockchain engineering roles fit best.

Do not invent resume facts. Separate actual evidence from suggested positioning. If the user provides no job postings, ask whether to use current web research or run the `discover-finance-blockchain-jobs` style workflow as part of the analysis.

## Inputs

Useful inputs include:

- Resume text or career profile.
- Target jobs or job URLs.
- Target role families.
- Preferred industries.
- Constraints such as location, remote, seniority, visa, and compensation.

## Analysis

For each job, assess:

- Core technical match.
- Domain match.
- Seniority match.
- Location and constraint match.
- Missing required skills.
- Resume evidence strength.
- Suggested keywords and bullet revisions.

Use a 0-100 fit score. Explain the score in human terms and avoid implying mathematical precision.

## Output

Follow `templates/report.md`. The report should include:

- Overall fit summary.
- Ranked job matches.
- Evidence from the resume.
- Missing skills and risks.
- Suggested resume edits.
- Suggested application strategy.

When suggesting resume bullets, write them as drafts the user can adapt. Do not claim experience the user did not provide.

