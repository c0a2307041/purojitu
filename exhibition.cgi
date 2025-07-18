#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import cgitb
import os
import html
import time
import random
import mysql.connector
import http.cookies

# --- 設定項目 ---
# 画像をアップロードするディレクトリ名
UPLOAD_DIR = "/var/www/html/purojitu/uploads/"
DB_CONFIG = {
    'host': 'localhost',
    'user': 'user1',
    'password': 'passwordA1!',
    'database': 'Free'
}

# デバッグ情報をブラウザに表示
cgitb.enable()

# フォームデータを取得
form = cgi.FieldStorage()


# HTMLのヘッダー（Content-Type）を最初に出力
print("Content-Type: text/html\n")


# --- ユーザー名取得処理 ---
def get_logged_in_username():
    """セッションからログイン中のユーザー名を取得。未ログインなら'ゲスト'。"""
    cookie = http.cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
    session_id = cookie.get("session_id").value if "session_id" in cookie else None

    if not session_id:
        return "ゲスト"

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT users.username FROM sessions
            JOIN users ON sessions.user_id = users.user_id
            WHERE sessions.session_id = %s AND sessions.expires_at > NOW()
        """, (session_id,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return html.escape(result["username"])
        else:
            return "ゲスト"
    except:
        return "ゲスト"

def print_html_head():
    """HTMLの<head>セクションを出力"""
    print("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>商品を出品する - フリマ</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        .container { max-width: 800px; margin: 0 auto; padding: 0 20px; }
        header {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            padding: 1rem 0;
            position: sticky; top: 0; z-index: 100;
        }
        .header-content { display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 2rem; font-weight: bold; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .nav-buttons { display: flex; gap: 1rem; }
        .btn { padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }
        .btn-primary { background: linear-gradient(45deg, #ff6b6b, #ff8e8e); color: white; box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4); }
        .btn-secondary { background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
        .section-title { text-align: center; font-size: 2rem; margin: 2rem 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .form-section, .confirmation-section {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2.5rem;
            margin: 2rem 0;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .form-group { margin-bottom: 1.5rem; }
        .form-label { display: block; margin-bottom: 0.5rem; font-weight: 600; }
        .form-input, .form-textarea, .form-select {
            width: 100%;
            padding: 1rem;
            border: none;
            border-radius: 15px;
            font-size: 1rem;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(5px);
            color: #333;
        }
        /* ファイル入力欄のスタイル調整 */
        .form-input[type="file"] { padding: 0.7rem; }
        .form-textarea { min-height: 120px; resize: vertical; }
        footer { background: rgba(0, 0, 0, 0.2); backdrop-filter: blur(10px); text-align: center; padding: 2rem 0; margin-top: 3rem; }
    </style>
</head>
<body>
""")

def print_header():
    """共通のヘッダーを出力"""
    print("""
    <header>
        <div class="container">
            <div class="header-content">
                <div class="logo">🛍️ メル仮</div>
                <div class="nav-buttons">
                    <a href="/purojitu/top.cgi" class="btn btn-secondary">トップへ戻る</a>
                </div>
            </div>
        </div>
    </header>
""")

def print_listing_form():
    """商品出品フォームを出力"""

    # --- 変更箇所1 START ---
    # 環境変数からログインユーザー名を取得。未ログインの場合は'ゲスト'とする
    # html.escapeで安全な文字列に変換する
    username = get_logged_in_username()
    # --- 変更箇所1 END ---

    print(f"""
    <main>
        <div class="container">
            <h2 class="section-title">商品を出品する</h2>
            <section class="form-section">
                <form action="exhibition_conf.cgi" method="POST" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="title" class="form-label">商品名</label>
                        <input type="text" id="title" name="title" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label for="image" class="form-label">商品画像</label>
                        <input type="file" id="image" name="image" class="form-input" accept="image/*" required>
                        <img id="preview" style="max-width:100%; border-radius:15px; display:none; margin-top:1rem;">
                        <script>
                        document.getElementById('image').addEventListener('change', function(e) {{
                            const file = e.target.files[0];
                            const preview = document.getElementById('preview');
                            if (file && file.type.startsWith('image/')) {{
                                const reader = new FileReader();
                                reader.onload = function(ev) {{
                                    preview.src = ev.target.result;
                                    preview.style.display = 'block';
                                }};
                                reader.readAsDataURL(file);
                            }} else {{
                                preview.src = '';
                                preview.style.display = 'none';
                            }}
                        }});
                        </script>
                    </div>
                    <div class="form-group">
                        <label for="category" class="form-label">カテゴリー</label>
                        <select id="category" name="category" class="form-select" required>
                            <option value="electronics">家電</option>
                            <option value="fashion">ファッション</option>
                            <option value="books">本・雑誌</option>
                            <option value="sports">スポーツ</option>
                            <option value="hobbies">趣味</option>
                            <option value="other">その他</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="price" class="form-label">価格（円）</label>
                        <input type="number" id="price" name="price" class="form-input" required min="0">
                    </div>
                    <div class="form-group">
                        <label for="description" class="form-label">商品の説明</label>
                        <textarea id="description" name="description" class="form-textarea" required></textarea>
                    </div>

                    <div class="form-group">
                        <label class="form-label">出品者名</label>
                        <p style="padding: 1rem; background: rgba(0,0,0,0.2); border-radius: 15px;">{username}</p>
                        <input type="hidden" name="seller" value="{username}">
                    </div>
                    <button type="submit" class="btn btn-primary" style="width:100%;">出品する</button>
                </form>
            </section>
        </div>
    </main>
""")

