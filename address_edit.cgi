#!/usr/bin/env python3
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

# DB接続情報
DB_CONFIG = {
    'host': 'localhost',
    'user': 'user1',
    'passwd': 'passwordA1!',
    'db': 'Free',
    'charset': 'utf8'
}

def get_db_connection():
    """データベース接続を確立し、辞書カーソルを返す"""
    return mysql.connector.connect(**DB_CONFIG)

def validate_session(cursor, session_id):
    """セッションIDを検証し、有効な場合はユーザーIDを返す"""
    query = "SELECT user_id FROM sessions WHERE session_id = %s AND expires_at > NOW()"
    cursor.execute(query, (session_id,))
    result = cursor.fetchone()
    return result['user_id'] if result else None

def get_user_address(cursor, user_id):
    """ユーザーIDに基づいて住所情報を取得する"""
    query = """
        SELECT
            u.address_id,
            a.postal_code,
            a.prefecture,
            a.city,
            a.street,
            a.building
        FROM
            users AS u
        LEFT JOIN
            addresses AS a ON u.address_id = a.address_id
        WHERE
            u.user_id = %s
    """
    cursor.execute(query, (user_id,))
    return cursor.fetchone()

def update_address(connection, cursor, user_id, address_id, postal_code, prefecture, city, street, building):
    """既存の住所情報を更新する"""
    try:
        query = """
            UPDATE addresses
            SET postal_code = %s, prefecture = %s, city = %s, street = %s, building = %s
            WHERE address_id = %s
        """
        cursor.execute(query, (postal_code, prefecture, city, street, building, address_id))
        connection.commit()
        return True
    except mysql.connector.Error as err:
        connection.rollback()
        print(f"DEBUG: Update Error: {err}") # デバッグ用
        return False

