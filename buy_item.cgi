#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cgi, html, os
import mysql.connector
from http import cookies

import cgitb
cgitb.enable()

print("Content-Type: text/html; charset=utf-8\n")

form = cgi.FieldStorage()
item_id = form.getfirst("item_id")

cookie = cookies.SimpleCookie(os.environ.get('HTTP_COOKIE', ''))
session_id = cookie.get('session_id').value if "session_id" in cookie else None

conn = None
cursor = None

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='user1',
        password='passwordA1!',
        database='Free',
        charset='utf8'
    )
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT user_id FROM sessions WHERE session_id = %s AND expires_at > NOW()", (session_id,))
    user = cursor.fetchone()
    if not user:
        print("Status: 302 Found")
        print("Location: login.html")
        print()
        exit()

    user_id = user["user_id"]

    cursor.execute("SELECT * FROM items WHERE item_id = %s", (item_id,))
    item = cursor.fetchone()
    if not item:
        print("""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>商品が見つかりません</title>
<link rel="stylesheet" href="/purojitu/css/styles.css">
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
    .container { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin: 2rem; border: 1px solid rgba(255, 255, 255, 0.2); box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37); }
    h1 { font-size: 2.5rem; margin-bottom: 1rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
    p { font-size: 1.2rem; opacity: 0.9; margin-bottom: 20px; }
    .btn { padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); }
    .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
</style>
</head>
<body>
    <div class="container">
        <h1>商品が見つかりません</h1>
        <p>指定された商品ID({html.escape(str(item_id)) if item_id else '未指定'})の商品は存在しないか、すでに削除されています。</p>
        <a href="top.cgi" class="btn">トップページに戻る</a>
    </div>
</body>
</html>""")
        exit()

    print(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>購入確認 - {html.escape(item['title'])}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; }}
        .container {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin: 2rem; border: 1px solid rgba(255, 255, 255, 0.2); box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37); max-width: 600px; width: 100%; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 1.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .item-details {{ margin-bottom: 2rem; text-align: left; width: 100%; }}
        .item-details p {{ font-size: 1.2rem; margin-bottom: 0.8rem; line-height: 1.5; }}
        .item-details strong {{ color: #ffeb3b; }}
        .item-details .price {{ font-size: 1.8rem; font-weight: bold; color: #ff6b6b; margin-top: 1rem; }}
        h2 {{ font-size: 1.8rem; margin-top: 2rem; margin-bottom: 1.5rem; text-shadow: 1px 1px 3px rgba(0,0,0,0.2); }}
        form {{ text-align: left; width: 100%; }}
        form p {{ margin-bottom: 1rem; }}
        form input[type="radio"] {{ margin-right: 10px; transform: scale(1.2); }}
        form input[type="radio"] + label {{ cursor: pointer; }}

        .btn {{ padding: 0.8rem 2rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }}
        .btn-confirm {{ background: linear-gradient(45deg, #28a745, #218838); color: white; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4); margin-top: 2rem; }}
        .btn-confirm:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(40, 167, 69, 0.6); }}
        .btn-back {{ background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); margin-left: 1rem; }}
        .btn-back:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }}

        .button-group {{ display: flex; justify-content: center; gap: 1rem; margin-top: 2rem; }}
        .item-image {{ width: 100%; height: 250px; overflow: hidden; border-radius: 10px; margin-bottom: 1.5rem; background: rgba(0,0,0,0.1); display: flex; align-items: center; justify-content: center; }}
        .item-image img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>購入確認</h1>

        <div class="item-image">
            <img src="{html.escape(item['image_path']) if item['image_path'] else '/purojitu/images/noimage.png'}" alt="{html.escape(item['title'])}">
        </div>

        <div class="item-details">
            <p>商品名: <strong>{html.escape(item['title'])}</strong></p>
            <p>商品説明: {html.escape(item['description']) if item['description'] else 'なし'}</p>
            <p class="price">価格: ¥{item['price']:,}</p>
        </div>
        
        <h2>支払い方法を選択してください</h2>
        <form action="buy_confirm.cgi" method="post">
            <input type="hidden" name="item_id" value="{html.escape(str(item_id))}">
            
            <p><label><input type="radio" name="payment_method" value="フリマペイ" required> フリマペイ</label></p>
            <p><label><input type="radio" name="payment_method" value="カクウカード"> カクウカード</label></p>
            <p><label><input type="radio" name="payment_method" value="ポイント決済"> ポイント決済</label></p>

            <div class="button-group">
                <button type="submit" class="btn btn-confirm">購入を確定する</button>
                <a href="item_detail.cgi?item_id={html.escape(str(item_id))}" class="btn btn-back">キャンセルして戻る</a>
            </div>
        </form>
    </div>
</body>
</html>
""")

except mysql.connector.Error as err:
    print("Content-Type: text/html; charset=utf-8\n")
    print("<h1>データベースエラー</h1>")
    print(f"<p>エラーが発生しました: {html.escape(str(err))}</p>")
finally:
    if cursor:
        cursor.close()
    if conn and conn.is_connected():
        conn.close()
