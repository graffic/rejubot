from pathlib import Path

from rejubot.settings import load_settings

FIXTURES_BASE = Path(__file__).parent / "fixtures"


def test_load_settings_ok():
    settings = load_settings(FIXTURES_BASE / "test_settings.toml")
    assert settings.telegram_token == "a"
    assert settings.db_url == "b"
    assert settings.telegram_channels == {"rejugando": 1, "development": 2}
    assert settings.telegram_channels_by_id == {1: "rejugando", 2: "development"}
