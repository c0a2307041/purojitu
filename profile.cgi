#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import cgitb
import mysql.connector
import html
from datetime import datetime

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

# --- データベース関連の関数 ---
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def get_user_info(cursor, user_id):
    query = """
        SELECT u.user_id, u.username, u.created_at, a.prefecture, a.city
        FROM users u
        LEFT JOIN addresses a ON u.address_id = a.address_id
        WHERE u.user_id = %s
    """
    cursor.execute(query, (user_id,))
    return cursor.fetchone()

def get_items_for_sale(cursor, user_id):
    query = """
        SELECT i.item_id, i.title, i.description, i.price, i.image_path, i.created_at
        FROM items i
        LEFT JOIN purchases p ON i.item_id = p.item_id
        WHERE i.user_id = %s AND p.purchase_id IS NULL
        ORDER BY i.created_at DESC
    """
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def get_sold_items(cursor, user_id):
    query = """
        SELECT i.item_id, i.title, i.price, i.image_path, p.purchased_at, u.username as buyer_name
        FROM items i
        JOIN purchases p ON i.item_id = p.item_id
        JOIN users u ON p.buyer_id = u.user_id
        WHERE i.user_id = %s
        ORDER BY p.purchased_at DESC
    """
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def get_received_reviews(cursor, user_id):
    # 'user_reviews' テーブルを使用
    query = """
        SELECT ur.content, ur.created_at, u.username as reviewer_name, i.title as item_title
        FROM user_reviews ur
        JOIN items i ON ur.item_id = i.item_id
        JOIN users u ON ur.reviewer_id = u.user_id
        WHERE ur.reviewee_id = %s
        ORDER BY ur.created_at DESC
    """
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

# --- ヘルパー関数 ---
def format_date(dt):
    if not dt or not isinstance(dt, datetime):
        return '未設定'
    return dt.strftime('%Y年%m月%d日')

def format_price(price):
    if price is None:
        return '価格未設定'
    return f"¥{price:,}"

# --- HTML生成の関数 ---
def print_error_page(message):
    print("Content-Type: text/html; charset=utf-8\n")
    print(f"""
    <!DOCTYPE html><html lang="ja"><head><title>エラー</title><style>
    body{{font-family:-apple-system,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);display:flex;align-items:center;justify-content:center;color:white;text-align:center;}}
    .error-container{{background:rgba(255,255,255,0.1);backdrop-filter:blur(10px);border-radius:20px;padding:40px;}}
    </style></head><body><div class="error-container"><h1>エラー</h1><p>{html.escape(message)}</p></div></body></html>
    """)

