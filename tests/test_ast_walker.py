"""Tests for the AST walker.

The walker is what powers ``regcite check`` — getting line numbers,
function names, and the resolved/unresolved/malformed bucketing right
matters because those are the things a user sees in error messages.
"""

from __future__ import annotations

from pathlib import Path

from regcite import Citation
from regcite.ast_walker import (
    CitationFinding,
    ParseFailure,
    UnresolvedCitation,
    find_citations,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "sample_project"


def _by_type(findings):
    out: dict[type, list] = {CitationFinding: [], ParseFailure: [], UnresolvedCitation: []}
    for f in findings:
        out[type(f)].append(f)
    return out


class TestSAFile:
    def test_finds_all_sa_citations(self):
        findings = find_citations([FIXTURE_ROOT / "sa.py"])
        successes = [f for f in findings if isinstance(f, CitationFinding)]
        assert len(successes) == 3
        names = {f.function for f in successes}
        assert names == {"calculate_sa_rwa", "sovereign_rw", "exposure_value_sa"}

    def test_line_numbers_point_at_decorator(self):
        findings = find_citations([FIXTURE_ROOT / "sa.py"])
        funcs = {f.function: f.line for f in findings if isinstance(f, CitationFinding)}
        # The decorator is on the line above the def, and ast records
        # the decorator's own lineno on the @-line.
        source = (FIXTURE_ROOT / "sa.py").read_text().splitlines()
        for name, line in funcs.items():
            assert "cites" in source[line - 1], (name, line, source[line - 1])


class TestIRBFile:
    def test_finds_qualified_decorator(self):
        # irb.py uses `@regcite.cites(...)` rather than the bare name.
        findings = find_citations([FIXTURE_ROOT / "irb.py"])
        successes = [f for f in findings if isinstance(f, CitationFinding)]
        assert len(successes) == 4

    def test_resolves_citations_correctly(self):
        findings = find_citations([FIXTURE_ROOT / "irb.py"])
        by_name = {f.function: f.citation for f in findings if isinstance(f, CitationFinding)}
        assert by_name["corporate_rw"] == Citation(
            instrument="CRR", article=153, paragraph=1, point="a"
        )
        assert by_name["retail_rw"] == Citation(instrument="CRR", article=154, paragraph=1)
        assert by_name["model_validation"].instrument == "SS"
        assert by_name["model_validation"].instrument_id == "SS1/23"
        assert by_name["model_validation"].section == (2, 5)
        assert by_name["is_corporate"].point == "75"


class TestDynamicAndMalformed:
    def test_unresolved_non_literal(self):
        findings = find_citations([FIXTURE_ROOT / "dynamic.py"])
        bucket = _by_type(findings)
        unresolved_names = {f.function for f in bucket[UnresolvedCitation]}
        assert "dynamic_string" in unresolved_names

    def test_parse_failure_reported(self):
        findings = find_citations([FIXTURE_ROOT / "dynamic.py"])
        bucket = _by_type(findings)
        failures = {f.function: f for f in bucket[ParseFailure]}
        assert "malformed_string" in failures
        assert "CRR Article zero" in failures["malformed_string"].raw

    def test_citation_constructor_resolved(self):
        findings = find_citations([FIXTURE_ROOT / "dynamic.py"])
        bucket = _by_type(findings)
        successes = {f.function: f.citation for f in bucket[CitationFinding]}
        assert successes["constructed_literal"] == Citation(instrument="CRR", article=92)

    def test_undecorated_function_not_reported(self):
        findings = find_citations([FIXTURE_ROOT / "dynamic.py"])
        all_names = {f.function for f in findings}
        assert "not_decorated" not in all_names


class TestDirectoryWalk:
    def test_walks_directory_recursively(self):
        findings = find_citations([FIXTURE_ROOT])
        successes = [f for f in findings if isinstance(f, CitationFinding)]
        # 3 from sa.py + 4 from irb.py + 1 from dynamic.py = 8
        assert len(successes) == 8

    def test_findings_are_deterministic_order(self):
        a = find_citations([FIXTURE_ROOT])
        b = find_citations([FIXTURE_ROOT])
        assert [(f.file.name, f.line, f.function) for f in a] == [
            (f.file.name, f.line, f.function) for f in b
        ]


class TestMissingPath:
    def test_missing_path_yields_no_findings(self):
        findings = find_citations([FIXTURE_ROOT.parent / "does_not_exist"])
        assert findings == []

    def test_single_file_path_works(self):
        findings = find_citations([str(FIXTURE_ROOT / "sa.py")])
        assert any(isinstance(f, CitationFinding) for f in findings)


class TestStaticOnly:
    def test_does_not_import_user_code(self, tmp_path):
        # Write a file whose import would explode. The walker should
        # still parse it and find the decorator.
        bad = tmp_path / "boom.py"
        bad.write_text(
            "from regcite import cites\n"
            "raise RuntimeError('importing me would explode')\n"
            "@cites('CRR Art. 92')\n"
            "def f():\n"
            "    pass\n"
        )
        findings = find_citations([tmp_path])
        successes = [f for f in findings if isinstance(f, CitationFinding)]
        assert len(successes) == 1
        assert successes[0].citation.article == 92
