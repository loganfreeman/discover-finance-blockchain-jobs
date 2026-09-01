import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("install_skills", ROOT / "scripts" / "install_skills.py")
install_skills = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(install_skills)


class InstallSkillsTest(unittest.TestCase):
    def test_discovers_repository_skills(self):
        skills = install_skills.discover_skills()
        self.assertEqual(
            set(skills),
            {
                "discover-finance-blockchain-jobs",
                "generate-weekly-market-report",
                "match-resume-to-jobs",
                "research-company-hiring-signal",
            },
        )

    def test_installs_selected_skill(self):
        skill = install_skills.discover_skills()["match-resume-to-jobs"]
        with tempfile.TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory) / ".agents" / "skills"
            summary = install_skills.install_skill(skill, target)
            self.assertIn("install:", summary)
            self.assertTrue((target / skill.name / "SKILL.md").is_file())

    def test_existing_skill_requires_force(self):
        skill = install_skills.discover_skills()["generate-weekly-market-report"]
        with tempfile.TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory)
            install_skills.install_skill(skill, target)
            with self.assertRaises(install_skills.InstallError):
                install_skills.install_skill(skill, target)
            summary = install_skills.install_skill(skill, target, force=True)
            self.assertIn("update:", summary)

    def test_dry_run_does_not_create_target(self):
        skill = install_skills.discover_skills()["research-company-hiring-signal"]
        with tempfile.TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory) / "missing"
            install_skills.install_skill(skill, target, dry_run=True)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
