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
            page.goto("https://note.com/notes/new")
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            if "login" in page.url:
                print("⚠️【緊急】ログイン画面に飛ばされちゃいました！")
                return

# 🖼️ 見出し画像の自動アップロード（Shift+Tab ＆ JS直撃 ＆ 待ち伏せ保存作戦！）
# 🖼️ 見出し画像の自動アップロード（Shift+Tab ＆ JS直撃 ＆ 待ち伏せ保存作戦！）
# 🖼️ 見出し画像の自動アップロード（Shift+Tab ＆ JS直撃 ＆ 待ち伏せ保存作戦！）
            if os.path.exists("default_header.png"):
                print("🖼️ 見出し画像をセットするよ...")
                try:
                    # 1. タイトル入力欄が表示されるまで待つ
                    page.locator('textarea[placeholder="記事タイトル"]').wait_for(state="visible", timeout=10000)
                    time.sleep(1)
                    
                    print("👉 1. タイトル欄にフォーカスして、Shift+Tabで見出し画像ボタンを狙い撃ちするよ！")
                    page.locator('textarea[placeholder="記事タイトル"]').focus()
                    time.sleep(0.5)
                    
                    # 2. Shift+Tabで1つ前の要素（見出し画像ボタン）に戻ってEnter（クリック）！
                    page.keyboard.press("Shift+Tab")
                    time.sleep(0.5)
                    page.keyboard.press("Enter")
                    time.sleep(2) # メニューがふわっと出るのを待つ
                    
                    print("👉 2. メニューから「アップロード」を【JavaScript】で強制クリックするよ！")
                    try:
                        with page.expect_file_chooser(timeout=5000) as fc_info:
                            # Playwrightを使わず、JSで直接クリックさせてガタガタを100%防ぐ！
                            page.evaluate("""
                                () => {
                                    const xpath = "//*[contains(text(), '画像をアップロード') or contains(text(), 'ライブラリ')]";
                                    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                                    const element = result.singleNodeValue;
                                    if (element) {
                                        const clickable = element.closest('button, label, [role="button"]') || element;
                                        clickable.click();
                                    } else {
                                        throw new Error("アップロードボタンが見つかりませんでした");
                                    }
                                }
                            """)
                        
                        file_chooser = fc_info.value
                        file_chooser.set_files("default_header.png")
                        print("✅ 画像ファイルをセットしたよ！アップロード完了を待ちます...")
                    except Exception as e:
                        print(f"⚠️ JSクリックに失敗。直接 input[type=file] へのセットを試します！: {e}")
                        page.locator('input[type="file"]').first.set_input_files("default_header.png", timeout=3000)
                    
                    # 💡 【大改善】アップロードが終わって「保存」ボタンが出現するまで最大15秒待機する！
# 💡 【大改善】「下書き保存」を誤クリックしないよう、モーダルの中の「保存」をJSで狙い撃ち！
                    print("👉 3. トリミング画面の保存ボタンをJSで強制クリックするよ！")
                    try:
                        # 画像のアップロード完了を安全に5秒スリープして待つ
                        time.sleep(5)
                        
                        # 💡 JSでモーダル（ダイアログ）の中の「保存」を確実にクリックし、結果をPython側に返す！
                        click_result = page.evaluate("""
                            () => {
                                // 1. トリミング画面のモーダル要素自体を見つける
                                const modal = document.querySelector('[role="dialog"], [class*="modal" i], .o-modal, .m-modal, [class*="dialog" i]');
                                if (!modal) {
                                    return "❌ 【エラー】切り抜きモーダル自体が画面上に見つかりませんでした！";
                                }
                                
                                // 2. モーダルの中にあるすべての要素（button, div, spanなど）を取得
                                const elements = Array.from(modal.querySelectorAll('button, [role="button"], div, span'));
                                
                                // 3. テキストが完全に「保存」だけの要素を探す（「下書き保存」を完全スルー）
                                const saveBtn = elements.find(el => {
                                    // 子要素を持たない末端の要素で、中身が完全に「保存」のもの
                                    return el.children.length === 0 && el.textContent.trim() === '保存';
                                });
                                
                                if (saveBtn) {
                                    // クリック可能な親要素を遡る（buttonタグなどがあればそれ、無ければ自身）
                                    const clickable = saveBtn.closest('button, [role="button"]') || saveBtn;
                                    clickable.click();
                                    return `✅ モーダル内の「保存」をクリックしました！ (Tag: ${clickable.tagName})`;
                                } else {
                                    return "❌ 【エラー】モーダルの中に「保存」という文字のボタンが見つかりませんでした。";
                                }
                            }
                        """)
                        
                        # 🔍 JSが実際にどう動いたかをターミナルに表示！
                        print(f"🕵️‍♂️ JSの実行結果: {click_result}")
                        
                        # 💡 【超重要】モーダル画面自体が「完全に消える」まで待機！
                        print("⏳ トリミング画面が閉じるのを待っています...")
                        page.locator('[role="dialog"], [class*="modal" i], .o-modal, .m-modal').wait_for(state="hidden", timeout=10000)
                        
                        print("✅ 見出し画像の設定成功！！（完全勝利！）")
                    except Exception as e:
                        print(f"⚠️ 保存ボタンのクリックでエラー: {e}")
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"⚠️ 画像設定スキップ（作戦失敗。手強すぎるので諦めますw）: {e}")

            # タイトルの入力
            print("✍️ タイトル入力中...")
            page.locator('textarea[placeholder="記事タイトル"]').fill(title)

            # 本文エディタをクリック
            editor = page.locator('.ProseMirror')
            editor.click()
            time.sleep(1)

            # 📑 目次の挿入
            print("📑 目次を挿入するよ...")
            try:
                page.keyboard.type("/")
                time.sleep(1.5)
                page.locator('text="目次"').first.click(timeout=3000)
                time.sleep(1)
                page.keyboard.press("Enter")
                print("✅ 目次を挿入したよ！")
            except Exception as e:
                print(f"⚠️ 目次挿入スキップ: {e}")
                page.keyboard.press("Backspace")

            # 本文のタイピング（楽天アフィ用）
            print("✍️ 本文を1行ずつタイピングして流し込むよ...")
            for line in body.split("\n"):
                if line.strip() == "":
                    page.keyboard.press("Enter")
                else:
                    page.keyboard.type(line, delay=30)
                    page.keyboard.press("Enter")
                time.sleep(1) 

            time.sleep(5)

            # 保存または公開
            if publish_type == "公開":
                print("⚙️ 公開設定画面を開くよ...")
                page.get_by_role("button", name="公開に進む").click()
                time.sleep(3)

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
                print("📝 記事をそのまま「下書き」保存します！")
                page.get_by_text("下書き保存").first.click()
                final_status = "下書き済"

            time.sleep(5)

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
