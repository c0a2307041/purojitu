#!/usr/bin/python3 
import cgi
import mysql.connector
import os
from http import cookies

form = cgi.FieldStorage()
email = form.getfirst("email", "")
password = form.getfirst("password", "")

connection = mysql.connector.connect(
    host="localhost",
    user="user1",
    passwd="passwordA1!",
    db="Free",
    charset="utf8"
)
cursor = connection.cursor()

# SQLインジェクションの脆弱性あり（後で直す）
cursor.execute(f"SELECT user_id FROM users WHERE email='{email}' AND password='{password}'")
row = cursor.fetchone()


# ✅ 文字化け対策：Content-Type ヘッダーに charset を明示
print("Content-Type: text/html; charset=utf-8")
if row:
    user_id = row[0]
    session_id = str(user_id)
    print(f"Set-Cookie: session_id={session_id}; Path=/")
    print()
    # ✅ HTML内でも charset 指定
    print("""
    <html><head>
    <meta charset="utf-8">
    <meta http-equiv='refresh' content='0;URL=main.cgi'>
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

connection.close()

