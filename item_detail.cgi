#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import cgi
import html
import datetime
import mysql.connector
from http import cookies
import cgitb # エラー表示のために追加

# エラー表示を有効にする
cgitb.enable()

# --- DB接続情報 (top.cgiと共通化) ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'user1',
    'passwd': 'passwordA1!',
    'db': 'Free',
    'charset': 'utf8'
}

# --- データベース関連の関数 (top.cgiからコピーまたは共通化) ---
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

# --- メイン処理 ---
def main():
    connection = None
    user_id = None
    user_name = "ゲスト"
    item = None # 商品情報を格納する変数

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True) # 辞書形式で結果を取得

        # セッション認証 (top.cgiと同様のロジックを適用)
        sid_cookie = cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
        session_id = None
        cookie_user_id = None

        if "session_id" in sid_cookie and "user_id" in sid_cookie:
            session_id = sid_cookie["session_id"].value
            cookie_user_id = sid_cookie["user_id"].value

            valid_user_id = validate_session(cursor, session_id)

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

        # --- 商品ID取得 ---
        form = cgi.FieldStorage()
        item_id = form.getfirst("item_id", "")
        review_content = form.getfirst("content", "") # レビューフォームからのデータも取得

        if not item_id or not item_id.isdigit():
            print("Content-Type: text/html; charset=utf-8\n")
            print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>エラー</title>
    <style>
        /* top.cgiのスタイルを簡略化して適用 */
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 1rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        p {{ font-size: 1.2rem; opacity: 0.9; }}
        .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; margin-top: 20px; }}
        .btn-secondary {{ background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }}
    </style>
</head>
<body>
    <h1>不正な商品IDです。</h1>
    <p>指定された商品が見つからないか、IDが正しくありません。</p>
    <a href="top.cgi" class="btn btn-secondary">トップページに戻る</a>
</body>
</html>
            """)
            return

        # レビュー投稿処理
        if review_content and review_content.strip() != "":
            # `user_id` はセッション認証で取得済み
            insert_review_query = """
                INSERT INTO reviews (item_id, reviewer_id, content, created_at)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_review_query, (item_id, user_id, review_content.strip(), datetime.datetime.now()))
            connection.commit()

        # 商品情報取得
        select_item_query = "SELECT item_id, title, price, description, image_path, user_id as seller_id FROM items WHERE item_id = %s"
        cursor.execute(select_item_query, (item_id,))
        item = cursor.fetchone()

        if not item:
            print("Content-Type: text/html; charset=utf-8\n")
            print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>エラー</title>
    <style>
        /* top.cgiのスタイルを簡略化して適用 */
        body {{ font-family: -apple-system, BlinkMacMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 1rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        p {{ font-size: 1.2rem; opacity: 0.9; }}
        .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; margin-top: 20px; }}
        .btn-secondary {{ background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }}
    </style>
</head>
<body>
    <h1>商品が見つかりません。</h1>
    <p>指定された商品ID ({html.escape(str(item_id))}) の商品が見つかりませんでした。</p>
    <a href="top.cgi" class="btn btn-secondary">トップページに戻る</a>
