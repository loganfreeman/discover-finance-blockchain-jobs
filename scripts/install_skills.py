#!/usr/bin/env python3
"""Install this repository's skills into the current user's Codex skill directory."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import NamedTuple


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPOSITORY_ROOT / "skills"
DEFAULT_TARGET = Path.home() / ".agents" / "skills"


class InstallError(RuntimeError):
    """Raised when a skill cannot be installed safely."""


class Skill(NamedTuple):
    name: str
    path: Path


def read_skill_name(skill_file: Path) -> str:
    """Read the required name field from a SKILL.md YAML frontmatter block."""
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise InstallError(f"{skill_file} does not start with YAML frontmatter")

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("name:"):
            name = stripped.partition(":")[2].strip().strip("'\"")
            if name:
                return name

    raise InstallError(f"{skill_file} has no frontmatter name")


def discover_skills(source: Path = DEFAULT_SOURCE) -> dict[str, Skill]:
    """Return valid immediate child skill directories, keyed by skill name."""
    if not source.is_dir():
        raise InstallError(f"skill source directory does not exist: {source}")

    discovered: dict[str, Skill] = {}
    for child in sorted(source.iterdir(), key=lambda item: item.name):
        skill_file = child / "SKILL.md"
        if not child.is_dir() or not skill_file.is_file():
            continue
        name = read_skill_name(skill_file)
        if name in discovered:
            raise InstallError(f"duplicate skill name {name!r} in {source}")
        discovered[name] = Skill(name=name, path=child)

    if not discovered:
        raise InstallError(f"no skills containing SKILL.md were found in {source}")
    return discovered


def select_skills(available: dict[str, Skill], requested: list[str]) -> list[Skill]:
    """Select requested skills, or every available skill when none are named."""
    if not requested:
        return list(available.values())

    unknown = sorted(set(requested) - available.keys())
    if unknown:
        choices = ", ".join(available)
        raise InstallError(f"unknown skill(s): {', '.join(unknown)}. Available: {choices}")
    return [available[name] for name in dict.fromkeys(requested)]


def install_skill(skill: Skill, target: Path, *, force: bool = False, dry_run: bool = False) -> str:
    """Copy one skill into the target directory and return an action summary."""
    destination = target / skill.name
    if destination.exists() and not force:
        raise InstallError(
            f"{skill.name} is already installed at {destination}; use --force to update it"
        )

    action = "update" if destination.exists() else "install"
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill.path, destination, dirs_exist_ok=force)
    return f"{action}: {skill.name} -> {destination}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install finance and blockchain skills into ~/.agents/skills."
    )
    parser.add_argument(
        "skills",
        nargs="*",
        metavar="SKILL",
        help="skill names to install (default: all)",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help=f"installation directory (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="update files in skills that are already installed",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be installed without writing files",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list the skills available in this repository and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        available = discover_skills()
        if args.list:
            for name in available:
                print(name)
            return 0

        selected = select_skills(available, args.skills)
        failures = 0
        for skill in selected:
            try:
                print(
                    install_skill(
                        skill,
                        args.target.expanduser(),
                        force=args.force,
                        dry_run=args.dry_run,
                    )
                )
            except InstallError as error:
                failures += 1
                print(f"error: {error}", file=sys.stderr)
        return 1 if failures else 0
    except InstallError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
