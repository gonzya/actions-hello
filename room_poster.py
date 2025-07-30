"""
room_poster.py – 楽天ROOM 自動投稿（すべて Selenium 経由）
2025-07-27 版 / Python 3.11+
依存: selenium>=4.21 webdriver-manager python-dotenv schedule
"""

import os, time, random, argparse, schedule
import sys
from datetime import datetime
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

########################## ① 事前設定 ##########################
load_dotenv()
RID, RPW = os.getenv("RAKUTEN_ID"), os.getenv("RAKUTEN_PW")
PROFILE_DIR = r"C:\room_auto\selenium-profile"

TEMPL = [
    "【SALE】{name} が{off}%OFF！私も愛用✨",
    "＼タイムセール／ {name} {off}%OFF！家事が時短に⏱️",
    "{name} が{off}%OFF！プチ贅沢にどうぞ🎁",
]

########################## ② ドライバ ##########################
def get_driver(headless: bool = True):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    # ★ DNS を OS だけに固定（重要）
    opts.add_argument("--disable-features=AsyncDNS,DnsOverHttps,IntranetRedirectDetector")
    opts.add_argument("--dns-prefetch-disable")
    # ─────お好みフラグ─────
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--remote-debugging-port=0")

    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opts)
########################## ③ ログイン（手動1回方式・URL 判定） ##########################

LOGIN_PAGE = "https://room.rakuten.co.jp/login"

def login(drv, wait_sec: int = 30):
    """Cookie が無ければブラウザを開き、手動でログインしてもらう"""
    # すでにマイルーム URL ならログイン済みとみなす
    if "room.rakuten.co.jp" in drv.current_url and "/login" not in drv.current_url:
        return

    print(f"🔑 まだ Cookie が無いので {wait_sec} 秒以内に手動ログインしてください…")
    drv.get(LOGIN_PAGE)

    for i in range(wait_sec, 0, -1):
        sys.stdout.write(f"\r残り {i:2d} 秒でログイン… ")
        sys.stdout.flush()
        time.sleep(1)
        # URL が /login を抜けていればログイン成功
        if "room.rakuten.co.jp" in drv.current_url and "/login" not in drv.current_url:
            print("\n✅ ログイン検出、処理を再開します")
            return
    raise RuntimeError("ログインが完了しませんでした。ID/パスワードを入力しましたか？")

########################## ④ ランキング取得 ##########################
from selenium.webdriver.support.ui  import WebDriverWait
from selenium.webdriver.support      import expected_conditions as EC
from selenium.common.exceptions      import TimeoutException

def pick_product(drv) -> dict:
    drv.get("https://ranking.rakuten.co.jp/daily/")
    wait = WebDriverWait(drv, 30)          # ← 最大 30 秒に延長

    # JS がアイテムを描画するまで 0.5 秒間隔でスクロールして待つ
    end = time.time() + 30
    while time.time() < end:
        try:
            a = drv.find_element(By.CSS_SELECTOR, "a[href*='item.rakuten.co.jp']")
            if a.is_displayed():
                break                      # 見える位置に来た
        except Exception:
            pass
        drv.execute_script("window.scrollBy(0, 800);")
        time.sleep(0.5)
    else:
        raise TimeoutException("ランキング商品が見つかりません")

    url  = a.get_attribute("href")
    name = a.text or "楽天人気商品"
    return {"url": url, "name": name, "off": random.choice([10, 15, 20, 25])}

########################## ⑤ 投稿作成 ##########################
def create_post(drv, prod):
    """商品ページを直接開き、ROOM 投稿ボタンを押すだけ"""
    drv.get(prod["url"])

    BTN_SEL = "button[data-rat='button-add-to-room']"   # ← DevTools で確認可
    WebDriverWait(drv, 15).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, BTN_SEL))
    )
    drv.find_element(By.CSS_SELECTOR, BTN_SEL).click()

    # ★キャプションはあとで編集したいなら別関数で対応
    time.sleep(3)  # 投稿 API 反映待ち
########################## ⑥ 1 回実行 ##########################
def one_shot(headless=True):
    d = get_driver(headless)
    try:
        login(d)                     # まず確実にログイン
        prod = pick_product(d)
        create_post(d, prod)
        print(f"[{datetime.now():%F %T}] 投稿完了: {prod['name']}")
    finally:
        input("👀 画面を確認したら Enter を押してください…")   # ←★追加ここ
        d.quit()

########################## ⑦ 定期実行 ##########################
def daily():
    POSTS = ["09:05", "15:00", "22:30"]
    for t in POSTS:
        schedule.every().day.at(t).do(one_shot)
    print("自動投稿スケジュール稼働中…", POSTS)
    while True:
        schedule.run_pending()
        time.sleep(30)

########################## ⑧ CLI ##########################
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily", action="store_true", help="24h 常駐して毎日自動投稿")
    ap.add_argument("--no-headless", action="store_true", help="ブラウザを表示して実行")
    args = ap.parse_args()

    if args.daily:
        one_shot(headless=not args.no_headless)  # 初回投稿
        daily()
    else:
        one_shot(headless=not args.no_headless)
