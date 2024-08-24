#!/usr/bin/env python

import asyncio
import csv
import logging
from os.path import exists, join

import aiohttp
import path_util  # noqa: F401
from dotenv import load_dotenv

from scraper import data_path
from scraper.utils.csv import upload_data

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_application() -> None:
    root_path = data_path()
    file_path = join(root_path, "posts.csv")

    try:
        if not exists(file_path):
            raise FileNotFoundError("File not found")

        async with aiohttp.ClientSession() as session:
            with open(file_path, 'r', newline='', encoding="utf-8") as fd:
                reader = csv.DictReader(fd)
                data = [row for row in reader]

            tasks = [upload_data(session, row) for row in data]
            await asyncio.gather(*tasks)
            logger.info("Done!")

    except Exception as ex:
        logger.error(f'Error at read csv file {file_path}: {ex}')


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_application())