def main():
    form = cgi.FieldStorage()
    user_id = form.getfirst('user_id')

    if not user_id or not user_id.isdigit():
        print_error_page("無効なユーザーIDです。")
        return

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        user_info = get_user_info(cursor, user_id)
        if not user_info:
            print_error_page("指定されたユーザーが見つかりません。")
            return

        uid, username, created_at, prefecture, city = user_info
        items_for_sale = get_items_for_sale(cursor, user_id)
        sold_items = get_sold_items(cursor, user_id)
        reviews = get_received_reviews(cursor, user_id)

        # HTML生成
        items_for_sale_html = ""
        if items_for_sale:
            for item in items_for_sale:
                item_id, title, desc, price, img, date = item
                items_for_sale_html += f"""
                <div class="product-card" onclick="location.href='item_detail.cgi?item_id={item_id}'">
                    <div class="product-image"><img src="{html.escape(str(img or ''))}" alt="{html.escape(title)}" onerror="this.parentElement.innerHTML='🛍️'"></div>
                    <div class="product-info">
                        <div class="product-title">{html.escape(title)}</div>
                        <div class="product-price">{format_price(price)}</div>
                    </div>
                </div>"""
        else:
            items_for_sale_html = "<div class='empty-state'>現在出品中の商品はありません。</div>"

        sold_items_html = ""
        if sold_items:
            for item in sold_items:
                item_id, title, price, img, date, buyer = item
                sold_items_html += f"""
                <div class="product-card">
                    <div class="product-image"><img src="{html.escape(str(img or ''))}" alt="{html.escape(title)}" onerror="this.parentElement.innerHTML='✅'"></div>
                    <div class="product-info">
                        <div class="product-title">{html.escape(title)}</div>
                        <div class="product-price">{format_price(price)}</div>
                        <div class="product-meta"><span>購入者: {html.escape(buyer)}</span></div>
                    </div>
                </div>"""
        else:
            sold_items_html = "<div class='empty-state'>売却済みの商品はありません。</div>"

        reviews_html = ""
        if reviews:
            for review in reviews:
                content, date, reviewer, item_title = review
                reviews_html += f"""
                <div class="review-card">
                    <div class="review-header"><strong>⭐ {html.escape(reviewer)}さんからのレビュー</strong></div>
                    <div class="review-content">{html.escape(content)}</div>
                    <div class="review-meta">商品: {html.escape(item_title)}</div>
                </div>"""
        else:
            reviews_html = "<div class='empty-state'>まだレビューがありません。</div>"

        print("Content-Type: text/html; charset=utf-8\n")
        print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(username)}さんのページ</title>
    <style>
        body {{ font-family:-apple-system,sans-serif; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:white; }}
        .container {{ max-width:1200px; margin:0 auto; padding:0 20px; }}
        header {{ background:rgba(255,255,255,0.1); backdrop-filter:blur(10px); padding:1rem 0; position:sticky; top:0; z-index:100; }}
        .header-content {{ display:flex; justify-content:space-between; align-items:center; }}
        .logo {{ font-size:2rem; font-weight:bold; }}
        .hero {{ text-align:center; padding:3rem 0; }}
        .profile-section, .stats {{ background:rgba(255,255,255,0.1); backdrop-filter:blur(10px); border-radius:20px; padding:2rem; margin:2rem 0; }}
        .stats {{ display:flex; justify-content:space-around; }}
        .stat-item {{ text-align:center; }} .stat-number {{ font-size:2.5rem; font-weight:bold; display:block; }}
        .section-title {{ text-align:center; font-size:2rem; margin:2rem 0; padding-top:1rem; }}
        .products-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:2rem; }}
        .product-card {{ background:rgba(255,255,255,0.1); backdrop-filter:blur(10px); border-radius:20px; overflow:hidden; cursor:pointer; }}
        .product-image {{ width:100%; height:200px; display:flex; align-items:center; justify-content:center; font-size:3rem; }}
        .product-image img {{ width:100%; height:100%; object-fit:cover; }}
        .product-info {{ padding:1.5rem; }} .product-title {{ font-weight:bold; }} .product-price {{ font-size:1.3rem; color:#ff6b6b; }}
        .product-meta {{ font-size:0.9rem; opacity:0.8; }}
        .review-card {{ background:rgba(0,0,0,0.2); border-radius:15px; padding:1.5rem; margin-bottom:1.5rem; }}
        .review-header {{ font-weight:bold; }} .review-content {{ line-height:1.6; margin:1rem 0; }} .review-meta {{ opacity:0.8; text-align:right; }}
        .empty-state {{ text-align:center; opacity:0.8; padding:2rem; }}
    </style>
</head>
<body>
    <header><div class="container header-content"><div class="logo">🛍️ メル仮</div></div></header>
    <main class="container">
        <section class="hero"><h1>{html.escape(username)}さんのページ</h1></section>
        <section class="stats">
            <div class="stat-item"><span class="stat-number">{len(items_for_sale)}</span><span>出品中</span></div>
            <div class="stat-item"><span class="stat-number">{len(sold_items)}</span><span>売却済み</span></div>
            <div class="stat-item"><span class="stat-number">{len(reviews)}</span><span>レビュー</span></div>
        </section>
        <section><h2 class="section-title">出品中の商品</h2><div class="products-grid">{items_for_sale_html}</div></section>
        <section><h2 class="section-title">売却済み商品</h2><div class="products-grid">{sold_items_html}</div></section>
        <section><h2 class="section-title">受け取った評価</h2><div>{reviews_html}</div></section>
    </main>
</body>
</html>""")
    except Exception as e:
        print_error_page(str(e))
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    main()
