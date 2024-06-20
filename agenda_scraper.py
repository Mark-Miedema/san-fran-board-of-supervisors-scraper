import os
import requests
import fitz  # PyMuPDF
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup the Chrome driver
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run headless Chrome to avoid opening a browser window
driver = webdriver.Chrome(service=service, options=options)

# Base directory for saving files
base_output_dir = 'San_Fran_Board_of_Supervisors_File'
os.makedirs(base_output_dir, exist_ok=True)

# Month mapping for folder naming
month_map = {
    'Jan': '01-Jan', 'Feb': '02-Feb', 'Mar': '03-Mar', 'Apr': '04-Apr', 'May': '05-May', 'Jun': '06-Jun',
    'Jul': '07-Jul', 'Aug': '08-Aug', 'Sep': '09-Sep', 'Oct': '10-Oct', 'Nov': '11-Nov', 'Dec': '12-Dec'
}


# Function to extract data from the current page
def extract_data_from_page():
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "table.views-table tbody tr")
        for row in rows:
            date_time = row.find_element(By.CSS_SELECTOR, "td.views-field-field-event-date").text
            event = row.find_element(By.CSS_SELECTOR, "td.views-field-title a").text
            location = row.find_element(By.CSS_SELECTOR, "td.views-field-field-event-location-premise").text
            link = row.find_element(By.CSS_SELECTOR, "td.views-field-title a").get_attribute("href")
            events.append({
                "date_time": date_time,
                "event": event,
                "location": location,
                "link": link
            })
    except Exception as e:
        logger.error(f"Error while extracting data from page: {e}")


# Function to download file
def download_file(url, dest_path):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(dest_path, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
        else:
            logger.error(f"Failed to download file from {url}: Status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Exception while downloading file from {url}: {e}")
        return False
    return True


# Function to convert PDF to HTML
def convert_pdf_to_html(pdf_path, html_path):
    try:
        doc = fitz.open(pdf_path)
        html_content = "<html><body>"
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("html")
            html_content += text
        html_content += "</body></html>"
        with open(html_path, 'w', encoding='utf-8') as html_file:
            html_file.write(html_content)
    except Exception as e:
        logger.error(f"Exception in converting PDF to HTML: {e}")


# Function to rename and save the file
def save_meeting_file(date_str, event, link, file_type):
    try:
        date_obj = datetime.strptime(date_str, '%A, %B %d, %Y - %I:%M%p')
        year = date_obj.strftime('%Y')
        month = date_obj.strftime('%b')
        formatted_date = date_obj.strftime('%b %d, %Y')
        meeting_type = "Regular" if "Board of Supervisors" in event else "Special"
        file_name = f"San_Fran_Board_of_Supervisors_File_{formatted_date}_Meeting {meeting_type} {file_type}.html"

        year_dir = os.path.join(base_output_dir, year)
        month_dir = os.path.join(year_dir, month_map[month])
        os.makedirs(month_dir, exist_ok=True)

        file_path = os.path.join(month_dir, file_name)

        if link.endswith('.pdf'):
            pdf_path = file_path.replace('.html', '.pdf')
            if download_file(link, pdf_path):
                convert_pdf_to_html(pdf_path, file_path)
                os.remove(pdf_path)
        else:
            if download_file(link, file_path):
                if link.endswith('.html') or link.endswith('.htm'):
                    logger.info(f"Downloaded HTML file for {link}")
                else:
                    convert_pdf_to_html(file_path, file_path)

    except Exception as e:
        logger.error(f"Exception in saving meeting file: {e}")


# Navigate to the website
driver.get("https://sfbos.org/events/calendar/past?field_event_category_tid=54")

# Wait until the table is loaded
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "table.views-table"))
)

events = []

# Extract data from the first page
extract_data_from_page()

# Iterate over all pages
while True:
    try:
        # Check if there is a "Next" button and it is enabled
        next_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@title, 'Go to next page')]"))
        )
        if 'disabled' in next_button.get_attribute('class'):
            break

        # Click the "Next" button
        next_button.click()

        # Wait for the new page to load
        time.sleep(2)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.views-table"))
        )

        # Extract data from the new page
        extract_data_from_page()

    except Exception as e:
        logger.error(f"Exception occurred during pagination: {e}")
        break

# Process each event
for event in events:
    date_time = event['date_time']
    event_name = event['event']
    link = event['link']
    if 'Board of Supervisors' in event_name:
        save_meeting_file(date_time, event_name, link, "Agenda")

# Close the driver
driver.quit()
