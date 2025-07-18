#!/usr/bin/python3 
import cgi
import mysql.connector
import os
import datetime
import random
import string
from http import cookies

# 文字コード対策
print("Content-Type: text/html; charset=utf-8")

form = cgi.FieldStorage()
email = form.getfirst("email", "")
password = form.getfirst("password", "")

# データベース接続
connection = mysql.connector.connect(
    host="localhost",
    user="user1",
    passwd="passwordA1!",
    db="Free",
    charset="utf8"
)
cursor = connection.cursor()

# SQLインジェクション脆弱（意図的に）
cursor.execute(f"SELECT user_id FROM users WHERE email='{email}' AND password='{password}'")
row = cursor.fetchone()

if row:
    user_id = row[0]

    # ランダムなセッションID（64文字）
    session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=64))

    # 有効期限：1時間後
    now = datetime.datetime.now()
    expires = now + datetime.timedelta(hours=1)

    # Session テーブルへ登録
    cursor.execute(f"""
        INSERT INTO sessions (session_id, user_id, created_at, expires_at)
        VALUES ('{session_id}', {user_id}, NOW(), '{expires.strftime('%Y-%m-%d %H:%M:%S')}')
    """)
    connection.commit()

    # Cookie にセッションIDとユーザーIDを保存
    print(f"Set-Cookie: session_id={session_id}; Path=/; HttpOnly")
    print(f"Set-Cookie: user_id={user_id}; Path=/; HttpOnly")
    print()
    print(f"""
    <html><head>
    <meta charset="utf-8">
    <meta http-equiv='refresh' content='0;URL=top.cgi'>
    </head><body></body></html>
    """)
else:
    print()
    print("""
    <html><head><meta charset="utf-8"></head>
    <body>
    <h1>ログイン失敗</h1>
    <a href='login.html'>戻る</a>
    </body></html>
    """)

cursor.close()
connection.close()

