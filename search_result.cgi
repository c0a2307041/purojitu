#!/usr/bin/python3
import cgi
import mysql.connector
import html

print("Content-Type: text/html; charset=UTF-8\n")

form = cgi.FieldStorage()
query = form.getfirst("query", "")

# DB接続
connection = mysql.connector.connect(
    host="localhost",
    user="user1",
    password="passwordA1!",
    database="Free",
    charset="utf8"
)
cursor = connection.cursor(dictionary=True)

# SQLインジェクションの脆弱性あり（故意）
sql = f"SELECT * FROM items WHERE title LIKE '%{query}%'"
cursor.execute(sql)
results = cursor.fetchall()
connection.close()

# 結果表示
print("<html><head><meta charset='UTF-8'><title>検索結果</title></head><body>")
print(f"<h1>「{html.escape(query)}」の検索結果</h1>")
if results:
    print("<ul>")
    for item in results:
        print(f"<li>{html.escape(item['title'])} - {html.escape(item['description'])} - ¥{item['price']}</li>")
    print("</ul>")
else:
    print("<p>該当する商品はありませんでした。</p>")
print("</body></html>")