def insert_address(connection, cursor, user_id, postal_code, prefecture, city, street, building):
    """新しい住所情報を挿入し、usersテーブルを更新する"""
    try:
        # 新しい住所を挿入
        insert_query = """
            INSERT INTO addresses (postal_code, prefecture, city, street, building)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (postal_code, prefecture, city, street, building))
        new_address_id = cursor.lastrowid

        # users テーブルの address_id を更新
        update_user_query = "UPDATE users SET address_id = %s WHERE user_id = %s"
        cursor.execute(update_user_query, (new_address_id, user_id))
        connection.commit()
        return True
    except mysql.connector.Error as err:
        connection.rollback()
        print(f"DEBUG: Insert Error: {err}") # デバッグ用
        return False

def is_valid_postal_code(code):
    """郵便番号の形式を検証 (XXX-XXXX または XXXXXXX)"""
    return len(code) in [7, 8] and code.replace('-', '').isdigit()

def main():
    form = cgi.FieldStorage()
    connection = None
    logged_in_user_id = None
    message = ""
    message_type = "" # 'success' or 'error'

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # --- セッションとユーザーIDの取得と検証 ---
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
            logged_in_user_id = valid_user_id
        else:
            print("Status: 302 Found")
            print("Location: login.html")
            print()
            return
        # --- セッションとユーザーIDの取得と検証 終わり ---

        user_address = get_user_address(cursor, logged_in_user_id)
        current_address_id = user_address['address_id'] if user_address else None

        # フォームが送信された場合の処理
        if os.environ['REQUEST_METHOD'] == 'POST':
            postal_code = form.getvalue('postal_code', '').strip()
            prefecture = form.getvalue('prefecture', '').strip()
            city = form.getvalue('city', '').strip()
            street = form.getvalue('street', '').strip()
            building = form.getvalue('building', '').strip()

            errors = []

            if not is_valid_postal_code(postal_code):
                errors.append("郵便番号はXXX-XXXX形式または7桁の数字で入力してください。")
            if not prefecture:
                errors.append("都道府県は必須です。")
            if not city:
                errors.append("市区町村は必須です。")
            if not street:
                errors.append("番地は必須です。")

            if errors:
                message = "<br>".join(errors)
                message_type = "error"
            else:
                # データベース更新
                if current_address_id:
                    # 既存の住所を更新
                    if update_address(connection, cursor, logged_in_user_id, current_address_id, postal_code, prefecture, city, street, building):
                        message = "住所情報を更新しました！"
                        message_type = "success"
                        # 更新後の情報を再取得
                        user_address = get_user_address(cursor, logged_in_user_id)
                    else:
                        message = "住所情報の更新に失敗しました。"
                        message_type = "error"
                else:
                    # 新しい住所を挿入
                    if insert_address(connection, cursor, logged_in_user_id, postal_code, prefecture, city, street, building):
                        message = "新しい住所情報を登録しました！"
                        message_type = "success"
                        # 新しい情報を再取得
                        user_address = get_user_address(cursor, logged_in_user_id)
                    else:
                        message = "住所情報の登録に失敗しました。"
                        message_type = "error"
        
        # フォームの初期値または更新後の値を設定
        display_postal_code = user_address['postal_code'] if user_address and user_address['postal_code'] else ''
        display_prefecture = user_address['prefecture'] if user_address and user_address['prefecture'] else ''
        display_city = user_address['city'] if user_address and user_address['city'] else ''
        display_street = user_address['street'] if user_address and user_address['street'] else ''
        display_building = user_address['building'] if user_address and user_address['building'] else ''

    except mysql.connector.Error as err:
        message = f"データベースエラーが発生しました: {html.escape(str(err))}"
        message_type = "error"
        display_postal_code = display_prefecture = display_city = display_street = display_building = ''
    except Exception as e:
        message = f"予期せぬエラーが発生しました: {html.escape(str(e))}"
        message_type = "error"
        display_postal_code = display_prefecture = display_city = display_street = display_building = ''
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

    # HTML出力
    print("Content-Type: text/html; charset=utf-8\n")
    print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>住所情報編集 - フリマアプリ</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; display: flex; flex-direction: column; }}
        
        main {{ flex-grow: 1; padding-top: 2rem; padding-bottom: 3rem; display: flex; flex-direction: column; align-items: center; }}
        .container {{ max-width: 1200px; width: 100%; padding: 0 20px; box-sizing: border-box; }}

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

        /* Section */
        .section {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2.5rem; margin-bottom: 2rem; border: 1px solid rgba(255, 255, 255, 0.2); width: 100%; max-width: 600px; margin-left: auto; margin-right: auto; }}
        .section-title {{ text-align: center; font-size: 2rem; color: white; margin-bottom: 2rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}

        /* Form Specific Styles */
        .form-group {{ margin-bottom: 1.5rem; }}
        label {{ display: block; font-size: 1.1rem; margin-bottom: 0.5rem; color: #a7f3d0; font-weight: bold; }}
        input[type="text"] {{
            width: 100%;
            padding: 0.8rem;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            background-color: rgba(255, 255, 255, 0.05);
            color: white;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }}
        input[type="text"]:focus {{
            outline: none;
            border-color: #ff6b6b;
            box-shadow: 0 0 0 3px rgba(255, 107, 107, 0.3);
        }}
        .form-actions {{ text-align: center; margin-top: 2rem; }}
        .form-actions .btn {{ margin: 0 0.5rem; }}

        /* Message Styles */
        .message {{
            padding: 1rem;
            margin-bottom: 1.5rem;
            border-radius: 10px;
            text-align: center;
            font-weight: bold;
        }}
        .message.success {{
            background-color: rgba(167, 243, 208, 0.2); /* light green */
            color: #a7f3d0;
            border: 1px solid #a7f3d0;
        }}
        .message.error {{
            background-color: rgba(255, 107, 107, 0.2); /* light red */
            color: #ff6b6b;
            border: 1px solid #ff6b6b;
        }}

        /* Footer */
        footer {{ background: rgba(0, 0, 0, 0.2); backdrop-filter: blur(10px); color: white; text-align: center; padding: 2rem 0; margin-top: auto; border-top: 1px solid rgba(255,255,255,0.1); }}
        footer p {{ font-size: 0.9rem; opacity: 0.8; }}

        @media (max-width: 768px) {{
            .header-content {{ flex-direction: column; align-items: stretch; }}
            .nav-buttons {{ width: 100%; justify-content: space-around; }}
            .btn {{ flex: 1; }}
            .section {{ padding: 1.5rem; margin-top: 1.5rem; max-width: 95%; }}
            .section-title {{ font-size: 1.5rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div class="logo"><a href="top.cgi" style="text-decoration: none; color: white;">🛍️ メル仮</a></div>
                <div class="nav-buttons">
                    <a href="top.cgi" class="btn btn-secondary">トップページ</a>
                    <a href="account.cgi" class="btn btn-secondary">マイページ</a>
                    <a href="account_detail.cgi" class="btn btn-secondary">アカウント情報</a>
                    <a href="exhibition.cgi" class="btn btn-primary">出品する</a>
                </div>
            </div>
        </div>
    </header>

    <main>
        <div class="container">
            <section class="section">
                <h2 class="section-title">住所情報編集</h2>

                {'<div class="message ' + message_type + '">' + html.escape(message) + '</div>' if message else ''}

                <form method="post" action="address_edit.cgi">
                    <div class="form-group">
                        <label for="postal_code">郵便番号 (例: 123-4567 または 1234567)</label>
                        <input type="text" id="postal_code" name="postal_code" value="{html.escape(display_postal_code)}" maxlength="8" required>
                    </div>
                    <div class="form-group">
                        <label for="prefecture">都道府県</label>
                        <input type="text" id="prefecture" name="prefecture" value="{html.escape(display_prefecture)}" required>
                    </div>
                    <div class="form-group">
                        <label for="city">市区町村</label>
                        <input type="text" id="city" name="city" value="{html.escape(display_city)}" required>
                    </div>
                    <div class="form-group">
                        <label for="street">番地</label>
                        <input type="text" id="street" name="street" value="{html.escape(display_street)}" required>
                    </div>
                    <div class="form-group">
                        <label for="building">建物名 (任意)</label>
                        <input type="text" id="building" name="building" value="{html.escape(display_building)}">
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">更新する</button>
                        <a href="account_detail.cgi" class="btn btn-secondary">戻る</a>
                    </div>
                </form>
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

if __name__ == "__main__":
    main()
