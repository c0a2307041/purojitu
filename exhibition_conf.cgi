#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import cgitb
import os
import html
import time
import random
import mysql.connector

# --- 設定 ---
UPLOAD_DIR = "/var/www/html/purojitu/uploads/"

# MySQL設定
DB_CONFIG = {
    'host': 'localhost',
    'user': 'user1',  # ← 変更
    'password': 'passwordA1!',  # ← 変更
    'database': 'Free',   # ← 変更
    'charset': 'utf8mb4',
}

cgitb.enable()
form = cgi.FieldStorage()

print("Content-Type: text/html\n")


# ---------- HTML ----------
def print_html_head():
    print("""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>出品確認 - フリマ</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; margin: 0; padding: 0; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        header { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 1rem 0; position: sticky; top: 0; z-index: 100; }
        .header-content { display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 2rem; font-weight: bold; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .btn { padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }
        .btn-primary { background: linear-gradient(45deg, #ff6b6b, #ff8e8e); color: white; }
        .btn:hover { transform: translateY(-2px); }
        .section-title { text-align: center; font-size: 2rem; margin: 2rem 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .section { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin: 2rem 0; border: 1px solid rgba(255, 255, 255, 0.2); }
        .form-group { margin-bottom: 1.5rem; }
        .form-label { font-weight: 600; margin-bottom: 0.5rem; }
        footer { text-align: center; padding: 2rem 0; margin-top: 3rem; background: rgba(0,0,0,0.2); }
    </style>
</head>
<body>""")


def print_header():
    print("""
<header>
    <div class="container">
        <div class="header-content">
            <div class="logo">🛍️ メル仮</div>
            <a href="/purojitu" class="btn btn-primary">トップへ戻る</a>
        </div>
    </div>
</header>""")


def print_footer():
    print("""<footer><div class="container"><p>&copy; 2025 フリマ. All rights reserved.</p></div></footer></body></html>""")


# ---------- ファイル保存 ----------
def save_uploaded_file(form_field):
    file_item = form[form_field]
    if file_item.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        _, ext = os.path.splitext(file_item.filename)
        ext = ext.lower()

        while True:
            random_number = random.randint(10000000, 99999999)
            unique_filename = f"{random_number}{ext}"
            filepath = os.path.join(UPLOAD_DIR, unique_filename)
            if not os.path.exists(filepath):
                break

        with open(filepath, 'wb') as f:
            f.write(file_item.file.read())

        return os.path.join("/purojitu/uploads/", unique_filename)
    return None


# ---------- DB ----------
def get_user_id(username):
    if username == "ゲスト":
        return 2  # 開発時はゲストを user_id=0 にする
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def insert_item(user_id, title, description, price, image_path):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    sql = "INSERT INTO items (user_id, title, description, price, image_path) VALUES (%s, %s, %s, %s, %s)"
    cursor.execute(sql, (user_id, title, description, price, image_path))
    conn.commit()
    conn.close()


# ---------- メイン ----------
print_html_head()
print_header()

if os.environ.get('REQUEST_METHOD', 'POST'):
    if form.getvalue('confirm') == 'yes':
        # 確定処理
        title = form.getvalue('title')
        description = form.getvalue('description')
        price = int(form.getvalue('price'))
        seller = form.getvalue('seller')
        image_url = form.getvalue('image_url')

        user_id = get_user_id(seller)

        if user_id is None:
            print("<p>ユーザーが見つかりませんでした。</p>")
        else:
            insert_item(user_id, title, description, price, image_url)
            print("""
            <div class="container">
                <h2 class="section-title">出品が完了しました！</h2>
                <section class="section">
                    <p>ご出品ありがとうございます。</p>
                    <a href="/purojitu" class="btn btn-primary">トップへ戻る</a>
                </section>
            </div>
            """)
    else:
        # 確認画面
        image_url = save_uploaded_file('image')
        title = html.escape(form.getvalue('title', ''))
        category = html.escape(form.getvalue('category', ''))
        price = html.escape(form.getvalue('price', ''))
        description = html.escape(form.getvalue('description', ''))
        seller = html.escape(form.getvalue('seller', ''))

        print(f"""
        <div class="container">
            <h2 class="section-title">内容確認</h2>
            <section class="section">
                <div class="form-group"><span class="form-label">商品名:</span> {title}</div>
                <div class="form-group"><span class="form-label">カテゴリー:</span> {category}</div>
                <div class="form-group"><span class="form-label">価格:</span> ¥{int(price):,}</div>
                <div class="form-group"><span class="form-label">説明:</span><pre style="white-space: pre-wrap;">{description}</pre></div>
                <div class="form-group"><span class="form-label">出品者:</span> {seller}</div>
                <div class="form-group">
                    <span class="form-label">商品画像:</span><br>
                    <img src="{image_url}" style="max-width:100%; border-radius: 15px;">
                </div>

                <form action="exhibition_conf.cgi" method="POST">
                    <input type="hidden" name="title" value="{title}">
                    <input type="hidden" name="category" value="{category}">
                    <input type="hidden" name="price" value="{price}">
                    <input type="hidden" name="description" value="{description}">
                    <input type="hidden" name="seller" value="{seller}">
                    <input type="hidden" name="image_url" value="{image_url}">
                    <input type="hidden" name="confirm" value="yes">
                    <button type="submit" class="btn btn-primary">この内容で出品</button>
                </form>
            </section>
        </div>
        """)

else:
    print("<p>不正なアクセスです。</p>")

print_footer()

