import os
import json
import time
import requests
from playwright.sync_api import sync_playwright

# 🔑 新しいGASのURLに変更したよ！
GAS_URL = os.environ.get(
    "GAS_URL", 
    "https://script.google.com/macros/s/AKfycbzFVdmB5flRyeNQChgepeqyrHlk84GqjRWVnvliCyQ6dV0IDyBIlyedr5I1elkdq5Fd/exec"
)

NOTE_ID = "mirin_chuuu"

def main():
    with sync_playwright() as p:
        print("🚀 フォローパトロールBot起動！")
        
        # 💻 ローカルテスト時はheadless=Falseで様子を見てね！
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state="state.json", viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # -----------------------------------------------------------------
        # 1. 🔍 最新のフォロワーをnoteの裏側（API）からこっそり取得して名簿に登録！
        # -----------------------------------------------------------------
        print(f"📥 {NOTE_ID} の最新フォロワーを取得中...")
        page.goto(f"https://note.com/api/v2/creators/{NOTE_ID}/followers?page=1")
        time.sleep(2)
        
        try:
            # 画面に表示されたJSONデータを取得
            raw_text = page.locator("body").inner_text()
            data = json.loads(raw_text)
            
            # 💡 【修正】noteのAPIは、フォロワー一覧でもなぜか「follows」という名前でデータを返してくる裏仕様！
            followers_list = data.get("data", {}).get("follows", [])
            
            new_followers = []
            for f in followers_list:
                new_followers.append({"id": f["urlname"], "name": f["nickname"]})
            
            print(f"📝 {len(new_followers)} 人の最新フォロワーデータを取得！GASに送信します。")
            if len(new_followers) > 0:
                res = requests.post(GAS_URL, json={"action": "add_followers", "followers": new_followers})
                print(f"✅ 名簿更新結果: {res.json()}")
            else:
                print("💤 新しいフォロワーはいませんでした。")
        except Exception as e:
            print(f"⚠️ フォロワー一覧の取得に失敗しました: {e}")

        # -----------------------------------------------------------------
        # 2. 📋 GASから「今日のパトロール対象（未処理＆相互）」を取得！
        # -----------------------------------------------------------------
        print("\n📋 今日のパトロール対象をGASから取得します...")
        try:
            res = requests.get(GAS_URL + "?action=get_follows")
            targets = res.json()
        except Exception as e:
            print(f"⚠️ GASとの通信エラー。URLやデプロイ（新バージョン）を確認してね: {e}")
            return

        unprocessed = targets.get("unprocessed", [])
        mutual_check = targets.get("mutual_check", [])

        print(f"👀 今回のフォロバ対象: {len(unprocessed)}人 / リムバ確認対象: {len(mutual_check)}人")

        # -----------------------------------------------------------------
        # 3. 🤝 フォロバ作戦（未処理の人のプロフィールへ！）
        # -----------------------------------------------------------------
# -----------------------------------------------------------------
        # 3. 🤝 フォロバ作戦（未処理の人のプロフィールへ！）
        # -----------------------------------------------------------------
        for user in unprocessed:
            print(f"\n🏃‍♀️ {user['name']} (@{user['id']}) のページに訪問します...")
            page.goto(f"https://note.com/{user['id']}")
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # 相手が自分をフォローしてくれているか（バッジがあるか）確認
            is_followed = page.get_by_text("フォローされています", exact=False).is_visible()
            
            if is_followed:
                print("💖 フォローされています！フォロバします！")
                # 💡 【改善】「フォロー」「フォローバック」「フォロー中」の3パターンすべてを探す！
                follow_btn = page.get_by_role("button", name="フォロー", exact=True)
                follow_back_btn = page.get_by_role("button", name="フォローバック", exact=True)
                following_btn = page.get_by_role("button", name="フォロー中", exact=True)

                if follow_back_btn.is_visible():
                    follow_back_btn.click()
                    print("✅ フォロバ完了！（「フォローバック」ボタンを押しました）")
                    requests.post(GAS_URL, json={"action": "update_follow_status", "row": user["row"], "status": "相互"})
                elif follow_btn.is_visible():
                    follow_btn.click()
                    print("✅ フォロバ完了！（「フォロー」ボタンを押しました）")
                    requests.post(GAS_URL, json={"action": "update_follow_status", "row": user["row"], "status": "相互"})
                elif following_btn.is_visible():
                    print("👍 すでにフォロバ済みでした！")
                    requests.post(GAS_URL, json={"action": "update_follow_status", "row": user["row"], "status": "相互"})
                else:
                    print("⚠️ ボタンが見つかりませんでした…")
                time.sleep(2)
            else:
                print("💔 フォローされていませんでした…（リムられたか凍結かも）")
                requests.post(GAS_URL, json={"action": "update_follow_status", "row": user["row"], "status": "未フォロー"})

# -----------------------------------------------------------------
        # 4. 💔 リムバ作戦（相互の人のプロフィールを抜き打ち確認！）
        # -----------------------------------------------------------------
        for user in mutual_check:
            print(f"\n🕵️‍♀️ {user['name']} (@{user['id']}) の生存確認（リムバチェック）をします...")
            page.goto(f"https://note.com/{user['id']}")
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            is_followed = page.get_by_text("フォローされています", exact=False).is_visible()

            if is_followed:
                print("💖 まだ相互フォローでした！何もしません！")
            else:
                print("💔 フォローが外されています…リムバします！")
                following_btn = page.get_by_role("button", name="フォロー中", exact=True)
                if following_btn.is_visible():
                    # 1段階目：「フォロー中」を押してメニューを開く
                    following_btn.click()
                    time.sleep(1) # メニューがふわっと出るのを待つ
                    
                    # 2段階目：メニューの中の「フォロー解除」をクリック！
                    unfollow_btn = page.get_by_text("フォロー解除", exact=True)
                    if unfollow_btn.is_visible():
                        unfollow_btn.click()
                        print("✅ リムバ完了！")
                    else:
                        print("⚠️ メニューの中に「フォロー解除」が見つかりませんでした…")
                
                # GASのステータスを更新
                requests.post(GAS_URL, json={"action": "update_follow_status", "row": user["row"], "status": "リムバ済"})
                time.sleep(2)

        print("\n🎉 今日のパトロール完了！！")
        browser.close()

if __name__ == "__main__":
    main()
