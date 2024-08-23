import logging
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from random import randint

from dateutil.parser import parse
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

_data_path = None

logger = logging.getLogger()


def extract_id_from_link(link):
    # extracts out post_id from that URL
    try:
        status = "NA"
        # if url pattern container "/posts"
        if "posts/" in link:
            status = link.split('/')[5].split('?')[0]
        # if url pattern container "/photos"
        elif "photos/" in link:
            status = link.split("/")[-2]
        # if url pattern container "/videos"
        if "/videos/" in link:
            status = link.split("/")[5]
        elif "/reel/" in link:
            status = link.split("/")[4]
        elif "/events/" in link:
            status = link.split("/")[4]
        elif "fbid=" in link:
            status = link.split("=")[1].split("&")[0]
        elif "group" in link:
            status = link.split("/")[6]
        return status
    except IndexError:
        pass
    except Exception as ex:
        logger.error(
            'Error at extract_id_from_link : {}'.format(ex))


def convert_to_iso(t):
    past_date = "Failed to fetch!"
    if 'h' in t.lower() or "hr" in t.lower() or "hrs" in t.lower():
        hours_to_subract = re.sub("\D", '', t)
        past_date = datetime.today() - timedelta(hours=int(hours_to_subract))
        return past_date.isoformat()

    if 'm' in t.lower() or "min" in t.lower() or "mins" in t.lower():
        minutes_to_subtract = re.sub("\D", '', t)
        past_date = datetime.now() - timedelta(minutes=int(minutes_to_subtract))
        return past_date.isoformat()

    if 's' in t.lower():
        seconds_to_subtract = re.sub("\D", '', t)
        past_date = datetime.now() - timedelta(seconds=int(seconds_to_subtract))
        return past_date.isoformat()

    elif 'd' in t.lower() or "ds" in t.lower():
        days_to_subtract = re.sub("\D", '', t)
        past_date = datetime.today() - timedelta(days=int(days_to_subtract))
        return past_date.isoformat()
    return past_date


def close_driver(driver):
    try:
        driver.close()
        driver.quit()
    except Exception as ex:
        logger.error("Error at close_driver method : {}".format(ex))


def close_error_popup(driver):
    # checks if error shows up
    # like "We could not process your request. Please try again later" than click on close button to skip that popup
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'a.layerCancel')))  # wait for popup to show
        # grab that popup's close button
        button = driver.find_element(By.CSS_SELECTOR, "a.layerCancel")
        button.click()  # click "close" button
    except WebDriverException:
        # it is possible that even after waiting for given amount of time,modal may not appear
        pass
    except NoSuchElementException:
        pass  # passing this error silently because it may happen that popup never shows up

    except Exception as ex:
        # if any other error occured except the above one
        logger.error(
            "Error at close_error_popup method : {}".format(ex))


def scroll_down_half(driver):
    try:
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight / 2);")
    except Exception as ex:
        close_driver(driver)
        logger.error(
            "Error at scroll_down_half method : {}".format(ex))


def close_modern_layout_signup_modal(driver):
    try:
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        close_button = driver.find_element(
            By.CSS_SELECTOR, '[aria-label="Close"]')
        close_button.click()
    except NoSuchElementException:
        pass
    except Exception as ex:
        logger.error(
            "Error at close_modern_layout_signup_modal: {}".format(ex))


def scroll_down(driver):
    # Scrolls down page to the most bottom till the height
    try:
        body = driver.find_element(By.CSS_SELECTOR, "body")
        for _ in range(randint(1, 3)):
            body.send_keys(Keys.PAGE_UP)
        time.sleep(randint(5, 6))
        for _ in range(randint(5, 8)):
            body.send_keys(Keys.PAGE_DOWN)
        # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # close_modern_layout_signup_modal(driver)
    except Exception as ex:
        # if any error occured than close the driver and exit
        close_driver(driver)
        logger.error("Error at scroll_down method : {}".format(ex))


def close_popup(driver):
    # closes modal that ask for login, by clicking "Not Now" button
    try:
        # croll_down_half(driver)  #try to scroll
        # wait for popup to show
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
            (By.ID, 'expanding_cta_close_button')))
        # grab "Not Now" button
        popup_close_button = driver.find_element(
            By.ID, 'expanding_cta_close_button')
        popup_close_button.click()  # click the button
    except WebDriverException:
        # modal may not popup, so no need to raise exception in case it is not found
        pass
    except NoSuchElementException:
        pass  # passing this exception silently as modal may not show up
    except Exception as ex:
        logger.error("Error at close_popup method : {}".format(ex))


def wait_for_element_to_appear(driver, timeout):
    # wait for posts to show, post's CSS class name is userContentWrapper
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-posinset]")))
        return True

    except WebDriverException:
        # if it was not found,it means either page is not loading or it does not exists
        logger.critical("No posts were found!")
        return False
        # (optional) exit the program, because if posts does not exists,we cannot go further
        # close_driver(driver)
        # sys.exit(1)
    except Exception as ex:
        logger.error(
            "Error at wait_for_element_to_appear method : {}".format(ex))
        return False
        # close_driver(driver)


def click_see_more(driver, content, selector=None):
    # click on "see more" link to open hidden content
    try:
        if not selector:
            # find element and click 'see more' button
            element = content.find_element(
                By.CSS_SELECTOR, 'span.see_more_link_inner')
        else:
            element = content.find_element(By.CSS_SELECTOR,
                                           selector)
        # click button using js
        driver.execute_script("arguments[0].click();", element)

    except NoSuchElementException:
        # if it doesn't exists than no need to raise any error
        pass
    except AttributeError:
        pass
    except IndexError:
        pass
    except Exception as ex:
        logger.error("Error at click_see_more method : {}".format(ex))


def close_cookie_consent_modern_layout(driver):
    try:
        allow_span = driver.find_element(
            By.XPATH, '//div[contains(@aria-label, "Allow")]/../following-sibling::div')
        allow_span.click()
    except Exception as ex:
        logger.info('The Cookie Consent Prompt was not found!: ', ex)


def find_post_status(post, isGroup):
    # finds URL of the post, then extracts link from that URL and returns it
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
        return element.find_element(By.CSS_SELECTOR, css_selector)
    except NoSuchElementException:
        return False


def find_post_content(post, driver):
    # finds content of the facebook post, returns string containing text of the posts
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
    # finds posted time of the facebook post
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


def find_post_image_url(post):
    # finds all image of the facebook post
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
    # finds all posts of the facebook page
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
    # finds name of the facebook page or post
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
        except Exception:
            logger.info("Pop-up not found")

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
