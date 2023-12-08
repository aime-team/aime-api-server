import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


num_tabs = 3

url ="http://0.0.0.0:7777/stable_diffusion_img2img.html"

firefox_options = webdriver.FirefoxOptions()
firefox_options.set_preference("network.http.max-urgent-start-excessive-connections-per-host", 10)
firefox_options.set_preference("network.http.max-persistent-connections-per-server", 20)
browser = webdriver.Firefox(options=firefox_options)
browser.get("about:config")

for tab_number in range(num_tabs):
    browser.execute_script("window.open('', '_blank');")
tabs = browser.window_handles

for tab_number, tab in enumerate(tabs):
    browser.switch_to.window(tab)
    browser.get(url)

    file_input = browser.find_element(By.CSS_SELECTOR, "input[type='file']")
    file_input.send_keys('test_image.png')
    time.sleep(1)
    client_session_auth_key = browser.execute_script("return modelAPI.client_session_auth_key;")
    print('Tab no', tab_number, client_session_auth_key)



for tab_number, tab in enumerate(tabs):
    time.sleep(1)
    browser.switch_to.window(tab)
    send_button = browser.find_element(By.ID, "prompt_send")
    send_button.click()
    time.sleep(0.5)

finished_all = False

while not finished_all:
    finished_tab = [False for _ in tabs]
    for tab_number, tab in enumerate(tabs):

        browser.switch_to.window(tab)

        progress_label = browser.find_element(By.ID, "progress_label")
        queue_position_element = browser.find_element(By.ID, "queue_position")
    
        progress_data = progress_label.text
        queue_position = queue_position_element.text
        print(f"Tab {tab_number + 1} Progress Data: {progress_data}")
        print(f"Tab {tab_number + 1} {queue_position}")

        if progress_data == "100%":
            finished_tab[tab_number] = True
        finished_all = all(finished_tab)

        time.sleep(1)
browser.quit()





