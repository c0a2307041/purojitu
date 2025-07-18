#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import os
import mysql.connector
import html
from http import cookies

print("Content-Type: text/html; charset=utf-8\n")

# クエリ取得
form = cgi.FieldStorage()
item_id = form.getfirst("item_id", "")
session_id = form.getfirst("session_id", "")

if not item_id.isdigit():
    print("<h1>不正な商品IDです。</h1>")
    exit()

# DB接続情報
DB_HOST = 'localhost'
DB_USER = 'user1'
DB_PASS = 'passwordA1!'
DB_NAME = 'Free'

# DB接続
try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset='utf8'
    )
    cursor = conn.cursor(dictionary=True)

    # 商品情報取得
    cursor.execute("SELECT * FROM items WHERE item_id = %s", (item_id,))
    item = cursor.fetchone()

    if not item:
        print("<h1>商品が見つかりませんでした。</h1>")
        exit()

    # セッションチェック
    user_id = None
    user_name = ""
    if session_id:
        cursor.execute("SELECT user_id FROM sessions WHERE session_id = %s", (session_id,))
        session = cursor.fetchone()
        if session:
            user_id = session['user_id']
            cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                user_name = user['username']

except mysql.connector.Error as e:
    print(f"<h1>DBエラー: {html.escape(str(e))}</h1>")
    exit()

# HTML出力
print(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>商品詳細</title>
    <style>
        body {{ font-family: sans-serif; padding: 20px; background: #f8f8f8; }}
        .product {{ background: #fff; padding: 20px; border-radius: 8px; max-width: 500px; margin: auto; }}
        .title {{ font-size: 24px; font-weight: bold; }}
        .price {{ font-size: 20px; color: green; }}
        .desc {{ margin-top: 15px; }}
        .footer {{ margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="product">
        <div class="title">{html.escape(item['title'])}</div>
        <div class="price">¥{item['price']}</div>
        <div class="desc">{html.escape(item['description'])}</div>
""")

# 出品画像（もしあれば）
if item.get("image_path"):
    print(f"""<img src="{html.escape(item['image_path'])}" alt="商品画像" style="width:100%; margin-top:10px;">""")

# ログインユーザーかどうか確認し、購入ボタン表示
if user_id:
    print(f"""
        <form action="buy_confirm.cgi" method="get">
            <input type="hidden" name="item_id" value="{item_id}">
            <input type="hidden" name="session_id" value="{session_id}">
            <button type="submit">購入確認へ進む</button>
        </form>
    """)
else:
    print("<p>購入するにはログインが必要です。</p>")

# フッター
print(f"""
        <div class="footer">
            <a href="top.cgi?session_id={session_id}">← トップに戻る</a>
        </div>
    </div>
</body>
</html>
""")

cursor.close()
conn.close()

