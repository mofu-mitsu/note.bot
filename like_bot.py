import os
import json
import time
import random
import urllib.parse
from playwright.sync_api import sync_playwright

# 💡 みりんてゃのIDを設定
NOTE_ID = "mirin_chuuu"

# みりんてゃが気まぐれに見に行くハッシュタグのリスト！
HASHTAGS = ["地雷系", "自己紹介", "bot", "個人開発","ぬい撮り", "可愛い", "個人サイト", "ネット考古学", "AI"]

def main():
    with sync_playwright() as p:
        print("💕 いいね（スキ）パトロールBot起動！")
        
        # 💻 GitHub Actions等の環境に合わせてUser-Agentを人間っぽく偽装する（Bot弾き対策）
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state="state.json", 
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        target_note_urls = []

        # -----------------------------------------------------------------
        # 1. 💌 スキ返し！（🔔ベルマークから通知を開いて読み取る！）
        # -----------------------------------------------------------------
        print("📥 お知らせ（ベルマーク）を開いて、スキしてくれた人を探します...")
        try:
            page.goto("https://note.com/")
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)
            
            # 💡 【魔法1】ベルマークが表示されるまで、最大10秒間じっと待つ！
            bell_selector = 'a[href="/notifications"], button[aria-label*="お知らせ"], button[aria-label*="通知"], .o-headerNotification__icon'
            
            try:
                page.wait_for_selector(bell_selector, state="visible", timeout=10000)
                bell_btn = page.locator(bell_selector).first
                bell_btn.click()
                time.sleep(4) # お知らせ画面が描画されるのを待つ
                
                js_code = """
                    () => {
                        const urlnames = [];
                        const popover = Array.from(document.querySelectorAll('div, ul, [role="dialog"], section')).find(el => {
                            const text = el.textContent || '';
                            return text.includes('最新の通知は以上です') && el.innerHTML.length < 15000;
                        });
                        
                        if (!popover) return urlnames;
                        
                        const items = Array.from(popover.querySelectorAll('li, div'));
                        for (const item of items) {
                            const text = item.textContent || '';
                            if (text.includes('スキしました') || text.includes('スキをしました')) {
                                const links = Array.from(item.querySelectorAll('a'));
                                for (const link of links) {
                                    let path = link.pathname;
                                    if (path.endsWith('/')) path = path.slice(0, -1);
                                    const parts = path.split('/');
                                    
                                    if (parts.length === 2) {
                                        const urlname = parts[1];
                                        if (urlname && urlname !== 'n' && urlname !== '__NOTE_ID__' && !urlname.includes('intent') && urlname !== 'notifications') {
                                            if (!urlnames.includes(urlname)) {
                                                urlnames.push(urlname);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        return urlnames;
                    }
                """.replace("__NOTE_ID__", NOTE_ID)

                liker_urlnames = page.evaluate(js_code)
                print(f"👀 通知から、最近スキしてくれた {len(liker_urlnames)} 人を見つけました！")
                
                for urlname in liker_urlnames[:3]:
                    page.goto(f"https://note.com/{urlname}")
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)
                    try:
                        user_notes = page.evaluate("""
                            (myId) => {
                                const urls = [];
                                const links = document.querySelectorAll('a[href*="/n/"]');
                                for (const link of links) {
                                    if (!link.href.includes('/' + myId + '/') && !urls.includes(link.href)) urls.push(link.href);
                                }
                                return urls;
                            }
                        """, NOTE_ID)
                        if user_notes:
                            target_note_urls.append(user_notes[0])
                    except Exception as e:
                        pass
            except Exception as e:
                print("⚠️ ベルマークが見つからなかったよ！もしかして state.json のログイン期限が切れてるかも？🤔")

        except Exception as e:
            print(f"⚠️ 通知の取得に失敗しました: {e}")

        # -----------------------------------------------------------------
        # 2. 🏠 タイムライン巡回！
        # -----------------------------------------------------------------
        print("\n📥 ホーム画面（タイムライン）から、フォロワーさんの最新記事を探します...")
        try:
            page.goto("https://note.com/")
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            
            timeline_urls = page.evaluate("""
                (myId) => {
                    const urls = [];
                    const links = document.querySelectorAll('a[href*="/n/"]');
                    for (const link of links) {
                        const href = link.href;
                        if (href.includes("note.com") && !href.includes('/' + myId + '/') && !urls.includes(href)) urls.push(href);
                    }
                    return urls;
                }
            """, NOTE_ID)
            print(f"👀 ホーム画面から {len(timeline_urls)} 件の記事を見つけたよ！")
            for url in timeline_urls[:3]:
                target_note_urls.append(url)
        except Exception as e:
            print(f"⚠️ ホーム画面の取得に失敗しました: {e}")

        # -----------------------------------------------------------------
        # 3. 🦋 気まぐれハッシュタグ巡回！
        # -----------------------------------------------------------------
        selected_tag = random.choice(HASHTAGS)
        print(f"\n🦋 今日の気まぐれ巡回ハッシュタグは「#{selected_tag}」に決定！")
        try:
            encoded_tag = urllib.parse.quote(selected_tag)
            page.goto(f"https://note.com/hashtag/{encoded_tag}")
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            
            tag_note_urls = page.evaluate("""
                (myId) => {
                    const urls = [];
                    const links = document.querySelectorAll('a[href*="/n/"]');
                    for (const link of links) {
                        const href = link.href;
                        if (href.includes("note.com") && !href.includes('/' + myId + '/') && !urls.includes(href)) urls.push(href);
                    }
                    return urls;
                }
            """, NOTE_ID)
            print(f"📖 ハッシュタグ画面から {len(tag_note_urls)} 件の記事を見つけたよ！")
            for url in tag_note_urls[:3]:
                target_note_urls.append(url)
        except Exception as e:
            print(f"⚠️ ハッシュタグ検索に失敗しました: {e}")

        target_note_urls = list(set(target_note_urls))
        print(f"\n🎯 今回スキしにいく記事は全部で {len(target_note_urls)} 件だよ！")

        # -----------------------------------------------------------------
        # 4. 💖 ターゲットの記事に突撃してスキボタンを押す！
        # -----------------------------------------------------------------
        for url in target_note_urls:
            print(f"\n🏃‍♀️ 記事に訪問します: {url}")
            try:
                page.goto(url)
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                
                # 下までスクロールしてボタンを確実に画面内に描画させる
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(1)
                
                # 💡 【魔法2】JS側では「クリックすべきボタンの番号」を探すだけにする！
                result_data = page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        
                        const likeBtnIndex = buttons.findIndex(b => {
                            const className = b.className || '';
                            const label = b.getAttribute('aria-label') || '';
                            return className.includes('Like') || className.includes('like') || label.includes('スキ');
                        });
                        
                        if (likeBtnIndex !== -1) {
                            const likeBtn = buttons[likeBtnIndex];
                            const isPressed = likeBtn.getAttribute('aria-pressed') === 'true';
                            const isCancelLabel = (likeBtn.getAttribute('aria-label') || '').includes('取り消す');
                            
                            if (isPressed || isCancelLabel) {
                                return { status: "already_liked" };
                            }
                            return { status: "found", index: likeBtnIndex };
                        }
                        return { status: "not_found" };
                    }
                """)
                
                status = result_data.get("status")
                
                if status == "found":
                    btn_index = result_data.get("index")
                    
                    # 💡 【魔法3】Python側から「本物のクリック」を発動！
                    # 画面内にボタンをスクロールさせてからクリックするよ！
                    page.evaluate(f"document.querySelectorAll('button')[{btn_index}].scrollIntoView({{behavior: 'smooth', block: 'center'}})")
                    time.sleep(1)
                    
                    # Playwrightの物理クリック（これでReactにも完全に通信が飛ぶ！）
                    page.locator('button').nth(btn_index).click()
                    
                    # 💡 サーバーに通信が飛ぶのを待つために3秒待機！
                    time.sleep(3)
                    print("✅ スキ♡ しました！")
                    
                elif status == "already_liked":
                    print("👍 すでにスキ♡ 済みでした！")
                else:
                    print(f"⚠️ スキボタンが見つかりませんでした…")
                    
            except Exception as e:
                print(f"⚠️ 記事の訪問中にエラー: {e}")

        print("\n🎉 今日のいいね（スキ）パトロール完了！！")
        browser.close()

if __name__ == "__main__":
    main()
