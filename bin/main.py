#!/usr/bin/env python

import argparse
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
logger = logging.getLogger(__name__)
max_concurrent_requests = 10


async def bound_send_post(sem: asyncio.Semaphore, session: aiohttp.ClientSession, data: dict) -> None:
    async with sem:
        await upload_data(session, data)


async def run_application() -> None:
    parser = argparse.ArgumentParser(description="App parse facebook posts and user activities")
    parser.add_argument("-t", "--timeout", help="Set up page element timeout", default=30)
    parser.add_argument("-c", "--count", help="Set up count posts", default=10)
    parser.add_argument("-hl", "--headless", help="Use headless", default=True)

    args = parser.parse_args()
    username = os.getenv('USERNAME')
    password = os.getenv('PASS')
    group_name = os.getenv('GROUP_NAME')
    sem = asyncio.Semaphore(max_concurrent_requests)

    init_logging("scrapper_logs.yml")
    start_at = time.time()

    s = FbScraper(
        page_or_group_name=group_name,
        posts_count=args.count,
        isGroup=True,
        proxy=None,
        headless=args.headless,
        username=username,
        password=password,
        timeout=args.timeout
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
