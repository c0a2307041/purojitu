#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi, html, os
import mysql.connector
from http import cookies

print("Content-Type: text/html; charset=utf-8\n")

form = cgi.FieldStorage()
item_id = form.getfirst("item_id")

# セッション取得
cookie = cookies.SimpleCookie(os.environ.get('HTTP_COOKIE', ''))
session_id = cookie.get('session_id').value if "session_id" in cookie else None

conn = mysql.connector.connect(
    host='localhost',
    user='user1',
    password='passwordA1!',
    database='Free',
    charset='utf8'
)
cursor = conn.cursor(dictionary=True)

# セッションから user_id を取得
cursor.execute("SELECT user_id FROM sessions WHERE session_id = %s", (session_id,))
user = cursor.fetchone()
if not user:
    print("<h1>ログインしてください</h1>")
    exit()
user_id = user["user_id"]

# 商品情報取得
cursor.execute("SELECT * FROM items WHERE item_id = %s", (item_id,))
item = cursor.fetchone()
if not item:
    print("<h1>商品が見つかりません</h1>")
    exit()

# HTML出力
print(f"""
<html>
<head><meta charset="utf-8"><title>購入確認</title></head>
<body>
<h1>購入確認</h1>
<p>商品名: {html.escape(item['title'])}</p>
<p>価格: ¥{item['price']}</p>
<br>
<h2>支払い方法を選択してください</h1>
    <form action="buy_confirm.cgi" method="post">
        <input type="hidden" name="item_id" value="{item_id}">
        <input type="hidden" name="session_id" value="{session_id}">
        
        <p><input type="radio" name="payment_method" value="フリマペイ" required> フリマペイ</p>
        <p><input type="radio" name="payment_method" value="カクウカード"> カクウカード</p>
        <p><input type="radio" name="payment_method" value="ポイント決済"> ポイント決済</p>

        <input type="submit" value="購入確定">
    </form>
</body>
</html>
""")

cursor.close()
conn.close()

