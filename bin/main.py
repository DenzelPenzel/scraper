import os
import scraper
import json
import logging
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_concurrent_requests = 10


async def upload_data(session: aiohttp.ClientSession, data: dict) -> None:
    try:
        server_uri = os.getenv('SERVER_URL')
        async with session.post(server_uri, json=data, headers=None) as resp:
            resp.raise_for_status()
            result = await resp.json()
            logger.info(f"Successfully sent data: {result}")
    except aiohttp.ClientError as e:
        logger.error(f"Request failed for data: {data['name']} with error: {str(e)}")


async def bound_send_post(sem: asyncio.Semaphore, session: aiohttp.ClientSession, data: dict) -> None:
    async with sem:
        await upload_data(session, data)


async def main():
    username = os.getenv('USERNAME')
    password = os.getenv('PASS')
    group_name = "UTrippers"
    posts_count = 100
    timeout = 600
    headless = True
    sem = asyncio.Semaphore(max_concurrent_requests)

    data = scraper.FbScraper(
        page_or_group_name=group_name,
        posts_count=posts_count,
        isGroup=True,
        proxy=None,
        # Do not set chrome_options.add_argument("--headless") to see the browser window
        headless=headless,
        username=username,
        password=password,
        timeout=timeout
    ).scrap_to_json()

    # save parsed data to csv file
    scraper.save_csv(data)

    async with aiohttp.ClientSession() as session:
        json_data = json.loads(data)
        tasks = [
            asyncio.create_task(bound_send_post(sem, session, json_data[key]))
            for key in json_data
        ]
        await asyncio.gather(*tasks)

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
