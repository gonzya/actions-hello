#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub Actions 専用：楽天ROOM 投稿ボット
  * Selenium + Chrome (headless)
  * 商品はランキングページから 1 件抜粋
  * ID / PASS は環境変数で受け取る
"""

import os, time, random, sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException


RANKING_URL = "https://ranking.rakuten.co.jp/daily/"
LOGIN_URL   = "https://id.rakuten.co.jp/"
ROOM_POST_URL = "https://room.rakuten.co.jp/myroom/items/new"


# ---------- Selenium driver ----------
def get_driver() -> webdriver.Chrome:
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(
        service=webdriver.chrome.service.Service(
            ChromeDriverManager().install()
        ),
        options=opt,
    )


# ---------- login ----------
def login(drv: webdriver.Chrome):
    uid  = os.environ["RAKUTEN_ID"]
    pw   = os.environ["RAKUTEN_PASS"]

    drv.get(LOGIN_URL)
    WebDriverWait(drv, 15).until(
        EC.presence_of_element_located((By.ID, "loginInner_u"))
    )
    drv.find_element(By.ID, "loginInner_u").send_keys(uid)
    drv.find_element(By.ID, "loginInner_p").send_keys(pw)
    drv.find_element(By.ID, "loginInner_submit").click()

    # 成功判定：ROOM トップへのリンクが現れるまで待つ
    WebDriverWait(drv, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='room.rakuten.co.jp']"))
    )


# ---------- pick product ----------
def pick_product(drv: webdriver.Chrome) -> str:
    drv.get(RANKING_URL)

    try:
        a = WebDriverWait(drv, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[href^='https://item.rakuten.co.jp/']")
            )
        )
    except TimeoutException:
        raise TimeoutException("ランキング商品が見つかりません")

    return a.get_attribute("href")


# ---------- create post ----------
def create_post(drv: webdriver.Chrome, url: str):
    drv.get(ROOM_POST_URL)
    WebDriverWait(drv, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='url']"))
    )
    drv.find_element(By.CSS_SELECTOR, "input[name='url']").send_keys(url)
    drv.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # 投稿完了のトースト / テキストを確認
    WebDriverWait(drv, 20).until(
        EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'投稿が完了')]"))
    )


# ---------- main ----------
def main():
    daily_mode = "--daily" in sys.argv
    drv = get_driver()

    try:
        login(drv)
        url = pick_product(drv)
        if daily_mode:
            print("[dry-run] URL だけ表示:", url)
        else:
            create_post(drv, url)
            print("✅ 投稿完了:", url)
    finally:
        drv.quit()


if __name__ == "__main__":
    main()
