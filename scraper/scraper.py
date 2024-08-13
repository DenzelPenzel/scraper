from seleniumwire import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.firefox import GeckoDriverManager
import logging
import json
import time
import scraper.find as find
import scraper.utils as utils

logger = logging.getLogger(__name__)
format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(format)
logger.addHandler(ch)


class Init:
    def __init__(self, proxy=None, headless=True):
        self.proxy = proxy
        self.headless = headless

    def set_properties(self, browser_option):
        if self.headless:
            browser_option.add_argument('--headless')  # runs browser in headless mode
        browser_option.add_argument('--no-sandbox')
        browser_option.add_argument("--disable-dev-shm-usage")
        browser_option.add_argument('--ignore-certificate-errors')
        browser_option.add_argument('--disable-gpu')
        browser_option.add_argument('--log-level=3')
        browser_option.add_argument('--disable-notifications')
        browser_option.add_argument('--disable-popup-blocking')
        return browser_option

    def init(self) -> webdriver.Firefox:
        logger.setLevel(logging.INFO)
        browser_option = FirefoxOptions()
        # automatically installs chromedriver and initialize it and returns the instance
        firefox_service = FirefoxService(executable_path=GeckoDriverManager().install())

        if self.proxy is not None:
            options = {
                'https': 'https://{}'.format(self.proxy.replace(" ", "")),
                'http': 'http://{}'.format(self.proxy.replace(" ", "")),
                'no_proxy': 'localhost, 127.0.0.1'
            }
            logger.info("Using: {}".format(self.proxy))
            return webdriver.Firefox(executable_path=GeckoDriverManager().install(),
                                     options=self.set_properties(browser_option), seleniumwire_options=options)

        return webdriver.Firefox(service=firefox_service,
                                 options=self.set_properties(browser_option))


class FbScraper:
    def __init__(self, page_or_group_name, posts_count=10, proxy=None,
                 timeout=600, headless=True, isGroup=False, username=None, password=None):
        self.page_or_group_name = page_or_group_name
        self.posts_count = posts_count
        self.URL = f"https://facebook.com/groups/{self.page_or_group_name}"
        self.driver: webdriver.Firefox
        self.proxy = proxy
        self.layout = None
        self.timeout = timeout
        self.headless = headless
        self.isGroup = isGroup
        self.username = username
        self.password = password
        self.data_dct = {}
        # __extracted_post contains all the post's ID that have been scraped before and as it set()
        # it avoids post's ID duplication
        self.extracted_post = set()

    def _init_driver(self):
        self.driver = Init(self.proxy, self.headless).init()

    def _handle_popup(self, layout):
        try:
            if layout == "old":
                # if during scrolling any of error or signup popup shows
                utils.close_error_popup(self.driver)
                utils.close_popup(self.driver)
            elif layout == "new":
                utils.close_modern_layout_signup_modal(self.driver)
                utils.close_cookie_consent_modern_layout(self.driver)
        except Exception as ex:
            logger.exception("Error at handle_popup : {}".format(ex))

    def reach_timeout(self, start_time, current_time) -> bool:
        return (current_time - start_time) > self.timeout

    def remove_duplicates(self, posts):
        if len(self.extracted_post) == 0:
            self.extracted_post.update(posts)
            return posts
        removed_duplicated = [post for post in posts if post not in self.extracted_post]
        self.extracted_post.update(posts)
        return removed_duplicated

    def scrap_to_json(self):
        self._init_driver()
        start_at = time.time()

        self.driver.get(self.URL)

        find.accept_cookies(self.driver)
        # pass login creds
        self.username is not None and find.login(self.driver, self.username, self.password)

        self.layout = find.detect_ui(self.driver)
        # sometimes we get popup that says "your request couldn't be processed", however
        # posts are loading in background if popup is closed, so call this method in case if it pops up.
        utils.close_error_popup(self.driver)

        elements_have_loaded = utils.wait_for_element_to_appear(self.driver, self.layout, self.timeout)
        utils.scroll_down(self.driver, self.layout)
        self._handle_popup(self.layout)

        while len(self.data_dct) < self.posts_count and elements_have_loaded:
            self._handle_popup(self.layout)

            all_posts = find.find_all_posts(self.driver, self.layout, self.isGroup)
            all_posts = self.remove_duplicates(all_posts)

            logger.info("Found posts len: {}".format(len(all_posts)))

            for post in all_posts:
                try:
                    key, post_url, link_element = find.find_post_status(post, self.layout, self.isGroup)

                    if post_url is None:
                        continue

                    post_url = post_url.split('?')[0]
                    name, profile_url = find.find_post_name(post, self.layout)
                    content = find.find_post_content(post, self.driver, self.layout)
                    group_images = find.find_post_image_url(post, self.layout)

                    create_at = find.find_post_time(
                        post, self.layout, link_element, self.driver, self.isGroup)

                    self.data_dct[key] = {
                        "name": name,
                        "profile_url": profile_url,
                        "content": content,
                        "post_url": post_url,
                        "group_images": group_images,
                        "create_at": create_at,
                    }
                except Exception as ex:
                    logger.exception("Error at find_elements method : {}".format(ex))

            current_time = time.time()

            if self.reach_timeout(start_at, current_time):
                logger.setLevel(logging.INFO)
                logger.info('Timeout...')
                time.sleep(10)
                start_at = time.time()

            utils.scroll_down(self.driver, self.layout)

        for key, item in self.data_dct.items():
            self.driver.get(item['profile_url'])
            images = find.find_profile_image(self.driver, item['name'])
            self.data_dct[key]['profile_images'] = images

        utils.close_driver(self.driver)
        return json.dumps(self.data_dct, ensure_ascii=False)
