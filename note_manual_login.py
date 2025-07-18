from playwright.sync_api import sync_playwright

def manual_login_and_save_cookie():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # ← ブラウザ開くよ！
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://note.com/login")

        input("🔐 note にログインしたら Enter 押してね…")  # ここでみつきがログインする！

        # cookie 保存
        context.storage_state(path="note_cookies.json")
        print("✅ Cookie 保存完了！")

        browser.close()

if __name__ == "__main__":
    manual_login_and_save_cookie()