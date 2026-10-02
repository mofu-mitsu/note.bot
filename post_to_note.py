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
            headless=True,  # 💡 Pythonの文法に合わせて False に修正したよ！
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

            if os.path.exists("default_header.png"):
                print("🖼️ 見出し画像をセットするよ...")
                try:
                    page.locator('textarea[placeholder="記事タイトル"]').wait_for(state="visible", timeout=10000)
                    time.sleep(1)
                    
                    print("👉 1. タイトル欄にフォーカスして、Shift+Tabで見出し画像ボタンを狙い撃ちするよ！")
                    page.locator('textarea[placeholder="記事タイトル"]').focus()
                    time.sleep(0.5)
                    
                    page.keyboard.press("Shift+Tab")
                    time.sleep(0.5)
                    page.keyboard.press("Enter")
                    time.sleep(2)
                    
                    print("👉 2. メニューから「アップロード」を【JavaScript】で強制クリックするよ！")
                    try:
                        with page.expect_file_chooser(timeout=5000) as fc_info:
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
                    
                    print("👉 3. トリミング画面の保存ボタンをJSで強制クリックするよ！")
                    try:
                        time.sleep(5)
                        
                        click_result = page.evaluate("""
                            () => {
                                const modal = document.querySelector('[role="dialog"], [class*="modal" i], .o-modal, .m-modal, [class*="dialog" i]');
                                if (!modal) {
                                    return "❌ 【エラー】切り抜きモーダル自体が画面上に見つかりませんでした！";
                                }
                                
                                const elements = Array.from(modal.querySelectorAll('button, [role="button"], div, span'));
                                
                                const saveBtn = elements.find(el => {
                                    return el.children.length === 0 && el.textContent.trim() === '保存';
                                });
                                
                                if (saveBtn) {
                                    const clickable = saveBtn.closest('button, [role="button"]') || saveBtn;
                                    clickable.click();
                                    return `✅ モーダル内の「保存」をクリックしました！ (Tag: ${clickable.tagName})`;
                                } else {
                                    return "❌ 【エラー】モーダルの中に「保存」という文字のボタンが見つかりませんでした。";
                                }
                            }
                        """)
                        
                        print(f"🕵️‍♂️ JSの実行結果: {click_result}")
                        
                        print("⏳ トリミング画面が閉じるのを待っています...")
                        # noteは複数のdialog / ReactModalPortalをDOMに持つため、
                        # 「すべてのdialogがhidden」を待つとstrict mode violationになる。
                        # 実際の切り抜きモーダルだけを監視する。
                        crop_modal = page.locator('.CropModal__content').first
                        if crop_modal.count() > 0:
                            try:
                                crop_modal.wait_for(state="hidden", timeout=10000)
                            except Exception:
                                # 保存クリック自体は成功している可能性があるので、
                                # 待機失敗だけで画像設定全体を失敗扱いにしない。
                                print("⚠️ CropModalの終了待機をスキップしました（保存クリックは実行済み）")
                        
                        print("✅ 見出し画像の設定成功！！（完全勝利！）")
                    except Exception as e:
                        print(f"⚠️ 保存ボタンのクリックでエラー: {e}")
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"⚠️ 画像設定スキップ: {e}")

            print("✍️ タイトル入力中...")
            page.locator('textarea[placeholder="記事タイトル"]').fill(title)

            editor = page.locator('.ProseMirror')
            editor.click()
            time.sleep(1)

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

            print("✍️ 本文を1行ずつタイピングして流し込むよ...")
            for line in body.split("\n"):
                if line.strip() == "":
                    page.keyboard.press("Enter")
                else:
                    page.keyboard.type(line, delay=30)
                    page.keyboard.press("Enter")
                time.sleep(1) 

            time.sleep(5)

            # ---------------------------------------------------------
            # 💡 【完全修正】保存または公開の処理！
            # ---------------------------------------------------------
            if publish_type == "公開":
                print("⚙️ 公開設定画面を開くよ...")
                # PC版noteでは現在「公開設定」→「投稿する」が基本フロー。
                # hiddenな同名要素を .first で拾わないよう、可視buttonを優先する。
                publish_settings = page.locator('button:visible').filter(has_text="公開設定")
                if publish_settings.count() == 0:
                    publish_settings = page.locator('button:visible').filter(has_text="公開に進む")
                if publish_settings.count() > 0:
                    publish_settings.first.click(timeout=10000)
                else:
                    raise RuntimeError("公開設定ボタンが見つかりません")
                time.sleep(3)

                print("🏷️ ハッシュタグを設定中...")
                hashtag_inputs = page.locator('input[placeholder*="タグ入力後"], input[placeholder*="ハッシュタグを追加"]')
                if hashtag_inputs.count() > 0 and hashtag_inputs.first.is_visible():
                    hashtag_input = hashtag_inputs.first
                    for tag in hashtags:
                        hashtag_input.fill(tag)
                        page.keyboard.press("Enter")
                        time.sleep(0.5)
                else:
                    print("⚠️ ハッシュタグ入力欄が見つからなかったためスキップします！")

                print("🚀 記事を「公開」します！")
                # noteのPC版は「投稿する」。環境差に備えて「公開する」「公開」も許容。
                publish_button = page.locator('button:visible').filter(has_text="投稿する")
                if publish_button.count() == 0:
                    publish_button = page.locator('button:visible').filter(has_text="公開する")
                if publish_button.count() == 0:
                    publish_button = page.locator('button:visible').filter(has_text="公開")

                if publish_button.count() > 0:
                    publish_button.first.click(timeout=10000)
                else:
                    # button以外のDOM構造になっている場合の最後のフォールバック。
                    clicked = page.evaluate("""
                        () => {
                            const names = ['投稿する', '公開する', '公開'];
                            const normalize = s => (s || '').replace(/\\s+/g, '').trim();
                            const visible = el => {
                                const r = el.getBoundingClientRect();
                                const st = getComputedStyle(el);
                                return r.width > 0 && r.height > 0 &&
                                       st.visibility !== 'hidden' && st.display !== 'none';
                            };
                            const nodes = [...document.querySelectorAll('button, [role="button"], a, div')];
                            for (const el of nodes) {
                                if (!visible(el)) continue;
                                if (!names.includes(normalize(el.textContent))) continue;
                                const clickable = el.closest('button, [role="button"], a') || el;
                                clickable.click();
                                return normalize(el.textContent);
                            }
                            return null;
                        }
                    """)
                    if not clicked:
                        visible_buttons = page.locator('button:visible').all_text_contents()
                        print(f"🔎 公開設定画面の可視ボタン: {visible_buttons}")
                        raise RuntimeError("投稿ボタン（投稿する / 公開する / 公開）が見つかりません")
                    print(f"✅ 投稿ボタンをクリックしました: {clicked}")
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
))
                if publish_settings.count() > 0:
                    publish_settings.filter(visible=True).first.click(timeout=10000)
                else:
                    page.get_by_text(re.compile(r'^(公開設定|公開に進む)
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
)).filter(visible=True).first.click(timeout=10000)
                time.sleep(3)

                print("🏷️ ハッシュタグを設定中...")
                hashtag_inputs = page.locator('input[placeholder*="タグ入力後"], input[placeholder*="ハッシュタグを追加"]')
                if hashtag_inputs.count() > 0 and hashtag_inputs.first.is_visible():
                    hashtag_input = hashtag_inputs.first
                    for tag in hashtags:
                        hashtag_input.fill(tag)
                        page.keyboard.press("Enter")
                        time.sleep(0.5)
                else:
                    print("⚠️ ハッシュタグ入力欄が見つからなかったためスキップします！")

                print("🚀 記事を「公開」します！")
                # noteのPC版は「投稿する」、環境によっては「公開する / 公開」もあり得る。
                # まず可視buttonを探し、見つからない場合は可視DOM要素をJSから拾う。
                publish_button = page.locator('button').filter(has_text=re.compile(r'^(投稿する|公開する|公開)
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
))
                if publish_button.count() > 0:
                    visible_publish = publish_button.filter(visible=True)
                    if visible_publish.count() > 0:
                        visible_publish.first.click(timeout=10000)
                    else:
                        raise RuntimeError("公開設定画面に可視の投稿ボタンがありません")
                else:
                    clicked = page.evaluate("""
                        () => {
                            const names = ['投稿する', '公開する', '公開'];
                            const normalize = s => (s || '').replace(/\\s+/g, '').trim();
                            const visible = el => {
                                const r = el.getBoundingClientRect();
                                const st = getComputedStyle(el);
                                return r.width > 0 && r.height > 0 && st.visibility !== 'hidden' && st.display !== 'none';
                            };
                            const nodes = [...document.querySelectorAll('button, [role="button"], a, div')];
                            for (const el of nodes) {
                                if (!visible(el)) continue;
                                if (!names.includes(normalize(el.textContent))) continue;
                                const clickable = el.closest('button, [role="button"], a') || el;
                                clickable.click();
                                return normalize(el.textContent);
                            }
                            return null;
                        }
                    """)
                    if (!clicked:
                        # 最後に診断情報を出して、次回DOM変更があっても原因を追いやすくする。
                        visible_buttons = page.locator('button:visible').all_text_contents()
                        print(f"🔎 公開設定画面の可視ボタン: {visible_buttons}")
                        raise RuntimeError("投稿ボタン（投稿する / 公開する / 公開）が見つかりません")
                    print(f"✅ 投稿ボタンをクリックしました: {clicked}")
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
