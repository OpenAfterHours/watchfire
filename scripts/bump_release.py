"""Bump the ``watchfire`` release version.

Runs the four CI gates (``ruff check``, ``ruff format --check``,
``ty check``, ``pytest``) and, if all pass, rewrites the two version
strings that must stay in sync:

- ``pyproject.toml``        (``[project] version``)
- ``src/watchfire/__init__.py``  (``__version__``)

It also promotes the ``## [Unreleased]`` section in ``CHANGELOG.md`` to
``## [<new>] - <today>`` (Keep a Changelog flow) and inserts a fresh
empty ``## [Unreleased]`` header above it. The script refuses to run
if the existing ``## [Unreleased]`` section has no entries; pass
``--allow-empty-changelog`` to override.

This script does not commit, tag, or push - inspect ``git diff`` after
it runs and create the release commit yourself.

Run from the repo root:

    uv run python scripts/bump_release.py 0.2.0
    uv run python scripts/bump_release.py --part minor
    uv run python scripts/bump_release.py --part patch --skip-tests   # gates off for a dry run

A ``--dry-run`` flag prints the planned change without touching files.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
INIT_PY = REPO_ROOT / "src" / "watchfire" / "__init__.py"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# The existing CHANGELOG uses an em dash between version and date. Mirror it.
CHANGELOG_DATE_SEP = "—"  # em dash

# PEP 440-ish: major.minor.patch with an optional pre/post/dev suffix
# (e.g. 0.2.0rc1, 0.2.0.dev3). Strict enough to reject typos, loose
# enough to allow the release flows we actually use.
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)([abc]\d+|rc\d+|\.dev\d+|\.post\d+)?$")

GATES: list[tuple[str, list[str]]] = [
    ("ruff check", ["uv", "run", "ruff", "check", "src/", "tests/"]),
    ("ruff format --check", ["uv", "run", "ruff", "format", "--check", "src/", "tests/"]),
    ("ty check", ["uv", "run", "ty", "check", "src/watchfire/"]),
    ("pytest", ["uv", "run", "pytest", "tests/"]),
]


@dataclass(frozen=True)
class Bump:
    old: str
    new: str


class BumpError(Exception):
    """Raised when the bump cannot proceed (bad input, dirty tree, gate failure)."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bump the watchfire release version.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "version",
        nargs="?",
        help="Explicit target version, e.g. 0.2.0 or 0.2.0rc1.",
    )
    target.add_argument(
        "--part",
        choices=["major", "minor", "patch"],
        help="Increment the named part of the current version.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip the four CI gates. Use only for dry runs.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Proceed even if the working tree has uncommitted changes.",
    )
    parser.add_argument(
        "--allow-empty-changelog",
        action="store_true",
        help="Promote ## [Unreleased] even if it has no entries underneath.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned bump and exit without writing files.",
    )
    return parser.parse_args(argv)


def read_current_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', text)
    if match is None:
        raise BumpError(f"could not find version in {PYPROJECT}")
    return match.group(1)


def compute_target(current: str, args: argparse.Namespace) -> str:
    if args.version is not None:
        if not VERSION_RE.match(args.version):
            raise BumpError(
                f"target version {args.version!r} is not of the form MAJOR.MINOR.PATCH[suffix]"
            )
        return args.version

    match = VERSION_RE.match(current)
    if match is None:
        raise BumpError(
            f"current version {current!r} does not match MAJOR.MINOR.PATCH — "
            "pass an explicit target instead of --part"
        )
    major, minor, patch = (int(match.group(i)) for i in (1, 2, 3))
    if args.part == "major":
        major, minor, patch = major + 1, 0, 0
    elif args.part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def check_clean_tree() -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise BumpError(f"git status failed: {result.stderr.strip()}")
    if result.stdout.strip():
        raise BumpError(
            "working tree is not clean. Commit or stash changes, or pass --allow-dirty.\n"
            f"{result.stdout}"
        )


