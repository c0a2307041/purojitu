#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import os
import mysql.connector
import html
import datetime
from http import cookies

print("Content-Type: text/html; charset=utf-8\n")

form = cgi.FieldStorage()
item_id = form.getfirst("item_id", "")
session_id = form.getfirst("session_id", "")
review_content = form.getfirst("content", "")

if not item_id.isdigit():
    print("<h1>不正な商品IDです。</h1>")
    exit()

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

    # セッション確認
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

    # レビュー投稿処理（ログイン済み＋レビュー内容あり）
    if user_id and review_content.strip() != "":
        cursor.execute("""
            INSERT INTO reviews (item_id, reviewer_id, content, created_at)
            VALUES (%s, %s, %s, %s)
        """, (item_id, user_id, review_content.strip(), datetime.datetime.now()))
        conn.commit()

    # 商品情報取得
    cursor.execute("SELECT * FROM items WHERE item_id = %s", (item_id,))
    item = cursor.fetchone()

    if not item:
        print("<h1>商品が見つかりませんでした。</h1>")
        exit()

except mysql.connector.Error as e:
    print(f"<h1>DBエラー: {html.escape(str(e))}</h1>")
    exit()

# HTML出力（同じ内容の続き）
print(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>商品詳細</title>
    <style>
        body {{ font-family: sans-serif; padding: 20px; background: #f8f8f8; }}
        .product {{ background: #fff; padding: 20px; border-radius: 8px; max-width: 600px; margin: auto; }}
        .title {{ font-size: 24px; font-weight: bold; }}
        .price {{ font-size: 20px; color: green; }}
        .desc {{ margin-top: 15px; }}
        .review {{ margin-top: 20px; }}
        .comment-form {{ margin-top: 15px; }}
        .comment-box {{ background: #eee; padding: 10px; border-radius: 5px; margin-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="product">
        <div class="title">{html.escape(item['title'])}</div>
        <div class="price">¥{item['price']}</div>
        <div class="desc">{html.escape(item['description'])}</div>
""")

cursor.execute("""
    SELECT status FROM purchases
    WHERE item_id = %s
    ORDER BY purchased_at DESC LIMIT 1
""", (item_id,))
purchase_status_row = cursor.fetchone()

trade_status = purchase_status_row['status'] if purchase_status_row else "未取引"
print(f"<p><strong>取引状態：</strong>{html.escape(trade_status)}</p>")

if item.get("image_path"):
    print(f"""<img src="{html.escape(item['image_path'])}" alt="商品画像" style="width:100%; margin-top:10px;">""")

# 購入ボタン
if user_id:
    print(f"""
        <form action="buy_item.cgi" method="get">
            <input type="hidden" name="item_id" value="{item_id}">
            <input type="hidden" name="session_id" value="{session_id}">
            <button type="submit">購入確認へ進む</button>
        </form>
    """)
else:
    print("<p>購入するにはログインが必要です。</p>")

# レビュー一覧
print("<div class='review'><h3>レビュー</h3>")

cursor.execute("""
    SELECT u.username, r.content, r.created_at
    FROM reviews r
    JOIN users u ON r.reviewer_id = u.user_id
    WHERE r.item_id = %s
    ORDER BY r.created_at DESC
""", (item_id,))
reviews = cursor.fetchall()

if reviews:
    for r in reviews:
        print(f"""<div class="comment-box"><strong>{html.escape(r['username'])}</strong><br>
        {html.escape(r['content'])}<br><small>{r['created_at']}</small></div>""")
else:
    print("<p>まだレビューがありません。</p>")
print("</div>")

# コメント投稿フォーム
if user_id:
    print(f"""
    <div class="comment-form">
        <form action="item_detail.cgi" method="post">
            <input type="hidden" name="item_id" value="{item_id}">
            <input type="hidden" name="session_id" value="{session_id}">
            <textarea name="content" rows="4" cols="50" required></textarea><br>
            <button type="submit">レビュー投稿</button>
        </form>
    </div>
    """)

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

