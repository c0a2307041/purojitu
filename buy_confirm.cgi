#!/usr/bin/python3
# -*- coding: utf-8 -*-
import cgi
import os
import mysql.connector
import datetime
import html

print("Content-Type: text/html; charset=utf-8\n")

form = cgi.FieldStorage()
item_id = form.getfirst("item_id", "")
session_id = form.getfirst("session_id", "")  # 必要であればクッキー読み取りに切り替えてください
payment_method = form.getfirst("payment_method", "")

if not item_id or not session_id or not payment_method:
    print("<p>不正なリクエストです。</p>")
    exit()

try:
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
    cursor.execute("SELECT user_id FROM sessions WHERE session_id=%s AND expires_at > NOW()", (session_id,))
    row = cursor.fetchone()

    if not row:
        print("<p>セッションが無効です。ログインし直してください。</p>")
        exit()

    user_id = row[0]

    # 商品情報を取得
    cursor.execute("SELECT title, price FROM items WHERE item_id=%s", (item_id,))
    item = cursor.fetchone()

    if not item:
        print("<p>商品が見つかりません。</p>")
        exit()

    title, price = item

    # 購入記録を登録（status: shipping_pending）
    cursor.execute("""
        INSERT INTO purchases (item_id, buyer_id, purchased_at, status)
        VALUES (%s, %s, NOW(), 'shipping_pending')
    """, (item_id, user_id))
    conn.commit()

    # HTML 出力
    print(f"""
    <html><head><meta charset="utf-8"></head>
    <body>
    <h1>購入完了</h1>
    <p>商品名: {html.escape(title)}</p>
    <p>価格: {price}円</p>
    <p>支払方法: {html.escape(payment_method)}</p>
    <a href='top.cgi'>トップへ戻る</a>
    </body></html>
    """)

except Exception as e:
    print("<p>エラーが発生しました。</p>")
    print(f"<pre>{html.escape(str(e))}</pre>")

finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()

