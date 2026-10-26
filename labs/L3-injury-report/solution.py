"""L3 reference solution: read the week 4 injury report as a PDF, by file id, and from a photo.

Run from labs/ (each command is one step of the lab):
  uv run python L3-injury-report/solution.py count                    # tokens per page, free
  uv run python L3-injury-report/solution.py extract                  # base64 PDF -> InjuryReport, scored
  uv run python L3-injury-report/solution.py upload                   # Files API, expires in 24 hours
  uv run python L3-injury-report/solution.py ask                      # 3 cited questions on the file id
  uv run python L3-injury-report/solution.py extract --via file       # same extraction, by file id
  uv run python L3-injury-report/solution.py photo path/to/photo.jpg  # a phone photo of the printout
  uv run python L3-injury-report/solution.py cleanup                  # delete the upload
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gridiron.client import MODEL, client, log_usage
from l3_report import REPORT_PDF, InjuryReport, image_block, pdf_base64_block, pdf_file_block, score

LAB_DIR = Path(__file__).resolve().parent
UPLOAD_FILE = LAB_DIR / "out" / "upload.json"
EXPIRES_IN = 24 * 3600  # the report holds health information: keep it no longer than the job needs

EXTRACT_REQUEST = (
    "Extract every player row from this injury report. Copy names, injuries and statuses exactly as "
    "printed; don't infer anything that isn't on the page."
)
QUESTIONS = [
    "Which players are listed as Out or Doubtful, and for which teams?",
    "How did Elijah Mulroney practice this week?",
    "Which quarterbacks appear on the report, and why is each one listed?",
]


def check_stop(message: Any) -> None:
    if message.stop_reason == "refusal":
        raise RuntimeError("Claude declined the request (refusal).")
    if message.stop_reason == "max_tokens":
        raise RuntimeError("Output was cut off at max_tokens.")


def saved_file_id() -> str:
    if not UPLOAD_FILE.exists():
        raise SystemExit("No upload yet: run `upload` first.")
    return json.loads(UPLOAD_FILE.read_text())["id"]


def count() -> None:
    """count_tokens is free: measure a document before you send it a hundred times."""
    pdf = REPORT_PDF.read_bytes()
    total = client.messages.count_tokens(
        model=MODEL, messages=[{"role": "user", "content": [pdf_base64_block(pdf), {"type": "text", "text": "x"}]}]
    ).input_tokens
    print(f"{REPORT_PDF.name}: {len(pdf)} bytes, 2 pages -> {total} input tokens on {MODEL} (~{total // 2} per page)")
    print("Each page is sent as an image AND as extracted text, so pages cost more than their words suggest.")


def extract(via: str) -> None:
    document = pdf_file_block(saved_file_id()) if via == "file" else pdf_base64_block(REPORT_PDF.read_bytes())
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "low"},
        # The document comes first, the request last.
        messages=[{"role": "user", "content": [document, {"type": "text", "text": EXTRACT_REQUEST}]}],
        output_format=InjuryReport,
    )
    log_usage(f"extract via {via}", response.usage)
    check_stop(response)
    report_card(response.parsed_output)


def report_card(report: InjuryReport | None) -> None:
    if report is None:
        raise RuntimeError("No parsed output.")
    for e in report.entries:
        print(f"  {e.team} {e.player:<20} {e.position:<3} {e.injury:<20} {'/'.join(e.practice):<22} {e.game_status}")
    result = score(report)
    print(f"\nRows {result['rows_found']}/{result['rows_expected']}, field accuracy {result['field_accuracy']:.0%}")
    for problem in result["problems"]:
        print(f"  - {problem}")


def upload() -> None:
    meta = client.files.upload(
        file=(REPORT_PDF.name, REPORT_PDF.read_bytes(), "application/pdf"),
        expires_in_seconds=EXPIRES_IN,
    )
    UPLOAD_FILE.parent.mkdir(exist_ok=True)
    UPLOAD_FILE.write_text(json.dumps({"id": meta.id, "filename": meta.filename}, indent=2) + "\n")
    print(f"Uploaded {meta.filename} as {meta.id} ({meta.size_bytes} bytes, {meta.mime_type}), expires {meta.expires_at}")


def ask() -> None:
    """Several questions about one uploaded file: no re-upload, a cached document, cited answers."""
    document = pdf_file_block(
        saved_file_id(),
        title=f"Official Injury Report - Week 4 ({REPORT_PDF.name})",
        citations={"enabled": True},
        cache_control={"type": "ephemeral"},  # questions 2 and 3 read the document from the cache
    )
    for question in QUESTIONS:
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": [document, {"type": "text", "text": question}]}],
        )
        log_usage("ask", response.usage)
        check_stop(response)
        print(f"\nQ: {question}\nA: {cited_answer(response)}")


def cited_answer(message: Any) -> str:
    """Join the text blocks; mark each cited span with the pages it came from."""
    parts = []
    for block in message.content:
        if block.type != "text":
            continue
        pages = sorted({p for c in (block.citations or []) if c.type == "page_location"
                        for p in range(c.start_page_number, c.end_page_number)})  # fmt: skip
        parts.append(block.text + (f" [p. {', '.join(map(str, pages))}]" if pages else ""))
    return "".join(parts)


def photo(path: Path) -> None:
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": [image_block(path), {"type": "text", "text": EXTRACT_REQUEST}]}],
        output_format=InjuryReport,
    )
    log_usage("photo", response.usage)
    check_stop(response)
    report_card(response.parsed_output)


def cleanup() -> None:
    file_id = saved_file_id()
    client.files.delete(file_id)
    UPLOAD_FILE.unlink()
    remaining = [f.filename for f in client.files.list()]
    print(f"Deleted {file_id}. Files left in this workspace: {len(remaining)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="L3 injury report reader")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("count")
    e = sub.add_parser("extract")
    e.add_argument("--via", choices=["base64", "file"], default="base64")
    sub.add_parser("upload")
    sub.add_parser("ask")
    p = sub.add_parser("photo")
    p.add_argument("path", type=Path)
    sub.add_parser("cleanup")
    args = parser.parse_args()
    if args.command == "count":
        count()
    elif args.command == "extract":
        extract(args.via)
    elif args.command == "upload":
        upload()
    elif args.command == "ask":
        ask()
    elif args.command == "photo":
        photo(args.path)
    else:
        cleanup()


if __name__ == "__main__":
    main()
