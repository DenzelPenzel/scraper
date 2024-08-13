import csv
import json
import logging
import sys
import time
import re
import os
from os.path import join, realpath, exists
from pathlib import Path

from random import randint
from datetime import datetime
from datetime import datetime as dt
from datetime import timedelta

from selenium.common.exceptions import (NoSuchElementException,
                                        WebDriverException)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)
format = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(format)
logger.addHandler(ch)

_data_path = None


def extract_numbers(string):
    """expects string and returns numbers from them as integer type,
    e.g => input = '54454 comment', than output => 54454
    """
    try:
        # return string.split(" ")[0]
        return re.findall("\d+", string)[0]
    except IndexError:
        return 0


def exists_in_list(li, word):
    """expects list and a element, returns all the occurence of element in the list.
    e.g input => li = ['sajid','sajid','sajid','d','s'] with given word = 'sajid',
    output => ['sajid','sajid','sajid'] """
    return [substring for substring in li if word in substring]


def convert_time(unix_timestamp):
    try:
        return dt.utcfromtimestamp(float(unix_timestamp)).isoformat()
    except Exception as ex:
        logger.exception('Error at convert_time : {}'.format(ex))


def extract_content(content):
    """returns the text content of selenium element, else if content is string than returns a empty string"""
    if type(content) is not str:
        all_para = content.find_elements(By.TAG_NAME, "p")
        paragraph = ''
        for para in all_para:
            paragraph += para.get_attribute("textContent")
            content = paragraph
    else:
        content = ""
    return content


def count_reaction(dictionary):
    """expects a dictionary and returns sum of all values of dictionary.
    e.g =>
    input dictionary = {"s":1,"d":34},
    output=> 35"""
    return sum(dictionary.values())


def extract_id_from_link(link):
    """expects the post's URL as a argument, and extracts out post_id from that URL"""
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
        logger.exception(
            'Error at extract_id_from_link : {}'.format(ex))


def value_to_float(x):
    try:
        x = float(x)
        return x
    except:
        pass
    x = x.lower()
    if 'k' in x:
        if len(x) > 1:
            return float(x.replace('k', '')) * 1000
        return 1000
    if 'm' in x:
        if len(x) > 1:
            return float(x.replace('m', '')) * 1000000
        return 1000000
    if 'm' in x:
        return float(x.replace('m', '')) * 1000000000
    return 0


def find_reaction_by_text(l, string):
    reaction = [substring for substring in l if string in substring]
    if len(reaction) == 0:
        return '0'
    reaction = re.findall(
        r"(\d+(?:\.\d+)?)([MmBbKk])?", reaction[0])
    if len(reaction) > 0:
        return ''.join(reaction[0])  # list of tuple, return first tuple's first result
    return '0'


def convert_to_iso(t):
    past_date = "Failed to fetch!"
    if 'h' in t.lower() or "hr" in t.lower() or "hrs" in t.lower():
        hours_to_subract = re.sub("\D", '', t)
        # print(f"{hours_to_subract} subtracting hours\n")
        past_date = datetime.today() - timedelta(hours=int(hours_to_subract))
        # print(past_date.timestamp())
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
        # print(f"{days_to_subtract} subtracting days\n")
        past_date = datetime.today() - timedelta(days=int(days_to_subtract))
        # print(past_date.timestamp())
        return past_date.isoformat()
    # print(f"time is : {t}")
    return past_date


def close_driver(driver):
    """expects driver's instance, closes the driver"""
    try:
        driver.close()
        driver.quit()
    except Exception as ex:
        logger.exception("Error at close_driver method : {}".format(ex))


def close_error_popup(driver):
    '''expects driver's instance as a argument and checks if error shows up
    like "We could not process your request. Please try again later" ,
    than click on close button to skip that popup.'''
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
        logger.exception(
            "Error at close_error_popup method : {}".format(ex))


def scroll_down_half(driver):
    try:
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight / 2);")
    except Exception as ex:
        # if any error occured than close the driver and exit
        close_driver(driver)
        logger.exception(
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
        logger.exception(
            "Error at close_modern_layout_signup_modal: {}".format(ex))


def scroll_down(driver, layout):
    """expects driver's instance as a argument, and it scrolls down page to the most bottom till the height"""
    try:
        if layout == "old":
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
        elif layout == "new":
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
        logger.exception("Error at scroll_down method : {}".format(ex))


def close_popup(driver):
    """expects driver's instance and closes modal that ask for login, by clicking "Not Now" button """
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
        logger.exception("Error at close_popup method : {}".format(ex))


def wait_for_element_to_appear(driver, layout, timeout):
    """expects driver's instance, wait for posts to show.
    post's CSS class name is userContentWrapper
    """
    try:
        if layout == "old":
            # wait for page to load so posts are visible
            body = driver.find_element(By.CSS_SELECTOR, "body")
            for _ in range(randint(3, 5)):
                body.send_keys(Keys.PAGE_DOWN)
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.userContentWrapper')))
            return True
        elif layout == "new":
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-posinset]")))
            print("new layout loaded")

            return True

    except WebDriverException:
        # if it was not found,it means either page is not loading or it does not exists
        logger.critical("No posts were found!")
        return False
        # (optional) exit the program, because if posts does not exists,we cannot go further
        # close_driver(driver)
        # sys.exit(1)
    except Exception as ex:
        logger.exception(
            "Error at wait_for_element_to_appear method : {}".format(ex))
        return False
        # close_driver(driver)


def click_see_more(driver, content, selector=None):
    """expects driver's instance and selenium element, click on "see more" link to open hidden content"""
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
        logger.exception("Error at click_see_more method : {}".format(ex))


def close_cookie_consent_modern_layout(driver):
    try:
        allow_span = driver.find_element(
            By.XPATH, '//div[contains(@aria-label, "Allow")]/../following-sibling::div')
        allow_span.click()
    except Exception as ex:
        logger.info('The Cookie Consent Prompt was not found!: ', ex)


def root_path() -> Path:
    return Path(realpath(join(__file__, "../../")))


def data_path():
    global _data_path
    if _data_path is None:
        _data_path = realpath(join(root_path(), "data"))

    if not os.path.exists(_data_path):
        os.makedirs(_data_path)
    return _data_path


def save_csv(data):
    try:
        data = json.loads(data)
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
        logger.exception(f'Error at save to csv: {ex}')
