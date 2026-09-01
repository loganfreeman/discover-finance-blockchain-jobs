import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("discover_jobs", ROOT / "scripts" / "discover_jobs.py")
discover_jobs = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(discover_jobs)


class DiscoverJobsTest(unittest.TestCase):
    def setUp(self):
        self.fixtures = Path(__file__).parent / "fixtures"
        self.sources = [
            {"company": "DemoPay", "industry_category": "fintech", "provider": "greenhouse", "token": "demo"},
            {"company": "DemoChain", "industry_category": "blockchain-infra", "provider": "lever", "token": "demo"},
            {"company": "DemoProtocol", "industry_category": "blockchain-infra", "provider": "ashby", "token": "demo"},
        ]
        self.profile = {
            "target_roles": ["backend", "platform"],
            "industries": ["fintech", "blockchain-infra"],
            "remote_preference": "remote",
            "skills": ["Go", "AWS", "Postgres"],
            "max_results": 10,
            "min_score": 0,
        }

    def test_all_providers_normalize_and_rank(self):
        result = discover_jobs.discover(self.profile, self.sources, 1, self.fixtures)
        self.assertEqual(result["stats"]["sources_succeeded"], 3)
        self.assertEqual(result["stats"]["postings_fetched"], 4)
        self.assertEqual(result["stats"]["engineering_postings"], 3)
        self.assertEqual(len(result["roles"]), 3)
        self.assertEqual(result["roles"][0]["company"], "DemoPay")
        self.assertTrue(all(job["url"].startswith("https://") for job in result["roles"]))

    def test_source_failure_is_reported_without_losing_results(self):
        sources = self.sources + [
            {"company": "Missing", "industry_category": "fintech", "provider": "ashby", "token": "missing"}
        ]
        result = discover_jobs.discover(self.profile, sources, 1, self.fixtures)
        self.assertEqual(len(result["source_errors"]), 1)
        self.assertEqual(len(result["roles"]), 3)

    def test_json_serializable_and_markdown_contains_links(self):
        result = discover_jobs.discover(self.profile, self.sources, 1, self.fixtures)
        json.dumps(result)
        report = discover_jobs.markdown_report(result)
        self.assertIn("[Backend Engineer, Payments](https://example.test/jobs/greenhouse-backend)", report)


if __name__ == "__main__":
    unittest.main()
