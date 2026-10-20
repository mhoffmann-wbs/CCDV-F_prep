"""L1 reference solution: play-by-play summarizer.

Run from labs/:  uv run python L1-play-by-play/solution.py
Cheaper iteration:  MODEL=claude-haiku-5-5 uv run python L1-play-by-play/solution.py
"""

from __future__ import annotations

import anthropic
from l1_recap import PROSE_REQUEST, SYSTEM_PROMPT, Recap, build_user_message, validate_recap

from gridiron.client import MODEL, TIERS, client, log_usage
from gridiron.data import load_game, load_players


def check_stop(message: anthropic.types.Message) -> None:
    """Raise before any content is used if the response can't be trusted."""
    if message.stop_reason == "refusal":
        details = message.stop_details
        category = details.category if details else None
        raise RuntimeError(f"Claude declined the request (refusal, category={category}).")
    if message.stop_reason == "max_tokens":
        raise RuntimeError("Output was cut off at max_tokens; raise max_tokens instead of using a partial answer.")


def main() -> None:
    game = load_game()
    players = load_players()

    # Step 1: count input tokens on each tier. Tokenizers differ between models,
    # so never estimate from word counts or reuse one model's count for another.
    messages = [{"role": "user", "content": build_user_message(game)}]
    print("== Step 1: input tokens per tier")
    for tier, model in TIERS.items():
        count = client.messages.count_tokens(model=model, system=SYSTEM_PROMPT, messages=messages)
        print(f"  {tier:<7} {model:<20} {count.input_tokens} input tokens")

    # Step 2: stream a prose recap. Streaming fixes time-to-first-token; it does
    # not make the request cheaper. Check the stop reason on the final message.
    print(f"\n== Step 2: streamed prose recap ({MODEL})\n")
    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": build_user_message(game, PROSE_REQUEST)}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        prose = stream.get_final_message()
    print()
    log_usage("stream", prose.usage)
    check_stop(prose)

    # Step 3: structured recap. messages.parse() sends the Pydantic schema as a
    # structured-output format and returns a validated Recap in parsed_output.
    print(f"\n== Step 3: structured recap ({MODEL})")
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "low"},
        messages=messages,
        output_format=Recap,
    )
    log_usage("parse", response.usage)
    check_stop(response)  # a refusal or truncation is not a valid Recap
    recap = response.parsed_output
    if recap is None:
        raise RuntimeError("No parsed output in the response.")
    print(recap.model_dump_json(indent=2))

    # Step 4: correct shape is not correct facts. Check the recap against the data.
    print("\n== Step 4: validation")
    problems = validate_recap(recap, game, players)
    if problems:
        print("Problems found:")
        for problem in problems:
            print(f"  - {problem}")
    else:
        print("Recap matches the game data.")


if __name__ == "__main__":
    main()
