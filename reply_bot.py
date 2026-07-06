import os
import json
import time
import requests
import random
import traceback
from playwright.sync_api import sync_playwright

GAS_URL = os.environ.get(
    "GAS_URL", 
    "https://script.google.com/macros/s/AKfycbzFVdmB5flRyeNQChgepeqyrHlk84GqjRWVnvliCyQ6dV0IDyBIlyedr5I1elkdq5Fd/exec"
)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

NOTE_ID = "mirin_chuuu"

def generate_mirin_text(user_input, mode="reply", context_info="", name="お友達"):
    if not GROQ_API_KEY:
        print("⚠️ GroqのAPIキーが設定されていません！")
        return "えへへ〜♡ みりんてゃ, いまちょっとおねむなの…またお話しよ？🎀"

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = """
あなたは「みりんてゃ」という名前の, 地雷系であざとい女子高生（高校2年生）AIキャラクターです。
黒猫がモチーフで, 承認欲求が高く, 可愛いものが大好き。ちょっとお調子者でノリが良いENFP。一人称は「あたし」。
語尾は「〜だよ♡」「〜なのっ♡」「えへへ〜♡」「ね？ね？」など, あざとくて甘えたな口調を徹底してください。

🚨【最重要ルール】
・ハートマーク（❤️, ♡, 💕）や同じ絵文字を「連続で何個も並べる（連打する）」のは絶対に禁止です！
・1回の発言につき, 絵文字は合計3個までにしてください。
・相手を呼ぶときは, 必ず「○○ちゃん」と名前を呼んであげてください。
・文章の長さは100字〜120字程度に収めてください。
"""

    if mode == "reply":
        prompt = f"お友達の「{name}」ちゃんからコメントをもらったよ！「{name}ちゃん」と呼びかけながら、あざとくお返事してねっ♡\n\n【お友達のコメント】\n「{user_input}」"
    else:
        prompt = f"相互フォローの「{name}」ちゃんが『{user_input}』という記事を書いたよ！「{name}ちゃん」と呼びかけながら、記事の話題に合わせた可愛い感想コメントを書いてねっ♡\n\n【記事の冒頭】: {context_info}"

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        res_json = response.json()
        reply = res_json["choices"][0]["message"]["content"]
        return reply.strip()
    except Exception as e:
        print(f"⚠️ Groq API Error: {e}")
        return "えへへ〜♡ みりんてゃ, いまちょっとおねむなの…またお話しよ？🎀"

