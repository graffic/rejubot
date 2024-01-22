import logging
import os


def setup_logging():
    logging_format = "%(levelname)s %(name)s %(message)s"
    logging.basicConfig(format=logging_format, level=logging.INFO)
    if os.environ.get("SQLALCHEMY_ECHO"):
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
