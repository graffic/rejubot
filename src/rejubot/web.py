import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rejubot.settings import load_settings
from rejubot.storage import UrlEntry

logger = logging.getLogger(__name__)
base = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:  # pylint: disable=W0612
    logging_format = "%(levelname)s %(name)s %(message)s"
    logging.basicConfig(format=logging_format, level=logging.INFO)
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
    db: AsyncSession = Depends(get_session),
    channels: dict[str, id] = Depends(get_channels),
):
    # From next day to 7 days ago
    start = (datetime.now() + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = start - timedelta(days=30)

    query = (
        select(UrlEntry)
        .where(
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
        "links.html", dict(request=request, days=entries_by_day)
    )


@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("root.html", dict(request=request))
