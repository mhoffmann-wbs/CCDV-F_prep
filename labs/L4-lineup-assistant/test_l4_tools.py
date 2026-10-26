from l4_league import LineupStore
from l4_tools import TOOL_NAMES, TOOLS, run_tool, tool_result
from test_l4_league import GOOD


def never(_: str) -> bool:
    raise AssertionError("approval must not be requested")


def walk(schema):
    yield schema
    for child in schema.get("properties", {}).values():
        yield from walk(child)
    if "items" in schema:
        yield from walk(schema["items"])


def test_every_tool_is_strict_with_closed_fully_required_objects():
    for tool in TOOLS:
        assert tool["strict"] is True, tool["name"]
        for node in walk(tool["input_schema"]):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False, tool["name"]
                assert set(node["required"]) == set(node["properties"]), tool["name"]


def test_schemas_have_no_unsupported_numeric_limits():
    text = str([t["input_schema"] for t in TOOLS])
    for keyword in ("minItems", "maxItems", "minimum", "maximum", "minLength"):
        assert keyword not in text


def test_descriptions_say_when_to_call():
    for tool in TOOLS:
        assert "call" in tool["description"].lower(), tool["name"]


def test_read_tools_return_text(tmp_path):
    store = LineupStore(tmp_path / "l.json")
    out = run_tool("get_player_stats", {"player_ids": ["POR-QB1"], "detail": "summary"}, approve=never, store=store)
    assert not out.is_error and "POR-QB1" in out.content


def test_bad_calls_come_back_as_error_results_not_exceptions(tmp_path):
    store = LineupStore(tmp_path / "l.json")
    unknown_id = run_tool("get_injury_status", {"player_ids": ["XXX"]}, approve=never, store=store)
    assert unknown_id.is_error and "Unknown player id" in unknown_id.content
    unknown_tool = run_tool("drop_player", {}, approve=never, store=store)
    assert unknown_tool.is_error and all(n in unknown_tool.content for n in TOOL_NAMES)
    missing_arg = run_tool("get_player_stats", {}, approve=never, store=store)
    assert missing_arg.is_error


def test_invalid_lineup_is_rejected_before_anyone_is_asked(tmp_path):
    store = LineupStore(tmp_path / "l.json")
    bad = dict(GOOD, WR1="NSH-WR1")
    out = run_tool("set_lineup", {"week": 4, "lineup": bad, "rationale": "x"}, approve=never, store=store)
    assert out.is_error and "ruled Out" in out.content
    assert store.load() is None


def test_declined_lineup_is_not_saved(tmp_path):
    store = LineupStore(tmp_path / "l.json")
    seen = []
    out = run_tool(
        "set_lineup", {"week": 4, "lineup": GOOD, "rationale": "x"}, approve=lambda p: seen.append(p) or False, store=store
    )
    assert out.is_error and "declined" in out.content
    assert "Marcus Holloway" in seen[0]
    assert store.load() is None


def test_approved_lineup_is_saved(tmp_path):
    store = LineupStore(tmp_path / "l.json")
    out = run_tool("set_lineup", {"week": 4, "lineup": GOOD, "rationale": "x"}, approve=lambda _: True, store=store)
    assert not out.is_error
    assert store.load()["lineup"] == GOOD


def test_tool_result_shape():
    from l4_tools import ToolOutcome

    assert tool_result("toolu_1", ToolOutcome("ok")) == {"type": "tool_result", "tool_use_id": "toolu_1", "content": "ok"}
    assert tool_result("toolu_2", ToolOutcome("bad", is_error=True))["is_error"] is True
