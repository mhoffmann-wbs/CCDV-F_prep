"""L3 starter: read the week 4 injury report as a PDF, by file id, and from a photo.

Run from labs/ (each command is one step of the lab):
  uv run python L3-injury-report/starter.py count                    # tokens per page, free
  uv run python L3-injury-report/starter.py extract                  # base64 PDF -> InjuryReport, scored
  uv run python L3-injury-report/starter.py upload                   # Files API, expires in 24 hours
  uv run python L3-injury-report/starter.py ask                      # 3 cited questions on the file id
  uv run python L3-injury-report/starter.py extract --via file       # same extraction, by file id
  uv run python L3-injury-report/starter.py photo path/to/photo.jpg  # a phone photo of the printout
  uv run python L3-injury-report/starter.py cleanup                  # delete the upload

Each command explains itself until you fill in its TODO. Stuck? Compare with solution.py.
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
    # TODO 1: client.messages.count_tokens(model=MODEL, messages=[{"role": "user", "content":
    #   [pdf_base64_block(REPORT_PDF.read_bytes()), {"type": "text", "text": "x"}]}]).input_tokens
    #   Print the total and the tokens per page (the report has 2 pages). More than you expected?
    raise NotImplementedError("TODO 1: count")


def extract(via: str) -> None:
    # TODO 2: build the document block: pdf_base64_block(REPORT_PDF.read_bytes()), or
    #   pdf_file_block(saved_file_id()) when via == "file". Then
    #   client.messages.parse(model=MODEL, max_tokens=16000, output_config={"effort": "low"},
    #       messages=[{"role": "user", "content": [document, {"type": "text", "text": EXTRACT_REQUEST}]}],
    #       output_format=InjuryReport)
    #   The document goes FIRST. log_usage, check_stop, then report_card(response.parsed_output).
    raise NotImplementedError("TODO 2: extract")


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
    # TODO 3: meta = client.files.upload(file=(REPORT_PDF.name, REPORT_PDF.read_bytes(), "application/pdf"),
    #   expires_in_seconds=EXPIRES_IN). Save {"id": meta.id, "filename": meta.filename} to UPLOAD_FILE
    #   and print the id, size and expires_at.
    raise NotImplementedError("TODO 3: upload")


def ask() -> None:
    """Several questions about one uploaded file: no re-upload, a cached document, cited answers."""
    # TODO 4: build ONE pdf_file_block(saved_file_id(), title=..., citations={"enabled": True},
    #   cache_control={"type": "ephemeral"}). For each of QUESTIONS, call client.messages.create with
    #   [document, question] as the user content, log_usage, check_stop, and print cited_answer(response).
    #   Watch the usage lines: the first call writes the cache, the next two read it.
    raise NotImplementedError("TODO 4: ask")


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
    # TODO 5: the same parse call as extract, with image_block(path) instead of the document.
    raise NotImplementedError("TODO 5: photo")


def cleanup() -> None:
    # TODO 6: client.files.delete(saved_file_id()), remove UPLOAD_FILE, and print how many files
    #   client.files.list() still shows. Uploaded files stay until they expire or you delete them.
    raise NotImplementedError("TODO 6: cleanup")


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
    try:
        run(args)
    except NotImplementedError as todo:
        print(f"Not built yet: {todo}. No API calls were made.")


def run(args: argparse.Namespace) -> None:
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
