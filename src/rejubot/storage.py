from datetime import datetime
from logging import getLogger

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

logger = getLogger(__name__)


class Base(DeclarativeBase):
    pass


class VideoEntry(Base):
    __tablename__ = "video_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_type: Mapped[str] = mapped_column(String(255))
    width: Mapped[int] = mapped_column(Integer, nullable=True)
    height: Mapped[int] = mapped_column(Integer, nullable=True)
    url: Mapped[str] = mapped_column(Text)


class UrlEntry(Base):
    __tablename__ = "url_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Telegram asks for 64 bit signed integers
    channel_id: Mapped[int] = mapped_column(BigInteger, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    who: Mapped[str] = mapped_column(String(255))
    who_id: Mapped[int] = mapped_column(BigInteger)
    url: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    og_site: Mapped[str | None] = mapped_column(Text, nullable=True)
    og_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    og_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    og_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_id: Mapped[int | None] = mapped_column(
        ForeignKey("video_entries.id"), nullable=True
    )
    video: Mapped[VideoEntry | None] = relationship(uselist=False, cascade="all")


Index(None, UrlEntry.channel_id, UrlEntry.message_id)
