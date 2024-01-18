import asyncio
import html
import json
import logging
import os
import re
import traceback
from dataclasses import dataclass
from datetime import timedelta
from pprint import pprint

import aiohttp
import telegram.ext.filters as filters
import validators
from bs4 import BeautifulSoup
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from telegram import Message, Update
from telegram.constants import ChatMemberStatus, MessageEntityType, ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    ChatMemberHandler,
    ContextTypes,
    MessageHandler,
)

from rejubot.settings import Settings, load_settings
from rejubot.storage import UrlEntry, VideoEntry

logger = logging.getLogger(__name__)
FIND_URLS = re.compile(r"https?://\S+")
HEADERS = {
    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"
}


def get_meta(soup: BeautifulSoup, property: str) -> str | None:
    meta = soup.find("meta", property=property)
    if not meta:
        return None
    return meta.get("content")


def get_meta_name(soup: BeautifulSoup, name: str) -> str | None:
    meta = soup.find("meta", attrs=dict(name=name))
    if not meta:
        return None
    return meta.get("content")


@dataclass
class UrlMetadata:
    site: str | None
    title: str | None
    description: str | None
    image: str | None
    video_url: str | None
    video_type: str | None
    video_width: int | None
    video_height: int | None


async def scrape_og_metadata_html(html: str, url: str) -> UrlMetadata | None:
    soup = BeautifulSoup(html, "html.parser")
    gets = lambda prop: get_meta(soup, prop)
    gets_name = lambda prop: get_meta_name(soup, prop)

    if url.startswith("https://vxtwitter.com"):
        og_site = "Twitter / X"
        og_title = gets_name("twitter:title")
    else:
        og_site = gets("og:site_name")
        og_title = gets("og:title")

    og_image = gets("og:image")
    if og_image == "0" or og_image == "null":
        og_image = None

    video_url = gets("og:video")
    video_type = gets("og:video:type")
    # Some times there is a video link without a type, meaning it is another
    # website. So it is not a real video.
    if not video_type:
        video_url = None
    video_width = gets("og:video:width")
    video_height = gets("og:video:height")

    og_description = gets("og:description")
    if og_title is None and og_description is None:
        return None
    return UrlMetadata(
        site=og_site,
        title=og_title,
        description=og_description,
        image=og_image,
        video_url=video_url,
        video_type=video_type,
        video_width=video_width,
        video_height=video_height,
    )


async def scrape_og_metadata(url: str) -> UrlMetadata | None:
    if not url.startswith("http"):
        url = f"http://{url}"

    url = re.sub(r"^https://(x|twitter)\.com", "https://vxtwitter.com", url)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(20)) as session:
        try:
            async with session.get(url, headers=HEADERS) as response:
                content_type = response.headers.get("Content-Type")
                await response.read()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            logger.exception("Error scraping %s", url)
            return None
    if not content_type:
        logger.warning("No content type for %s", url)
        return None
    if content_type.startswith("text/html"):
        return await scrape_og_metadata_html(await response.text(errors="ignore"), url)
    elif content_type.startswith("image/"):
        return UrlMetadata(
            site=None,
            title=None,
            description=None,
            image=url,
            video_url=None,
            video_type=None,
            video_width=None,
            video_height=None,
        )
    elif content_type.startswith("video/"):
        return UrlMetadata(
            site=None,
            title=None,
            description=None,
            image=None,
            video_url=url,
            video_type=content_type,
            video_width=None,
            video_height=None,
        )
    else:
        logger.warning("Unknown content type %s for %s", content_type, url)
        return None


def get_telegram_urls(message: Message) -> set[str]:
    results = set()
    msg_text = message.text
    # Guard condition
    if not msg_text.strip():
        return results

    for ent, text in message.parse_entities().items():
        if ent.type != MessageEntityType.URL:
            continue
        if not text.startswith("http"):
            continue
        try:
            validators.url(text)
        except validators.ValidationError:
            logger.warning("Invalid url %s", text)
            continue

        results.add(text)
    return results


