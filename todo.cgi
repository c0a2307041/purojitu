#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import cgitb
import mysql.connector
import html

# エラー表示を有効にする
cgitb.enable()

# --- 設定 ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'user1',
    'passwd': 'passwordA1!',
    'db': 'Free',
    'charset': 'utf8'
}
# ログイン機能を省略し、ユーザーID=1で固定
CURRENT_USER_ID = 1

# --- データベース関連の関数 ---

def get_db_connection():
    """データベース接続を取得する"""
    return mysql.connector.connect(**DB_CONFIG)

def get_awaiting_shipment_items(cursor, user_id):
    """発送待ちの商品リストを、商品IDと共に取得"""
    query = """
        SELECT i.item_id, i.title, i.price, u.username as buyer_name
        FROM purchases p
        JOIN items i ON p.item_id = i.item_id
        JOIN users u ON p.buyer_id = u.user_id
        WHERE i.user_id = %s AND p.status = 'shipping_pending'
        ORDER BY p.purchased_at ASC;
    """
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def get_awaiting_review_items(cursor, user_id):
    """評価待ちの商品リストを、商品IDと共に取得"""
    query = """
        SELECT i.item_id, i.title, i.price, u.username as seller_name
        FROM purchases p
        JOIN items i ON p.item_id = i.item_id
        JOIN users u ON i.user_id = u.user_id
        LEFT JOIN reviews r ON p.item_id = r.item_id AND r.reviewer_id = p.buyer_id
        WHERE p.buyer_id = %s AND p.status = 'completed' AND r.review_id IS NULL
        ORDER BY p.purchased_at DESC;
    """
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

# --- HTML生成の関数 ---

def generate_todo_html(items, action_text, is_linkable=False):
    """やることリストのHTMLを生成"""
    if not items:
        return "<li>対象の商品はありません。</li>"
    
    html_parts = []
    for item in items:
        item_id, title, price, partner_name = item
        safe_title = html.escape(title)
        safe_partner = html.escape(partner_name)
        formatted_price = f"¥{price:,}"
        
        # リンクが必要なリスト項目の情報を包むdiv
        item_info_html = f"""
            <div class="item-info">
                <span class="item-title">{safe_title}</span>
                <span class="item-meta">{formatted_price} / 取引相手: {safe_partner}さん</span>
            </div>
        """

        # is_linkableがTrueの場合、詳細ページへのリンクを追加
        if is_linkable:
            list_item_content = f'<a href="item_detail.cgi?item_id={item_id}" class="item-link">{item_info_html}</a>'
        else:
            list_item_content = item_info_html

        html_parts.append(f"""
        <li class="todo-detail-item">
            {list_item_content}
            <a href="#" class="btn btn-action">{action_text}</a>
        </li>
        """)
    return "".join(html_parts)

# --- メイン処理 ---

def main():
    """CGIスクリプトのメイン処理"""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # DBから各リストのデータを取得
        awaiting_shipment = get_awaiting_shipment_items(cursor, CURRENT_USER_ID)
        awaiting_review = get_awaiting_review_items(cursor, CURRENT_USER_ID)
        
        # HTML部品を生成
        shipment_html = generate_todo_html(awaiting_shipment, "発送を通知する", is_linkable=True)
        review_html = generate_todo_html(awaiting_review, "レビューを投稿する")

        # CGIヘッダーを出力
        print("Content-Type: text/html; charset=utf-8\n")
        
        # ページ全体のHTMLを出力
        print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>やることリスト - フリマ</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 20px; }}
        header {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 1rem; border-radius: 20px; margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-size: 2rem; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; }}
        .btn-secondary {{ background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); }}
        .btn-action {{ background: linear-gradient(45deg, #ff6b6b, #ff8e8e); color: white; font-size: 0.9rem; padding: 0.5rem 1rem; }}
        .section {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin-bottom: 2rem; }}
        .section-title {{ font-size: 1.8rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); margin-bottom: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 0.5rem; }}
        .todo-detail-list {{ list-style: none; padding: 0; }}
        .todo-detail-item {{ display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.2); }}
        .todo-detail-item:last-child {{ border-bottom: none; }}
        .item-link {{ text-decoration: none; color: white; flex-grow: 1; }}
        .item-info {{ flex-grow: 1; }}
        .item-title {{ display: block; font-weight: bold; margin-bottom: 0.25rem; }}
        .item-meta {{ font-size: 0.9rem; opacity: 0.8; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">🛍️ やることリスト</div>
            <a href="account.cgi" class="btn btn-secondary">アカウントページに戻る</a>
        </header>

        <main>
            <section class="section">
                <h2 class="section-title">📦 発送待ちの商品</h2>
                <ul class="todo-detail-list">
                    {shipment_html}
                </ul>
            </section>

            <section class="section">
                <h2 class="section-title">⭐ 評価待ちの取引</h2>
                <ul class="todo-detail-list">
                    {review_html}
                </ul>
            </section>
        </main>
    </div>
</body>
</html>
        """)
    except mysql.connector.Error as err:
        print("Content-Type: text/html\n\n<h1>Database Error</h1><p>" + html.escape(str(err)) + "</p>")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    main()
