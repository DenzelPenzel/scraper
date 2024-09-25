#!/usr/bin/env python

import asyncio
import json
import logging
import os
import time

import aiohttp
import path_util  # noqa: F401
from dotenv import load_dotenv

from scraper import init_logging
from scraper.app.scraper_app import FbScraper
from scraper.utils.csv import save_csv, upload_data

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_concurrent_requests = 10


async def bound_send_post(sem: asyncio.Semaphore, session: aiohttp.ClientSession, data: dict) -> None:
    async with sem:
        await upload_data(session, data)


async def run_application() -> None:
    username = os.getenv('USERNAME')
    password = os.getenv('PASS')
    group_name = os.getenv('GROUP_NAME')
    posts_count = 10
    timeout = 600
    # Do not set chrome_options.add_argument("--headless") to see the browser window
    headless = False
    sem = asyncio.Semaphore(max_concurrent_requests)

    init_logging("scrapper_logs.yml")
    start_at = time.time()
    logger.info("Start scrapper app")

    s = FbScraper(
        page_or_group_name=group_name,
        posts_count=posts_count,
        isGroup=True,
        proxy=None,
        headless=headless,
        username=username,
        password=password,
        timeout=timeout
    )

    try:
        data = s.scrap_to_json()
        logger.info(f"Script running time {time.time() - start_at}")
        json_data = json.loads(data)
        logger.info(f"Parsed {len(json_data)} posts, saving phase...")

        # save parsed data to csv file
        save_csv(json_data)

        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.create_task(bound_send_post(sem, session, json_data[key]))
                for key in json_data
            ]
            await asyncio.gather(*tasks)

        logger.info("Done!")

    except Exception as ex:
        logging.error("An error occurred while running the application")
        logging.exception(ex)


if __name__ == "__main__":
    asyncio.run(run_application())
