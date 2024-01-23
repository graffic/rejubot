import logging
import os


def setup_logging():
    logging_format = "%(levelname)s %(name)s %(message)s"
    logging.basicConfig(format=logging_format, level=logging.INFO)
    if os.environ.get("SQLALCHEMY_ECHO"):
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    # Telegram bot uses httpx, and httpx logs every request in info level
    logging.getLogger("httpx").setLevel(logging.WARNING)
