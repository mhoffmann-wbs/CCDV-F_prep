"""Offline tests for the API app's MCP side: what it would send to Claude. No API calls."""

import anyio
from l5_app import PREVIEW_WEEK, build_request
from mcp import Client
from test_l5_server import solution


def build(question):
    async def main():
        async with Client(solution.server) as mcp:
            return await build_request(mcp, question)

    return anyio.run(main)


def test_mcp_tools_become_runner_tools():
    tools, _ = build("Who starts at TE?")
    assert sorted(t.name for t in tools) == ["get_injury_status", "get_player_stats"]
    schema = next(t for t in tools if t.name == "get_player_stats").to_dict()["input_schema"]
    assert schema["properties"]["player_ids"]["type"] == "array"


def test_question_gets_the_schedule_resource_as_a_document_first():
    _, messages = build("Who starts at TE?")
    (msg,) = messages
    doc, question = msg["content"]
    assert doc["type"] == "document" and "2026 season schedule" in doc["source"]["data"]
    assert question == {"type": "text", "text": "Who starts at TE?"}


def test_no_question_runs_the_weekly_preview_prompt():
    _, messages = build(None)
    content = messages[0]["content"]
    assert content[0]["type"] == "document"
    assert content[1]["text"].startswith(f"<schedule>\nWeek {PREVIEW_WEEK}:")
