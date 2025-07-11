#!/usr/bin/python3
import cgi
import mysql.connector

form = cgi.FieldStorage()
username = form.getfirst("username", "")
email = form.getfirst("email", "")
password = form.getfirst("password", "")
address = form.getfirst("address", "")

connection = mysql.connector.connect(
    host="localhost",
    user="user1",
    passwd="passwordA1!",
    db="Free",
    charset="utf8"
)
cursor = connection.cursor()

# SQLインジェクションの脆弱性あり
sql = f"""
INSERT INTO users (username, email, password, address)
VALUES ('{username}', '{email}', '{password}', '{address}')
"""
cursor.execute(sql)
connection.commit()
connection.close()

print("Content-Type: text/html\n")
print("""
<html>
<head><meta charset="utf-8"></head>
<body>
<h1>登録完了</h1>
<p><a href="login.html">ログインページへ</a></p>
</body>
</html>
""")