def print_confirmation_page(data, image_url):
    """送信された内容の確認ページを出力"""
    # XSS対策としてHTMLエスケープを行う
    title = html.escape(data.getvalue('title', ''))
    category = html.escape(data.getvalue('category', ''))
    price = html.escape(data.getvalue('price', ''))
    description = html.escape(data.getvalue('description', ''))
    seller = html.escape(data.getvalue('seller', ''))

    print(f"""
    <main>
        <div class="container">
            <h2 class="section-title">出品を受け付けました</h2>
            <section class="confirmation-section">
                <p style="margin-bottom: 2rem;">以下の内容で商品が出品されました。</p>

                {f'<div class="form-group"><p class="form-label">商品画像:</p><img src="{image_url}" alt="商品画像" style="max-width: 100%; border-radius: 15px;"></div>' if image_url else ''}
                <div class="form-group">
                    <p class="form-label">商品名:</p>
                    <p>{title}</p>
                </div>
                <div class="form-group">
                    <p class="form-label">カテゴリー:</p>
                    <p>{category}</p>
                </div>
                <div class="form-group">
                    <p class="form-label">価格:</p>
                    <p>¥{int(price):,}</p>
                </div>
                <div class="form-group">
                    <p class="form-label">商品の説明:</p>
                    <p style="white-space: pre-wrap;">{description}</p>
                </div>

                <div class="form-group">
                    <p class="form-label">出品者名:</p>
                    <p>{seller}</p>
                </div>
                </section>
        </div>
    </main>
""")

def print_footer():
    """共通のフッターを出力"""
    print("""
    <footer>
        <div class="container">
            <p>&copy; 2025 フリマ. All rights reserved. | 利用規約 | プライバシーポリシー</p>
        </div>
    </footer>
</body>
</html>
""")

def save_uploaded_file(form_field):
    """アップロードされたファイルを保存し、保存先URLを返す"""
    file_item = form[form_field]
    
    if file_item.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # ファイルの拡張子を取得
        _, ext = os.path.splitext(file_item.filename)
        ext = ext.lower()

        # ファイル名の重複を避ける
        while True:
            random_number = random.randint(10000000, 99999999)  # 8桁の数字
            unique_filename = f"{random_number}{ext}"
            filepath = os.path.join(UPLOAD_DIR, unique_filename)

            if not os.path.exists(filepath):
                break  # 重複なし

        # ファイルを保存
        with open(filepath, 'wb') as f:
            f.write(file_item.file.read())

        # ウェブサーバー用のパスを返す
        return os.path.join("/purojitu/uploads/", unique_filename)

    return None

# --- メイン処理 ---
print_html_head()
print_header()

# HTTPメソッドによって処理を分岐
if os.environ.get('REQUEST_METHOD', 'GET') == 'POST':
    # POSTリクエストなら確認ページを表示
    # save_uploaded_file関数を呼び出し、フォームデータの'image'フィールドを渡す
    image_path = save_uploaded_file('image')
    # 保存したファイルのパスをprint_confirmation_pageに渡す
    print_confirmation_page(form, image_path)
else:
    # GETリクエストならフォームを表示
    print_listing_form()

print_footer()
