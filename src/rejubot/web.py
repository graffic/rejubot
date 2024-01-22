import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import joinedload

from rejubot.logging import setup_logging
from rejubot.settings import load_settings
from rejubot.storage import UrlEntry

logger = logging.getLogger(__name__)
base = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:  # pylint: disable=W0612
    setup_logging()

    settings = load_settings()
    engine = create_async_engine(settings.db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.session_factory = session_factory
    app.state.channels = settings.telegram_channels
    yield


async def get_session(request: Request):
    async with request.app.state.session_factory() as session:
        yield session


def get_channels(request: Request) -> dict[str, id]:
    return request.app.state.channels


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=base / "static"), name="static")

templates = Jinja2Templates(directory=base / "templates")


@app.get("/links", response_class=HTMLResponse)
async def read_item(
    request: Request,
    partial_after: date = None,
    from_date: date = None,
    db: AsyncSession = Depends(get_session),
):
    if from_date is None:
        from_date = datetime.now().date()
    # Find the last 7 days
    query = select(func.date(UrlEntry.created_at))
    if partial_after or from_date:
        base_date = partial_after or from_date
        query = query.where(func.date(UrlEntry.created_at) < base_date)
    query = query.distinct().order_by(func.date(UrlEntry.created_at).desc()).limit(7)
    result = (await db.scalars(query)).all()

    entries_by_day = []
    if len(result) != 0:
        entries_by_day = await get_url_entries(db, result[0], result[-1])

    template = "links.html"
    if partial_after:
        template = "links_days.html"
    # Format today's date as year-month-day
    today = datetime.now().strftime("%Y-%m-%d")
    return templates.TemplateResponse(
        template, dict(request=request, days=entries_by_day, today=today)
    )


async def get_url_entries(db, first_day, last_day):
    query = (
        select(UrlEntry)
        .where(func.date(UrlEntry.created_at).between(last_day, first_day))
        .order_by(UrlEntry.created_at.desc())
    ).options(joinedload(UrlEntry.video))
    result = await db.scalars(query)

    # Group entries by day
    entries_by_day = []
    current_day = None
    entries = None
    for entry in result.all():
        day = entry.created_at.date()
        if day != current_day:
            current_day = day
            entries = []
            entries_by_day.append([current_day, entries, False])
        entries.append(entry)
    entries_by_day[-1][2] = True
    return entries_by_day


@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("root.html", dict(request=request))
