import logging
import re
import sys
import time
import urllib.request

from dateutil.parser import parse
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from scraper.utils import extract_id_from_link, convert_to_iso, close_driver, click_see_more

logger = logging.getLogger(__name__)
format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(format)
logger.addHandler(ch)


def get_status_link(link_list):
    status = ""
    for link in link_list:
        link_value = link.get_attribute("href")
        if "/posts/" in link_value and "/groups/" in link_value:
            status = link
            break
        if "/posts/" in link_value:
            status = link
            break
        if "/videos/pcb" in link_value:
            status = link
            break
        elif "/photos/" in link_value:
            status = link
            break
        if "fbid=" in link_value:
            status = link
            break
        elif "/group/" in link_value:
            status = link
            break
        if "/videos/" in link_value:
            status = link
            break
        elif "/groups/" in link_value:
            status = link
            break
    return status


def find_post_status(post, isGroup):
    """finds URL of the post, then extracts link from that URL and returns it"""
    try:
        link = None
        status_link = None
        status = None

        link = post.find_element(
            By.CSS_SELECTOR, 'span > a[role="link"]' if isGroup else 'span > a[aria-label][role="link"]'
        )
        if link is not None:
            status_link = link.get_attribute("href")
            status = extract_id_from_link(status_link)
            if not isGroup and status_link and status:  # early exit for non group
                return status, status_link, link

        links = post.find_elements(By.TAG_NAME, 'a')
        if links:
            # Initialize variables to store the matching link element and URL
            matching_link_element = None
            post_url = None

            # Iterate over links to find the first one that matches the criteria
            for link in links:
                href = link.get_attribute('href')
                if href and '/groups/' in href:
                    post_url = href  # Store the URL
                    matching_link_element = link  # Store the link element
                    break  # Exit the loop after finding the first match

            # Check if a matching link was found
            if post_url and matching_link_element:
                status = extract_id_from_link(post_url)
                # Now you have the URL, the status, and the matching link element itself
                return status, post_url, matching_link_element

    except NoSuchElementException:
        # if element is not found
        status = "NA"

    except Exception as ex:
        logger.exception("Error at find_status method : {}".format(ex))
        status = "NA"
    return status, status_link, link


def find_share(post):
    """finds shares count of the facebook post using selenium's webdriver's method"""
    try:
        element = post.find_element(
            By.XPATH, './/div/span/div/span[contains(text(), " share")]'
        )
        shares = "0"
        if not element:
            return shares
        return element.text.replace(' shares', '').replace(' share', '')
    except NoSuchElementException:
        # if element is not present that means there wasn't any shares
        shares = 0

    except Exception as ex:
        logger.exception("Error at Find Share method : {}".format(ex))
        shares = 0

    return shares


def find_reactions(post):
    """finds all reaction of the facebook post using selenium's webdriver's method"""
    try:
        # find element that have attribute aria-label as 'See who reacted to this
        reactions_all = post.find_element(
            By.CSS_SELECTOR, '[aria-label="See who reacted to this"]'
        )
    except NoSuchElementException:
        reactions_all = ""
    except Exception as ex:
        logger.exception("Error at find_reactions method : {}".format(ex))
    return reactions_all


def find_comments(post):
    """finds comments count of the facebook post using selenium's webdriver's method"""
    try:
        element = post.find_element(
            By.XPATH, './/div/span/div/span[contains(text(), " comment")]'
        )
        comments = 0
        if element is None:
            return comments
        return element.text.replace(' comments', '').replace(' comment', '')
    except NoSuchElementException:
        comments = 0
    except Exception as ex:
        logger.exception("Error at find_comments method : {}".format(ex))
        comments = 0

    return comments


def fetch_post_passage(href):
    response = urllib.request.urlopen(href)

    text = response.read().decode("utf-8")

    post_message_div_finder_regex = (
        '<div data-testid="post_message" class=".*?" data-ft=".*?">(.*?)<\/div>'
    )

    post_message = re.search(post_message_div_finder_regex, text)

    replace_html_tags_regex = "<[^<>]+>"
    message = re.sub(replace_html_tags_regex, "", post_message.group(0))

    return message


