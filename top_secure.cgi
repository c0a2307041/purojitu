#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# print("Content-Type: text/html; charset=utf-8\n")

import cgi
import cgitb # エラー表示のために追加
import mysql.connector
import html
import os
from http import cookies
from datetime import datetime # セッションの期限切れチェックのため追加

# エラー表示を有効にする
cgitb.enable()

# DB接続情報
DB_CONFIG = {
    'host': 'localhost',
    'user': 'user1',
    'passwd': 'passwordA1!',
    'db': 'Free',
    'charset': 'utf8'
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def get_user_info(cursor, user_id):
    query = "SELECT username FROM users WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    return result['username'] if result else "ゲスト"

def validate_session(cursor, session_id):
    query = "SELECT user_id FROM sessions WHERE session_id = %s AND expires_at > NOW()"
    cursor.execute(query, (session_id,))
    result = cursor.fetchone()
    return result['user_id'] if result else None

def main():
    connection = None
    user_id = None
    user_name = "ゲスト"

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sid_cookie = cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
        session_id = None
        cookie_user_id = None

        if "session_id" in sid_cookie and "user_id" in sid_cookie:
            session_id = sid_cookie["session_id"].value
            cookie_user_id = sid_cookie["user_id"].value

            # セッションテーブルで正当性を検証
            valid_user_id = validate_session(cursor, session_id)

            # セッションが無効 or クッキーのuser_idとセッションテーブルのuser_idが不一致
            if not valid_user_id or str(valid_user_id) != cookie_user_id:
                print("Status: 302 Found")
                print("Location: login.html")
                print()
                return

            user_id = valid_user_id
            user_name = get_user_info(cursor, user_id)
        else:
            # クッキーに必要な情報がない場合もログインページへ
            print("Status: 302 Found")
            print("Location: login.html")
            print()
            return

        print("Content-Type: text/html; charset=utf-8\n")

        form = cgi.FieldStorage()
        search_query = form.getfirst("search", "").strip()

        # SQLクエリの基本形（購入されていない商品のみ）
        base_sql = """
            SELECT i.item_id, i.title, i.price, i.image_path
            FROM items AS i
            LEFT JOIN purchases AS p ON i.item_id = p.item_id
            WHERE p.purchase_id IS NULL -- ここが変更点: 購入されていない商品のみ
        """
        params = []

        if search_query:
            sql = base_sql + " AND i.title LIKE %s"
            params.append(f"%{search_query}%")
            if user_id:
                sql += " AND i.user_id != %s"
                params.append(user_id)
            sql += " ORDER BY i.created_at DESC"
            cursor.execute(sql, tuple(params))
            items = cursor.fetchall()
            section_title = f'検索結果: 「{html.escape(search_query)}」'
        else:
            sql = base_sql
            if user_id:
                sql += " AND i.user_id != %s"
                params.append(user_id)
            sql += " ORDER BY i.created_at DESC"
            cursor.execute(sql, tuple(params))
            items = cursor.fetchall()
            section_title = "新着商品"

        products_html = []
        for item in items:
            title = html.escape(item['title'])
            price = item['price']
            item_id = item['item_id']
            image_path = html.escape(item['image_path']) if item['image_path'] else "/purojitu/images/noimage.png"
            formatted_price = f"¥{price:,}"

            products_html.append(f"""
            <a href="item_detail.cgi?item_id={item_id}" class="product-card">
                <div class="product-image">
                    <img src="{image_path}" alt="{title}">
                </div>
                <div class="product-info">
                    <div class="product-title">{title}</div>
                    <div class="product-price">{formatted_price}</div>
                </div>
            </a>
            """)

        if not products_html:
            products_html.append('<p class="no-items-message">該当する商品はありません。</p>')

        print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>フリマアプリ - トップページ</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 0 20px; }}
    header {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 1rem 0; position: sticky; top: 0; z-index: 100; }}
    .header-content {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; }}
    .logo {{ font-size: 2rem; font-weight: bold; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
    .nav-buttons {{ display: flex; gap: 1rem; }}
    .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }}
    .btn-primary {{ background: linear-gradient(45deg, #ff6b6b, #ff8e8e); color: white; box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4); }}
    .btn-secondary {{ background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); }}
    .btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }}
    .section-title {{ text-align: center; font-size: 2rem; color: white; margin-bottom: 2rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
    .products-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 2rem; margin-top: 2rem; }}
    .product-card {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; overflow: hidden; transition: all 0.3s ease; border: 1px solid rgba(255, 255, 255, 0.2); position: relative; display: block; text-decoration: none; color: inherit; }}
    .product-card:hover {{ transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
    .product-image {{ width: 100%; height: 200px; background: linear-gradient(45deg, #ff9a9e, #fecfef); display: flex; align-items: center; justify-content: center; overflow: hidden; border-radius: 20px 20px 0 0;}}
    .product-image img {{ width: 100%; height: 100%; object-fit: cover; }}
    .product-info {{ padding: 1.5rem; color: white; }}
    .product-title {{ font-size: 1.1rem; font-weight: bold; margin-bottom: 0.5rem; }}
    .product-price {{ font-size: 1.3rem; font-weight: bold; color: #ff6b6b; margin-bottom: 0.5rem; }}
    footer {{ background: rgba(0, 0, 0, 0.2); backdrop-filter: blur(10px); color: white; text-align: center; padding: 2rem 0; margin-top: 3rem; }}
    .top-header {{ text-align: center; padding: 3rem 0 1rem 0; }}
    .top-header p {{ font-size: 1.5rem; opacity: 0.9; }}
    .no-items-message {{ text-align: center; padding: 50px; font-size: 1.2rem; opacity: 0.8; }}
    form.search-form {{
        display: flex;
        gap: 0.5rem;
    }}
    form.search-form input[type="text"] {{
        flex: 1;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        border: none;
        font-size: 1rem;
    }}
    form.search-form button {{
        padding: 0 1.5rem;
        border: none;
        border-radius: 25px;
        background: linear-gradient(45deg, #ff6b6b, #ff8e8e);
        color: white;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }}
    form.search-form button:hover {{
        filter: brightness(1.1);
    }}
    @media (max-width: 768px) {{
        .header-content {{
            flex-direction: column;
            align-items: stretch;
        }}
        form.search-form {{
            width: 100%;
        }}
    }}
</style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div class="logo"><a href="top_secure.cgi" style="text-decoration: none; color: white;">🛍️ メル仮</a></div>

                <form method="get" class="search-form" action="top_secure.cgi" style="flex:1; max-width:400px;">
                    <input type="text" name="search" placeholder="商品名で検索" value="{html.escape(search_query)}" autocomplete="off" />
                    <button type="submit">検索</button>
                </form>

                <div class="nav-buttons">
                    <a href="account.cgi" class="btn btn-secondary">マイページ</a>
                    <a href="exhibition.cgi" class="btn btn-primary">出品する</a>
                </div>
            </div>
        </div>
    </header>

    <main>
        <div class="container">
            <section class="top-header">
                <h1>ようこそ、{html.escape(user_name)}さん！</h1>
            </section>
            <section class="products-section">
                <h2 class="section-title">{section_title}</h2>
                <div class="products-grid">
                    {''.join(products_html)}
                </div>
            </section>
        </div>
    </main>
    <footer>
        <div class="container">
            <p>&copy; 2025 フリマ. All rights reserved. | 利用規約 | プライバシーポリシー</p>
        </div>
    </footer>
</body>
</html>
        """)
    except mysql.connector.Error as err:
        print("Content-Type: text/html; charset=utf-8\n")
        print("<h1>データベースエラー</h1>")
        print(f"<p>エラーが発生しました: {html.escape(str(err))}</p>")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    main()
