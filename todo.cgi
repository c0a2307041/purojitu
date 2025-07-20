#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import cgitb
import mysql.connector
import html
import os # 環境変数 (HTTP_COOKIE) を取得するために必要
from http import cookies # クッキーを扱うために必要
from datetime import datetime # セッションの期限切れチェックのため必要

cgitb.enable()

DB_CONFIG = {
    'host': 'localhost', 'user': 'user1', 'passwd': 'passwordA1!',
    'db': 'Free', 'charset': 'utf8'
}
# CURRENT_USER_ID は認証後に動的に設定されるため、ここでは削除

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# top.cgi から持ってきたセッション検証関数
def validate_session(cursor, session_id):
    query = "SELECT user_id FROM sessions WHERE session_id = %s AND expires_at > NOW()"
    cursor.execute(query, (session_id,))
    result = cursor.fetchone()
    return result['user_id'] if result else None

# top.cgi から持ってきたユーザー情報取得関数 (辞書カーソルに対応)
def get_user_info(cursor, user_id):
    query = "SELECT username FROM users WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    return result['username'] if result else "ゲスト"


def get_awaiting_shipment_items(cursor, user_id):
    """発送待ちの商品リストを取得"""
    query = "SELECT p.purchase_id, i.item_id, i.title, i.price, u.username as partner_name FROM purchases p JOIN items i ON p.item_id = i.item_id JOIN users u ON p.buyer_id = u.user_id WHERE i.user_id = %s AND p.status = 'shipping_pending' ORDER BY p.purchased_at ASC;"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def get_awaiting_my_review_items(cursor, user_id):
    """自分が購入者で、評価待ちの商品リストを取得"""
    query = "SELECT p.purchase_id, i.item_id, i.title, i.price, u.username as partner_name FROM purchases p JOIN items i ON p.item_id = i.item_id JOIN users u ON i.user_id = u.user_id LEFT JOIN user_reviews r ON p.item_id = r.item_id AND r.reviewer_id = p.buyer_id WHERE p.buyer_id = %s AND p.status = 'shipped' AND r.review_id IS NULL ORDER BY p.purchased_at DESC;"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def get_awaiting_buyer_review_items(cursor, user_id):
    """自分が出品者で、購入者の評価待ちリストを取得"""
    query = """
        SELECT p.purchase_id, i.item_id, i.title, i.price, u.username as partner_name
        FROM purchases p
        JOIN items i ON p.item_id = i.item_id
        JOIN users u ON p.buyer_id = u.user_id
        -- 自分(出品者)からのレビューがまだ存在しないことを確認
        LEFT JOIN user_reviews r ON p.item_id = r.item_id AND r.reviewer_id = i.user_id
        WHERE
            i.user_id = %s
            AND p.status = 'completed'
            AND r.review_id IS NULL
        ORDER BY p.purchased_at DESC;
    """
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def generate_todo_html(items, button_text, button_link_base):
    if not items:
        return "<li>対象の取引はありません。</li>"
    html_parts = []
    for item in items:
        purchase_id, item_id, title, price, partner_name = item['purchase_id'], item['item_id'], item['title'], item['price'], item['partner_name'] # 辞書形式で取得
        action_link = f"{button_link_base}?purchase_id={purchase_id}"
        html_parts.append(f'<li class="todo-detail-item"><a href="item_detail.cgi?item_id={item_id}" class="item-link"><div class="item-info"><span class="item-title">{html.escape(title)}</span><span class="item-meta">¥{price:,} / 取引相手: {html.escape(partner_name)}さん</span></div></a><a href="{action_link}" class="btn-action">{button_text}</a></li>')
    return "".join(html_parts)

def main():
    connection = None
    user_id = None # 動的に設定されるユーザーID
    user_name = "ゲスト"

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True) # 辞書形式で結果を取得するように変更

        # --- セッションとユーザーIDの取得と検証 ---
        sid_cookie = cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
        session_id_from_cookie = None
        user_id_from_cookie = None

        if "session_id" in sid_cookie and "user_id" in sid_cookie:
            session_id_from_cookie = sid_cookie["session_id"].value
            user_id_from_cookie = sid_cookie["user_id"].value

            # セッションテーブルで正当性を検証
            valid_user_id = validate_session(cursor, session_id_from_cookie)

            # セッションが無効 or クッキーのuser_idとセッションテーブルのuser_idが不一致
            if not valid_user_id or str(valid_user_id) != user_id_from_cookie:
                print("Status: 302 Found")
                print("Location: login.html")
                print()
                return # ここで処理を終了

            user_id = valid_user_id # 認証されたユーザーIDを使用
            user_name = get_user_info(cursor, user_id)
        else:
            # クッキーに必要な情報がない場合もログインページへ
            print("Status: 302 Found")
            print("Location: login.html")
            print()
            return # ここで処理を終了
        # --- セッションとユーザーIDの取得と検証 終わり ---


        # 各リストのデータを取得
        # 認証された user_id を使用
        awaiting_shipment = get_awaiting_shipment_items(cursor, user_id)
        awaiting_my_review = get_awaiting_my_review_items(cursor, user_id)
        awaiting_buyer_review = get_awaiting_buyer_review_items(cursor, user_id)
        
        # HTML部品を生成
        shipment_html = generate_todo_html(awaiting_shipment, "取引画面へ", "trade.cgi")
        my_review_html = generate_todo_html(awaiting_my_review, "評価する", "trade.cgi")
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
