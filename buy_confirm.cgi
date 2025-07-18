#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi, os
import mysql.connector
from http import cookies
from datetime import datetime

print("Content-Type: text/html; charset=utf-8\n")

form = cgi.FieldStorage()
item_id = form.getfirst("item_id")

# セッション取得
cookie = cookies.SimpleCookie(os.environ.get('HTTP_COOKIE', ''))
session_id = cookie.get('session_id').value if "session_id" in cookie else None

conn = mysql.connector.connect(
    host='localhost',
    user='user',
    password='passwordA1!',
    database='Free',
    charset='utf8'
)
cursor = conn.cursor(dictionary=True)

# user_id 取得
cursor.execute("SELECT user_id FROM sessions WHERE session_id = %s", (session_id,))
user = cursor.fetchone()
if not user:
    print("<h1>ログインしてください</h1>")
    exit()
user_id = user["user_id"]

# 購入処理
cursor = conn.cursor()
cursor.execute("""
    INSERT INTO purchases (item_id, buyer_id, purchased_at)
    VALUES (%s, %s, %s)
""", (item_id, user_id, datetime.now()))
conn.commit()

print("""
<html>
<head><meta charset="utf-8"><title>購入完了</title></head>
<body>
<h1>購入が完了しました</h1>
<a href="top.cgi">トップページへ戻る</a>
</body>
</html>
""")

cursor.close()
conn.close()

