import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from itertools import islice
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rejubot.settings import Channel, Settings, load_channels
from rejubot.storage import UrlEntry

logger = logging.getLogger(__name__)
base = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:  # pylint: disable=W0612
    logging_format = "%(levelname)s %(name)s %(message)s"
    logging.basicConfig(format=logging_format, level=logging.INFO)
    settings = Settings()
    engine = create_async_engine(settings.db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.session_factory = session_factory
    app.state.channels = {e.name: e for e in load_channels()}
    yield


async def get_session(request: Request):
    async with request.app.state.session_factory() as session:
        yield session


def get_channels(request: Request) -> dict[str, Channel]:
    return request.app.state.channels


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=base / "static"), name="static")

templates = Jinja2Templates(directory=base / "templates")


@app.get("/channel/{channel}", response_class=HTMLResponse)
async def read_item(
    request: Request,
    channel: str,
    db: AsyncSession = Depends(get_session),
    channels: dict[str, Channel] = Depends(get_channels),
):
    if channel not in channels:
        raise HTTPException(status_code=404, detail="channel not found")
    # From next day to 7 days ago
    start = (datetime.now() + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = start - timedelta(days=30)

    query = (
        select(UrlEntry)
        .where(
            UrlEntry.channel_id == channels[channel].id,
            UrlEntry.created_at.between(end, start),
        )
        .order_by(UrlEntry.created_at.desc())
    )
    result = await db.scalars(query)

    # Group entries by day
    entries_by_day = {}
    for entry in result.all():
        day = entry.created_at.date()
        if day not in entries_by_day:
            entries_by_day[day] = []
        entries_by_day[day].append(entry)

    return templates.TemplateResponse(
        "channels.html", dict(request=request, channel=channel, days=entries_by_day)
    )
