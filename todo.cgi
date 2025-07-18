#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import cgitb
import mysql.connector
import html

cgitb.enable()

DB_CONFIG = {
    'host': 'localhost', 'user': 'user1', 'passwd': 'passwordA1!',
    'db': 'Free', 'charset': 'utf8'
}
CURRENT_USER_ID = 1

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def get_awaiting_shipment_items(cursor, user_id):
    """発送待ちの商品リストを取得"""
    query = "SELECT p.purchase_id, i.item_id, i.title, i.price, u.username as partner_name FROM purchases p JOIN items i ON p.item_id = i.item_id JOIN users u ON p.buyer_id = u.user_id WHERE i.user_id = %s AND p.status = 'shipping_pending' ORDER BY p.purchased_at ASC;"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def get_awaiting_my_review_items(cursor, user_id):
    """自分が購入者で、評価待ちの商品リストを取得"""
    query = "SELECT p.purchase_id, i.item_id, i.title, i.price, u.username as partner_name FROM purchases p JOIN items i ON p.item_id = i.item_id JOIN users u ON i.user_id = u.user_id LEFT JOIN reviews r ON p.item_id = r.item_id AND r.reviewer_id = p.buyer_id WHERE p.buyer_id = %s AND p.status = 'shipped' AND r.review_id IS NULL ORDER BY p.purchased_at DESC;"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

# ▼▼▼ 追加 ▼▼▼
def get_awaiting_buyer_review_items(cursor, user_id):
    """自分が出品者で、購入者の評価待ちリストを取得"""
    query = """
        SELECT p.purchase_id, i.item_id, i.title, i.price, u.username as partner_name
        FROM purchases p
        JOIN items i ON p.item_id = i.item_id
        JOIN users u ON p.buyer_id = u.user_id
        -- 自分(出品者)からのレビューがまだ存在しないことを確認
        LEFT JOIN reviews r ON p.item_id = r.item_id AND r.reviewer_id = i.user_id
        WHERE
            i.user_id = %s
            AND p.status = 'completed'
            AND r.review_id IS NULL
        ORDER BY p.purchased_at DESC;
    """
    cursor.execute(query, (user_id,))
    return cursor.fetchall()
# ▲▲▲ 追加 ▲▲▲

def generate_todo_html(items, button_text, button_link_base):
    if not items:
        return "<li>対象の取引はありません。</li>"
    html_parts = []
    for item in items:
        purchase_id, item_id, title, price, partner_name = item
        action_link = f"{button_link_base}?purchase_id={purchase_id}"
        html_parts.append(f'<li class="todo-detail-item"><a href="item_detail.cgi?item_id={item_id}" class="item-link"><div class="item-info"><span class="item-title">{html.escape(title)}</span><span class="item-meta">¥{price:,} / 取引相手: {html.escape(partner_name)}さん</span></div></a><a href="{action_link}" class="btn-action">{button_text}</a></li>')
    return "".join(html_parts)

def main():
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # 各リストのデータを取得
        awaiting_shipment = get_awaiting_shipment_items(cursor, CURRENT_USER_ID)
        awaiting_my_review = get_awaiting_my_review_items(cursor, CURRENT_USER_ID)
        # ▼▼▼ 追加 ▼▼▼
        awaiting_buyer_review = get_awaiting_buyer_review_items(cursor, CURRENT_USER_ID)
        
        # HTML部品を生成
        shipment_html = generate_todo_html(awaiting_shipment, "取引画面へ", "trade.cgi")
        my_review_html = generate_todo_html(awaiting_my_review, "評価する", "trade.cgi")
        # ▼▼▼ 追加 ▼▼▼
        buyer_review_html = generate_todo_html(awaiting_buyer_review, "購入者を評価", "trade.cgi")

        print("Content-Type: text/html; charset=utf-8\n")
        print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8"><title>やることリスト - フリマ</title>
    <style>
        body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); min-height:100vh; color:white; }}
        .container {{ max-width:900px; margin:0 auto; padding:20px; }}
        header {{ background:rgba(255,255,255,0.1); backdrop-filter:blur(10px); padding:1rem; border-radius:20px; margin-bottom:2rem; display:flex; justify-content:space-between; align-items:center; }}
        .logo {{ font-size:2rem; font-weight:bold; }}
        .btn-secondary {{ background:rgba(255,255,255,0.2); color:white; padding:0.7rem 1.5rem; border-radius:25px; text-decoration:none; }}
        .btn-action {{ background:linear-gradient(45deg,#ff6b6b,#ff8e8e); color:white; font-size:0.9rem; padding:0.5rem 1rem; border-radius:25px; text-decoration:none; }}
        .section {{ background:rgba(255,255,255,0.1); backdrop-filter:blur(10px); border-radius:20px; padding:2rem; margin-bottom:2rem; }}
        .section-title {{ font-size:1.8rem; margin-bottom:1.5rem; border-bottom:1px solid rgba(255,255,255,0.2); padding-bottom:0.5rem; }}
        .todo-detail-list {{ list-style:none; padding:0; }}
        .todo-detail-item {{ display:flex; justify-content:space-between; align-items:center; padding:1rem; border-bottom:1px solid rgba(255,255,255,0.2); }}
        .todo-detail-item:last-child {{ border-bottom:none; }}
        .item-link {{ text-decoration:none; color:white; flex-grow:1; }}
        .item-info {{ flex-grow:1; }} .item-title {{ display:block; font-weight:bold; }} .item-meta {{ font-size:0.9rem; opacity:0.8; }}
    </style>
</head>
<body>
    <div class="container">
        <header><div class="logo">🛍️ やることリスト</div><a href="account.cgi" class="btn-secondary">アカウントページに戻る</a></header>
        <main>
            <section class="section"><h2 class="section-title">📦 発送待ちの商品</h2><ul class="todo-detail-list">{shipment_html}</ul></section>
            <section class="section"><h2 class="section-title">⭐ 評価が必要な取引</h2><ul class="todo-detail-list">{my_review_html}</ul></section>
            {f'<section class="section"><h2 class="section-title">👥 購入者の評価</h2><ul class="todo-detail-list">{buyer_review_html}</ul></section>' if awaiting_buyer_review else ''}
        </main>
    </div>
</body>
</html>""")
    except Exception as e:
        print("Content-Type: text/html\n\n<h1>エラーが発生しました</h1><p>" + html.escape(str(e)) + "</p>")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    main()
