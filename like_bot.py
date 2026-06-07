import os
import json
import time
import random
import urllib.parse
from playwright.sync_api import sync_playwright

# 💡 みりんてゃのIDを設定
NOTE_ID = "mirin_chuuu"

# みりんてゃが気まぐれに見に行くハッシュタグのリスト！
HASHTAGS = ["地雷系", "ぬい撮り", "可愛い", "個人サイト", "ネット考古学", "AI"]

def main():
    with sync_playwright() as p:
        print("💕 いいね（スキ）パトロールBot起動！")
        
        # 💻 ローカルテスト時はheadless=False、GitHub Actions時はTrue！
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state="state.json", viewport={"width": 1280, "height": 800})
        page = context.new_page()

        target_note_urls = []

        # -----------------------------------------------------------------
        # 1. 💌 スキ返し！（🔔ベルマークから通知を開いて読み取る！）
        # -----------------------------------------------------------------
        print("📥 お知らせ（ベルマーク）を開いて、スキしてくれた人を探します...")
        try:
            page.goto("https://note.com/")
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            
            # 🔔 note of ヘッダーにある本物の通知マークをクリック！
            bell_btn = page.locator('a[href="/notifications"], button[aria-label*="お知らせ"], button[aria-label*="通知"], .o-headerNotification__icon').first
            if bell_btn.is_visible():
                bell_btn.click()
                time.sleep(4) # お知らせ画面がしっかり描画されるのを待つ
                
                # 💡 f-stringを使わず安全に置換！
                js_code = """
                    () => {
                        const urlnames = [];
                        
                        // 1. 画面の中から「最新の通知は以上です」というテキストが含まれる「お知らせの箱」を特定！
                        const popover = Array.from(document.querySelectorAll('div, ul, [role="dialog"], section')).find(el => {
                            const text = el.textContent || '';
                            return text.includes('最新の通知は以上です') && el.innerHTML.length < 15000;
                        });
                        
                        if (!popover) {
                            return urlnames;
                        }
                        
                        // 2. そのポップアップの箱の「内側だけ」から、スキしてくれた人のIDをスナイプ！
                        const items = Array.from(popover.querySelectorAll('li, div'));
                        for (const item of items) {
                            const text = item.textContent || '';
                            if (text.includes('スキしました') || text.includes('スキをしました')) {
                                const links = Array.from(item.querySelectorAll('a'));
                                for (const link of links) {
                                    let path = link.pathname;
                                    if (path.endsWith('/')) {
                                        path = path.slice(0, -1);
                                    }
                                    const parts = path.split('/');
                                    
                                    // /sorake のようなプロフリンク（長さ2）だけを抽出！
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
                
                # その人たちのプロフィール画面に行って、最新記事を1件取得
                for urlname in liker_urlnames[:3]: # 最大3人にスキ返し
                    page.goto(f"https://note.com/{urlname}")
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)
                    try:
                        # 自分の記事を除外するフィルタをJS側に追加！
                        user_notes = page.evaluate("""
                            (myId) => {
                                const urls = [];
                                const links = document.querySelectorAll('a[href*="/n/"]');
                                for (const link of links) {
                                    if (!link.href.includes('/' + myId + '/') && !urls.includes(link.href)) {
                                        urls.push(link.href);
                                    }
                                }
                                return urls;
                            }
                        """, NOTE_ID)
                        if user_notes:
                            target_note_urls.append(user_notes[0]) # 最新記事
                    except Exception as e:
                        print(f"⚠️ {urlname} さんの記事取得をスキップしました: {e}")
            else:
                print("⚠️ ベルマーク（お知らせボタン）が見つからなかったよ！")
        except Exception as e:
            print(f"⚠️ 通知の取得に失敗しました: {e}")

        # -----------------------------------------------------------------
        # 2. 🏠 タイムライン巡回！（ホーム画面からフォロワーさんの最新記事を特定）
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
                        if (href.includes("note.com") && !href.includes('/' + myId + '/') && !urls.includes(href)) {
                            urls.push(href);
                        }
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
        # 3. 🦋 気まぐれハッシュタグ巡回！（物理画面から取得）
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
                        if (href.includes("note.com") && !href.includes('/' + myId + '/') && !urls.includes(href)) {
                            urls.push(href);
                        }
                    }
                    return urls;
                }
            """, NOTE_ID)
            print(f"📖 ハッシュタグ画面から {len(tag_note_urls)} 件の記事を見つけたよ！")
            for url in tag_note_urls[:3]:
                target_note_urls.append(url)
        except Exception as e:
            print(f"⚠️ ハッシュタグ検索に失敗しました: {e}")

        # 重複を削除
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
                
                # 💡 【JSエラーを100%修正！】
                # 内部の「#」コメントを完全に削除して、文法エラーを解決しました！
                result_data = page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        
                        const debugList = buttons.map(b => ({
                            tag: b.tagName,
                            className: b.className,
                            label: b.getAttribute('aria-label'),
                            pressed: b.getAttribute('aria-pressed')
                        })).filter(b => (b.className || '').includes('Like') || (b.className || '').includes('like') || (b.label || '').includes('スキ'));
                        
                        const likeBtn = buttons.find(b => {
                            const className = b.className || '';
                            const label = b.getAttribute('aria-label') || '';
                            return className.includes('Like') || className.includes('like') || label.includes('スキ');
                        });
                        
                        if (likeBtn) {
                            const isPressed = likeBtn.getAttribute('aria-pressed') === 'true';
                            const isCancelLabel = (likeBtn.getAttribute('aria-label') || '').includes('取り消す');
                            
                            if (isPressed || isCancelLabel) {
                                return { status: "already_liked", debug: debugList };
                            }
                            
                            likeBtn.click();
                            return { status: "clicked", debug: debugList };
                        }
                        return { status: "not_found", debug: debugList };
                    }
                """)
                
                status = result_data.get("status")
                debug_list = result_data.get("debug", [])
                
                if status == "clicked":
                    print("✅ スキ♡ しました！")
                elif status == "already_liked":
                    print("👍 すでにスキ♡ 済みでした！")
                else:
                    print(f"⚠️ スキボタンが見つかりませんでした… (検出したボタン候補: {debug_list})")
                    
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️ 記事の訪問中にエラー: {e}")

        print("\n🎉 今日のいいね（スキ）パトロール完了！！")
        browser.close()

if __name__ == "__main__":
    main()
