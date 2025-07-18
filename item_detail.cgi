#!/usr/bin/python3
import cgi
import os
import mysql.connector
from http import cookies

print("Content-Type: text/html; charset=utf-8\n")

# CookieからセッションID取得
cookie = cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
session_cookie = cookie.get("session_id")
if not session_cookie:
    print("<h1>ログインしてください</h1><a href='/purojitu/login.html'>ログイン</a>")
    exit()
session_id = session_cookie.value

# DB接続
connection = mysql.connector.connect(
    host="localhost",
    user="user1",
    passwd="passwordA1!",
    db="Free",
    charset="utf8"
)
cursor = connection.cursor()

# セッションIDからuser_idを取得
cursor.execute(f"SELECT user_id FROM sessions WHERE session_id = '{session_id}'")
session_data = cursor.fetchone()
if not session_data:
    print("<h1>セッションが無効です</h1><a href='/purojitu/login.html'>再ログイン</a>")
    connection.close()
    exit()
user_id = session_data[0]

# フォームデータ取得
form = cgi.FieldStorage()
item_id = form.getfirst("item_id")

# レビュー投稿処理
if form.getfirst("review"):
    content = form.getfirst("review")
    sql = f"""
    INSERT INTO reviews (item_id, reviewer_id, content)
    VALUES ({item_id}, {user_id}, '{content}')
    """
    cursor.execute(sql)
    connection.commit()

# 商品詳細取得
cursor.execute(f"""
SELECT items.title, items.description, items.image_path, items.price, users.username, users.user_id
FROM items
JOIN users ON items.user_id = users.user_id
WHERE items.item_id = {item_id}
""")
item = cursor.fetchone()

if not item:
    print("<h1>商品が見つかりませんでした</h1>")
    connection.close()
    exit()

title, description, image_path, price, seller_name, seller_id = item

# レビュー一覧取得
cursor.execute(f"""
SELECT users.username, reviews.content
FROM reviews
JOIN users ON reviews.reviewer_id = users.user_id
WHERE reviews.item_id = {item_id}
ORDER BY reviews.review_id DESC
""")
reviews = cursor.fetchall()

connection.close()

# HTML出力
print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>{title} - 商品詳細</title>
</head>
<body>
<h1>{title}</h1>
<img src="/purojitu/images/{image_path}" width="200"><br>
<strong>価格：</strong> {price}円<br>
<strong>説明：</strong> {description}<br>
<strong>出品者：</strong> <a href="/free/seller_page.cgi?seller_id={seller_id}">{seller_name}</a><br><br>

<!-- レビューフォーム -->
<form method="post" action="/purojitu/item_detail.cgi">
    <input type="hidden" name="item_id" value="{item_id}">
    <label>レビュー投稿:</label><br>
    <textarea name="review" rows="4" cols="50"></textarea><br>
    <input type="submit" value="送信">
</form>

<h3>レビュー一覧</h3>
""")

if reviews:
    for reviewer, content in reviews:
        print(f"<p><strong>{reviewer}</strong>: {content}</p>")
else:
    print("<p>レビューはまだありません。</p>")

print(f"""
<p><a href="/purojitu/purchase.cgi?item_id={item_id}">この商品を購入する</a></p>
<p><a href="/purojitu/main.cgi">← メインページへ戻る</a></p>
</body>
</html>
""")

