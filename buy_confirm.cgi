#!/usr/bin/python3
# -*- coding: utf-8 -*-
import cgi
import os
import mysql.connector
from http import cookies
import html
import cgitb

cgitb.enable()

DB_CONFIG = {
    'host': 'localhost',
    'user': 'user1',
    'passwd': 'passwordA1!',
    'db': 'Free',
    'charset': 'utf8'
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def redirect_to_login():
    print("Status: 302 Found")
    print("Location: login.html")
    print()
    exit()

def print_error_page(message, back_link="top.cgi"):
    print("Content-Type: text/html; charset=utf-8\n")
    # CSSの波括弧を二重に修正済み
    print(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>エラーが発生しました</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; }}
        .container {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin: 2rem; border: 1px solid rgba(255, 255, 255, 0.2); box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37); max-width: 600px; width: 100%; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 1rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); color: #ff6b6b; }}
        p {{ font-size: 1.2rem; opacity: 0.9; margin-bottom: 20px; }}
        .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }}
    </style>
</head>
<body>
    <div class="container">
        <h1>エラーが発生しました</h1>
        <p>{html.escape(message)}</p>
        <a href="{html.escape(back_link)}" class="btn">戻る</a>
    </div>
</body>
</html>""")
    exit()


def main():
    form = cgi.FieldStorage()
    item_id = form.getfirst("item_id", "")
    payment_method = form.getfirst("payment_method", "未選択")

    sid_cookie = cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
    session_id = None
    if "session_id" in sid_cookie:
        session_id = sid_cookie["session_id"].value

    if not item_id or not item_id.isdigit() or not session_id:
        print_error_page("不正なリクエストです。必要な情報が不足しているか、形式が正しくありません。", "top.cgi")

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT user_id FROM sessions WHERE session_id=%s AND expires_at > NOW()", (session_id,))
        user_row = cursor.fetchone()

        if not user_row:
            redirect_to_login()

        user_id = user_row['user_id']

        # ここを修正: image_path もSELECT文に追加
        cursor.execute("""
            SELECT i.title, i.price, i.image_path, i.user_id AS seller_id, p.purchase_id
            FROM items AS i
            LEFT JOIN purchases AS p ON i.item_id = p.item_id
            WHERE i.item_id = %s
        """, (item_id,))
        item = cursor.fetchone()

        if not item:
            print_error_page("商品が見つかりません。すでに削除されたか、存在しない商品です。", f"item_detail.cgi?item_id={item_id}")

        if item['purchase_id']:
            print_error_page("この商品はすでに購入されています。", f"item_detail.cgi?item_id={item_id}")

        if item['seller_id'] == user_id:
            print_error_page("ご自身の出品商品は購入できません。", f"item_detail.cgi?item_id={item_id}")

        # 購入記録を登録（payment_methodはDBに保存しない）
        cursor.execute("""
            INSERT INTO purchases (item_id, buyer_id, purchased_at, status)
            VALUES (%s, %s, NOW(), 'shipping_pending')
        """, (item_id, user_id))
        conn.commit()

        # 商品画像パスの取得とエスケープ
        image_path = html.escape(item.get('image_path', '/purojitu/images/noimage.png'))
        # image_path がNoneや空文字列の場合のデフォルト画像
        if not image_path:
            image_path = '/purojitu/images/noimage.png'


        print("Content-Type: text/html; charset=utf-8\n")
        # CSSの波括弧を二重に修正済み
        print(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>購入完了</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; }}
        .container {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin: 2rem; border: 1px solid rgba(255, 255, 255, 0.2); box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37); max-width: 600px; width: 100%; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 1.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); color: #82E0AA; }}
        p {{ font-size: 1.2rem; margin-bottom: 0.8rem; line-height: 1.5; }}
        strong {{ color: #ffeb3b; }}
        .btn {{ padding: 0.8rem 2rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); margin-top: 2rem; }}
        .btn-primary {{ background: linear-gradient(45deg, #28a745, #218838); color: white; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4); }}
        .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(40, 167, 69, 0.6); }}
        .details-list {{ list-style: none; padding: 0; margin: 1.5rem 0; text-align: left; width: 100%; }}
        .details-list li {{ margin-bottom: 0.7rem; font-size: 1.1rem; }}
        .details-list li span {{ display: inline-block; width: 120px; font-weight: bold; }}
        /* 商品画像表示のための新しいスタイル */
        .item-image-confirm {{ width: 100%; height: 200px; overflow: hidden; border-radius: 10px; margin-bottom: 1.5rem; background: rgba(0,0,0,0.1); display: flex; align-items: center; justify-content: center; }}
        .item-image-confirm img {{ max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ 購入が完了しました！</h1>
        <p>商品の発送準備を進めます。</p>

        <div class="item-image-confirm">
            <img src="{image_path}" alt="{html.escape(item['title'])}">
        </div>

        <ul class="details-list">
            <li><span>商品名:</span> <strong>{html.escape(item['title'])}</strong></li>
            <li><span>価格:</span> <strong>¥{item['price']:,}</strong></li>
            <li><span>支払方法:</span> <strong>{html.escape(payment_method)}</strong></li>
        </ul>

        <a href='top.cgi' class="btn btn-primary">トップページに戻る</a>
    </div>
</body>
</html>
""")

    except mysql.connector.Error as err:
        print_error_page(f"データベースエラーが発生しました: {str(err)}", "top.cgi")
    except Exception as e:
        print_error_page(f"予期せぬエラーが発生しました: {str(e)}", "top.cgi")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    main()
