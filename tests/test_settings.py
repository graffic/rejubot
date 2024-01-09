from pathlib import Path

from rejubot.settings import Channel, load_channels

FIXTURES_BASE = Path(__file__).parent / "fixtures"


def test_load_channels_ok():
    channels = load_channels(FIXTURES_BASE / "test_channels.toml")

    assert channels == [
        Channel(**dict(name="channel-a", id=42, public=True)),
        Channel(**dict(name="channel-b", id=43, public=False)),
    ]