def run_gates() -> None:
    for label, cmd in GATES:
        print(f"==> {label}")
        result = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
        if result.returncode != 0:
            raise BumpError(f"{label} failed with exit code {result.returncode}")


def apply_bump(bump: Bump, *, today: date) -> None:
    _rewrite(
        PYPROJECT,
        old_pattern=re.compile(rf'(?m)^version\s*=\s*"{re.escape(bump.old)}"\s*$'),
        new_line=f'version = "{bump.new}"',
        description="pyproject.toml [project] version",
    )
    _rewrite(
        INIT_PY,
        old_pattern=re.compile(rf'(?m)^__version__\s*=\s*"{re.escape(bump.old)}"\s*$'),
        new_line=f'__version__ = "{bump.new}"',
        description="src/watchfire/__init__.py __version__",
    )
    _promote_changelog(bump, today=today)


def check_changelog_has_entries() -> None:
    """Refuse to release if ## [Unreleased] has no content under it."""

    text = CHANGELOG.read_text(encoding="utf-8")
    body = _unreleased_body(text)
    if body is None:
        raise BumpError(
            f"could not find '## [Unreleased]' heading in {CHANGELOG.name}; "
            "is the changelog using Keep a Changelog format?"
        )
    if not body.strip():
        raise BumpError(
            f"{CHANGELOG.name} has an empty ## [Unreleased] section. "
            "Add entries or pass --allow-empty-changelog."
        )


def _unreleased_body(text: str) -> str | None:
    """Return the text between '## [Unreleased]' and the next '## [' heading."""

    match = re.search(r"(?m)^##[ \t]*\[Unreleased\][ \t]*$", text)
    if match is None:
        return None
    start = match.end()
    next_heading = re.search(r"(?m)^##[ \t]*\[", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def _promote_changelog(bump: Bump, *, today: date) -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    pattern = re.compile(r"(?m)^##[ \t]*\[Unreleased\][ \t]*$")
    new_heading = f"## [Unreleased]\n\n## [{bump.new}] {CHANGELOG_DATE_SEP} {today.isoformat()}"
    new_text, count = pattern.subn(new_heading, text, count=1)
    if count != 1:
        raise BumpError(
            f"could not promote ## [Unreleased] in {CHANGELOG.name}: "
            f"expected exactly one match, found {count}"
        )
    CHANGELOG.write_text(new_text, encoding="utf-8")
    print(f"  promoted ## [Unreleased] -> ## [{bump.new}] in CHANGELOG.md")


def _rewrite(path: Path, *, old_pattern: re.Pattern[str], new_line: str, description: str) -> None:
    text = path.read_text(encoding="utf-8")
    new_text, count = old_pattern.subn(new_line, text, count=1)
    if count != 1:
        raise BumpError(
            f"could not update {description}: expected exactly one match in {path.name}, found {count}"
        )
    path.write_text(new_text, encoding="utf-8")
    print(f"  rewrote {description}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        if not args.allow_dirty and not args.dry_run:
            check_clean_tree()

        current = read_current_version()
        target = compute_target(current, args)
        if target == current:
            raise BumpError(f"target version {target} matches current — nothing to do")

        bump = Bump(old=current, new=target)
        print(f"bumping watchfire: {bump.old} -> {bump.new}")

        if not args.allow_empty_changelog:
            check_changelog_has_entries()

        if args.dry_run:
            print("dry run: not running gates, not writing files")
            return 0

        if not args.skip_tests:
            run_gates()
        else:
            print("warning: --skip-tests was set; gates were not run")

        apply_bump(bump, today=date.today())
        print(
            f"\ndone. Review with `git diff`, then commit:\n"
            f"    git commit -am 'chore: release {bump.new}'\n"
            f"    git tag v{bump.new}"
        )
        return 0
    except BumpError as exc:
        print(f"bump_release: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
