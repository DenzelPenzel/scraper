import json
import logging
import os
import platform
import time
from os.path import join

from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from seleniumwire import webdriver
from webdriver_manager.firefox import GeckoDriverManager

import scraper.utils.csv as csvutils
import scraper.utils.selenium_utils as sutils
from scraper import data_path

s_logger = None


def is_macos_platform():
    return platform.system() == 'Darwin'


class Init:
    def __init__(self, proxy=None, headless=True):
        self.proxy = proxy
        self.headless = headless

    @classmethod
    def logger(cls):
        global s_logger
        if s_logger is None:
            s_logger = logging.getLogger(__name__)
        return s_logger

    def set_properties(self, browser_option):
        if self.headless:
            browser_option.add_argument('--headless')
        # browser_option.add_argument('--no-sandbox')
        browser_option.add_argument("--disable-dev-shm-usage")
        browser_option.add_argument('--ignore-certificate-errors')
        browser_option.add_argument('--disable-gpu')
        # browser_option.add_argument('--log-level=3')
        browser_option.add_argument('--disable-notifications')
        # browser_option.add_argument('--disable-popup-blocking')
        return browser_option

    def init(self) -> webdriver.Firefox:
        browser_option = FirefoxOptions()
        # automatically installs chromedriver and initialize it and returns the instance
        firefox_service = FirefoxService(executable_path=GeckoDriverManager().install(), log_path='geckodriver.log')

        if self.proxy is not None:
            options = {
                'https': 'https://{}'.format(self.proxy.replace(" ", "")),
                'http': 'http://{}'.format(self.proxy.replace(" ", "")),
                'no_proxy': 'localhost, 127.0.0.1'
            }
            self.logger().info("Using: {}".format(self.proxy))
            return webdriver.Firefox(executable_path=GeckoDriverManager().install(),
                                     options=self.set_properties(browser_option), seleniumwire_options=options)

        if is_macos_platform():
            return webdriver.Firefox(service=firefox_service, options=self.set_properties(browser_option),
                                     log_path='geckodriver.log')
        else:
            return webdriver.Firefox(options=self.set_properties(browser_option), log_path='geckodriver.log')


class FbScraper:
    def __init__(self, page_or_group_name, posts_count=10, proxy=None,
                 timeout=600, headless=True, isGroup=False, username=None, password=None):
        self.page_or_group_name = page_or_group_name
        self.posts_count = posts_count
        self.URL = f"https://facebook.com/groups/{self.page_or_group_name}"
        self.driver: webdriver.Firefox
        self.proxy = proxy
        self.timeout = timeout
        self.headless = headless
        self.isGroup = isGroup
        self.username = username
        self.password = password
        self.count = 0
        self.data_dct = {}
        self.visited_posts = set()
        root_path = data_path()
        file_path = join(root_path, "posts.csv")

        if os.path.exists(file_path):
            self.visited_posts = csvutils.parse_csv(file_path)

    @classmethod
    def logger(cls):
        global s_logger
        if s_logger is None:
            s_logger = logging.getLogger(__name__)
        return s_logger

    def _init_driver(self):
        self.logger().info("Init selenium driver...")
        self.driver = Init(self.proxy, self.headless).init()

    def _handle_popup(self):
        try:
            sutils.close_modern_layout_signup_modal(self.driver)
            sutils.close_cookie_consent_modern_layout(self.driver)
        except Exception as ex:
            self.logger().exception("Error at handle_popup : {}".format(ex))

    def reach_timeout(self, start_time, current_time) -> bool:
        return (current_time - start_time) > self.timeout

    def parse_page(self, url: str, name: str):
        self._init_driver()

        self.driver.get(self.URL)

        sutils.accept_cookies(self.driver)
        # pass login and pass
        self.username is not None and sutils.login(self.driver, self.username, self.password)

        # sometimes we get popup that says "your request couldn't be processed", however
        # posts are loading in background if popup is closed, so call this method in case if it pops up.
        sutils.close_error_popup(self.driver)

        self._handle_popup()

        self.driver.get(url)
        images = sutils.find_profile_image(self.driver, name)
        self.logger().info(f"Found images: {images}")

    def scrap_to_json(self):
        self.logger().info("Scraping posts and saving them as JSON...")
        self._init_driver()
        start_at = time.time()

        self.driver.get(self.URL)

        sutils.accept_cookies(self.driver)
        # pass login and pass
        self.username is not None and sutils.login(self.driver, self.username, self.password)

        # sometimes we get popup that says "your request couldn't be processed", however
        # posts are loading in background if popup is closed, so call this method in case if it pops up.
        sutils.close_error_popup(self.driver)

        elements_have_loaded = sutils.wait_for_element_to_appear(self.driver, self.timeout)
        sutils.scroll_down(self.driver)
        self._handle_popup()

        while len(self.data_dct) < self.posts_count and elements_have_loaded:
            found_posts = 0
            while found_posts < self.posts_count:
                self._handle_popup()
                posts = sutils.find_all_posts(self.driver, self.isGroup)
                found_posts = len(posts)
                start_at = self.sleep(start_at)
                sutils.scroll_down(self.driver)

            self._handle_popup()
            posts = sutils.find_all_posts(self.driver, self.isGroup)

            self.logger().info(f"Processed {len(self.data_dct)} posts 🎊 continue...")

            for post in posts:
                try:
                    key, post_url, link_element = sutils.find_post_status(post, self.isGroup)

                    if post_url is None or key in self.visited_posts:
                        continue

                    self.visited_posts.add(key)

                    post_url = post_url.split('?')[0]
                    name, profile_url = sutils.find_post_name(post)
                    content = sutils.find_post_content(post, self.driver)
                    group_images = sutils.find_post_image_url(post)
                    create_at = sutils.find_post_time(
                        post, link_element, self.driver, self.isGroup)

                    if not name or name == 'Anonymous participant' or not content or not group_images:
                        continue

                    self.data_dct[key] = {
                        "name": name,
                        "profile_url": profile_url,
                        "content": content,
                        "post_url": post_url,
                        "group_images": group_images,
                        "create_at": create_at,
                    }
                except Exception as ex:
                    self.logger().exception(f"Failed to process the post, error: {ex}")

            start_at = self.sleep(start_at)
            sutils.scroll_down(self.driver)

        for key, item in self.data_dct.items():
            try:
                self.driver.get(item['profile_url'])
                sutils.wait_for_element_to_appear(self.driver, self.timeout)
                images = sutils.find_profile_image(self.driver, item['name'])
                if not images:
                    self.logger().info(f"Not found profile image name: {item['name']} url: {item['profile_url']}")
                self.data_dct[key]['profile_images'] = images
                time.sleep(3.0)
            except Exception as ex:
                self.logger().info(f"Failed to parse user profile: {item['profile_url']}, error: {ex}")

        sutils.close_driver(self.driver)
        return json.dumps(self.data_dct, ensure_ascii=False)

    def sleep(self, start_at):
        if self.reach_timeout(start_at, time.time()):
            self.logger().info('Timeout...')
            time.sleep(60.0)
            return time.time()
        else:
            return start_at
