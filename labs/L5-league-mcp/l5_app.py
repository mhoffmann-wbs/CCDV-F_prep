"""L5 API app: your own MCP client that hands the server's tools to Claude.

The Messages API's MCP connector can only reach REMOTE servers, and it only uses
their tools. To use a local stdio server, or its resources and prompts, the app
runs its own MCP client:

  1. launch the server and connect (stdio here; pass --url for Streamable HTTP)
  2. convert each MCP tool for the SDK's tool runner (async_mcp_tool)
  3. attach the schedule RESOURCE as a document: the app decides, not Claude
  4. start from the weekly-preview PROMPT, or from your own question

Run from labs/:
  uv run python L5-league-mcp/l5_app.py                         # weekly-preview for week 4
  uv run python L5-league-mcp/l5_app.py "Who should I start at TE, Ashby or Mulroney?"
  uv run python L5-league-mcp/l5_app.py --server L5-league-mcp/starter.py
  uv run python L5-league-mcp/l5_app.py --url http://127.0.0.1:8765/mcp   # server started with --http
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import anyio
from anthropic import AsyncAnthropic
from anthropic.lib.tools.mcp import async_mcp_tool, mcp_message, mcp_resource_to_content
from mcp import Client, StdioServerParameters

from gridiron.client import MODEL, log_usage

LAB_DIR = Path(__file__).resolve().parent
SCHEDULE_URI = "league://schedule/2026"
PREVIEW_WEEK = "4"


async def build_request(mcp: Client, question: str | None) -> tuple[list[Any], list[dict[str, Any]]]:
    """Tools and opening messages for the tool runner, all fetched from the MCP server."""
    tools = [async_mcp_tool(t, mcp.session) for t in (await mcp.list_tools()).tools]

    schedule = mcp_resource_to_content(await mcp.read_resource(SCHEDULE_URI))
    if question:
        messages = [{"role": "user", "content": [schedule, {"type": "text", "text": question}]}]
    else:
        prompt = await mcp.get_prompt("weekly-preview", {"week": PREVIEW_WEEK})
        messages = [mcp_message(m) for m in prompt.messages]
        messages[0]["content"] = [schedule, *messages[0]["content"]]  # data first, request last
    return tools, messages


async def run(server: StdioServerParameters | str, question: str | None) -> None:
    async with Client(server) as mcp:
        info = mcp.server_info
        print(f"== Connected to {info.name if info else '?'} (MCP protocol {mcp.protocol_version})", file=sys.stderr)
        tools, messages = await build_request(mcp, question)
        print(f"== Tools: {', '.join(t.name for t in tools)}", file=sys.stderr)

        runner = AsyncAnthropic().beta.messages.tool_runner(
            model=MODEL,
            max_tokens=16000,
            output_config={"effort": "medium"},
            max_iterations=8,
            tools=tools,
            messages=messages,
        )
        final = None
        async for message in runner:
            log_usage("turn", message.usage)
            for block in message.content:
                if block.type == "tool_use":
                    print(f"  -> {block.name}({block.input})", file=sys.stderr)
            final = message

    if final is None or final.stop_reason in ("max_tokens", "refusal"):
        raise SystemExit(f"No usable answer (stop_reason={final.stop_reason if final else None}).")
    print("".join(b.text for b in final.content if b.type == "text"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask Claude a question using the League Stats MCP server")
    parser.add_argument("question", nargs="?", help="omit to run the weekly-preview prompt for week 4")
    parser.add_argument("--server", default=str(LAB_DIR / "solution.py"), help="server script to launch over stdio")
    parser.add_argument("--url", help="connect to a running Streamable HTTP server instead")
    args = parser.parse_args()
    server = args.url or StdioServerParameters(command=sys.executable, args=[args.server])
    anyio.run(run, server, args.question)


if __name__ == "__main__":
    main()
