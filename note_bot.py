from playwright.sync_api import sync_playwright
import time
import json
import logging
import os
from dotenv import load_dotenv

# ログ設定
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# 環境変数
load_dotenv()
NOTE_USERNAME = os.getenv("NOTE_USERNAME")
NOTE_PASSWORD = os.getenv("NOTE_PASSWORD")

# スパムキーワード
SPAM_KEYWORDS = ["競艇", "ギャンブル", "賭博", "副業", "稼ぐ", "投資"]

def save_cookies(context, path="note_cookies.json"):
    """cookieを保存"""
    context.storage_state(path=path)
    logger.info("✅ cookie保存完了")

def load_cookies(browser, path="note_cookies.json"):
    """cookieを読み込み"""
    try:
        context = browser.new_context(storage_state=path)
        logger.info("✅ cookie読み込み成功")
        return context
    except Exception as e:
        logger.error(f"❌ cookie読み込み失敗: {e}")
        return None

def get_following_list(page):
    """フォロー中のユーザー一覧を取得"""
    try:
        page.goto("https://note.com/following")
        page.wait_for_load_state("networkidle")
        users = page.query_selector_all(".o-userListItem__link")
        return [user.get_attribute("href").replace("/", "") for user in users]
    except Exception as e:
        logger.error(f"❌ フォロー一覧取得失敗: {e}")
        return []

def get_followers_list(page):
    """フォロワーのユーザー一覧を取得"""
    try:
        page.goto("https://note.com/followers")
        page.wait_for_load_state("networkidle")
        users = page.query_selector_all(".o-userListItem__link")
        return [user.get_attribute("href").replace("/", "") for user in users]
    except Exception as e:
        logger.error(f"❌ フォロワー一覧取得失敗: {e}")
        return []

def note_auto_like_follow_back():
    """note Botメイン処理"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = load_cookies(browser)
        
        if context is None:
            logger.error("🔐 cookieが無いので処理終了（初回ログイン必要）")
            return
        
        page = context.new_page()
        
        # 通知チェック
        try:
            page.goto("https://note.com/notifications")
            page.wait_for_load_state("networkidle")
            notifications = page.query_selector_all(".o-notificationItem")
            actions_done = 0
            
            for note in notifications:
                if actions_done >= 10:
                    logger.info("⏩ 上限到達、処理終了")
                    break
                content = note.inner_text().lower()
                if any(kw.lower() in content for kw in SPAM_KEYWORDS):
                    logger.info(f"⏩ スパム通知スキップ: {content[:40]}")
                    continue
                if "フォロー" in content:
                    username = note.query_selector("a").get_attribute("href").replace("/", "")
                    page.goto(f"https://note.com/{username}")
                    if page.query_selector("button:has-text('フォロー中')"):
                        logger.info(f"⏩ フォロー済み: {username}")
                        continue
                    follow_btn = page.query_selector("button:has-text('フォロー')")
                    if follow_btn:
                        follow_btn.click()
                        logger.info(f"✅ フォロー返し: {username}")
                        actions_done += 1
                        time.sleep(2)
                elif "スキ" in content:
                    username = note.query_selector("a").get_attribute("href").replace("/", "")
                    page.goto(f"https://note.com/{username}")
                    like_btn = page.query_selector("button:has-text('スキ')")
                    if like_btn and not like_btn.get_attribute("disabled"):
                        like_btn.click()
                        logger.info(f"❤️ いいね返し: {username}")
                        actions_done += 1
                        time.sleep(2)
        
        except Exception as e:
            logger.error(f"❌ 通知処理エラー: {e}")
        
        # フォロー解除
        try:
            following = set(get_following_list(page))
            followers = set(get_followers_list(page))
            to_unfollow = following - followers
            for username in to_unfollow:
                if actions_done >= 10:
                    logger.info("⏩ 上限到達、解除処理終了")
                    break
                page.goto(f"https://note.com/{username}")
                unfollow_btn = page.query_selector("button:has-text('フォロー中')")
                if unfollow_btn:
                    unfollow_btn.click()
                    logger.info(f"🔕 フォロー解除: {username}")
                    actions_done += 1
                    time.sleep(2)
        except Exception as e:
            logger.error(f"❌ フォロー解除エラー: {e}")
        
        save_cookies(context)
        browser.close()

if __name__ == "__main__":
    note_auto_like_follow_back()