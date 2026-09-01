from app.parser import stat_parser


def test_plus_all_skills():
    result = stat_parser.parse_stat_line("+2 To All Skills")
    assert result.field == "plus_to_skills"
    assert result.value == 2


def test_defense_line():
    result = stat_parser.parse_stat_line("Defense: 98")
    assert result.field == "defense"
    assert result.value == 98


def test_faster_cast_rate():
    result = stat_parser.parse_stat_line("35% Faster Cast Rate")
    assert result.field == "faster_cast_rate"
    assert result.value == 35


def test_unmapped_line_falls_back_to_extra():
    result = stat_parser.parse_stat_line("Damage Reduced By 10%")
    assert result.field is None
    assert result.extra_key == "Damage Reduced By 10%"


def test_resistance_line():
    assert stat_parser.parse_resistance_line("Fire Resist +30%") == ("fire", 30)
    assert stat_parser.parse_resistance_line("Cold Resistance 20") == ("cold", 20)
    assert stat_parser.parse_resistance_line("Not a resist line") is None


def test_damage_line():
    assert stat_parser.parse_damage_line("Damage: 15-25") == (15, 25)
    assert stat_parser.parse_damage_line("One-Handed Damage: 20 to 40") == (20, 40)


def test_socket_line():
    assert stat_parser.parse_socket_line("Socketed (4)") == 4
    assert stat_parser.parse_socket_line("Not sockets") is None


def test_ethereal_detection():
    assert stat_parser.is_ethereal_line("Ethereal (Cannot Be Repaired)") is True
    assert stat_parser.is_ethereal_line("+2 To All Skills") is False


def test_skill_line_with_tab():
    skill = stat_parser.parse_skill_line("+3 To Fire Ball (Sorceress Only)")
    assert skill == {"skill": "Fire Ball", "amount": 3, "tab": "Sorceress"}


def test_skill_line_excludes_all_skills():
    assert stat_parser.parse_skill_line("+2 To All Skills") is None
