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
        # todo.cgiのno-comments-messageを参考にメッセージを生成
        return '<p class="no-items-message">対象の取引はありません。</p>'
    html_parts = []
    for item in items:
        # 辞書形式で取得
        purchase_id, item_id, title, price, partner_name = item['purchase_id'], item['item_id'], item['title'], item['price'], item['partner_name']
        action_link = f"{button_link_base}?purchase_id={purchase_id}"
        # item_detail.cgi のコメントカードに近い構造に調整
        html_parts.append(f"""
        <li class="todo-card">
            <div class="todo-info">
                <div class="todo-header">
                    <span class="todo-title item-title">{html.escape(title)}</span>
                    <span class="todo-partner item-meta">取引相手: {html.escape(partner_name)}さん</span>
                </div>
                <p class="todo-price">¥{price:,}</p>
            </div>
            <div class="todo-actions">
                <a href="item_detail.cgi?item_id={item_id}" class="btn btn-secondary btn-small">商品詳細</a>
                <a href="{action_link}" class="btn btn-primary btn-action">{button_text}</a>
            </div>
        </li>
        """)
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
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>やることリスト - フリマ</title>
    <style>
        /* top.cgi および item_detail.cgi と共通のスタイル */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 0 20px; }}

        /* Header */
        header {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); padding: 1rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.2); position: sticky; top: 0; z-index: 100; }}
        .header-content {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; }}
        .logo {{ font-size: 2rem; font-weight: bold; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .logo a {{ text-decoration: none; color: inherit; }}
        .nav-buttons {{ display: flex; gap: 1rem; }}

        /* Buttons */
        .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }}
        .btn-primary {{ background: linear-gradient(45deg, #ff6b6b, #ff8e8e); color: white; box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4); }}
        .btn-secondary {{ background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }}
        .btn-small {{ padding: 0.5rem 1rem; font-size: 0.9rem; }} /* 追加 */
        .btn-action {{ /* todo.cgiからbtn-actionを維持しつつ、btn-primaryのグラデーションを適用 */
            background: linear-gradient(45deg, #ff6b6b, #ff8e8e);
            color: white;
            font-size: 0.9rem;
            padding: 0.5rem 1rem;
            border-radius: 25px;
            text-decoration: none;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4); /* btn-primaryから継承 */
        }}
        .btn-action:hover {{ filter: brightness(1.1); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.5); }}


        /* Sections and Titles (共通化) */
        .section {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin-bottom: 2rem; border: 1px solid rgba(255, 255, 255, 0.2); }}
        .section-title {{ font-size: 1.8rem; margin-bottom: 1.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding-bottom: 0.5rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); text-align: center; }}

        /* Footer */
        footer {{ background: rgba(0, 0, 0, 0.2); backdrop-filter: blur(10px); color: white; text-align: center; padding: 2rem 0; margin-top: 3rem; border-top: 1px solid rgba(255,255,255,0.1); }}
        footer p {{ font-size: 0.9rem; opacity: 0.8; }}


        /* --- todo.cgi 個別スタイル --- */
        main {{ margin-top: 3rem; }}

        .todo-list {{ /* todo-detail-list から変更 */
            list-style: none;
            padding: 0;
            margin-top: 1rem; /* 調整 */
        }}
        .todo-card {{ /* todo-detail-item から変更し、item_detail.cgiのコメントカードに近づける */
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.2rem; /* パディングを少し増やす */
            background: rgba(255, 255, 255, 0.08); /* 背景色を追加 */
            border-radius: 15px; /* 角丸を追加 */
            margin-bottom: 1.5rem; /* 下マージン */
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            transition: all 0.3s ease; /* ホバー効果のため */
        }}
        .todo-card:last-child {{ margin-bottom: 0; }} /* 最後の要素の下マージンを削除 */
        .todo-card:hover {{ background: rgba(255,255,255,0.05); transform: translateY(-3px); box-shadow: 0 6px 15px rgba(0,0,0,0.3); }} /* ホバー効果 */

        .todo-info {{
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            margin-right: 1rem; /* ボタンとの間にスペース */
        }}
        .todo-header {{
            display: flex;
            flex-wrap: wrap; /* スマホで折り返す */
            gap: 0.5rem 1rem; /* 行間の調整 */
            align-items: baseline;
            margin-bottom: 0.5rem;
        }}
        .todo-title {{
            font-weight: bold;
            font-size: 1.3rem; /* 少し大きく */
            color: #ffde59; /* ハイライト色 */
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        }}
        .todo-partner {{
            font-size: 0.95rem;
            opacity: 0.8;
        }}
        .todo-price {{
            font-size: 1.2rem; /* item-priceに近づける */
            font-weight: bold;
            color: #a7f3d0; /* 価格のハイライト */
            margin-top: 0.5rem;
        }}
        .todo-actions {{
            display: flex;
            flex-direction: column; /* ボタンを縦に並べる */
            gap: 0.7rem; /* ボタン間のスペース */
            flex-shrink: 0; /* 縮小させない */
            align-items: flex-end; /* 右寄せ */
        }}
        .no-items-message {{ /* no-comments-messageを流用 */
            text-align: center;
            padding: 30px;
            font-size: 1.1rem;
            opacity: 0.8;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .header-content {{
                flex-direction: column;
                align-items: stretch;
            }}
            .nav-buttons {{
                width: 100%;
                justify-content: space-around;
            }}
            .btn {{
                flex: 1;
            }}
            .todo-card {{
                flex-direction: column; /* 要素を縦に並べる */
                align-items: flex-start; /* 左寄せ */
                gap: 1rem; /* todo-infoとtodo-actionsの間隔 */
            }}
            .todo-info {{
                width: 100%; /* 幅を広げる */
                margin-right: 0; /* 右マージンを解除 */
            }}
            .todo-actions {{
                width: 100%; /* ボタンも幅を広げる */
                align-items: stretch; /* ボタンを横いっぱいに */
            }}
            .btn-action, .btn-small {{
                width: 100%; /* ボタン幅を100%に */
            }}
            .todo-header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 0.3rem;
            }}
            .todo-title {{ font-size: 1.15rem; }}
            .todo-price {{ font-size: 1.05rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div class="logo"><a href="top.cgi">🛍️ メル仮</a></div>
                <div class="nav-buttons">
                    <a href="top.cgi" class="btn btn-secondary">トップページ</a>
                    <a href="account.cgi" class="btn btn-secondary">マイページ</a>
                    <a href="exhibition.cgi" class="btn btn-primary">出品する</a>
                </div>
            </div>
        </div>
    </header>
    <div class="container">
        <main>
            <section class="section">
                <h2 class="section-title">📦 発送待ちの商品</h2>
                <ul class="todo-list">{shipment_html}</ul>
            </section>
            <section class="section">
                <h2 class="section-title">⭐ 評価が必要な取引</h2>
                <ul class="todo-list">{my_review_html}</ul>
            </section>
            {f'<section class="section"><h2 class="section-title">👥 購入者の評価</h2><ul class="todo-list">{buyer_review_html}</ul></section>' if awaiting_buyer_review else ''}
        </main>
    </div>
    <footer>
        <div class="container">
            <p>&copy; 2025 フリマ. All rights reserved. | 利用規約 | プライバシーポリシー</p>
        </div>
    </footer>
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
