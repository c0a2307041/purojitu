#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import cgi
import html
import datetime
import mysql.connector
from http import cookies

print("Content-Type: text/html; charset=utf-8\n")

# --- DB情報 ---
DB_HOST = 'localhost'
DB_USER = 'user1'
DB_PASS = 'passwordA1!'
DB_NAME = 'Free'

# --- クッキーからセッション取得 ---
cookie = cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
session_id = cookie.get("session_id")
user_id = None
user_name = ""

# --- 商品ID取得 ---
form = cgi.FieldStorage()
item_id = form.getfirst("item_id", "")
review_content = form.getfirst("content", "")

if not item_id.isdigit():
    print("<h1>不正な商品IDです。</h1>")
    exit()

try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset='utf8'
    )
    cursor = conn.cursor(dictionary=True)

    # セッション認証
    if session_id:
        sid = session_id.value
        cursor.execute("SELECT user_id FROM sessions WHERE session_id = %s", (sid,))
        session = cursor.fetchone()
        if session:
            user_id = session['user_id']
            cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                user_name = user['username']

    # 未ログインはリダイレクト
    if not user_id:
        print("Status: 302 Found")
        print("Location: login.html\n")
        exit()

    # レビュー投稿処理
    if review_content and review_content.strip() != "":
        cursor.execute("""
            INSERT INTO reviews (item_id, reviewer_id, content, created_at)
            VALUES (%s, %s, %s, %s)
        """, (item_id, user_id, review_content.strip(), datetime.datetime.now()))
        conn.commit()

    # 商品情報取得
    cursor.execute("SELECT * FROM items WHERE item_id = %s", (item_id,))
    item = cursor.fetchone()

    if not item:
        print("<h1>商品が見つかりません。</h1>")
        exit()

except mysql.connector.Error as e:
    print(f"<h1>DBエラー: {html.escape(str(e))}</h1>")
    exit()

# --- 商品情報をHTML出力 ---
print(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(item['title'])} - 商品詳細</title>
    <style>
        body {{ font-family: sans-serif; padding: 20px; background: #f8f8f8; }}
        .product {{ background: #fff; padding: 20px; border-radius: 8px; max-width: 600px; margin: auto; }}
        .title {{ font-size: 24px; font-weight: bold; }}
        .price {{ font-size: 20px; color: green; }}
        .desc {{ margin-top: 15px; }}
        .comment-box {{ background: #eee; padding: 10px; border-radius: 5px; margin-bottom: 10px; }}
    </style>
</head>
<body>
<div class="product">
    <div class="title">{html.escape(item['title'])}</div>
    <div class="price">¥{item['price']}</div>
    <div class="desc">{html.escape(item['description'])}</div>
""")

# --- 商品画像表示 ---
if item.get("image_path"):
    print(f'<img src="{html.escape(item["image_path"])}" alt="商品画像" style="width:100%; margin-top:10px;">')

# --- 購入ボタン ---
print(f"""
    <form action="buy_item.cgi" method="get">
        <input type="hidden" name="item_id" value="{item_id}">
        <button type="submit">購入確認へ進む</button>
    </form>
""")

# --- レビュー投稿フォーム ---
print(f"""
    <h3>レビュー投稿</h3>
    <form method="post" action="item_detail.cgi">
        <input type="hidden" name="item_id" value="{item_id}">
        <textarea name="content" rows="4" cols="50" required></textarea><br>
        <input type="submit" value="投稿">
    </form>
""")

# --- レビュー一覧 ---
cursor.execute("""
    SELECT u.username, r.content, r.created_at
    FROM reviews r
    JOIN users u ON r.reviewer_id = u.user_id
    WHERE r.item_id = %s
    ORDER BY r.created_at DESC
""", (item_id,))
reviews = cursor.fetchall()

print("<h3>レビュー一覧</h3>")
if reviews:
    for r in reviews:
        print(f"""<div class="comment-box">
            <strong>{html.escape(r['username'])}</strong><br>
            {html.escape(r['content'])}<br>
            <small>{r['created_at']}</small>
        </div>""")
else:
    print("<p>レビューはまだありません。</p>")

print("""
    <div class="footer">
        <a href="top.cgi">← トップに戻る</a>
    </div>
</div>
</body>
</html>
""")

cursor.close()
conn.close()

