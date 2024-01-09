import json
import logging
from datetime import datetime
from random import randint

import fire
import tabulate
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from telegram import Chat, Message, User

from rejubot.settings import Settings, load_channels
from rejubot.storage import UrlEntry
from rejubot.telegrambot import create_entry, scrape_og_metadata

logger = logging.getLogger(__name__)


def render_message(entries: list) -> str:
    """
    Render a message from the Telegram API text element as a string.

    It will detect the MessageEntityType, and for each type it will render the text.
    """
    result = []
    for entry in entries:
        if isinstance(entry, str):
            result.append(entry)
        else:
            result.append(entry["text"])
    return "".join(result)


async def import_urls(channel_name: str, import_file: str):
    """
    Generate a month of urls for a channel, some days might not have any urls, others might have up to 20.
    """

    settings = Settings()
    engine = create_async_engine(settings.db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    channels = {e.name: e for e in load_channels()}
    # Check that channel_name is in channels
    if (channel := channels.get(channel_name)) is None:
        raise ValueError(f"Channel {channel_name} not found")
    imported_msgs = json.load(open(import_file))
    assert len(imported_msgs) > 0
    # Clean the database for this channel
    async with async_session() as session:
        await session.execute(
            UrlEntry.__table__.delete().where(UrlEntry.channel_id == channel.id)
        )
        await session.commit()
    async with async_session() as session:
        for msg in imported_msgs:
            message = Message(
                message_id=msg["id"],
                date=datetime.fromisoformat(msg["date"]),
                chat=Chat(id=channel.id, type="channel", title=channel.name),
                text=render_message(msg["text"]),
                from_user=User(
                    first_name=msg["from"], id=randint(1, 1000000), is_bot=False
                ),
            )
            for entity in msg["text_entities"]:
                if entity["type"] != "link":
                    continue
                url = entity["text"]

                if not url.startswith("http"):
                    continue

                logger.info("Scraping %s", url)
                metadata = await scrape_og_metadata(url)
                entry = create_entry(message, url, metadata)
                entry.created_at = datetime.fromisoformat(msg["date"])
                session.add(entry)
        await session.commit()


async def scrape_test(url: str):
    """
    Scrape the Open Graph metadata from a url
    """
    result = await scrape_og_metadata(url)
    table = []
    for key, value in result.__dict__.items():
        if isinstance(value, str) and len(value) > 60:
            value = "\n".join([value[i : i + 60] for i in range(0, len(value), 60)])
        table.append([key, value])
    print(tabulate.tabulate(table, tablefmt="simple_grid"))


def main():
    logging.basicConfig(level=logging.INFO)
    fire.Fire(dict(import_urls=import_urls, scrape_test=scrape_test))
