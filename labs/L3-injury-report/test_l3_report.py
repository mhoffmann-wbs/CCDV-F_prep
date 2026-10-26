import base64
import importlib.util
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from l3_report import (
    REPORT_PDF,
    TRUTH,
    InjuryReport,
    build_pdf,
    image_block,
    pdf_base64_block,
    pdf_file_block,
    score,
)

from gridiron.data import load_injuries, load_players

_spec = importlib.util.spec_from_file_location("l3_solution", Path(__file__).with_name("solution.py"))
solution = importlib.util.module_from_spec(_spec)
sys.modules["l3_solution"] = solution
_spec.loader.exec_module(solution)


def test_committed_pdf_matches_the_generator():
    assert REPORT_PDF.read_bytes() == build_pdf(), "run build_pdf() and commit the new file"


def test_pdf_is_well_formed_with_two_pages_and_a_valid_xref():
    pdf = build_pdf()
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    assert b"/Count 2" in pdf
    xref_at = int(re.search(rb"startxref\n(\d+)", pdf).group(1))
    assert pdf[xref_at:].startswith(b"xref")
    offsets = [int(o) for o in re.findall(rb"(\d{10}) 00000 n", pdf)]
    for number, offset in enumerate(offsets, start=1):
        assert pdf[offset:].startswith(f"{number} 0 obj".encode())


def test_every_row_is_printed():
    text = build_pdf().decode("latin-1")
    for e in TRUTH.entries:
        assert f"({e.player})" in text and f"({e.injury})" in text


def test_truth_agrees_with_the_league_fixtures():
    players = {p.name: p for p in load_players()}
    injuries = {i.player_id: i for i in load_injuries()}
    for e in TRUTH.entries:
        p = players[e.player]
        assert (p.team, p.position) == (e.team, e.position)
        if p.id in injuries:
            designation = injuries[p.id].designation
            expected = "No status" if designation == "Full" else designation
            assert e.game_status == expected, e.player
    assert {i.player_id for i in load_injuries()} <= {players[e.player].id for e in TRUTH.entries}


def test_schema_leaves_list_lengths_to_code():
    schema = str(InjuryReport.model_json_schema())
    assert "minItems" not in schema and "maxItems" not in schema


def test_perfect_extraction_scores_100_percent():
    assert score(TRUTH) == {"field_accuracy": 1.0, "rows_found": 8, "rows_expected": 8, "problems": []}


def test_score_reports_each_kind_of_mistake():
    bad = TRUTH.model_copy(deep=True)
    bad.entries[0].game_status = "Doubtful"
    bad.entries[1].practice = ["Limited", "Full"]
    bad.entries[2].player = "  marcus   holloway "  # whitespace and case don't matter
    del bad.entries[5]
    bad.entries.append(bad.entries[0].model_copy(update={"player": "Ghost Player"}))
    result = score(bad)
    assert result["rows_found"] == 7
    assert sorted(result["problems"]) == sorted([
        "Devin Brightwater: game_status is 'Doubtful', expected 'Questionable'",
        "Cody Pruitt: 2 practice days, expected 3 (Wed, Thu, Fri)",
        "Cody Pruitt: practice is ['Limited', 'Full'], expected ['Limited', 'Full', 'Full']",
        "missing row: Darius Kincaid (NSH)",
        "extra row not in the report: Ghost Player (POR)",
    ])  # fmt: skip


def test_three_ways_to_send_the_document():
    b64 = pdf_base64_block(b"%PDF-test", title="t")
    assert b64["source"]["media_type"] == "application/pdf"
    assert base64.standard_b64decode(b64["source"]["data"]) == b"%PDF-test" and b64["title"] == "t"
    assert pdf_file_block("file_123", citations={"enabled": True}) == {
        "type": "document",
        "source": {"type": "file", "file_id": "file_123"},
        "citations": {"enabled": True},
    }


def test_image_block(tmp_path):
    photo = tmp_path / "report.JPG"
    photo.write_bytes(b"\xff\xd8fake")
    assert image_block(photo)["source"]["media_type"] == "image/jpeg"
    with pytest.raises(ValueError):
        image_block(tmp_path / "scan.bmp")


def test_cited_answer_marks_pages():
    def cite(start, end):
        return SimpleNamespace(type="page_location", start_page_number=start, end_page_number=end)

    message = SimpleNamespace(content=[
        SimpleNamespace(type="thinking"),
        SimpleNamespace(type="text", text="Kincaid is out", citations=[cite(2, 3)]),
        SimpleNamespace(type="text", text=" and Montague is doubtful.", citations=[cite(1, 2)]),
        SimpleNamespace(type="text", text=" Nobody else.", citations=None),
    ])  # fmt: skip
    assert solution.cited_answer(message) == "Kincaid is out [p. 2] and Montague is doubtful. [p. 1] Nobody else."
