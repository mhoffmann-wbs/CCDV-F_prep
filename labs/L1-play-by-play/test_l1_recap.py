from l1_recap import (
    EXAMPLE,
    RECAP_REQUEST,
    FinalScore,
    KeyPlay,
    Recap,
    build_user_message,
    format_plays,
    validate_recap,
)

from gridiron.data import load_game, load_players

GAME = load_game()
PLAYERS = load_players()


def good_recap() -> Recap:
    return Recap(
        headline="Holloway finds Pruitt with 41 seconds left as Portland steals one",
        summary="Portland rallied from a 20-17 deficit with a late touchdown drive to win 24-20 in Nashville.",
        final_score=FinalScore(home=20, away=24),
        key_plays=[
            KeyPlay(quarter=3, clock="12:30", player_ids=["POR-QB1", "POR-WR1"], impact="turnover",
                    why_it_mattered="The interception set up Nashville's go-ahead score."),
            KeyPlay(quarter=4, clock="1:22", player_ids=["POR-QB1", "POR-WR1"], impact="momentum",
                    why_it_mattered="A 4th-down conversion kept the final drive alive."),
            KeyPlay(quarter=4, clock="0:41", player_ids=["POR-QB1", "POR-WR2"], impact="scoring",
                    why_it_mattered="The winning touchdown."),
        ],
        player_of_the_game="POR-QB1",
    )


def test_plays_are_xml_tagged_and_complete():
    text = format_plays(GAME)
    assert text.startswith("<game") and "<plays>" in text and text.endswith("</plays>\n</game>")
    assert text.count("\nQ") == len(GAME.plays)
    assert "Q4 0:41" in text and "POR-WR2" in text


def test_data_comes_before_the_example_and_the_request():
    msg = build_user_message(GAME)
    assert msg.index("<plays>") < msg.index(EXAMPLE) < msg.index(RECAP_REQUEST)
    assert msg.endswith(RECAP_REQUEST)


def test_data_last_variant_reverses_the_order():
    msg = build_user_message(GAME, data_first=False)
    assert msg.startswith(RECAP_REQUEST)
    assert msg.index(RECAP_REQUEST) < msg.index("<game")


def test_good_recap_validates_cleanly():
    assert validate_recap(good_recap(), GAME, PLAYERS) == []


def test_bad_recap_yields_exactly_the_expected_problems():
    bad = good_recap().model_copy(deep=True)
    bad.final_score = FinalScore(home=24, away=20)  # home/away swapped
    bad.player_of_the_game = "POR-QB9"  # no such player
    bad.key_plays[1].clock = "1:30"  # no play at Q4 1:30
    bad.key_plays[2].player_ids = ["POR-QB1", "Cody Pruitt"]  # a name, not an ID

    assert validate_recap(bad, GAME, PLAYERS) == [
        "final_score is home 24 - away 20, but the game ended NSH 20 - POR 24",
        "key_plays[1]: no play at Q4 1:30 in the game",
        "key_plays[2]: unknown player ID 'Cody Pruitt'",
        "player_of_the_game: unknown player ID 'POR-QB9'",
    ]


def test_key_play_count_is_enforced_in_code():
    too_few = good_recap().model_copy(update={"key_plays": good_recap().key_plays[:2]})
    assert validate_recap(too_few, GAME, PLAYERS) == ["expected 3-5 key plays, got 2"]


def test_schema_has_no_unsupported_numeric_constraints():
    schema_text = str(Recap.model_json_schema())
    for keyword in ("minItems", "maxItems", "minimum", "maximum"):
        assert keyword not in schema_text
