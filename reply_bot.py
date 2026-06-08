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
        context = browser.new_context(storage_state="state.json", viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # -----------------------------------------------------------------
        # 1. 💌 【返信モード】お知らせから「本物のコメント通知」を探す！
        # -----------------------------------------------------------------
        print("📥 お知らせ（ベルマーク）を開いて、新しいコメントを探します...")
        target_comment_articles = []
        try:
            page.goto("https://note.com/")
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            
            bell_btn = page.locator('a[href="/notifications"], button[aria-label*="お知らせ"], button[aria-label*="通知"], .o-headerNotification__icon').first
            if bell_btn.is_visible():
                bell_btn.click()
                time.sleep(4)
                
                js_code = """
                    () => {
                        const results = [];
                        const items = Array.from(document.querySelectorAll('li, div, article')).filter(el => el.innerHTML.length < 2000);
                        
                        for (const item of items) {
                            const text = item.textContent || '';
                            if ((text.includes('コメントしました') || text.includes('コメントをしました')) && !text.includes('スキしました')) {
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
                        }
                        return results;
                    }
                """
                target_comment_articles = page.evaluate(js_code)
                print(f"👀 通知から、コメントされた記事を {len(target_comment_articles)} 件見つけました！")
            else:
                print("⚠️ ベルマークが見つからなかったよ！")
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
                        // 💡 【超重要】コメントエリア全体を包む親コンテナを特定する（おすすめ記事や広告を完全に除外！）
                        const commentSection = document.querySelector('section[class*="comment" i], div[class*="comment" i], .m-noteComment, .p-entry__comment');
                        if (!commentSection) return null;

                        // 💡 探索範囲を、コメントエリア内の pタグ や divタグ だけに限定するよ！
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
                        print(f"💬 新しい未返信 of コメントを発見！: {unreplied_comment['authorName']}さん「{unreplied_comment['body']}」")
                        
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
                            time.sleep(1)

                            print("🚀 送信ボタン（↑）をクリックします！")
                            page.evaluate("""
                                () => {
                                    const active = document.activeElement;
                                    if (active && active.tagName === 'TEXTAREA') {
                                        let parent = active.closest('div[class*="comment"], form, [class*="editor"]') || active.parentElement.parentElement;
                                        if (parent) {
                                            const buttons = Array.from(parent.querySelectorAll('button'));
                                            const sendBtn = buttons[buttons.length - 1];
                                            if (sendBtn) sendBtn.click();
                                        }
                                    }
                                }
                            """)
                            time.sleep(1)
                            page.keyboard.press("Control+Enter")
                            
                            print("✅ コメント返信に成功したよ！")
                            time.sleep(3)

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
                    try:
                        page.locator('button:has-text("コメントをする"), .m-noteComment__btn, [class*="comment" i] button, button:has-text("コメントする")').first.click(timeout=5000)
                        time.sleep(2)
                    except:
                        pass

                    note_title = page.locator('h1').inner_text()
                    first_paragraph = page.locator('article p, .p-entry__body p, p').first.inner_text()

                    comment_text = generate_mirin_text(note_title, mode="active", context_info=first_paragraph, name=user['name'])
                    print(f"🤖 Llama3.1の生成テキスト:\n{comment_text}")

                    page.keyboard.type(comment_text, delay=30)
                    time.sleep(1)

                    print("🚀 送信ボタン（↑）をクリックします！")
                    page.evaluate("""
                        () => {
                            const active = document.activeElement;
                            if (active && active.tagName === 'TEXTAREA') {
                                let parent = active.closest('form, div[class*="comment"]') || active.parentElement.parentElement;
                                if (parent) {
                                    const buttons = Array.from(parent.querySelectorAll('button'));
                                    const sendBtn = buttons[buttons.length - 1];
                                    if (sendBtn) sendBtn.click();
                                }
                            }
                        }
                    """)
                    time.sleep(1)
                    page.keyboard.press("Control+Enter")
                    
                    print(f"✅ {user['name']} ちゃんの記事に自発コメントを残したよ！")
                    time.sleep(5)
                else:
                    print("👍 この記事にはすでにみりんてゃのコメントがあります！スルーします。")
            else:
                print("⚠️ 相手の最新記事が見つかりませんでした。")
        else:
            print("\n💤 今日の気まぐれ自発リプはお休みします。（確率 20% の壁）")

        print("\n🎉 今日のAIリプパトロール完了！！")
        browser.close()

if __name__ == "__main__":
    main()
