"""Tests for seed_scoring.rewrite_exemplar_library_text and the
`alphamo score-seeds` CLI command (with mocked cascade)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from alphamo.evaluator import cascade as cascade_mod
from alphamo.evaluator.seed_scoring import rewrite_exemplar_library_text
from alphamo.main import cli
from alphamo.schemas.findings import (
    Severity,
    Stage1Finding,
    Stage2Finding,
    Stage3Finding,
    Stage4Finding,
    StructuralConcern,
)


# ----------------------------------------------------- rewrite text helper


SAMPLE_LIBRARY_TEXT = '''"""Reference exemplars docstring placeholder."""

from alphamo.schemas import Architecture, Scores


SATOSHI = Architecture(name="Satoshi", summary="x", value_chain="y", capture_mechanism="z", entry_resources="w")
ROWLING = Architecture(name="Rowling", summary="x", value_chain="y", capture_mechanism="z", entry_resources="w")
LEVELS = Architecture(name="Levels", summary="x", value_chain="y", capture_mechanism="z", entry_resources="w")
MEDVI = Architecture(name="Medvi", summary="x", value_chain="y", capture_mechanism="z", entry_resources="w")

EXEMPLARS = [SATOSHI, ROWLING, LEVELS, MEDVI]

# STARTERS robustness is hand-set to 0.85 (Phase 2). 1.0 would imply pristine,
# but these existence proofs all carry known fragilities — Satoshi depends on
# a 2009 launch window, Rowling on a cultural moment. 0.85 says "presumed
# reasonably robust as existence proofs, but with known fragilities".
_STARTER_ROBUSTNESS = 0.85

SATOSHI_SCORES = Scores(
    feasibility=0.95,
    structural=0.95,
    exemplar_similarity=1.00,
    robustness=_STARTER_ROBUSTNESS,
    middle_class_accessible=True,
)

ROWLING_SCORES = Scores(
    feasibility=0.85,
    structural=0.90,
    exemplar_similarity=0.95,
    robustness=_STARTER_ROBUSTNESS,
    middle_class_accessible=True,
)

LEVELS_SCORES = Scores(
    feasibility=0.90,
    structural=0.80,
    exemplar_similarity=0.85,
    robustness=_STARTER_ROBUSTNESS,
    middle_class_accessible=True,
)

MEDVI_SCORES = Scores(
    feasibility=0.90,
    structural=0.92,
    exemplar_similarity=0.90,
    robustness=_STARTER_ROBUSTNESS,
    middle_class_accessible=True,
)

STARTERS = [
    (SATOSHI, SATOSHI_SCORES),
    (ROWLING, ROWLING_SCORES),
    (LEVELS, LEVELS_SCORES),
    (MEDVI, MEDVI_SCORES),
]
'''


def _full_new_scores() -> dict:
    """Cover every *_SCORES block in SAMPLE_LIBRARY_TEXT — required by the
    strict mode in rewrite_exemplar_library_text."""
    return {
        "SATOSHI": {
            "feasibility": 0.91,
            "structural": 0.88,
            "exemplar_similarity": 1.00,
            "robustness": 0.62,
            "middle_class_accessible": True,
        },
        "ROWLING": {
            "feasibility": 0.78,
            "structural": 0.85,
            "exemplar_similarity": 0.91,
            "robustness": 0.71,
            "middle_class_accessible": True,
        },
        "LEVELS": {
            "feasibility": 0.83,
            "structural": 0.79,
            "exemplar_similarity": 0.81,
            "robustness": 0.68,
            "middle_class_accessible": True,
        },
        "MEDVI": {
            "feasibility": 0.88,
            "structural": 0.92,
            "exemplar_similarity": 0.84,
            "robustness": 0.45,
            "middle_class_accessible": True,
        },
    }


def test_rewrite_replaces_known_scores_blocks():
    out = rewrite_exemplar_library_text(
        SAMPLE_LIBRARY_TEXT,
        _full_new_scores(),
        generated_at="2026-05-15T00:00:00+00:00",
        parent_goal_version="v1",
        verifier_version="v1",
    )

    # New values present.
    assert "feasibility=0.9100" in out
    assert "robustness=0.6200" in out
    assert "feasibility=0.7800" in out
    assert "robustness=0.7100" in out
    assert "robustness=0.4500" in out  # Medvi
    # Old hand-picked numbers gone.
    assert "feasibility=0.95" not in out
    assert "_STARTER_ROBUSTNESS" not in out


def test_rewrite_drops_starter_robustness_constant_and_comment():
    out = rewrite_exemplar_library_text(
        SAMPLE_LIBRARY_TEXT,
        _full_new_scores(),
        generated_at="2026-05-15T00:00:00+00:00",
        parent_goal_version="v1",
        verifier_version="v1",
    )
    assert "_STARTER_ROBUSTNESS" not in out
    assert "STARTERS robustness is hand-set" not in out


def test_rewrite_inserts_provenance_header_above_first_block():
    out = rewrite_exemplar_library_text(
        SAMPLE_LIBRARY_TEXT,
        _full_new_scores(),
        generated_at="2026-05-15T12:00:00+00:00",
        parent_goal_version="v1",
        verifier_version="v3",
    )
    # Header sits above the first SATOSHI_SCORES block.
    header_idx = out.find("Cascade-produced seed scores")
    satoshi_idx = out.find("SATOSHI_SCORES = Scores(")
    assert header_idx != -1
    assert header_idx < satoshi_idx
    assert "2026-05-15T12:00:00+00:00" in out
    assert "verifier_version='v3'" in out


def test_rewrite_handles_robustness_none_for_short_circuit_seeds():
    """If a seed exits Stage 1 (middle-class filter), robustness is None and
    must be written literally as None — not as 0.0 or 'null'."""
    scores = _full_new_scores()
    scores["SATOSHI"] = {
        "feasibility": 0.3, "structural": 0.0, "exemplar_similarity": 0.0,
        "robustness": None, "middle_class_accessible": False,
    }
    out = rewrite_exemplar_library_text(
        SAMPLE_LIBRARY_TEXT,
        scores,
        generated_at="2026-05-15T00:00:00+00:00",
        parent_goal_version="v1",
        verifier_version="v1",
    )
    # SATOSHI block carries `robustness=None`.
    sat_block_start = out.find("SATOSHI_SCORES = Scores(")
    sat_block_end = out.find(")", sat_block_start)
    sat_block = out[sat_block_start:sat_block_end]
    assert "robustness=None" in sat_block
    assert "middle_class_accessible=False" in sat_block


def test_rewrite_raises_when_score_key_does_not_match_a_block():
    """Typo guard: a key in new_scores must correspond to an existing
    `<NAME>_SCORES =` block, else KeyError. Also flags any block that the
    caller forgot to score (strict mode in both directions).
    """
    # Typo: extra key with no matching block in the file.
    scores_with_typo = _full_new_scores()
    scores_with_typo["SATSHI_TYPO"] = scores_with_typo["SATOSHI"]
    with pytest.raises(KeyError, match="SATSHI_TYPO"):
        rewrite_exemplar_library_text(
            SAMPLE_LIBRARY_TEXT, scores_with_typo,
            generated_at="x", parent_goal_version="v1", verifier_version="v1",
        )

    # Omission: a block in the file isn't covered by new_scores.
    scores_missing_one = _full_new_scores()
    del scores_missing_one["MEDVI"]
    with pytest.raises(KeyError, match="MEDVI"):
        rewrite_exemplar_library_text(
            SAMPLE_LIBRARY_TEXT, scores_missing_one,
            generated_at="x", parent_goal_version="v1", verifier_version="v1",
        )


def test_rewrite_output_compiles_as_python():
    """Final smoke check: the rewritten text is valid Python that imports
    cleanly. Catches malformed Scores constructor output."""
    out = rewrite_exemplar_library_text(
        SAMPLE_LIBRARY_TEXT,
        _full_new_scores(),
        generated_at="2026-05-15T00:00:00+00:00",
        parent_goal_version="v1",
        verifier_version="v1",
    )
    compile(out, "<rewritten>", "exec")


# ----------------------------------------------------- CLI command (mocked cascade)


def _stub_cascade_for_score_seeds(monkeypatch):
    """Mock every stage to return controlled findings; verify the CLI
    invokes the cascade and produces the right output."""

    monkeypatch.setattr(
        cascade_mod,
        "stage1_feasibility",
        lambda a, c: Stage1Finding(
            feasibility=0.91,
            middle_class_accessible=True,
            reasoning=f"stub s1 for {a.name}",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage2_structured",
        lambda a, c: Stage2Finding(
            one_person_threshold=0.88,
            billion_dollar_potential=0.88,
            labor_separation=0.88,
            structural=0.88,
            reasoning=f"stub s2 for {a.name}",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage3_exemplars",
        lambda a, c: Stage3Finding(
            closest_exemplar=a.name,
            similarity=0.95,
            reasoning=f"stub s3 for {a.name}",
        ),
    )
    monkeypatch.setattr(
        cascade_mod,
        "stage4_adversarial",
        lambda a, c, **kw: Stage4Finding(
            robustness=0.72,
            concerns=[
                StructuralConcern(
                    framing="economic",
                    claim=f"economic concern for {a.name}",
                    evidence="ev",
                    falsification_condition="if x",
                    severity=Severity.MEDIUM,
                )
            ],
            reasoning=f"stub s4 for {a.name}",
        ),
    )


def test_score_seeds_dry_run_does_not_modify_exemplar_library(monkeypatch, tmp_path):
    """--no-write must not touch the library file but must still print verbose output."""
    import alphamo.evaluator.exemplar_library as exlib_module

    library_path = Path(exlib_module.__file__)
    original_bytes = library_path.read_bytes()

    _stub_cascade_for_score_seeds(monkeypatch)
    monkeypatch.setattr(
        "anthropic.Anthropic", lambda *a, **k: MagicMock()
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["score-seeds", "--no-write"])

    assert result.exit_code == 0, result.output
    assert library_path.read_bytes() == original_bytes
    # Verbose output produced per seed.
    assert "=== Satoshi ===" in result.output
    assert "=== Rowling ===" in result.output
    assert "Stage 1 (Haiku" in result.output
    assert "Stage 4 (Opus" in result.output
    assert "robustness    = 0.7200" in result.output
    assert "--no-write: skipped writing exemplar_library.py" in result.output


def test_score_seeds_writes_back_via_real_rewrite(monkeypatch, tmp_path):
    """`--write` invokes rewrite_exemplar_library_text on the real library.

    We can't safely test against the production file (it would mutate the
    repo). Instead, point exemplar_library.__file__ at a fixture copy and
    verify that gets rewritten.
    """
    fixture_path = tmp_path / "fake_exemplar_library.py"
    fixture_path.write_text(SAMPLE_LIBRARY_TEXT)

    import alphamo.evaluator.exemplar_library as exlib_module

    monkeypatch.setattr(exlib_module, "__file__", str(fixture_path))

    _stub_cascade_for_score_seeds(monkeypatch)
    monkeypatch.setattr(
        "anthropic.Anthropic", lambda *a, **k: MagicMock()
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["score-seeds", "--write"])

    assert result.exit_code == 0, result.output
    rewritten = fixture_path.read_text()
    # Cascade-stub scores: feasibility=0.91, structural=0.88, exemplar=0.95, robustness=0.72.
    assert "feasibility=0.9100" in rewritten
    assert "robustness=0.7200" in rewritten
    assert "_STARTER_ROBUSTNESS" not in rewritten
    assert "Cascade-produced seed scores" in rewritten
    # Original hand-picked values gone.
    assert "feasibility=0.95" not in rewritten


def test_score_seeds_emits_report_json_when_requested(monkeypatch, tmp_path):
    """--report-out PATH writes a structured JSON report of every stage's
    output across all seeds, suitable for archiving alongside the run."""
    import json

    _stub_cascade_for_score_seeds(monkeypatch)
    monkeypatch.setattr(
        "anthropic.Anthropic", lambda *a, **k: MagicMock()
    )

    report_path = tmp_path / "scoring_report.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["score-seeds", "--no-write", "--report-out", str(report_path)],
    )

    assert result.exit_code == 0, result.output
    assert report_path.exists()
    payload = json.loads(report_path.read_text())
    assert "generated_at" in payload
    assert "seeds" in payload
    assert len(payload["seeds"]) >= 2  # at least the seeds we have
    sample_seed = payload["seeds"][0]
    assert "stage1" in sample_seed
    assert "stage2" in sample_seed
    assert "stage3" in sample_seed
    assert "stage4" in sample_seed
    assert sample_seed["scores"]["robustness"] == 0.72
