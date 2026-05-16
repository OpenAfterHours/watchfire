"""Promote the ``## [Unreleased]`` section in ``CHANGELOG.md`` for a release.

Runs the four CI gates (``ruff check``, ``ruff format --check``,
``ty check``, ``pytest``) and, if all pass, rewrites
``## [Unreleased]`` to ``## [<new>] - <today>`` (Keep a Changelog flow)
and inserts a fresh empty ``## [Unreleased]`` header above it. Refuses to
run if the existing ``## [Unreleased]`` section has no entries; pass
``--allow-empty-changelog`` to override.

The package version itself lives in git tags (``hatch-vcs``) — there are no
version strings to rewrite. After promoting the changelog, the script
commits ``CHANGELOG.md`` with message ``chore: release <ver>`` and creates
a lightweight ``v<ver>`` tag locally. Pushing to the remote is left to
you: ``git push origin master --tags``.

Run from the repo root:

    uv run python scripts/bump_release.py 0.2.0
    uv run python scripts/bump_release.py 0.2.0 --skip-tests   # gates off for a dry run

A ``--dry-run`` flag prints the planned change without touching files
or git state.
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
    new: str


class BumpError(Exception):
    """Raised when the bump cannot proceed (bad input, dirty tree, gate failure)."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote CHANGELOG for a watchfire release.")
    parser.add_argument(
        "version",
        help="Target version, e.g. 0.2.0 or 0.2.0rc1.",
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
    args = parser.parse_args(argv)
    if not VERSION_RE.match(args.version):
        parser.error(
            f"target version {args.version!r} is not of the form MAJOR.MINOR.PATCH[suffix]"
        )
    return args


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


def check_tag_available(tag: str) -> None:
    """Refuse to release if ``tag`` already exists locally."""

    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        raise BumpError(
            f"tag {tag} already exists. Pick a different version, or delete the tag with "
            f"`git tag -d {tag}` if it was created in error."
        )


def commit_and_tag(bump: Bump) -> None:
    """Commit the promoted CHANGELOG and create a lightweight ``v<ver>`` tag."""

    tag = f"v{bump.new}"
    changelog_rel = CHANGELOG.relative_to(REPO_ROOT).as_posix()
    steps: list[tuple[str, list[str]]] = [
        ("git add CHANGELOG.md", ["git", "add", changelog_rel]),
        ("git commit", ["git", "commit", "-m", f"chore: release {bump.new}"]),
        (f"git tag {tag}", ["git", "tag", tag]),
    ]
    for label, cmd in steps:
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            raise BumpError(f"{label} failed: {stderr}")
    print(f"  committed CHANGELOG.md and tagged {tag}")


def run_gates() -> None:
    for label, cmd in GATES:
        print(f"==> {label}")
        result = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
        if result.returncode != 0:
            raise BumpError(f"{label} failed with exit code {result.returncode}")


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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        if not args.allow_dirty and not args.dry_run:
            check_clean_tree()

        bump = Bump(new=args.version)
        print(f"preparing watchfire release: {bump.new}")

        check_tag_available(f"v{bump.new}")

        if not args.allow_empty_changelog:
            check_changelog_has_entries()

        if args.dry_run:
            print("dry run: not running gates, not writing files, not tagging")
            return 0

        if not args.skip_tests:
            run_gates()
        else:
            print("warning: --skip-tests was set; gates were not run")

        _promote_changelog(bump, today=date.today())
        commit_and_tag(bump)
        print(
            f"\ndone. Review with `git show v{bump.new}`, then push:\n"
            f"    git push origin master --tags\n"
            f"Then create a GitHub Release from the v{bump.new} tag — "
            f"that triggers publish.yml."
        )
        return 0
    except BumpError as exc:
        print(f"bump_release: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