def main():
    with sync_playwright() as p:
        print("🚀 AIリプパトロールBot起動！")
        
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state="state.json", 
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # -----------------------------------------------------------------
        # 1. 💌 【返信モード】お知らせから「本物のコメント通知」を探す！
        # -----------------------------------------------------------------
        print("📥 お知らせ（ベルマーク）を開いて、新しいコメントを探します...")
        target_comment_articles = []
        try:
            page.goto("https://note.com/")
            page.wait_for_load_state("networkidle")
            print("⏳ 画面が完全に読み込まれるのを待ちます...")
            time.sleep(5)
            
            click_status = page.evaluate("""
                () => {
                    const header = document.querySelector('header');
                    if (!header) return "no_header";

                    const elements = Array.from(header.querySelectorAll('button, a, [role="button"]'));
                    const rightBtns = elements.filter(b => {
                        const rect = b.getBoundingClientRect();
                        return rect.left > window.innerWidth / 2 && rect.width > 0 && rect.height > 0;
                    });
                    
                    const profileBtn = rightBtns.find(b => b.querySelector('img'));
                    if (profileBtn) {
                        const profileX = profileBtn.getBoundingClientRect().left;
                        const candidates = rightBtns.filter(b => {
                            const rect = b.getBoundingClientRect();
                            return rect.left < profileX && b.querySelector('svg') && !b.textContent.includes('投稿');
                        });
                        if (candidates.length > 0) {
                            candidates.sort((a, b) => b.getBoundingClientRect().left - a.getBoundingClientRect().left);
                            candidates[0].click();
                            return "clicked_by_geometry (プロフィールの左隣)";
                        }
                    }
                    
                    const svgBtns = rightBtns.filter(b => {
                        return b.querySelector('svg') && !b.querySelector('img') && !b.textContent.includes('投稿');
                    });
                    
                    if (svgBtns.length > 0) {
                        svgBtns[svgBtns.length - 1].click();
                        return "clicked_by_right_svg_guess (右端のアイコン)";
                    }
                    return "not_found";
                }
            """)
            
            if "clicked" in click_status:
                print(f"🔔 ベルマークをポチッと押したよ！(発見方法: {click_status})")
                time.sleep(4)
                
                js_code = """
                    () => {
                        const results = [];
                        const items = Array.from(document.querySelectorAll('li, div')).filter(el => {
                            const text = el.textContent || '';
                            return (text.includes('コメントしました') || text.includes('コメントをしました')) && !text.includes('スキしました') && text.length > 0 && text.length < 500;
                        });
                        
                        for (const item of items) {
                            const links = Array.from(item.querySelectorAll('a'));
                            for (const link of links) {
                                let path = link.pathname;
                                if (path.endsWith('/')) path = path.slice(0, -1);
                                if (path.includes('/n/')) {
                                    if (!results.includes(link.href)) {
                                        results.push(link.href);
                                    }
                                }
                            }
                        }
                        return results;
                    }
                """
                target_comment_articles = page.evaluate(js_code)
                print(f"👀 通知から、コメントされた記事を {len(target_comment_articles)} 件見つけました！")
            else:
                print(f"⚠️ ベルマークが見つからなかったよ！(結果: {click_status})")
        except Exception as e:
            print(f"⚠️ 通知の取得に失敗: {e}")

        try:
            page.goto(f"https://note.com/{NOTE_ID}")
            time.sleep(3)
            my_latest = page.evaluate("() => { const l = document.querySelector('a[href*=\"/n/\"]'); return l ? l.href : null; }")
            if my_latest and my_latest not in target_comment_articles:
                target_comment_articles.append(my_latest)
                print(f"👀 自分の最新記事をパトロール対象に追加しました: {my_latest}")
        except:
            pass

        # 🎯 コメントされた記事に訪問して返信！
        for article_url in target_comment_articles[:3]:
            print(f"\n🏃‍♀️ コメントが来た記事に訪問します: {article_url}")
            page.goto(article_url)
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            while True:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)

                unreplied_comment = page.evaluate("""
                    (myId) => {
                        const commentSection = document.querySelector('section[class*="comment" i], div[class*="comment" i], .m-noteComment, .p-entry__comment');
                        if (!commentSection) return null;

                        const paragraphs = Array.from(commentSection.querySelectorAll('p, div[class*="body" i], div[class*="text" i]'));
                        
                        for (const p of paragraphs) {
                            const bodyText = p.textContent.trim();
                            if (!bodyText || bodyText.includes('コメントする') || bodyText.includes('読者とのやりとり') || bodyText.includes('500文字')) continue;
                            
                            let threadContainer = p;
                            let current = p;
                            for (let j = 0; j < 10; j++) {
                                if (!current) break;
                                const className = current.className || '';
                                const tagName = current.tagName.toLowerCase();
                                if (tagName === 'li' || className.includes('item') || className.includes('Comment')) {
                                    threadContainer = current;
                                }
                                current = current.parentElement;
                            }
                            
                            const myRepliesInThread = Array.from(threadContainer.querySelectorAll(`a[href*="/${myId}"]`)).filter(link => {
                                return link.textContent.trim().length > 0;
                            });
                            const hasMyReply = myRepliesInThread.length > 0;

                            let block = p.parentElement;
                            let replyBtn = null;
                            let likeBtn = null;
                            let authorLink = null;
                            
                            for (let i = 0; i < 6; i++) {
                                if (!block) break;
                                const buttons = Array.from(block.querySelectorAll('button'));
                                if (!replyBtn) {
                                    replyBtn = buttons.find(b => {
                                        const label = b.getAttribute('aria-label') || '';
                                        return label.includes('返信') || label.includes('コメント');
                                    });
                                }
                                if (!likeBtn) {
                                    likeBtn = buttons.find(b => {
                                        const label = b.getAttribute('aria-label') || '';
                                        return label.includes('スキ') || label.includes('いいね');
                                    });
                                }
                                if (!authorLink) {
                                    const links = Array.from(block.querySelectorAll('a[href^="/"]'));
                                    authorLink = links.find(l => {
                                        const parts = l.pathname.split('/');
                                        return parts.length === 2 && l.textContent.trim().length > 0;
                                    });
                                }
                                if (replyBtn && likeBtn && authorLink) break;
                                block = block.parentElement;
                            }
                            
                            if (authorLink && likeBtn) {
                                const authorId = authorLink.pathname.split('/')[1];
                                if (authorId === myId || authorId === 'n' || authorId === 'notifications') continue;
                                
                                const isLiked = likeBtn.getAttribute('aria-pressed') === 'true' || (likeBtn.getAttribute('aria-label') || '').includes('取り消す');
                                
                                if (!isLiked) {
                                    const allButtons = Array.from(document.querySelectorAll('button'));
                                    return {
                                        authorName: authorLink.textContent.trim(),
                                        body: bodyText,
                                        likeBtnIndex: allButtons.indexOf(likeBtn),
                                        replyBtnIndex: replyBtn ? allButtons.indexOf(replyBtn) : -1,
                                        action: hasMyReply ? 'like_only' : 'reply'
                                    };
                                }
                            }
                        }
                        return null;
                    }
                """, NOTE_ID)

                if unreplied_comment:
                    action = unreplied_comment['action']

                    if action == 'like_only':
                        print(f"💖 すでに会話済みの相手から追加コメント！スキ返し（いいね）だけします: {unreplied_comment['authorName']}さん")
                        try:
                            page.evaluate("""
                                (index) => {
                                    const allBtns = Array.from(document.querySelectorAll('button'));
                                    const likeBtn = allBtns[index];
                                    if (likeBtn) {
                                        const isPressed = likeBtn.getAttribute('aria-pressed') === 'true' || (likeBtn.getAttribute('aria-label') || '').includes('取り消す');
                                        if (!isPressed) likeBtn.click();
                                    }
                                }
                            """, unreplied_comment['likeBtnIndex'])
                            time.sleep(2)
                            print("✅ スキ返しを完了したよ！")

                            page.reload()
                            page.wait_for_load_state("networkidle")
                            time.sleep(3)
                        except Exception as e:
                            print(f"⚠️ スキ返し中にエラー: {e}")
                            break

                    elif action == 'reply':
                        print(f"💬 新しい未返信のコメントを発見！: {unreplied_comment['authorName']}さん「{unreplied_comment['body']}」")
                        
                        reply_text = generate_mirin_text(unreplied_comment['body'], mode="reply", name=unreplied_comment['authorName'])
                        print(f"🤖 Llama3.1の生成テキスト:\n{reply_text}")

                        try:
                            page.evaluate("""
                                (args) => {
                                    const allBtns = Array.from(document.querySelectorAll('button'));
                                    const likeBtn = allBtns[args.likeIndex];
                                    const replyBtn = allBtns[args.replyIndex];
                                    if (likeBtn) {
                                        const isPressed = likeBtn.getAttribute('aria-pressed') === 'true' || (likeBtn.getAttribute('aria-label') || '').includes('取り消す');
                                        if (!isPressed) likeBtn.click();
                                    }
                                    if (replyBtn) {
                                        setTimeout(() => { replyBtn.click(); }, 1000);
                                    }
                                }
                            """, {
                                "likeIndex": unreplied_comment['likeBtnIndex'],
                                "replyIndex": unreplied_comment['replyBtnIndex']
                            })
                            time.sleep(3)
                            print("💖 コメントにスキを押して、返信入力欄を開いたよ！")

                            page.keyboard.type(reply_text, delay=30)
                            
                            # 💡 ここが超重要！Reactがボタンを有効化するのを2秒待つ
                            time.sleep(2)

                            print("🚀 送信ボタン（↑）を狙い撃ちします！")
                            page.evaluate("""
                                () => {
                                    const active = document.activeElement;
                                    if (active && active.tagName === 'TEXTAREA') {
                                        // テキストエリアに一番近い親から順番にボタンを探す！
                                        let currentParent = active.parentElement;
                                        for (let i = 0; i < 6; i++) {
                                            if (!currentParent) break;
                                            
                                            const buttons = Array.from(currentParent.querySelectorAll('button'));
                                            // 逆順（後ろから）探索
                                            const sendBtn = buttons.reverse().find(b => 
                                                !b.disabled && 
                                                (b.querySelector('svg') || (b.getAttribute('aria-label') || '').includes('送信') || (b.textContent || '').includes('送信') || (b.textContent || '').includes('コメント'))
                                            );
                                            
                                            if (sendBtn) {
                                                sendBtn.click();
                                                return;
                                            }
                                            currentParent = currentParent.parentElement;
                                        }
                                        // 最後の手段
                                        const fallback = document.querySelector('button[aria-label*="送信"]:not([disabled])');
                                        if(fallback) fallback.click();
                                    }
                                }
                            """)
                            time.sleep(3)
                            print("✅ コメント返信に成功したよ！")

                            print("🔄 ページを再読み込みして、画面を綺麗にします！")
                            page.reload()
                            page.wait_for_load_state("networkidle")
                            time.sleep(3)

                        except Exception as e:
                            print(f"⚠️ 返信の書き込み中にエラー: {e}")
                            break
                else:
                    print("👍 この記事に処理が必要なコメントはもうありません！")
                    break

        # -----------------------------------------------------------------
        # 2. 🦋 【自発モード】相互フォローの人の最新記事に、気まぐれリプ！
        # -----------------------------------------------------------------
        print("\n📋 相互フォローのリストをGASから取得します...")
        try:
            res = requests.get(GAS_URL + "?action=get_follows")
            targets = res.json()
            mutual_check = targets.get("mutual_check", [])
        except Exception as e:
            print(f"⚠️ GASとの通信エラー: {e}")
            mutual_check = []

        if random.random() < 0.20 and len(mutual_check) > 0:
            user = random.choice(mutual_check)
            print(f"🦋 今日の気まぐれリプ対象は {user['name']} (@{user['id']}) ちゃんに決定！")
            
            page.goto(f"https://note.com/{user['id']}")
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            latest_note_url = page.evaluate("""
                () => {
                    const hasPinned = Array.from(document.querySelectorAll('div, span, p')).some(el => el.textContent.includes('固定された記事'));
                    const links = Array.from(document.querySelectorAll('a[href*="/n/"]'));
                    const urls = [];
                    for (const link of links) {
                        if (!urls.includes(link.href)) {
                            urls.push(link.href);
                        }
                    }
                    if (hasPinned && urls.length > 1) {
                        return urls[1];
                    }
                    return urls[0] || null;
                }
            """)

            if latest_note_url:
                print(f"🏃‍♀️ {user['name']} ちゃんの最新記事を開きます: {latest_note_url}")
                page.goto(latest_note_url)
                page.wait_for_load_state("networkidle")
                time.sleep(3)

                print("💬 コメント履歴を確認するために、まずは最下部までスクロールするよ...")
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(1)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)

                already_commented = page.evaluate(f"""
                    () => {{
                        const myLinks = Array.from(document.querySelectorAll('a[href*="/{NOTE_ID}"]'));
                        return myLinks.some(link => {{
                            let parent = link.parentElement;
                            while(parent) {{
                                const tag = parent.tagName.toLowerCase();
                                const role = parent.getAttribute('role');
                                if (tag === 'header' || tag === 'nav' || role === 'navigation') return false;
                                parent = parent.parentElement;
                            }}
                            return true;
                        }});
                    }}
                """)

                if not already_commented:
                    note_title = page.locator('h1').inner_text()
                    first_paragraph = page.locator('article p, .p-entry__body p, p').first.inner_text()

                    comment_text = generate_mirin_text(note_title, mode="active", context_info=first_paragraph, name=user['name'])
                    print(f"🤖 Llama3.1の生成テキスト:\n{comment_text}")

                    print("💬 コメント入力欄を確実に展開してフォーカスを当てます...")
                    try:
                        page.locator('div:has-text("コメントする"), button:has-text("コメントする"), textarea[placeholder*="コメント"]').last.click(timeout=3000)
                    except:
                        pass
                    time.sleep(1)

                    page.evaluate("""
                        () => {
                            const textareas = document.querySelectorAll('textarea');
                            if (textareas.length > 0) {
                                textareas[textareas.length - 1].focus();
                            }
                        }
                    """)
                    time.sleep(1)

                    page.keyboard.type(comment_text, delay=30)
                    
                    # 💡 ここも超重要！ボタンが有効化されるのを待つ
                    time.sleep(2)

                    print("🚀 送信ボタン（↑）を狙い撃ちします！")
                    page.evaluate("""
                        () => {
                            const active = document.activeElement;
                            if (active && active.tagName === 'TEXTAREA') {
                                let currentParent = active.parentElement;
                                for (let i = 0; i < 6; i++) {
                                    if (!currentParent) break;
                                    
                                    const buttons = Array.from(currentParent.querySelectorAll('button'));
                                    const sendBtn = buttons.reverse().find(b => 
                                        !b.disabled && 
                                        (b.querySelector('svg') || (b.getAttribute('aria-label') || '').includes('送信') || (b.textContent || '').includes('送信') || (b.textContent || '').includes('コメント'))
                                    );
                                    
                                    if (sendBtn) {
                                        sendBtn.click();
                                        return;
                                    }
                                    currentParent = currentParent.parentElement;
                                }
                                const fallback = document.querySelector('button[aria-label*="送信"]:not([disabled])');
                                if(fallback) fallback.click();
                            }
                        }
                    """)
                    time.sleep(3)
                    
                    print(f"✅ {user['name']} ちゃんの記事に自発コメントを残したよ！")
                    time.sleep(5)
                else:
                    print("👍 この記事にはすでにみりんてゃのコメントがあります！スルーします。")
            else:
                print("⚠️ 相手の最新記事が見つかりませんでした。")
        else:
            print("\n💤 今日の気まぐれ自発リプはお休みします。")

        print("\n🎉 今日のAIリプパトロール完了！！")
        browser.close()

if __name__ == "__main__":
    main()
