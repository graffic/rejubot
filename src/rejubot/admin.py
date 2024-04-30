import json
import logging
import operator
import os
import re
from datetime import datetime
from random import randint

import fire
import pytz
import tabulate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from telegram import Chat, Message, User

from rejubot.settings import load_settings
from rejubot.storage import UrlEntry
from rejubot.telegrambot import (
    assign_metadata,
    create_entry,
    process_url,
    scrape_og_metadata,
)

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


async def import_urls(channel_name: str, import_file: str, delete: bool = False):
    """
    Generate a month of urls for a channel, some days might not have any urls, others might have up to 20.
    """

    settings = load_settings()
    engine = create_async_engine(settings.db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Check that channel_name is in channels
    if (channel_id := settings.telegram_channels.get(channel_name)) is None:
        raise ValueError(f"Channel {channel_name} not found")
    imported_msgs = json.load(open(import_file))
    assert len(imported_msgs) > 0
    # Sort ascending by date_unixtime
    imported_msgs.sort(key=operator.itemgetter("date_unixtime"))

    # Convert the date to a datetime object with the right timezone
    timezone = pytz.timezone("Europe/Madrid")
    for msg in imported_msgs:
        dt_in_tz = datetime.fromisoformat(msg["date"])
        msg["date"] = timezone.localize(dt_in_tz).astimezone(pytz.utc)

    # Delete the range of dates included in the imported messages
    if delete:
        async with async_session() as session:
            first_date = imported_msgs[0]["date"]
            last_date = imported_msgs[-1]["date"]
            logger.info("Deleting entries between %s and %s", first_date, last_date)
            res = await session.execute(
                UrlEntry.__table__.delete()
                .where(UrlEntry.channel_id == channel_id)
                .where(UrlEntry.created_at.between(first_date, last_date))
            )
            logger.info("Deleted %d entries", res.rowcount)
            await session.commit()

    # Process each imported message
    async with async_session() as session:
        for msg in imported_msgs:
            message = Message(
                message_id=msg["id"],
                date=msg["date"],
                chat=Chat(id=channel_id, type="channel", title=channel_name),
                text=render_message(msg["text"]),
                from_user=User(
                    first_name=msg["from"] or "", id=randint(1, 1000000), is_bot=False
                ),
            )
            for entity in msg["text_entities"]:
                if entity["type"] != "link":
                    continue
                url = entity["text"]

                if not url.startswith("http"):
                    continue

                await process_url(message, url, session)
            # Save each url and continue
            await session.commit()


async def clear_urls(channel_name: str):
    """
    Deletes all the urls in a channel
    """
    settings = load_settings()
    engine = create_async_engine(settings.db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Check that channel_name is in channels
    if (channel_id := settings.telegram_channels.get(channel_name)) is None:
        raise ValueError(f"Channel {channel_name} not found")

    # Delete the range of dates included in the imported messages
    async with async_session() as session:
        res = await session.execute(
            UrlEntry.__table__.delete().where(UrlEntry.channel_id == channel_id)
        )
        logger.info("Deleted %d entries", res.rowcount)
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


async def repair_metadata(regex_filter: str = None):
    """
    Repair the metadata of the urls
    """
    logger.info(f"Repairing metadata for {regex_filter}")
    settings = load_settings()
    engine = create_async_engine(settings.db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    regex = re.compile(regex_filter) if regex_filter else None

    async with async_session() as session:
        query = select(UrlEntry)
        if regex_filter:
            query = query.where(UrlEntry.url.regexp_match(regex_filter))

        urls: list[UrlEntry] = (
            await session.scalars(query.order_by(UrlEntry.created_at.desc()))
        ).all()

        for idx, url in enumerate(urls):
            logger.info(
                f"Updating metadata {idx}/{len(urls)} {url.created_at.date()} {url.url}"
            )
            metadata = await scrape_og_metadata(url.url)
            if metadata is None:
                continue
            assign_metadata(url, metadata)
            await session.commit()


def main():
    logging_format = "%(levelname)s %(name)s %(message)s"
    logging.basicConfig(format=logging_format, level=logging.INFO)
    if os.environ.get("SQLALCHEMY_ECHO"):
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    fire.Fire(
        dict(
            clear_urls=clear_urls,
            import_urls=import_urls,
            scrape_test=scrape_test,
            repair_metadata=repair_metadata,
        )
    )