</body>
</html>
            """)
            return

        # レビュー一覧取得
        select_reviews_query = """
            SELECT u.username, r.content, r.created_at
            FROM reviews r
            JOIN users u ON r.reviewer_id = u.user_id
            WHERE r.item_id = %s
            ORDER BY r.created_at DESC
        """
        cursor.execute(select_reviews_query, (item_id,))
        reviews = cursor.fetchall()

        # レビューHTML生成
        reviews_html = []
        if reviews:
            for r in reviews:
                reviews_html.append(f"""
                <div class="review-card">
                    <div class="review-header">
                        <span class="reviewer-name">{html.escape(r['username'])}</span>
                        <span class="review-date">{r['created_at'].strftime('%Y/%m/%d %H:%M')}</span>
                    </div>
                    <p class="review-content">{html.escape(r['content'])}</p>
                </div>
                """)
        else:
            reviews_html.append('<p class="no-reviews-message">レビューはまだありません。</p>')

        # 画像パスの処理
        display_image_path = html.escape(item['image_path']) if item['image_path'] else "/purojitu/images/noimage.png"

        # CGIヘッダーを出力
        print("Content-Type: text/html; charset=utf-8\n")
        
        # HTML出力
        print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(item['title'])} - フリマアプリ</title>
    <style>
        /* top.cgiのスタイルをそのままコピー */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 20px; }}
        header {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 1rem 0; position: sticky; top: 0; z-index: 100; }}
        .header-content {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; }}
        .logo {{ font-size: 2rem; font-weight: bold; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .logo a {{ text-decoration: none; color: inherit; }} /* ロゴのリンクスタイルを追加 */
        .nav-buttons {{ display: flex; gap: 1rem; }}
        .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }}
        .btn-primary {{ background: linear-gradient(45deg, #ff6b6b, #ff8e8e); color: white; box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4); }}
        .btn-secondary {{ background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }}
        .section-title {{ text-align: center; font-size: 2rem; color: white; margin-bottom: 2rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .top-header {{ text-align: center; padding: 3rem 0 1rem 0; }}
        .top-header p {{ font-size: 1.5rem; opacity: 0.9; }}
        footer {{ background: rgba(0, 0, 0, 0.2); backdrop-filter: blur(10px); color: white; text-align: center; padding: 2rem 0; margin-top: 3rem; }}
        
        /* --- item_detail.cgi 用のスタイル --- */
        .item-detail-section {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2.5rem;
            margin-top: 3rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        .item-image-container {{
            width: 100%;
            max-width: 500px; /* 画像の最大幅 */
            height: 350px; /* 画像の高さ固定 */
            margin: 0 auto 2rem auto;
            overflow: hidden;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
            background: linear-gradient(45deg, #ff9a9e, #fecfef); /* 画像がない場合の背景 */
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .item-image-container img {{
            width: 100%;
            height: 100%;
            object-fit: cover; /* 画像をカバーフィット */
            display: block;
        }}
        .item-title {{
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 1rem;
            text-align: center;
            text-shadow: 2px 2px 6px rgba(0,0,0,0.4);
        }}
        .item-price {{
            font-size: 2.2rem;
            font-weight: bold;
            color: #ff6b6b;
            text-align: center;
            margin-bottom: 2rem;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.2);
        }}
        .item-description {{
            font-size: 1.1rem;
            line-height: 1.6;
            margin-bottom: 3rem;
            background: rgba(255, 255, 255, 0.08);
            padding: 1.5rem;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .buy-button-container {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        .buy-button {{
            padding: 1rem 3rem;
            font-size: 1.5rem;
            border-radius: 30px;
            box-shadow: 0 6px 20px rgba(255, 107, 107, 0.5);
        }}

        /* レビューセクション */
        .reviews-section {{
            margin-top: 3rem;
        }}
        .review-form {{
            background: rgba(255, 255, 255, 0.08);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 2rem;
        }}
        .review-form textarea {{
            width: 100%;
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 8px;
            border: none;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            font-size: 1rem;
            resize: vertical; /* 縦方向のみリサイズ可能 */
            min-height: 100px;
        }}
        .review-form textarea::placeholder {{
            color: rgba(255, 255, 255, 0.7);
        }}
        .review-form input[type="submit"] {{
            width: auto;
            padding: 0.8rem 2rem;
            font-size: 1.1rem;
            border-radius: 25px;
            cursor: pointer;
            border: none;
            background: linear-gradient(45deg, #ff6b6b, #ff8e8e);
            color: white;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        .review-form input[type="submit"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
        }}

        .review-list {{
            margin-top: 2rem;
        }}
        .review-card {{
            background: rgba(255, 255, 255, 0.08);
            padding: 1.5rem;
            border-radius: 15px;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        }}
        .review-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.8rem;
            font-weight: bold;
            font-size: 1.1rem;
        }}
        .reviewer-name {{ color: #ff6b6b; }}
        .review-date {{ font-size: 0.9rem; opacity: 0.7; }}
        .review-content {{ line-height: 1.5; opacity: 0.9; }}
        .no-reviews-message {{
            text-align: center;
            padding: 30px;
            font-size: 1.1rem;
            opacity: 0.8;
        }}
        .back-to-top {{
            display: block;
            text-align: center;
            margin-top: 3rem;
            font-size: 1.2rem;
            color: rgba(255, 255, 255, 0.8);
            text-decoration: none;
            transition: color 0.3s;
        }}
        .back-to-top:hover {{
            color: white;
            text-shadow: 0 0 5px rgba(255, 255, 255, 0.5);
        }}

        @media (max-width: 768px) {{
            .item-title {{ font-size: 2rem; }}
            .item-price {{ font-size: 1.8rem; }}
            .item-detail-section {{ padding: 1.5rem; }}
            .buy-button {{ padding: 0.8rem 2rem; font-size: 1.3rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div class="logo"><a href="top.cgi">🛍️ メル仮</a></div>
                <div class="nav-buttons">
                    <a href="account.cgi" class="btn btn-secondary">マイページ</a>
                    <a href="exhibition.cgi" class="btn btn-primary">出品する</a>
                    <a href="logout.cgi" class="btn btn-primary">ログアウト</a>
                </div>
            </div>
        </div>
    </header>

    <main>
        <div class="container">
            <section class="item-detail-section">
                <div class="item-image-container">
                    <img src="{display_image_path}" alt="{html.escape(item['title'])}">
                </div>
                <h1 class="item-title">{html.escape(item['title'])}</h1>
                <div class="item-price">¥{item['price']:,}</div>
                <p class="item-description">{html.escape(item['description'])}</p>
                
                <div class="buy-button-container">
                    <form action="buy_item.cgi" method="get">
                        <input type="hidden" name="item_id" value="{item_id}">
                        <button type="submit" class="btn btn-primary buy-button">購入確認へ進む</button>
                    </form>
                </div>

                <hr style="border-color: rgba(255,255,255,0.2); margin: 3rem 0;">

                <section class="reviews-section">
                    <h2 class="section-title" style="margin-bottom: 2rem;">レビュー</h2>
                    <div class="review-form">
                        <h3>レビューを投稿する</h3>
                        <form method="post" action="item_detail.cgi">
                            <input type="hidden" name="item_id" value="{item_id}">
                            <textarea name="content" rows="4" placeholder="レビューを記入してください" required></textarea><br>
                            <input type="submit" value="レビューを投稿">
                        </form>
                    </div>
                    <div class="review-list">
                        { "".join(reviews_html) }
                    </div>
                </section>
                <a href="top.cgi" class="back-to-top">← トップページに戻る</a>
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
