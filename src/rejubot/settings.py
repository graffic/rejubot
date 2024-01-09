import os
import tomllib
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Channel(BaseModel):
    name: str
    id: int
    public: bool


def load_channels(from_file=os.environ.get("REJUBOT_CHANNELS")) -> list[Channel]:
    if not from_file or not Path(from_file).exists():
        raise FileNotFoundError(from_file)
    with open(from_file, "rb") as input:
        input_channels = tomllib.load(input)

    results = []
    for name, values in input_channels.items():
        values["name"] = name
        results.append(Channel.model_validate(values))
    return results


class Settings(BaseSettings):
    telegram_token: str
    db_url: str
    model_config = SettingsConfigDict(env_prefix="REJUBOT_")
