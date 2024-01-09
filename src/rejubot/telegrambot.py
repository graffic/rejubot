import logging
import re
from dataclasses import dataclass
from pprint import pprint

import aiohttp
import telegram.ext.filters as filters
import validators
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from telegram import Message, Update
from telegram.constants import ChatMemberStatus, MessageEntityType
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    ChatMemberHandler,
    MessageHandler,
)

from rejubot.settings import Channel, Settings, load_channels
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
    return meta["content"]


def get_meta_name(soup: BeautifulSoup, name: str) -> str | None:
    meta = soup.find("meta", attrs=dict(name=name))
    if not meta:
        return None
    return meta["content"]


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


async def scrape_og_metadata(url: str) -> UrlMetadata | None:
    if not url.startswith("http"):
        url = f"http://{url}"

    url = re.sub(r"^https://(x|twitter)\.com", "https://vxtwitter.com", url)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=HEADERS) as response:
                html = await response.text()
        except aiohttp.ClientError:
            logger.exception("Error scraping %s", url)
            return None
    logger.debug(html)
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
    if og_image == "0":
        og_image = None

    video_url = gets("og:video")
    video_type = gets("og:video:type")
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


def get_telegram_urls(update: Update) -> set[str]:
    results = set()
    msg = update.message.text
    # Guard condition
    if not msg.strip():
        return results

    for ent, text in update.message.parse_entities().items():
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
    channel_id = msg.chat_id
    who = msg.from_user.first_name
    if msg.from_user.last_name:
        who += f" {msg.from_user.last_name}"
    who_id = msg.from_user.id
    message = msg.text_html

    entry = UrlEntry(
        channel_id=channel_id, who=who, who_id=who_id, message=message, url=url
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


async def handle_message(update: Update, context: CallbackContext):
    pprint(update.to_dict())
    urls = get_telegram_urls(update)
    logger.info("Found %s urls", len(urls))

    if len(urls) == 0:
        return
    entries = []
    for url in urls:
        logger.info("Scraping %s", url)
        metadata = await scrape_og_metadata(url)
        entry = create_entry(update.message, url, metadata)
        entries.append(entry)

    async with context.bot_data["async_session"]() as session:
        logger.info("Storing %d entries", len(entries))
        session.add_all(entries)
        await session.commit()


async def handle_membership(update: Update, context: CallbackContext):
    """
    Join only configured channels
    """
    if not update.my_chat_member:
        return
    if update.my_chat_member.chat.id in context.bot_data["channels"]:
        logger.info(
            f"Bot {update.my_chat_member.new_chat_member.status } from allowed channel"
        )
        return
    if update.my_chat_member.new_chat_member.status == ChatMemberStatus.MEMBER:
        # Joined to a channel notin the list
        logger.warning("Invited to the wrong channel, leaving.")
        await context.bot.leave_chat(update.my_chat_member.chat.id)


def create_app(token: str, channels: list[Channel]):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(ChatMemberHandler(handle_membership))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.bot_data["channels"] = {chan.id: chan for chan in channels}
    return app


def run():
    logging_format = "%(levelname)s %(name)s %(message)s"
    logging.basicConfig(format=logging_format, level=logging.INFO)
    settings = Settings()
    channels = load_channels()
    app = create_app(settings.telegram_token, channels)
    engine = create_async_engine(settings.db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    app.bot_data["async_session"] = async_session

    app.run_polling()


if __name__ == "__main__":
    run()