def element_exists(element, css_selector):
    try:
        found = element.find_element(By.CSS_SELECTOR, css_selector)
        return True
    except NoSuchElementException:
        return False


def find_post_content(post, driver):
    """finds content of the facebook post using selenium's webdriver's method and returns string containing text of the posts"""
    try:
        post_content = post.find_element(
            By.CSS_SELECTOR, '[data-ad-preview="message"]'
        )
        # if "See More" button exists
        if element_exists(
                post_content, 'div[dir="auto"] > div[role]'
        ):
            element = post_content.find_element(
                By.CSS_SELECTOR, 'div[dir="auto"] > div[role]'
            )  # grab that element
            if element.get_attribute("target"):
                content = fetch_post_passage(element.get_attribute("href"))
            else:
                click_see_more(
                    driver, post_content, 'div[dir="auto"] > div[role]'
                )
                content = post_content.get_attribute(
                    "textContent"
                )  # extract content out of it
        else:
            # if it does not have see more, just get the text out of it
            content = post_content.get_attribute("textContent")

    except NoSuchElementException:
        # if [data-testid="post_message"] is not found, it means that post did not had any text,either it is image or video
        content = ""
    except Exception as ex:
        logger.exception("Error at find_content method : {}".format(ex))
        content = ""
    return content


def find_post_time(post, link_element, driver, isGroup):
    """finds posted time of the facebook post using selenium's webdriver's method"""
    try:

        if isGroup:
            # NOTE There is no aria_label on these link elements anymore
            # Facebook uses a shadowDOM element to hide timestamp, which is tricky to extract
            # An unsuccesful attempt to extract time from nested shadowDOMs is below

            js_script = """
                // Starting from the provided element, find the SVG using querySelector
                var svgElement = arguments[0].querySelector('svg');

                // Assuming we're looking for a shadow DOM inside or related to the <use> tag, which is unconventional
                // var useElement = svgElement.querySelector('use');

                // Placeholder for accessing the shadow DOM, which is not directly applicable to <use> tags.
                // This step assumes there's some unconventional method to access related shadow content
                var shadowContent;

                // Hypothetically accessing shadow DOM or related content. This part needs adjustment based on actual structure or intent
                // As <use> tags don't host shadow DOMs, this is speculative and might represent a different approach in practice
                if (svgElement.shadowRoot) {
                    shadowContent = svgElement.shadowRoot.querySelector('some-element').textContent;
                } else {
                    // Fallback or alternative method to access intended content, as direct shadow DOM access on <use> is not standard
                    shadowContent = 'Fallback or alternative content access method needed';
                }

                return shadowContent;
            """
            # Execute the script with the link_element as the argument
            timestamp = driver.execute_script(js_script, link_element)
            print("TIMESTAMP: " + str(timestamp))
        elif not isGroup:
            aria_label_value = link_element.get_attribute("aria-label")
            timestamp = (
                parse(aria_label_value).isoformat()
                if len(aria_label_value) > 5
                else convert_to_iso(
                    aria_label_value
                )
            )
        return timestamp

    except TypeError:
        timestamp = ""
    except Exception as ex:
        logger.exception("Error at find_posted_time method : {}".format(ex))
        timestamp = ""
        return timestamp


def find_video_url(post):
    """finds video of the facebook post using selenium's webdriver's method"""
    try:
        # if video is found in the post, than create a video URL by concatenating post's id with page_name
        video_element = post.find_elements(By.TAG_NAME, "video")
        srcs = []
        for video in video_element:
            srcs.append(video.get_attribute("src"))
    except NoSuchElementException:
        video = []
        pass
    except Exception as ex:
        video = []
        logger.exception("Error at find_video_url method : {}".format(ex))

    return srcs


