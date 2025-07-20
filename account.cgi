#!/usr/bin/python3
# -*- coding: utf-8 -*-

import cgi
import cgitb
import mysql.connector
import html
import os
from http import cookies
from datetime import datetime

# エラー表示を有効にする
cgitb.enable()

# --- 設定 ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'user1',
    'passwd': 'passwordA1!',
    'db': 'Free',  # 指定されたデータベース
    'charset': 'utf8'
}
# 今回はログイン機能を省略し、ユーザーID=1の人で固定
# CURRENT_USER_ID は認証後に実際のユーザーIDが設定されます

# --- データベース関連の関数 ---

def get_db_connection():
    """データベース接続を取得する"""
    return mysql.connector.connect(**DB_CONFIG)

def get_user_info(cursor, user_id):
    """ユーザー情報を取得する"""
    query = "SELECT username FROM users WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    return result[0] if result else "ゲスト"
    
def get_todo_counts(cursor, user_id):
    """やることリストの件数を取得する"""
    counts = {'shipping': 0, 'review': 0}
    
    # 発送待ちの件数を取得
    shipping_query = """
        SELECT COUNT(*) FROM purchases p
        JOIN items i ON p.item_id = i.item_id
        WHERE i.user_id = %s AND p.status = 'shipping_pending'
    """
    cursor.execute(shipping_query, (user_id,))
    counts['shipping'] = cursor.fetchone()[0]

    # 評価待ちの件数を取得
    review_query = """
        SELECT COUNT(*) FROM purchases p
        LEFT JOIN user_reviews r ON p.item_id = r.item_id AND r.reviewer_id = p.buyer_id
        WHERE p.buyer_id = %s AND p.status = 'completed' AND r.review_id IS NULL
    """
    cursor.execute(review_query, (user_id,))
    counts['review'] = cursor.fetchone()[0]
    
    return counts

