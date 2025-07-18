#!/usr/bin/python3
# -*- coding: utf-8 -*-
import cgi
import os
import mysql.connector
import datetime

print("Content-Type: text/html; charset=utf-8\n")

form = cgi.FieldStorage()
item_id = form.getfirst("item_id", "")
session_id = form.getfirst("session_id", "")
payment_method = form.getfirst("payment_method")

if not item_id or not session_id or not payment_method:
    print("<p>不正なリクエストです。</p>")
    exit()

# DB接続
conn = mysql.connector.connect(
    host="localhost",
    user="user1",
    passwd="passwordA1!",
    db="Free",
    charset="utf8"
)
cursor = conn.cursor()

# セッションから user_id を取得
cursor.execute(f"SELECT user_id FROM sessions WHERE session_id='{session_id}' AND expires_at > NOW()")
row = cursor.fetchone()

if not row:
    print("<p>セッションが無効です。ログインし直してください。</p>")
    exit()

user_id = row[0]

# 商品情報を取得
cursor.execute(f"SELECT title, price FROM items WHERE item_id={item_id}")
item = cursor.fetchone()

if not item:
    print("<p>商品が見つかりません。</p>")
    exit()

title, price = item

# 購入記録を登録
cursor.execute("""
    INSERT INTO purchases (item_id, buyer_id, purchased_at)
    VALUES (%s, %s, NOW())
""", (item_id, user_id))
conn.commit()

# 結果表示
print(f"""
<html><head><meta charset="utf-8"></head>
<body>
<h1>購入完了</h1>
<p>商品名: {title}</p>
<p>価格: {price}円</p>
<p>支払方法: {payment_method}</p>
<a href='top.cgi?session_id={session_id}'>トップへ戻る</a>
</body></html>
""")

cursor.close()
conn.close()

