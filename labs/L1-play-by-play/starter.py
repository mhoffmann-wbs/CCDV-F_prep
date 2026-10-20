"""L1 starter: play-by-play summarizer.

Run from labs/:  uv run python L1-play-by-play/starter.py
Fill in the numbered TODOs in order. Until you do, the script makes no API calls.
The offline helpers (schema, prompt, validator) are ready in l1_recap.py.
Stuck? Compare with solution.py.
"""

from __future__ import annotations

import anthropic
from l1_recap import PROSE_REQUEST, SYSTEM_PROMPT, Recap, build_user_message, validate_recap  # noqa: F401

from gridiron.client import MODEL, TIERS, client, log_usage  # noqa: F401
from gridiron.data import load_game, load_players


def check_stop(message: anthropic.types.Message) -> None:
    """Raise before any content is used if the response can't be trusted."""
    # TODO 0: raise RuntimeError when message.stop_reason is "refusal"
    #   (include message.stop_details.category if stop_details is set)
    #   or "max_tokens" (the output was cut off).
    pass


def main() -> None:
    game = load_game()
    players = load_players()
    messages = [{"role": "user", "content": build_user_message(game)}]

    print("== The user message starts with the data (first 3 lines):")
    print("\n".join(messages[0]["content"].splitlines()[:3]))

    # TODO 1: count input tokens on every tier.
    #   Loop over TIERS.items() and call
    #   client.messages.count_tokens(model=..., system=SYSTEM_PROMPT, messages=messages).
    #   Print each result's .input_tokens. Do the counts match across models?

    # TODO 2: stream a prose recap.
    #   with client.messages.stream(model=MODEL, max_tokens=16000, system=SYSTEM_PROMPT,
    #                               output_config={"effort": "low"},
    #                               messages=[{"role": "user",
    #                                          "content": build_user_message(game, PROSE_REQUEST)}]) as stream:
    #       print each chunk of stream.text_stream (end="", flush=True)
    #       then take stream.get_final_message()
    #   Call log_usage("stream", final.usage), then check_stop(final).

    # TODO 3: get a structured recap.
    #   response = client.messages.parse(..., messages=messages, output_format=Recap)
    #   Call log_usage and check_stop BEFORE reading response.parsed_output.
    #   parsed_output is a Recap instance (or None if nothing could be parsed).

    # TODO 4: validate the recap against the game data.
    #   problems = validate_recap(recap, game, players); print each problem, or "OK".
    _ = players

    print("\nNothing called yet: work through TODO 1-4 in starter.py.")


if __name__ == "__main__":
    main()