def find_post_image_url(post):
    """finds all image of the facebook post using selenium's webdriver's method"""
    try:
        images = post.find_elements(
            By.CSS_SELECTOR, "div > img[referrerpolicy]"
        )
        sources = (
            [image.get_attribute("src") for image in images]
            if len(images) > 0
            else []
        )
    except NoSuchElementException:
        sources = []
        pass
    except Exception as ex:
        logger.exception("Error at find_image_url method : {}".format(ex))
        sources = []

    return sources


def find_all_posts(driver, isGroup):
    """finds all posts of the facebook page using selenium's webdriver's method"""
    try:
        # all_posts = driver.find_elements(By.CSS_SELECTOR, "div[role='feed'] > div")
        # different query selectors depending on if we are scraping a FB page or group
        return driver.find_elements(By.CSS_SELECTOR,
                                    "div[role='feed'] > div" if isGroup else 'div[role="article"]')
    except NoSuchElementException:
        logger.error("Cannot find any posts! Exiting!")
        # if this fails to find posts that means, code cannot move forward, as no post is found
        close_driver(driver)
        sys.exit(1)
    except Exception as ex:
        logger.exception("Error at find_all_posts method : {}".format(ex))
        close_driver(driver)
        sys.exit(1)


def find_post_name(driverOrPost):
    """finds name of the facebook page or post using selenium's webdriver's method"""
    # Attempt to print the outer HTML of the driverOrPost for debugging

    try:
        name = driverOrPost.find_element(By.TAG_NAME, "strong").get_attribute(
            "textContent"
        )

        profile_url = driverOrPost.find_element(
            By.CSS_SELECTOR, "span > a[attributionsrc]"
        ).get_attribute("href")

        return name, profile_url
    except Exception as ex:
        logger.exception("Error at __find_name method : {}".format(ex))


def find_profile_image(driver, name):
    try:
        profile_img = driver.find_elements(By.CSS_SELECTOR, f"svg[aria-label='{name}'][role='img'] > g > image")
        return [el.get_attribute("xlink:href") for el in profile_img]
    except Exception as ex:
        logger.exception("Error find_profile_image: {}".format(ex))


def detect_ui(driver):
    try:
        driver.find_element(By.ID, "pagelet_bluebar")
        return "old"
    except NoSuchElementException:
        return "new"
    except Exception as ex:
        logger.exception("Error art __detect_ui: {}".format(ex))
        close_driver(driver)
        sys.exit(1)


def find_reaction(reactions_all):
    try:
        return reactions_all.find_elements(By.TAG_NAME, "div")

    except Exception as ex:
        logger.exception("Error at find_reaction : {}".format(ex))
        return ""


def accept_cookies(driver):
    try:
        WebDriverWait(driver, 4)
        button = driver.find_elements(
            By.CSS_SELECTOR, '[aria-label="Allow all cookies"]'
        )
        button[-1].click()
    except (NoSuchElementException, IndexError):
        pass
    except Exception as ex:
        logger.exception("Error at accept_cookies: {}".format(ex))
        sys.exit(1)


def login(driver, username, password):
    try:

        wait = WebDriverWait(driver, 4)  # considering that the elements might load a bit slow

        # NOTE this closes the login modal pop-up if you choose to not login above
        try:
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Close"]')))
            element.click()  # Click the element
        except Exception as ex:
            print(f"no pop-up")

        time.sleep(1)
        # target username
        username_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='email']")))
        password_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='pass']")))

        # enter username and password
        username_element.clear()
        username_element.send_keys(str(username))
        password_element.clear()
        password_element.send_keys(str(password))

        # target the login button and click it
        try:
            # Try to click the first button of type 'submit'
            WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
        except TimeoutException:
            # If the button of type 'submit' is not found within 2 seconds, click the first 'button' found
            WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button"))).click()
    except (NoSuchElementException, IndexError):
        pass
    except Exception as ex:
        logger.exception("Error at login: {}".format(ex))
        # sys.exit(1)
