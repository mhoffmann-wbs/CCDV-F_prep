from gridiron.data import load_game, load_injuries, load_players, load_teams


def test_fixtures_load_and_validate():
    assert len(load_teams()) == 4
    assert len(load_players()) == 32
    assert load_injuries()
    assert len(load_game().plays) > 20


def test_fixtures_reference_only_existing_players():
    ids = {p.id for p in load_players()}
    assert all(i.player_id in ids for i in load_injuries())
    assert all(pid in ids for play in load_game().plays for pid in play.player_ids)


def test_game_score_never_decreases_and_ends_at_final_score():
    game = load_game()
    prev = {game.home: 0, game.away: 0}
    for play in game.plays:
        for team in (game.home, game.away):
            assert play.score_after[team] >= prev[team]
        prev = play.score_after
    assert prev == game.final_score
