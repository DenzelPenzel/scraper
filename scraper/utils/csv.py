import csv
import logging
import os
from datetime import datetime
from os.path import exists, join
from typing import Set

import aiohttp

from scraper import data_path

logger = logging.getLogger()


def parse_csv(file_path: str) -> Set[str]:
    res = set()
    with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            if i == 0:
                continue
            res.add(row['id'])
    return res


def save_csv(data):
    try:
        root_path = data_path()
        file_path = join(root_path, "posts.csv")
        fieldnames = ['id', 'name', 'profile_url', 'content', 'post_url', 'group_images', 'profile_images', 'create_at']
        mode = 'w'
        if exists(file_path):
            mode = 'a'
        with open(file_path, mode, newline='', encoding="utf-8") as fd:
            writer = csv.DictWriter(fd, fieldnames=fieldnames)
            if mode == 'w':
                writer.writeheader()
            for key in data:
                post = data[key]
                writer.writerow({
                    'id': key,
                    'name': post.get('name', ''),
                    'profile_url': post.get('profile_url', ''),
                    'content': post.get('content', ''),
                    'post_url': post.get('post_url', ''),
                    'group_images': " ".join(post.get('group_images', [])),
                    'profile_images': " ".join(post.get('profile_images', [])),
                    "create_at": post.get('create_at', datetime.now()),
                })
    except Exception as ex:
        logger.error(f'Error at save to csv: {ex}')


async def upload_data(session: aiohttp.ClientSession, data: dict) -> None:
    try:
        server_uri = os.getenv('SERVER_URL')
        async with session.post(server_uri, json=data, headers=None) as resp:
            resp.raise_for_status()
            result = await resp.json()
            logger.info(f"Successfully save post: {result}")
    except aiohttp.ClientError as e:
        logger.error(f"Failed to save post: {data['name']} with error: {str(e)}")
