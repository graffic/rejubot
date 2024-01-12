import os
import tomllib

from pydantic import FieldValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_token: str
    db_url: str
    telegram_channels: dict[str, int]
    telegram_channels_by_id: dict[int, str] = {}
    model_config = SettingsConfigDict(env_prefix="REJUBOT_")

    @field_validator("telegram_channels_by_id")
    def telegram_channels_by_id_from_channels(cls, _, info: FieldValidationInfo):
        return {v: k for k, v in info.data["telegram_channels"].items()}


def load_settings(from_file=os.environ.get("REJUBOT_SETTINGS")) -> Settings:
    with open(from_file, "rb") as input:
        input_settings = tomllib.load(input)

    return Settings.model_validate(input_settings)
