from app.rcon_admin_log_parser import parse_rcon_admin_log_message


def test_parse_match_start():
    parsed = parse_rcon_admin_log_message(
        "[2:09:15 hours (1779178245)] MATCH START UTAH BEACH Warfare"
    )

    assert parsed.event_type == "match_start"
    assert parsed.server_time == 1779178245
    assert parsed.map_name == "UTAH BEACH"
    assert parsed.game_mode == "Warfare"


def test_parse_match_end():
    parsed = parse_rcon_admin_log_message(
        "[20:36:53 hours (1779111786)] MATCH ENDED `ST MARIE DU MONT Warfare` ALLIED (5 - 0) AXIS "
    )

    assert parsed.event_type == "match_end"
    assert parsed.map_name == "ST MARIE DU MONT Warfare"
    assert parsed.allied_score == 5
    assert parsed.axis_score == 0
    assert parsed.winner == "allied"


def test_parse_kill():
    parsed = parse_rcon_admin_log_message(
        "[1:20:19 hours (1779181181)] KILL: AntonioPruna(Allies/76561198000000000) -> "
        "[7DV] NEⓇA TACTICAL FEMB✡Y(Axis/76561199000000000) with M1 GARAND"
    )

    assert parsed.event_type == "kill"
    assert parsed.killer_name == "AntonioPruna"
    assert parsed.killer_team == "Allies"
    assert parsed.killer_id == "76561198000000000"
    assert parsed.victim_name == "[7DV] NEⓇA TACTICAL FEMB✡Y"
    assert parsed.victim_team == "Axis"
    assert parsed.victim_id == "76561199000000000"
    assert parsed.weapon == "M1 GARAND"


def test_parse_team_switch():
    parsed = parse_rcon_admin_log_message(
        "[21:34:19 hours (1779108340)] TEAMSWITCH Ekenef (None > Allies)"
    )

    assert parsed.event_type == "team_switch"
    assert parsed.player_name == "Ekenef"
    assert parsed.from_team == "None"
    assert parsed.to_team == "Allies"


def test_parse_connected():
    parsed = parse_rcon_admin_log_message(
        "[21:34:22 hours (1779108337)] CONNECTED Ekenef (76561198109813520)"
    )

    assert parsed.event_type == "connected"
    assert parsed.player_name == "Ekenef"
    assert parsed.player_id == "76561198109813520"


def test_parse_disconnected():
    parsed = parse_rcon_admin_log_message(
        "[21:10:53 hours (1779109746)] DISCONNECTED [BxB] Rab◯l◯k◯ (76561198111111111)"
    )

    assert parsed.event_type == "disconnected"
    assert parsed.player_name == "[BxB] Rab◯l◯k◯"
    assert parsed.player_id == "76561198111111111"


def test_parse_chat():
    parsed = parse_rcon_admin_log_message(
        "[18:38:35 hours (1779118884)] CHAT[Team][BXB Ivanxu(Axis/6215e24a1f05c5815ed9e8bf185f94fd)]: !vip"
    )

    assert parsed.event_type == "chat"
    assert parsed.chat_scope == "Team"
    assert parsed.player_name == "BXB Ivanxu"
    assert parsed.chat_team == "Axis"
    assert parsed.player_id == "6215e24a1f05c5815ed9e8bf185f94fd"
    assert parsed.content == "!vip"


def test_parse_kick():
    parsed = parse_rcon_admin_log_message(
        "[2:09:10 hours (1779178249)] KICK: [[7DV] NEⓇA TACTICAL FEMB✡Y] has been kicked. "
        "[Making free spaces for members of the Spanish Discord community.]"
    )

    assert parsed.event_type == "kick"
    assert parsed.player_name == "[7DV] NEⓇA TACTICAL FEMB✡Y"
    assert "Making free spaces" in parsed.reason


def test_parse_message_profile():
    parsed = parse_rcon_admin_log_message(
        "[21:34:19 hours (1779108340)] MESSAGE: player [Ekenef(76561198109813520)], "
        "content [─ Ekenef ─\\n▒ Totales ▒\\nbajas : 141 (6 TKs)\\nmuertes : 268 (5 TKs)]"
    )

    assert parsed.event_type == "message"
    assert parsed.player_name == "Ekenef"
    assert parsed.player_id == "76561198109813520"
    assert "bajas : 141" in parsed.content
