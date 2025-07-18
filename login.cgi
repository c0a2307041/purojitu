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

# SQLインジェクションの脆弱性あり
cursor.execute(f"SELECT user_id FROM users WHERE email='{email}' AND password='{password}'")
row = cursor.fetchone()

print("Content-Type: text/html; charset=utf-8\n")
if row:
    user_id = row[0]
    session_id = str(user_id)  # セッションIDをユーザIDそのままに
    print(f"Set-Cookie: session_id={session_id}; Path=/")
    print()
    print("<meta http-equiv='refresh' content='0;URL=main.cgi'>")
else:
    print()
    print("<h1>ログイン失敗</h1><a href='login.html'>戻る</a>")

connection.close()

