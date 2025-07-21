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
    logged_in_user_id = None # ログイン中のユーザーID
    user_name = "ゲスト"
    item = None # 商品情報を格納する変数
    price_update_message = None # 価格更新メッセージ

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

            logged_in_user_id = valid_user_id # ログイン中のユーザーIDをセット
            user_name = get_user_info(cursor, logged_in_user_id)
        else:
            # クッキーに必要な情報がない場合もログインページへ
            print("Status: 302 Found")
            print("Location: login.html")
            print()
            return

        # --- 商品ID取得 ---
        form = cgi.FieldStorage()
        item_id = form.getfirst("item_id", "")
        comment_content = form.getfirst("content", "") # コメントフォームからのデータも取得

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
        /* エラーページ用スタイルも統一 */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 1rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        p {{ font-size: 1.2rem; opacity: 0.9; margin-bottom: 20px; }}
        .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }}
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

        # 商品情報取得と出品者情報取得 (コメント投稿、価格変更時に必要)
        select_item_query_for_seller = """
            SELECT user_id as seller_id FROM items WHERE item_id = %s
        """
        cursor.execute(select_item_query_for_seller, (item_id,))
        item_seller_info = cursor.fetchone()
        seller_id = item_seller_info['seller_id'] if item_seller_info else None

        # 価格変更処理
        if form.getfirst("action") == "update_price" and logged_in_user_id == seller_id:
            new_price_str = form.getfirst("new_price", "")
            try:
                new_price = int(new_price_str)
                if new_price <= 0:
                    price_update_message = "価格は1円以上に設定してください。"
                else:
                    update_price_query = "UPDATE items SET price = %s WHERE item_id = %s AND user_id = %s"
                    cursor.execute(update_price_query, (new_price, item_id, logged_in_user_id))
                    connection.commit()
                    # 更新成功後、リダイレクトしてGETリクエストにする（二重送信防止＆メッセージ表示のため）
                    print("Status: 302 Found")
                    print(f"Location: item_detail.cgi?item_id={item_id}&price_updated=true\n")
                    return
            except ValueError:
                price_update_message = "価格は半角数字で入力してください。"
            except Exception as e:
                price_update_message = f"価格更新中にエラーが発生しました: {html.escape(str(e))}"

        # コメント投稿処理
        if comment_content and comment_content.strip() != "" and logged_in_user_id:
            insert_comment_query = """
                INSERT INTO reviews (item_id, reviewer_id, content, created_at)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_comment_query, (item_id, logged_in_user_id, comment_content.strip(), datetime.datetime.now()))
            connection.commit()
            
            # コメント投稿後、ページをリロードしてGETリクエストにする（二重送信防止）
            print("Status: 302 Found")
            print(f"Location: item_detail.cgi?item_id={item_id}\n")
            return


        # 商品情報取得と出品者情報取得 (再取得、価格更新後に最新情報を得るため)
        select_item_query = """
            SELECT i.item_id, i.title, i.price, i.description, i.image_path, i.user_id as seller_id, u.username as seller_name
            FROM items i
            JOIN users u ON i.user_id = u.user_id
            WHERE i.item_id = %s
        """
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
        /* エラーページ用スタイルも統一 */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 1rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        p {{ font-size: 1.2rem; opacity: 0.9; margin-bottom: 20px; }}
        .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }}
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

        # コメント一覧取得
        select_comments_query = """
            SELECT r.reviewer_id, u.username, r.content, r.created_at
            FROM reviews r
            JOIN users u ON r.reviewer_id = u.user_id
            WHERE r.item_id = %s
            ORDER BY r.created_at DESC
        """
        cursor.execute(select_comments_query, (item_id,))
        comments = cursor.fetchall()

        # コメントHTML生成
        comments_html = []
        if comments:
            for c in comments:
                # コメント投稿者が商品の出品者であるか判定
                commenter_name = html.escape(c['username'])
                if c['reviewer_id'] == item['seller_id']:
                    commenter_name += ' <span class="seller-badge">(出品者)</span>'

                comments_html.append(f"""
                <li class="comment-card todo-detail-item">
                    <div class="comment-info item-info">
                        <div class="comment-header">
                            <span class="commenter-name">{commenter_name}</span>
                            <span class="comment-date item-meta">{c['created_at'].strftime('%Y/%m/%d %H:%M')}</span>
                        </div>
                        <p class="comment-content">{html.escape(c['content'])}</p>
                    </div>
                </li>
                """)
        else:
            comments_html.append('<p class="no-comments-message">コメントはまだありません。</p>')

        # 画像パスの処理
        display_image_path = html.escape(item['image_path']) if item['image_path'] else "/purojitu/images/noimage.png"

        # 購入ボタン/価格変更フォームの表示制御
        action_area_html = ""
        if logged_in_user_id != item['seller_id']:
            action_area_html = f"""
                <div class="buy-button-container">
                    <form action="buy_item.cgi" method="get">
                        <input type="hidden" name="item_id" value="{item_id}">
                        <button type="submit" class="btn btn-primary buy-button">購入確認へ進む</button>
                    </form>
                </div>
            """
        else:
            # 出品者本人の場合、価格変更フォームを表示
            action_area_html = f"""
                <div class="seller-actions-container">
                    <p class="seller-view-message">あなたが出品した商品です。</p>
                    <div class="price-edit-form-wrapper">
                        <h3>価格を変更する</h3>
                        <form method="post" action="item_detail.cgi">
                            <input type="hidden" name="item_id" value="{item_id}">
                            <input type="hidden" name="action" value="update_price">
                            <input type="number" name="new_price" value="{item['price']}" min="1" required class="price-input">
                            <button type="submit" class="btn btn-primary btn-update-price">価格を更新</button>
                        </form>
                        {"<p class='error-message'>" + html.escape(price_update_message) + "</p>" if price_update_message else ""}
                    </div>
                </div>
            """
        
        # 価格更新成功時のJavaScriptアラート
        js_alert_script = ""
        if form.getfirst("price_updated") == "true":
            js_alert_script = "<script>alert('価格が更新されました！');</script>"

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
        /* top.cgi および todo.cgi と共通のスタイル */
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

        /* Sections and Titles (共通化) */
        .section {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin-bottom: 2rem; border: 1px solid rgba(255, 255, 255, 0.2); }}
        .section-title {{ font-size: 1.8rem; margin-bottom: 1.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding-bottom: 0.5rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); text-align: center; }}

        /* Footer */
        footer {{ background: rgba(0, 0, 0, 0.2); backdrop-filter: blur(10px); color: white; text-align: center; padding: 2rem 0; margin-top: 3rem; border-top: 1px solid rgba(255,255,255,0.1); }}
        footer p {{ font-size: 0.9rem; opacity: 0.8; }}


        /* --- item_detail.cgi 個別スタイル --- */
        .item-detail-section {{
            margin-top: 3rem;
            padding: 2.5rem;
        }}
        .item-image-container {{
            width: 100%;
            max-width: 500px;
            height: 350px;
            margin: 0 auto 2rem auto;
            overflow: hidden;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
            background: linear-gradient(45deg, #ff9a9e, #fecfef);
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .item-image-container img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}
        .item-title {{
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
            text-align: center;
            text-shadow: 2px 2px 6px rgba(0,0,0,0.4);
        }}
        .seller-info {{
            text-align: center;
            margin-bottom: 1.5rem;
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        .seller-info a {{
            color: #add8e6;
            text-decoration: none;
            font-weight: bold;
            transition: color 0.3s ease;
        }}
        .seller-info a:hover {{
            color: #87ceeb;
            text-decoration: underline;
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
            white-space: pre-wrap;
            word-wrap: break-word;
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
            background: linear-gradient(45deg, #ff6b6b, #ff8e8e);
            color: white;
            border: none;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: inline-block;
        }}
        .buy-button:hover {{
             transform: translateY(-2px);
             box-shadow: 0 8px 25px rgba(255, 107, 107, 0.6);
        }}
        .seller-view-message {{
            font-size: 1.2rem;
            color: rgba(255, 255, 255, 0.8);
            padding: 1rem;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            display: inline-block;
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 1.5rem; /* 価格変更フォームとの間にスペース */
        }}

        /* 価格変更フォームのスタイル */
        .seller-actions-container {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        .price-edit-form-wrapper {{
            background: rgba(255, 255, 255, 0.08);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            max-width: 400px;
            margin: 0 auto;
        }}
        .price-edit-form-wrapper h3 {{
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            color: white;
            text-align: center;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        }}
        .price-edit-form-wrapper form {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
        }}
        .price-input {{
            width: 80%;
            padding: 0.8rem;
            border-radius: 8px;
            border: none;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            font-size: 1.2rem;
            text-align: center;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);
            -moz-appearance: textfield; /* Firefox の数値入力欄の矢印を非表示に */
        }}
        .price-input::-webkit-outer-spin-button,
        .price-input::-webkit-inner-spin-button {{
            -webkit-appearance: none; /* Chrome, Safari の数値入力欄の矢印を非表示に */
            margin: 0;
        }}
        .btn-update-price {{
            width: 80%;
            padding: 0.8rem 2rem;
            font-size: 1.1rem;
            border-radius: 25px;
            cursor: pointer;
            border: none;
            background: linear-gradient(45deg, #ff6b6b, #ff8e8e);
            color: white;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
        }}
        .btn-update-price:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(255, 107, 107, 0.5);
        }}
        .error-message {{
            color: #ffcccc;
            margin-top: 1rem;
            font-weight: bold;
        }}


        /* コメントセクション */
        .comments-section {{
            margin-top: 3rem;
        }}
        .comment-form {{
            background: rgba(255, 255, 255, 0.08);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 2rem;
        }}
        .comment-form h3 {{
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            color: white;
            text-align: center;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        }}
        .comment-form textarea {{
            width: 100%;
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 8px;
            border: none;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            font-size: 1rem;
            resize: vertical;
            min-height: 100px;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);
        }}
        .comment-form textarea::placeholder {{
            color: rgba(255, 255, 255, 0.7);
        }}
        .comment-form input[type="submit"] {{
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
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
        }}
        .comment-form input[type="submit"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
        }}

        .comment-list {{
            list-style: none; /* リストの点を削除 */
            padding: 0;
            margin-top: 2rem;
        }}
        .comment-card {{
            /* todo.cgi の .todo-detail-item をベースに */
            display: flex; /* flexboxで配置 */
            justify-content: space-between; /* 要素間のスペースを均等に */
            align-items: flex-start; /* 上端揃え */
            padding: 1rem;
            border-bottom: 1px solid rgba(255,255,255,0.2);
            transition: background 0.3s ease;
            background: rgba(255, 255, 255, 0.08); /* todo-detail-item にはなかった背景色を追加 */
            border-radius: 15px; /* todo-detail-item にはなかった角丸を追加 */
            margin-bottom: 1.5rem; /* todo-detail-item にはなかった下マージン */
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        }}
        .comment-card:last-child {{ border-bottom: none; }}
        .comment-card:hover {{ background: rgba(255,255,255,0.05); transform: translateY(-3px); box-shadow: 0 6px 15px rgba(0,0,0,0.3); }} /* ホバー効果 */

        .comment-info {{
            flex-grow: 1; /* スペースを埋める */
            display: flex;
            flex-direction: column;
        }}
        .comment-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.8rem;
            font-weight: bold;
            font-size: 1.1rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .commenter-name {{
            color: #ff6b6b;
            display: flex;
            align-items: center;
        }}
        .seller-badge {{
            background-color: #5cb85c;
            color: white;
            font-size: 0.75em;
            padding: 0.2em 0.5em;
            border-radius: 5px;
            margin-left: 0.5em;
            font-weight: normal;
        }}
        .comment-date {{
            font-size: 0.9rem;
            opacity: 0.7;
        }}
        .comment-content {{
            line-height: 1.5;
            opacity: 0.9;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .no-comments-message {{
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
            .item-title {{ font-size: 2rem; }}
            .item-price {{ font-size: 1.8rem; }}
            .item-detail-section {{ padding: 1.5rem; }}
            .buy-button {{ padding: 0.8rem 2rem; font-size: 1.3rem; }}
            .comment-card {{ flex-direction: column; align-items: flex-start; gap: 0.5rem; }}
            .comment-header {{ flex-direction: column; align-items: flex-start; }}
            .comment-date {{ margin-top: 0.3rem; }}
            .price-edit-form-wrapper {{ max-width: 100%; padding: 1.5rem; }}
            .price-input, .btn-update-price {{ width: 100%; }}
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

    <main>
        <div class="container">
            <section class="item-detail-section section">
                <h1 class="item-title section-title">{html.escape(item['title'])}</h1>
                <div class="item-image-container">
                    <img src="{display_image_path}" alt="{html.escape(item['title'])}">
                </div>
                <p class="seller-info">出品者: <a href="profile.cgi?user_id={item['seller_id']}">{html.escape(item['seller_name'])}</a></p>
                <div class="item-price">¥{item['price']:,}</div>
                <p class="item-description">{html.escape(item['description'])}</p>
                
                {action_area_html}

                <hr style="border-color: rgba(255,255,255,0.2); margin: 3rem 0;">

                <section class="comments-section">
                    <h2 class="section-title">コメント</h2>
                    <div class="comment-form">
                        <h3>コメントを投稿する</h3>
                        <form method="post" action="item_detail.cgi">
                            <input type="hidden" name="item_id" value="{item_id}">
                            <textarea name="content" rows="4" placeholder="コメントを記入してください" required></textarea><br>
                            <input type="submit" value="コメントを投稿">
                        </form>
                    </div>
                    <ul class="comment-list"> 
                        { "".join(comments_html) }
                    </ul>
                </section>
            </section>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2025 フリマ. All rights reserved. | 利用規約 | プライバシーポリシー</p>
        </div>
    </footer>
    {js_alert_script}
</body>
</html>
        """)

    except mysql.connector.Error as err:
        print("Content-Type: text/html; charset=utf-8\n")
        print("<h1>データベースエラー</h1>")
        print(f"<p>エラーが発生しました: {html.escape(str(err))}</p>")
    except Exception as e:
        print("Content-Type: text/html; charset=utf-8\n")
        print("<h1>エラーが発生しました</h1>")
        print(f"<p>予期せぬエラーが発生しました: {html.escape(str(e))}</p>")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    main()
