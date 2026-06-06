import os
import json
import time
import requests
import random
import urllib.parse
import traceback
from playwright.sync_api import sync_playwright

GAS_URL = os.environ.get(
    "GAS_URL", 
    "https://script.google.com/macros/s/AKfycbyy4b1p8shIW1EjYpNK658SZ9mk-vR8RC09C3fIxzsTKqkAHAg3S1pJiW8dEIi1DX9h/exec"
)

def generate_product_reply(keyword, app_id="1055088369869282145", affiliate_id="3d94ea21.0d257908.3d94ea22.0ed11c6e"):
    print(f"🛍️ グッズ提案ロジック開始: キーワード={keyword}")
    api_url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
    keywords = {
        "おすすめグッズ": "推し活 グッズ",
        "ぬい撮り": "ぬいぐるみ 背景布",
        "安眠": "安眠 グッズ",
        "推し活グッズ": "推し活 収納",
        "可愛いアイテム": "可愛い インテリア",
        "可愛いもの": "可愛い 雑貨"
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    params = {
        "applicationId": app_id,
        "keyword": keywords.get(keyword, keyword),
        "hits": 3,
        "format": "json"
    }
    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("Items"):
            items = data["Items"]
            item = random.choice(items)["Item"]
            product_url = item["itemUrl"].split("?")[0]
            affiliate_link = f"https://hb.afl.rakuten.co.jp/hgc/{affiliate_id}/?pc={urllib.parse.quote(product_url)}"
            return affiliate_link
        else:
            return None
    except Exception as e:
        return None

def replace_affiliate_placeholders(body_text):
    import re
    pattern = r"\[楽天アフィ:(.+?)\]"
    matches = re.findall(pattern, body_text)
    for match in matches:
        print(f"🔍 アフィ置換対象を発見: {match}")
        link = generate_product_reply(match)
        if link:
            body_text = body_text.replace(f"[楽天アフィ:{match}]", link)
            print(f"✨ リンクに置換成功: {link}")
        else:
            body_text = body_text.replace(f"[楽天アフィ:{match}]", "")
    return body_text

def main():
    print("📥 GASから記事を取得中...")
    response = requests.get(GAS_URL)
    article_data = response.json()

    if "error" in article_data:
        print(f"💤 {article_data['error']}")
        return

    row_num = article_data["row"]
    publish_type = article_data["publish_type"]
    title = article_data["title"]
    body = article_data["body"]
    raw_hashtags = article_data["hashtags"]

    print(f"📖 記事を発見！行番号: {row_num} | タイトル: {title}")

    hashtags = [t.strip() for t in raw_hashtags.replace("、", ",").split(",") if t.strip()]
    body = replace_affiliate_placeholders(body)

    with sync_playwright() as p:
        print("🚀 Playwright起動（Cookieを読み込みます）")
        browser = p.chromium.launch(headless=True) 
        
        try:
            context = browser.new_context(
                storage_state="state.json",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                # 📋 クリップボードの読み書き権限をブラウザに与える！
                permissions=["clipboard-write", "clipboard-read"]
            )
            page = context.new_page()

            print("🌐 noteの編集画面にアクセス中...")
            page.goto("https://note.com/notes/new")
            time.sleep(5)

            # タイトルの入力
            print("✍️ タイトル入力中...")
            page.locator('textarea[placeholder="記事タイトル"]').fill(title)

            # 本文エディタをクリック
            print("✍️ 本文をクリップボード経由で高速ペーストするよ...")
            editor = page.locator('.ProseMirror')
            editor.click()
            time.sleep(1)

            # page.evaluateを使って、仮想ブラウザのクリップボードに本文を書き込む
            page.evaluate("navigator.clipboard.writeText(arguments[0])", body)
            
            # ペースト（Control+V）を実行して、一瞬でnoteに流し込む！
            page.keyboard.press("Control+V")
            time.sleep(3) # コピペ展開とブログカード生成の待機

            # 公開設定画面へ
            print("⚙️ 公開設定画面を開くよ...")
            page.get_by_role("button", name="公開に進む").click()
            time.sleep(3)

            # ハッシュタグの設定
            print("🏷️ ハッシュタグを設定中...")
            hashtag_input = page.get_by_placeholder("ハッシュタグを追加")
            for tag in hashtags:
                hashtag_input.type(tag, delay=100)
                page.keyboard.press("Enter")
                time.sleep(0.5)

            # 投稿または下書き保存
            if publish_type == "公開":
                print("🚀 記事を「公開」します！")
                page.get_by_role("button", name="投稿する").click()
                final_status = "投稿済"
            else:
                print("🔙 下書き保存のために、一度公開設定パネルを閉じる（戻る）よ...")
                
                # 複数の候補から「閉じる/戻る/キャンセル」ボタンを探して確実にクリックする
                close_selectors = [
                    'button[aria-label="戻る"]',
                    'button[aria-label="閉じる"]',
                    'button:has-text("キャンセル")',
                    '.o-publishingSettings__close',
                    'button[class*="close"]'
                ]
                
                closed = False
                for selector in close_selectors:
                    try:
                        btn = page.locator(selector).first
                        # 今回は visibility の判定を待ってからクリック！
                        if btn.is_visible():
                            btn.click()
                            print(f"✅ パネルを閉じました ({selector})")
                            closed = True
                            break
                    except:
                        pass
                
                if not closed:
                    print("⚠️ ボタンが見つからなかったので、Escapeキーとエディタのクリックを試すよ...")
                    page.keyboard.press("Escape")
                    time.sleep(1)
                    try:
                        # エディタ部分をクリックしてフォーカスを外し、パネルを閉じるのを狙う
                        page.locator('.ProseMirror').click()
                    except:
                        pass

                time.sleep(2)

                print("📝 記事を「下書き」保存します！")
                # エディタ画面上部の「下書き保存」ボタンをクリック
                page.locator('button:has-text("下書き保存"), [aria-label*="下書き保存"]').first.click()
                final_status = "下書き済"

            time.sleep(5)

            # 3. GASにステータス更新を通知
            print(f"📤 GASのステータスを「{final_status}」に更新中...")
            update_res = requests.post(GAS_URL, json={"row": row_num, "status": final_status})
            print(f"✅ GAS更新結果: {update_res.text}")

        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            traceback.print_exc()
        finally:
            browser.close()

if __name__ == "__main__":
    main()
