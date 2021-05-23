import json
import time

from bs4 import BeautifulSoup
import requests
import pandas as pd

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

from tqdm import tqdm


base_url = "https://trustpilot.com"


def get_soup(url):
    return BeautifulSoup(requests.get(url).content, 'lxml')


def get_data():
    data = {}

    soup = get_soup(base_url + '/categories')
    for category in soup.findAll('div', {'class': 'categories_subCategory__3OxUx'}):
        name = category.find('h3', {'class': 'categories_subCategoryHeader__3Bd4c'}).text
        name = name.strip()
        data[name] = {}
        sub_categories = category.find('div', {'class': 'categories_subCategoryList__1FB-L'})
        for sub_category in sub_categories.findAll('div', {'class': 'categories_subCategoryItem__2Qwj8'}):
            sub_category_name = sub_category.text
            sub_category_uri = sub_category.find('a', {'class': 'link_internal__YpiJI typography_typography__23IQz typography_weight-inherit__2IsoB typography_fontstyle-inherit__PIgau link_navigation__2cxCi'})['href']
            data[name][sub_category_name] = sub_category_uri
    return data


def extract_company_urls_form_page(driver):
    a_list = driver.find_elements_by_xpath('//a[@class="link_internal__YpiJI link_wrapper__LEdx5"]')
    urls = [a.get_attribute('href') for a in a_list]
    dedup_urls = list(set(urls))
    dedup_urls = [url for url in dedup_urls if "/review/" in url]
    return dedup_urls


def go_next_page(driver):
    try:
        button = driver.find_element_by_xpath('//a[@class="pagination-link_paginationLinkNormalize__dzIry pagination-link_paginationLinkNext__1n3P4"]')
        return True, button
    except NoSuchElementException:
        return False, None


def setup_selenium():
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('start-maximized')
    options.add_argument('--headless')
    options.add_argument('disable-infobars')
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-web-security")

    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    return webdriver.Chrome('./driver/chromedriver', options=options)


def scrape_data(driver, data, timeout=3):

    company_urls = {}

    for category in tqdm(data):
        for sub_category in tqdm(data[category], leave=False):
            company_urls[sub_category] = []

            url = base_url + data[category][sub_category] + "?numberofreviews=0&timeperiod=0&status=all"
            driver.get(url)
            try:
                element_present = EC.presence_of_element_located(
                    (By.CLASS_NAME, 'link_internal__YpiJI link_wrapper__LEdx5'))

                WebDriverWait(driver, timeout).until(element_present)
            except Exception:
                pass

            next_page = True
            c = 1

            while next_page:
                extracted_company_urls = extract_company_urls_form_page(driver)
                company_urls[sub_category] += extracted_company_urls
                next_page, button = go_next_page(driver)

                if next_page:
                    c += 1
                    next_url = base_url + data[category][sub_category] + f"?numberofreviews=0&page={c}&status=all&timeperiod=0"
                    driver.get(next_url)
                    try:
                        element_present = EC.presence_of_element_located(
                            (By.CLASS_NAME, 'link_internal__YpiJI link_wrapper__LEdx5'))

                        WebDriverWait(driver, timeout).until(element_present)
                    except Exception:
                        pass

    return company_urls


def data_to_csv(company_urls, data):
    with open('./exports/company_urls_en', 'w') as f:
        json.dump(company_urls, f)

    consolidated_data = []
 
    for category in data:
        for sub_category in data[category]:
            for url in company_urls[sub_category]:
                consolidated_data.append((category, sub_category, url))

    df_consolidated_data = pd.DataFrame(consolidated_data, columns=['category', 'sub_category', 'company_url'])

    df_consolidated_data.to_csv('./exports/consolidate_company_urls.csv', index=False)


if __name__ == "__main__":
    data = get_data()
    data["Money & Insurance"]["Insurance"] = "/categories/insurance_agency"
    data["Shopping & Fashion"]["Accessories"] = "/categories/fashion_accessories_store"
    data["Travel & Vacation"]["Hotels"] = "/categories/hotel"
    data["Travel & Vacation"]["Travel Agencies"] = "/categories/travel_agency"
    data["Events & Entertainment"]["Gambling"] = "/categories/gambling_house"
    data["Events & Entertainment"]["Gaming"] = "/categories/gaming_service_provider"
    data["Home Services"]["Craftsman"] = "/categories/handyman"
    data["Vehicles & Transportation"]["Bicycles"] = "/categories/bicycle_store"
    driver = setup_selenium()
    company_urls = scrape_data(driver, data)
    data_to_csv(company_urls, data)