def create_entry(msg: Message, url: str, metadata: UrlMetadata | None) -> UrlEntry:
    who = msg.from_user.first_name
    if msg.from_user.last_name:
        who += f" {msg.from_user.last_name}"
    who_id = msg.from_user.id
    message = msg.text_html

    entry = UrlEntry(
        channel_id=msg.chat_id,
        message_id=msg.message_id,
        who=who,
        who_id=who_id,
        message=message,
        url=url,
        created_at=msg.date,
    )
    if not metadata:
        return entry

    entry.og_description = metadata.description
    entry.og_image = metadata.image
    entry.og_site = metadata.site
    entry.og_title = metadata.title
    if metadata.video_url:
        entry.video = VideoEntry(
            content_type=metadata.video_type,
            width=metadata.video_width,
            height=metadata.video_height,
            url=metadata.video_url,
        )

    return entry


IGNORED_HOSTNAMES = {"rejugan.do"}


def should_skip_url(url: str) -> bool:
    try:
        hostname = url.split("/")[2]
    except IndexError:
        logger.warning("Invalid url %s", url)
        # Log the issue but continue
        return False
    skip = hostname in IGNORED_HOSTNAMES
    if skip:
        logger.info("Skipping %s", url)
    return skip


async def process_url(message: Message, url: str, session: AsyncSession):
    """
    Process a single url into the database
    """

    if should_skip_url(url):
        return None
    # Check in the database if the url was already posted in the last 24 hours.
    query = (
        select(func.count("*"))
        .where(UrlEntry.url == url)
        .where(UrlEntry.created_at > message.date - timedelta(days=1))
    )
    res = (await session.scalars(query)).first()
    if res > 0:
        logger.info("Url %s already posted in the last 24h, skipping", url)
        return None

    logger.info("Scraping %s", url)
    metadata = await scrape_og_metadata(url)
    entry = create_entry(message, url, metadata)

    logger.info("Storing entry: %s", url)
    session.add(entry)


async def handle_message(update: Update, context: CallbackContext):
    message = update.message or update.edited_message
    if message is None:
        return

    urls = get_telegram_urls(message)
    logger.info("Found %s urls", len(urls))

    if len(urls) == 0:
        return

    async with context.bot_data["async_session"]() as session:
        for url in urls:
            await process_url(message, url, session)
        await session.commit()


async def handle_membership(update: Update, context: CallbackContext):
    """
    Join only configured channels
    """
    # pprint(update.to_dict())
    if not update.my_chat_member:
        return
    if update.my_chat_member.chat.id in context.bot_data["channels"]:
        logger.info(
            f"Bot {update.my_chat_member.new_chat_member.status } from allowed channel"
        )
        return
    if update.my_chat_member.new_chat_member.status == ChatMemberStatus.MEMBER:
        # Joined to a channel notin the list
        logger.warning(
            "Invited to the wrong channel %d, leaving.", update.my_chat_member.chat.id
        )
        await context.bot.leave_chat(update.my_chat_member.chat.id)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f'<pre><code class="language-json">update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        "</code></pre>\n\n"
        '<pre><code class="language-python">\n'
        f"context.chat_data = {html.escape(str(context.chat_data))}\n"
        f"context.user_data = {html.escape(str(context.user_data))}\n"
        "</code></pre>"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    await context.bot.send_message(
        chat_id=context.bot_data["error_chat_id"],
        text=message,
        parse_mode=ParseMode.HTML,
    )


def create_app(settings: Settings, async_session: async_sessionmaker):
    app = ApplicationBuilder().token(settings.telegram_token).build()
    app.add_handler(ChatMemberHandler(handle_membership))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_error_handler(error_handler)

    app.bot_data["channels"] = settings.telegram_channels_by_id
    app.bot_data["error_chat_id"] = settings.error_chat_id
    app.bot_data["async_session"] = async_session

    return app


def run():
    logging_format = "%(levelname)s %(name)s %(message)s"
    logging.basicConfig(format=logging_format, level=logging.INFO)
    if os.environ.get("SQLALCHEMY_ECHO"):
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    settings = load_settings()
    engine = create_async_engine(settings.db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    app = create_app(settings, async_session)
    app.run_polling()


if __name__ == "__main__":
    run()