def get_listed_items(cursor, user_id):
    """指定されたユーザーの出品履歴と販売状況を取得する"""
    # LEFT JOINを使って、購入されているかどうかを判定
    query = """
        SELECT
            i.title,
            i.price,
            i.image_path,
            (CASE WHEN p.purchase_id IS NOT NULL THEN 'sold' ELSE 'selling' END) as status
        FROM items AS i
        LEFT JOIN purchases AS p ON i.item_id = p.item_id
        WHERE i.user_id = %s
        ORDER BY i.created_at DESC;
    """
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def get_purchased_items(cursor, user_id):
    """指定されたユーザーの購入履歴を取得する"""
    query = """
        SELECT i.title, i.price, i.image_path
        FROM purchases AS p
        JOIN items AS i ON p.item_id = i.item_id
        WHERE p.buyer_id = %s
        ORDER BY p.purchased_at DESC;
    """
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def validate_session(cursor, session_id):
    """セッションIDを検証し、対応するユーザーIDを返す"""
    query = "SELECT user_id FROM sessions WHERE session_id = %s AND expires_at > NOW()"
    cursor.execute(query, (session_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# --- HTML生成の関数 ---

def generate_todo_list_html(counts):
    """やることリストのHTMLリスト部分を生成する"""
    html_parts = []
    
    # 発送待ちがあればリスト項目を追加
    if counts.get('shipping', 0) > 0:
        html_parts.append(f"""
        <li class="todo-item">
            <div class="todo-icon">📦</div>
            <div class="todo-text">発送待ちの商品があります</div>
            <span class="todo-badge">{counts['shipping']}</span>
        </li>
        """)

    # 評価待ちがあればリスト項目を追加
    if counts.get('review', 0) > 0:
        html_parts.append(f"""
        <li class="todo-item">
            <div class="todo-icon">⭐</div>
            <div class="todo-text">評価待ちの取引があります</div>
            <span class="todo-badge">{counts['review']}</span>
        </li>
        """)

    if not html_parts:
        return '<li class="todo-item"><div class="todo-text">現在、やることはありません。</div></li>'
        
    return "".join(html_parts)

def generate_listed_items_html(items):
    """出品履歴のHTMLを生成する"""
    html_parts = []
    for item in items:
        title, price, image_path, status = item
        status_class = "status-sold" if status == 'sold' else "status-selling"
        status_text = "売り切れ" if status == 'sold' else "出品中"
        
        # XSS対策のため、表示するデータはHTMLエスケープする
        safe_title = html.escape(title)
        
        # ★ ここを修正: image_path があれば <img> タグを生成し、なければデフォルト画像を表示
        display_image_path = html.escape(image_path) if image_path else "/purojitu/images/noimage.png"
        image_tag = f'<img src="{display_image_path}" alt="{safe_title}">'

        formatted_price = f"¥{price:,}"

        html_parts.append(f"""
        <div class="product-card">
            <div class="product-status {status_class}">{status_text}</div>
            <div class="product-image">{image_tag}</div>
            <div class="product-info">
                <div class="product-title">{safe_title}</div>
                <div class="product-price">{formatted_price}</div>
            </div>
        </div>
        """)
    return "".join(html_parts)

def generate_purchased_items_html(items):
    """購入履歴のHTMLを生成する"""
    html_parts = []
    for item in items:
        title, price, image_path = item
        safe_title = html.escape(title)
        
        # ★ ここを修正: image_path があれば <img> タグを生成し、なければデフォルト画像を表示
        display_image_path = html.escape(image_path) if image_path else "/purojitu/images/noimage.png"
        image_tag = f'<img src="{display_image_path}" alt="{safe_title}">'

        formatted_price = f"¥{price:,}"

        html_parts.append(f"""
        <div class="product-card">
            <div class="product-image">{image_tag}</div>
            <div class="product-info">
                <div class="product-title">{safe_title}</div>
                <div class="product-price">{formatted_price}</div>
            </div>
        </div>
        """)
    return "".join(html_parts)

# --- メイン処理 ---
def main():
    """CGIスクリプトのメイン処理"""
    connection = None
    CURRENT_USER_ID = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # クッキーからセッションIDを取得
        sid_cookie = cookies.SimpleCookie(os.environ.get("HTTP_COOKIE"))
        session_id = None
        if "session_id" in sid_cookie:
            session_id = sid_cookie["session_id"].value
        
        # セッションIDを検証
        if session_id:
            CURRENT_USER_ID = validate_session(cursor, session_id)

        # セッションが無効、またはユーザーIDが取得できない場合はリダイレクト
        if not CURRENT_USER_ID:
            print("Status: 302 Found")
            print("Location: login.html\n")
            return

        # データベースから情報を取得
        user_name = get_user_info(cursor, CURRENT_USER_ID)
        listed_items = get_listed_items(cursor, CURRENT_USER_ID)
        purchased_items = get_purchased_items(cursor, CURRENT_USER_ID)
        
        todo_counts = get_todo_counts(cursor, CURRENT_USER_ID)
        todo_list_html = generate_todo_list_html(todo_counts)

        # HTML部品を生成
        listed_items_html = generate_listed_items_html(listed_items)
        purchased_items_html = generate_purchased_items_html(purchased_items)

        # CGIヘッダーを出力
        print("Content-Type: text/html; charset=utf-8\n")
        
        # メインのHTMLテンプレートに取得したデータを埋め込む
        print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>アカウントページ - フリマ</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 20px; }}
        header {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 1rem 0; position: sticky; top: 0; z-index: 100; }}
        .header-content {{ display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-size: 2rem; font-weight: bold; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .nav-buttons {{ display: flex; gap: 1rem; }}
        .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }}
        .btn-primary {{ background: linear-gradient(45deg, #ff6b6b, #ff8e8e); color: white; box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4); }}
        .btn-secondary {{ background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }}
        .section-title {{ text-align: center; font-size: 2rem; color: white; margin-bottom: 2rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .products-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 2rem; margin-top: 2rem; }}
        .product-card {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; overflow: hidden; transition: all 0.3s ease; border: 1px solid rgba(255, 255, 255, 0.2); position: relative; }}
        .product-card:hover {{ transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
        /* product-imageに背景色や文字サイズは不要になり、imgタグにフィットするように修正 */
        .product-image {{ width: 100%; height: 200px; display: flex; align-items: center; justify-content: center; overflow: hidden; border-radius: 20px 20px 0 0; }}
        .product-image img {{ width: 100%; height: 100%; object-fit: cover; }} /* imgタグが親要素にフィットするように設定 */

        .product-info {{ padding: 1.5rem; color: white; }}
        .product-title {{ font-size: 1.1rem; font-weight: bold; margin-bottom: 0.5rem; }}
        .product-price {{ font-size: 1.3rem; font-weight: bold; color: #ff6b6b; margin-bottom: 0.5rem; }}
        .product-status {{ position: absolute; top: 15px; left: 15px; padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.8rem; font-weight: 600; color: white; }}
        .status-selling {{ background: rgba(255, 107, 107, 0.8); }}
        .status-sold {{ background: rgba(100, 100, 100, 0.8); }}
        footer {{ background: rgba(0, 0, 0, 0.2); backdrop-filter: blur(10px); color: white; text-align: center; padding: 2rem 0; margin-top: 3rem; }}
        .account-header {{ text-align: center; padding: 3rem 0; }}
        .account-header h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .account-header p {{ font-size: 1.2rem; opacity: 0.9; }}
        .todo-section {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin: 2rem 0; border: 1px solid rgba(255, 255, 255, 0.2); }}
        .todo-list {{ list-style: none; padding: 0; }}
        .todo-item {{ display: flex; align-items: center; padding: 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.2); transition: background 0.3s; }}
        .todo-item:last-child {{ border-bottom: none; }}
        .todo-item:hover {{ background: rgba(255, 255, 255, 0.1); }}
        .todo-icon {{ font-size: 1.5rem; margin-right: 1.5rem; width: 40px; text-align: center; }}
        .todo-text {{ flex: 1; font-size: 1.1rem; }}
        .todo-badge {{ background-color: #ff6b6b; color: white; padding: 0.2rem 0.6rem; border-radius: 10px; font-size: 0.9rem; font-weight: 600; }}
        @media (max-width: 768px) {{
            .account-header h1 {{ font-size: 2rem; }}
            .header-content {{ flex-direction: column; gap: 1rem; }}
        }}
        
        /* ▼▼▼ 追加 ▼▼▼ */
        .clickable-section {{
            display: block;
            text-decoration: none;
            color: white;
            transition: transform 0.2s ease-in-out;
        }}
        .clickable-section:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        /* ▲▲▲ 追加 ▲▲▲ */
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div class="logo">🛍️ メル仮</div>
                <div class="nav-buttons">
                    <a href="top.cgi" class="btn btn-secondary">トップページへ</a>
                    <a href="logout.cgi" class="btn btn-primary">ログアウト</a>
                </div>
            </div>
        </div>
    </header>
    <main>
        <div class="container">
            <section class="account-header">
                <h1>アカウントページ</h1>
                <p>ようこそ、{html.escape(user_name)}さん</p>
            </section>
            <a href="todo.cgi" class="clickable-section">
                <section class="todo-section">
                    <h2 class="section-title" style="margin-bottom: 1.5rem;">やることリスト</h2>
                    <ul class="todo-list">
                        {todo_list_html}
                    </ul>
                </section>
            </a>
            <section class="history-section">
                <h2 class="section-title">出品した商品</h2>
                <div class="products-grid">
                    {listed_items_html}
                </div>
            </section>
            <section class="history-section" style="margin-top: 4rem;">
                <h2 class="section-title">購入した商品</h2>
                <div class="products-grid">
                    {purchased_items_html}
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
        # エラー発生時の処理
        print("Content-Type: text/html; charset=utf-8\n")
        print("<h1>データベースエラー</h1>")
        print(f"<p>エラーが発生しました: {html.escape(str(err))}</p>")
    finally:
        # 確実に接続を閉じる
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    main()
