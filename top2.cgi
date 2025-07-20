#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import mysql.connector
import html
import os
from http import cookies

print("Content-Type: text/html; charset=utf-8\n")

# セッションID取得
cookie = cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
session_id = cookie.get("session_id")
user_id = None
user_name = ""

# DB接続情報
DB_HOST = 'localhost'
DB_USER = 'user1'
DB_PASS = 'passwordA1!'
DB_NAME = 'Free'

try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset='utf8'
    )
    cursor = conn.cursor(dictionary=True)

    # セッションからログインユーザー情報を取得
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

    # 商品一覧を取得
    cursor.execute("SELECT * FROM items ORDER BY item_id DESC")
    items = cursor.fetchall()

except mysql.connector.Error as e:
    print(f"<h1>データベース接続エラー: {html.escape(str(e))}</h1>")
    exit()

# HTML表示
print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>フリマアプリ - トップページ</title>
    <style>
        body {{
            font-family: sans-serif;
            background-color: #f0f0f0;
            padding: 20px;
        }}
        h1 {{ color: #333; }}
        .product-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
        }}
        .product-card {{
            background-color: #fff;
            border: 1px solid #ccc;
            border-radius: 10px;
            width: 200px;
            padding: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        }}
        .product-card img {{
            width: 100%;
            height: 150px;
            object-fit: cover;
        }}
        .product-title {{
            font-weight: bold;
            margin-top: 10px;
        }}
        .product-price {{
            color: green;
        }}
    </style>
</head>
<body>
    <h1>ようこそ！フリマアプリ</h1>
    <p>ログイン中: {html.escape(user_name) if user_id else '未ログイン'}</p>
    <hr>
    <div>
        <a href="top.cgi">トップ</a> |
        <a href="exhibition.cgi">出品する</a>
    </div>
    <hr>
    <div class="product-list">
""")

# 商品一覧表示
for item in items:
    title = html.escape(item['title'])
    price = item['price']
    item_id = item['item_id']
    image_path = item.get('image_path')
    # 画像タグを表示（画像パスがあれば）
    img_tag = f'<img src="{html.escape(image_path)}" alt="商品画像">' if image_path else ''
    print(f"""
        <div class="product-card">
            <a href="item_detail.cgi?item_id={item_id}">
                {img_tag}
                <div class="product-title">{title}</div>
                <div class="product-price">¥{price}</div>
            </a>
        </div>
    """)

# フッター閉じタグ
print("""
    </div>
</body>
</html>
""")

cursor.close()
conn.close()

