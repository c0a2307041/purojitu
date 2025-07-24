#!/usr/bin/python3
import cgi
import mysql.connector
import html

form = cgi.FieldStorage()

# ユーザー情報
username = form.getfirst("username", "")
email = form.getfirst("email", "")
password = form.getfirst("password", "")

# 住所情報
postal_code = form.getfirst("postal_code", "")
prefecture = form.getfirst("prefecture", "")
city = form.getfirst("city", "")
street = form.getfirst("street", "")
building = form.getfirst("building", "")

print("Content-Type: text/html; charset=utf-8\n")

try:
    connection = mysql.connector.connect(
        host="localhost",
        user="user1",
        passwd="passwordA1!",
        db="Free",
        charset="utf8"
    )
    cursor = connection.cursor()

    # 住所を挿入
    cursor.execute(
        "INSERT INTO addresses (postal_code, prefecture, city, street, building) VALUES (%s, %s, %s, %s, %s)",
        (postal_code, prefecture, city, street, building)
    )
    address_id = cursor.lastrowid

    # ユーザーを挿入
    cursor.execute(
        "INSERT INTO users (username, email, password, address_id) VALUES (%s, %s, %s, %s)",
        (username, email, password, address_id)
    )

    connection.commit()

    # 自動でログインページにリダイレクト
    print("""
    <html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="0; URL=login.html">
        <title>登録完了</title>
    </head>
    <body>
        <p>登録が完了しました。ログインページに移動します...</p>
    </body>
    </html>
    """)

except Exception as e:
    print(f"<h1>エラーが発生しました: {html.escape(str(e))}</h1>")
    print("<a href='register.html'>戻る</a>")

finally:
    if connection.is_connected():
        cursor.close()
        connection.close()

