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
        
        # 💻 GHAの仮想環境（Linux）でWebGLのロードエラーを防ぐためのGPUオフ設定を追加！
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        ) 
        
        try:
            context = browser.new_context(
                storage_state="state.json",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()

            print("🌐 noteの編集画面にアクセス中...")
            page.goto("https://editor.note.com/new") # editor.note.com に直通！
            time.sleep(5)

            # 🖼️ 見出し画像の自動アップロード（もしファイルがあれば）
            if os.path.exists("default_header.png"):
                print("🖼️ 見出し画像（default_header.png）をアップロード中...")
                try:
                    page.set_input_files('input[type="file"]', "default_header.png")
                    time.sleep(5)
                    save_btn = page.locator('button:has-text("保存"), button:has-text("適用")')
                    if save_btn.is_visible():
                        save_btn.click()
                        time.sleep(2)
                        print("✅ 見出し画像のアップロードに成功したよ！")
                except Exception as e:
                    print(f"⚠️ 画像のアップロードでエラー（スキップします）: {e}")

            # タイトルの入力
            print("✍️ タイトル入力中...")
            page.locator('textarea[placeholder="記事タイトル"]').fill(title)

            # 📋 ★【最強の改善】OSのクリップボードに依存しない「合成ペースト」を実行！
            # これでGHA上でも100%確実に本文が流し込まれ、お箸などのブログカードが展開されるよ！
            print("📋 本文を合成ペーストイベントで流し込むよ...")
            page.evaluate("""
                (text) => {
                    const editor = document.querySelector('.ProseMirror');
                    editor.focus();
                    const dataTransfer = new DataTransfer();
                    dataTransfer.setData('text/plain', text);
                    const event = new ClipboardEvent('paste', {
                        clipboardData: dataTransfer,
                        bubbles: true,
                        cancelable: true
                    });
                    editor.dispatchEvent(event);
                }
            """, body)
            time.sleep(5) # 楽天カードなどの自動展開をしっかり待つ

            # 投稿または下書き保存（★戻るボタンを一切使わない超シンプル設計！）
            if publish_type == "公開":
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

                print("🚀 記事を「公開」します！")
                page.get_by_role("button", name="公開する").click()
                final_status = "投稿済"
            else:
                # 💡 下書き保存のときは、公開設定を開かずにエディタ上のボタンをそのまま押すだけ！
                print("📝 記事をそのまま「下書き」保存します！")
                page.get_by_text("下書き保存").first.click()
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
