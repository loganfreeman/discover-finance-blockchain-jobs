#!/usr/bin/env python3
"""Discover and rank engineering jobs from public ATS job-board APIs."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


USER_AGENT = "skills-for-blockchain-jobs/0.1 (+open-source job discovery)"
ENGINEERING_TERMS = {
    "engineer", "engineering", "developer", "architect", "devops", "sre",
    "security", "quant", "infrastructure", "platform", "protocol", "data",
}
SOFTWARE_TITLE_MARKERS = (
    "software", "backend", "back-end", "platform", "infrastructure", "protocol",
    "blockchain", "smart contract", "full-stack", "full stack", "frontend", "front-end",
    "developer", "devops", "site reliability", "sre", "security engineer", "data engineer",
    "quant", "systems engineer", "machine learning engineer", "cloud engineer",
)
ROLE_RULES = {
    "smart-contract": ("smart contract", "solidity", "move engineer"),
    "protocol": ("protocol engineer", "core protocol", "consensus", "blockchain engineer"),
    "quant-dev": ("quant developer", "quantitative developer", "quant engineer", "low latency"),
    "full-stack": ("full stack", "full-stack", "fullstack"),
    "frontend": ("frontend", "front-end", "front end", "ui engineer"),
    "platform": ("platform", "developer experience", "devex", "site reliability", "sre"),
    "infrastructure": ("infrastructure", "devops", "cloud engineer", "systems engineer"),
    "security": ("security", "application security", "appsec", "audit engineer"),
    "data": ("data engineer", "analytics engineer", "data platform"),
    "ml-ai": ("machine learning", "ml engineer", "ai engineer"),
    "devrel": ("developer relations", "developer advocate", "devrel"),
    "backend": ("backend", "back-end", "back end", "server", "api engineer"),
}
KNOWN_TECH = (
    "aws", "azure", "c++", "docker", "ethereum", "evm", "gcp", "go", "golang",
    "java", "javascript", "kafka", "kubernetes", "move", "node.js", "postgres",
    "python", "react", "redis", "rust", "solidity", "sql", "terraform", "typescript",
)
US_STATE_PATTERN = re.compile(
    r",\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b",
    re.IGNORECASE,
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(value: Any) -> str:
    parser = _TextExtractor()
    parser.feed(html.unescape(str(value or "")))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_json(url: str, timeout: int) -> Any:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def greenhouse_url(token: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{quote(token)}/jobs?content=true"


def lever_url(token: str) -> str:
    return f"https://api.lever.co/v0/postings/{quote(token)}?mode=json"


def ashby_url(token: str) -> str:
    return f"https://api.ashbyhq.com/posting-api/job-board/{quote(token)}"


def source_endpoint(source: dict[str, Any]) -> str:
    provider = source["provider"].lower()
    token = source["token"]
    if provider == "greenhouse":
        return greenhouse_url(token)
    if provider == "lever":
        return lever_url(token)
    if provider == "ashby":
        return ashby_url(token)
    raise ValueError(f"Unsupported provider: {provider}")


def load_source_payload(source: dict[str, Any], timeout: int, fixture_dir: Path | None) -> Any:
    if fixture_dir:
        fixture = fixture_dir / f"{source['provider']}-{source['token']}.json"
        with fixture.open(encoding="utf-8") as handle:
            return json.load(handle)
    return fetch_json(source_endpoint(source), timeout)


def base_job(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "company": source["company"],
        "industry_category": source["industry_category"],
        "source_provider": source["provider"],
    }


def normalize_greenhouse(payload: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = []
    for raw in payload.get("jobs", []):
        job = base_job(source)
        job.update({
            "title": raw.get("title", ""),
            "url": raw.get("absolute_url", ""),
            "location": (raw.get("location") or {}).get("name", "Unspecified"),
            "description": plain_text(raw.get("content")),
            "published_at": raw.get("updated_at"),
        })
        jobs.append(job)
    return jobs


def normalize_lever(payload: list[dict[str, Any]], source: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = []
    for raw in payload:
        categories = raw.get("categories") or {}
        lists = " ".join(
            f"{item.get('text', '')} {plain_text(item.get('content', ''))}"
            for item in raw.get("lists", [])
        )
        job = base_job(source)
        job.update({
            "title": raw.get("text", ""),
            "url": raw.get("hostedUrl") or raw.get("applyUrl", ""),
            "location": categories.get("location") or raw.get("workplaceType") or "Unspecified",
            "description": plain_text(f"{raw.get('descriptionPlain', '')} {lists} {raw.get('additionalPlain', '')}"),
            "published_at": epoch_ms(raw.get("createdAt")),
        })
        jobs.append(job)
    return jobs


def normalize_ashby(payload: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = []
    for raw in payload.get("jobs", []):
        location = raw.get("location") or "Unspecified"
        if raw.get("isRemote") and "remote" not in location.lower():
            location = f"Remote - {location}"
        job = base_job(source)
        job.update({
            "title": raw.get("title", ""),
            "url": raw.get("jobUrl") or raw.get("applyUrl", ""),
            "location": location,
            "description": plain_text(raw.get("descriptionPlain") or raw.get("descriptionHtml")),
            "published_at": raw.get("publishedAt"),
        })
        jobs.append(job)
    return jobs


def epoch_ms(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).replace(microsecond=0).isoformat()


def normalize(payload: Any, source: dict[str, Any]) -> list[dict[str, Any]]:
    provider = source["provider"].lower()
    if provider == "greenhouse":
        return normalize_greenhouse(payload, source)
    if provider == "lever":
        return normalize_lever(payload, source)
    if provider == "ashby":
        return normalize_ashby(payload, source)
    raise ValueError(f"Unsupported provider: {provider}")


def terms(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#.]+", value.lower()))


def contains_phrase(text: str, phrase: str) -> bool:
    phrase = phrase.lower().strip()
    if not phrase:
        return False
    if len(phrase) <= 2 or re.search(r"[^a-z0-9 ]", phrase):
        return phrase in text
    return bool(re.search(rf"\b{re.escape(phrase)}\b", text))


def classify_role(title: str, description: str) -> str:
    value = f"{title} {description[:1200]}".lower()
    for family, markers in ROLE_RULES.items():
        if any(marker in value for marker in markers):
            return family
    return "other"


def infer_seniority(title: str) -> str:
    value = title.lower()
    if any(item in value for item in ("principal", "staff", "lead")):
        return "staff"
    if "senior" in value or re.search(r"\bsr\.?\b", value):
        return "senior"
    if any(item in value for item in ("junior", "entry", "new grad", "associate")):
        return "junior"
    return "mid"


def is_engineering_job(job: dict[str, Any], profile: dict[str, Any]) -> bool:
    title_terms = terms(job["title"])
    if not title_terms & ENGINEERING_TERMS:
        return False
    target_text = " ".join(str(item).lower() for item in profile.get("target_roles", []))
    title = job["title"].lower()
    if any(marker in title for marker in ("service desk", "it support", "technical support", "customer support")):
        return False
    if "manager" not in target_text and re.search(r"\b(manager|director|head of|vp)\b", title):
        return False
    if "product" not in target_text and "product manager" in title:
        return False
    if any(marker in title for marker in SOFTWARE_TITLE_MARKERS):
        return True
    body = job["description"].lower()
    evidence = sum(
        marker in body
        for marker in ("software development", "source code", "distributed systems", "backend", "api", "blockchain")
    )
    return "engineer" in title and evidence >= 2


def location_match(profile: dict[str, Any], location: str) -> tuple[int, list[str], bool]:
    pref = str(profile.get("remote_preference", "")).lower()
    desired = str(profile.get("location", "")).lower().strip()
    loc = location.lower()
    points = 0
    reasons = []
    wants_remote = "remote" in pref
    is_remote = "remote" in loc or "anywhere" in loc
    if wants_remote and is_remote:
        points += 5
        reasons.append("remote preference matches")
    elif wants_remote:
        points -= 8
        reasons.append("remote preference is not confirmed")

    if not desired:
        points += 5
        reasons.append("location not constrained")
    else:
        aliases = [desired]
        targets_us = desired in {"united states", "united states of america", "us", "usa", "u.s."}
        if targets_us:
            aliases = ["united states", "usa", "u.s.", " us ", "north america"]
        padded_location = f" {loc} "
        if any(alias in padded_location for alias in aliases) or (targets_us and US_STATE_PATTERN.search(location)):
            points += 5
            reasons.append("location matches")
        elif loc.strip() in {"remote", "anywhere", "unspecified"}:
            points += 1
            reasons.append("country eligibility needs review")
        else:
            points -= 15
            reasons.append("location appears outside the target region")
            return points, reasons, False
    return points, reasons, True


def required_years(description: str) -> int | None:
    values = [int(value) for value in re.findall(r"\b(\d{1,2})\s*\+?\s*years?\b", description.lower())]
    return min(values) if values else None


def score_job(job: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    title = job["title"].lower()
    body = f"{job['title']} {job['description']}".lower()
    role_family = classify_role(job["title"], job["description"])
    score = 15
    reasons = ["official ATS posting"]

    targets = [str(item).lower() for item in profile.get("target_roles", [])]
    role_hits = [target for target in targets if contains_phrase(title, target) or target == role_family]
    if role_hits:
        score += 25
        reasons.append(f"target role match: {', '.join(role_hits[:3])}")
    elif any(token in title for target in targets for token in terms(target)):
        score += 14
        reasons.append("partial target role match")

    skills = [str(item).lower() for item in profile.get("skills", [])]
    skill_hits = [skill for skill in skills if contains_phrase(body, skill)]
    if skills:
        score += round(25 * len(skill_hits) / len(skills))
        if skill_hits:
            reasons.append(f"skills found: {', '.join(skill_hits[:5])}")
    else:
        score += 8

    industries = [str(item).lower() for item in profile.get("industries", [])]
    if not industries:
        score += 10
    elif job["industry_category"].lower() in industries:
        score += 15
        reasons.append(f"industry match: {job['industry_category']}")

    location_points, location_reasons, location_eligible = location_match(profile, job["location"])
    score += location_points
    reasons.extend(location_reasons)

    desired_seniority = str(profile.get("seniority", "")).lower()
    actual_seniority = infer_seniority(job["title"])
    if not desired_seniority:
        score += 5
    elif desired_seniority in actual_seniority or actual_seniority in desired_seniority:
        score += 10
        reasons.append(f"seniority match: {actual_seniority}")
    else:
        score += 2

    experience = profile.get("years_experience")
    minimum_experience = required_years(job["description"])
    if isinstance(experience, (int, float)) and minimum_experience is not None:
        if experience >= minimum_experience:
            score += 5
            reasons.append(f"meets stated {minimum_experience}+ years experience")
        elif minimum_experience - experience <= 1:
            reasons.append(f"slightly below stated {minimum_experience}+ years experience")
        else:
            score -= min(20, 5 * int(minimum_experience - experience))
            reasons.append(f"below stated {minimum_experience}+ years experience")

    excluded_keywords = [str(item).lower() for item in profile.get("excluded_keywords", [])]
    excluded_hits = [item for item in excluded_keywords if contains_phrase(body, item)]
    if excluded_hits:
        score -= min(30, 12 * len(excluded_hits))
        reasons.append(f"excluded requirement found: {', '.join(excluded_hits[:3])}")

    gaps = [tech for tech in KNOWN_TECH if contains_phrase(body, tech) and tech not in skills]
    score = max(0, min(100, score))
    priority = "High" if score >= 80 else "Medium" if score >= 65 else "Exploratory"
    result = dict(job)
    result.update({
        "role_family": role_family,
        "seniority": actual_seniority,
        "match_score": score,
        "match_rationale": "; ".join(reasons),
        "matched_skills": skill_hits,
        "gaps": gaps[:5],
        "application_priority": priority,
        "location_eligible": location_eligible,
    })
    return result


def discover(profile: dict[str, Any], sources: list[dict[str, Any]], timeout: int,
             fixture_dir: Path | None = None) -> dict[str, Any]:
    fetched_at = now_iso()
    jobs: list[dict[str, Any]] = []
    source_results = []
    errors = []
    excluded_companies = {str(item).lower() for item in profile.get("excluded_companies", [])}

    for source in sources:
        if source.get("enabled", True) is False or source["company"].lower() in excluded_companies:
            continue
        try:
            payload = load_source_payload(source, timeout, fixture_dir)
            normalized = normalize(payload, source)
            jobs.extend(normalized)
            source_results.append({
                "label": f"{source['company']} careers ({source['provider']})",
                "url": source_endpoint(source),
                "retrieved_at": fetched_at,
                "job_count": len(normalized),
            })
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, HTTPError, URLError) as exc:
            errors.append({"company": source.get("company", "Unknown"), "error": str(exc)})

    unique: dict[str, dict[str, Any]] = {}
    for job in jobs:
        if not is_engineering_job(job, profile) or not job.get("url"):
            continue
        key = job["url"].split("?")[0].rstrip("/").lower()
        unique[key] = job

    ranked = [score_job(job, profile) for job in unique.values()]
    if profile.get("strict_location", True):
        ranked = [job for job in ranked if job["location_eligible"]]
    min_score = int(profile.get("min_score", 35))
    ranked = [job for job in ranked if job["match_score"] >= min_score]
    ranked.sort(key=lambda item: (-item["match_score"], item["company"], item["title"]))
    max_results = int(profile.get("max_results", 20))
    max_per_company = int(profile.get("max_per_company", 5))
    selected = []
    company_counts: dict[str, int] = {}
    for job in ranked:
        company_key = job["company"].lower()
        if company_counts.get(company_key, 0) >= max_per_company:
            continue
        selected.append(job)
        company_counts[company_key] = company_counts.get(company_key, 0) + 1
        if len(selected) >= max_results:
            break
    ranked = selected
    for rank, job in enumerate(ranked, 1):
        job["rank"] = rank

    assumptions = []
    if not profile.get("industries"):
        assumptions.append("All configured finance and blockchain industry categories were included.")
    if not profile.get("remote_preference") and not profile.get("location"):
        assumptions.append("No location filter was applied.")
    if not profile.get("seniority"):
        assumptions.append("All seniority levels were considered.")
    if profile.get("constraints"):
        assumptions.append(
            "Free-form constraints require manual verification: "
            + "; ".join(str(item) for item in profile["constraints"])
        )

    return {
        "generated_at": fetched_at,
        "query": profile,
        "assumptions": assumptions,
        "roles": ranked,
        "sources": source_results,
        "source_errors": errors,
        "stats": {
            "sources_attempted": len(source_results) + len(errors),
            "sources_succeeded": len(source_results),
            "postings_fetched": len(jobs),
            "engineering_postings": len(unique),
            "roles_returned": len(ranked),
        },
    }


def markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# Finance and Blockchain Job Discovery Report",
        "",
        f"Generated: {result['generated_at']}",
        "",
        "## Ranked Roles",
        "",
        "| Rank | Company | Role | Location | Category | Score | Priority |",
        "| ---: | --- | --- | --- | --- | ---: | --- |",
    ]
    for job in result["roles"]:
        title = job["title"].replace("|", "\\|")
        location = job["location"].replace("|", "\\|")
        lines.append(
            f"| {job['rank']} | {job['company']} | [{title}]({job['url']}) | "
            f"{location} | {job['industry_category']} | {job['match_score']} | "
            f"{job['application_priority']} |"
        )
    if not result["roles"]:
        lines.append("| - | - | No matching roles found | - | - | - | - |")

    lines.extend(["", "## Match Notes", ""])
    for job in result["roles"][:10]:
        lines.append(f"- **{job['company']} - {job['title']}**: {job['match_rationale']}.")
        if job["gaps"]:
            lines.append(f"  Potential keywords to verify: {', '.join(job['gaps'])}.")

    lines.extend(["", "## Sources", ""])
    for source in result["sources"]:
        lines.append(
            f"- [{source['label']}]({source['url']}) - {source['job_count']} postings, "
            f"retrieved {source['retrieved_at']}"
        )
    if result["source_errors"]:
        lines.extend(["", "## Source Errors", ""])
        for error in result["source_errors"]:
            lines.append(f"- {error['company']}: {error['error']}")
    return "\n".join(lines) + "\n"


def read_json(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Profile JSON path, or - for stdin")
    parser.add_argument(
        "--sources", default=str(script_dir.parent / "sources.json"), help="ATS source catalog JSON"
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", help="Output path; stdout when omitted")
    parser.add_argument("--timeout", type=int, default=20, help="Per-source HTTP timeout in seconds")
    parser.add_argument("--fixture-dir", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        profile = read_json(args.input)
        sources_document = read_json(args.sources)
        sources = sources_document.get("sources", sources_document)
        if not profile.get("target_roles"):
            raise ValueError("input.target_roles must contain at least one role")
        result = discover(profile, sources, args.timeout, args.fixture_dir)
        output = json.dumps(result, indent=2, ensure_ascii=True) + "\n" if args.format == "json" else markdown_report(result)
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
        return 0 if result["sources"] else 2
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
