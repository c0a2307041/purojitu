#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
    """データベース接続を確立し、辞書カーソルを返す"""
    return mysql.connector.connect(**DB_CONFIG)

def get_user_info(cursor, user_id):
    """ユーザーIDに基づいてユーザー名を取得する"""
    query = "SELECT username FROM users WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    return result['username'] if result else "ゲスト"

def validate_session(cursor, session_id):
    """セッションIDを検証し、有効な場合はユーザーIDを返す"""
    query = "SELECT user_id FROM sessions WHERE session_id = %s AND expires_at > NOW()"
    cursor.execute(query, (session_id,))
    result = cursor.fetchone()
    return result['user_id'] if result else None

def get_user_details(cursor, user_id):
    """ユーザーIDに基づいてユーザーの詳細情報と住所情報を取得する"""
    query = """
        SELECT
            u.username,
            u.email,
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

def main():
    connection = None
    logged_in_user_id = None
    user_name = "ゲスト" # デフォルト値
    user_details = None

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

            # セッションが無効、またはクッキーのuser_idとセッションテーブルのuser_idが不一致の場合
            if not valid_user_id or str(valid_user_id) != cookie_user_id:
                print("Status: 302 Found")
                print("Location: login.html")
                print()
                return # ここで処理を終了

            logged_in_user_id = valid_user_id # 認証されたユーザーIDをセット
            user_name = get_user_info(cursor, logged_in_user_id)
        else:
            # クッキーに必要な情報がない場合もログインページへ
            print("Status: 302 Found")
            print("Location: login.html")
            print()
            return # ここで処理を終了
        # --- セッションとユーザーIDの取得と検証 終わり ---

        # ユーザーの詳細情報を取得
        user_details = get_user_details(cursor, logged_in_user_id)

        # ユーザー情報が見つからない場合のエラーページ
        if not user_details:
            print("Content-Type: text/html; charset=utf-8\n")
            print("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>エラー - アカウント情報</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; }
        h1 { font-size: 2.5rem; margin-bottom: 1rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        p { font-size: 1.2rem; opacity: 0.9; margin-bottom: 20px; }
        .btn { padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }
        .btn-secondary { background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <h1>ユーザー情報が見つかりません。</h1>
    <p>アカウント情報を取得できませんでした。</p>
    <a href="top.cgi" class="btn btn-secondary">トップページに戻る</a>
</body>
</html>
            """)
            return

        # HTML出力
        print("Content-Type: text/html; charset=utf-8\n")
        print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>アカウント情報 - フリマアプリ</title>
    <style>
        /* top.cgi, account.cgi と共通のスタイル */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; display: flex; flex-direction: column; }}
        
        /* main要素自体を中央寄せのコンテナにするため、幅を設定 */
        main {{ 
            flex-grow: 1; 
            padding-top: 2rem; 
            padding-bottom: 3rem; 
            display: flex; /* flexboxを適用 */
            flex-direction: column; /* 子要素を縦に並べる */
            align-items: center; /* 子要素を中央寄せ */
        }}
        /* containerはmainの子要素として、コンテンツの幅を制御し、左右のpaddingを確保 */
        .container {{ 
            max-width: 1200px; /* 大画面での最大幅 */
            width: 100%; /* 親要素の幅に合わせて伸びる */
            padding: 0 20px; 
            box-sizing: border-box; /* paddingを含めて幅を計算 */
        }}

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
        .section {{ 
            background: rgba(255, 255, 255, 0.1); 
            backdrop-filter: blur(10px); 
            border-radius: 20px; 
            padding: 2rem; 
            margin-bottom: 2rem; 
            border: 1px solid rgba(255, 255, 255, 0.2); 
            width: 100%; /* 親要素（container）の幅いっぱいに */
        }}
        .section-title {{ text-align: center; font-size: 2rem; color: white; margin-bottom: 2rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        
        /* Footer */
        footer {{ background: rgba(0, 0, 0, 0.2); backdrop-filter: blur(10px); color: white; text-align: center; padding: 2rem 0; margin-top: auto; border-top: 1px solid rgba(255,255,255,0.1); }}
        footer p {{ font-size: 0.9rem; opacity: 0.8; }}

        /* --- account_detail.cgi 個別スタイル --- */
        .account-info-section {{
            margin-top: 3rem;
            padding: 2.5rem;
            /* ここを修正：最大幅を設定し、中央寄せにする */
            max-width: 800px; /* 例えば800pxに設定。この幅で細長に見えにくくなるはずです */
            margin-left: auto; /* 中央寄せ */
            margin-right: auto; /* 中央寄せ */
            flex-grow: 0; /* このセクションは伸びないようにする */
        }}

        .info-card {{
            background: rgba(255, 255, 255, 0.08);
            padding: 1.5rem;
            border-radius: 15px;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        }}

        .info-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .info-item:last-child {{
            border-bottom: none;
        }}

        .info-label {{
            font-weight: bold;
            font-size: 1.1rem;
            color: #a7f3d0; /* 緑系のハイライト */
            flex-basis: 30%; /* ラベルの幅を調整 */
            text-align: left;
        }}

        .info-value {{
            font-size: 1.1rem;
            color: white;
            opacity: 0.9;
            flex-basis: 65%; /* 値の幅を調整 */
            text-align: right;
            word-break: break-word; /* 長い文字列の折り返し */
        }}

        .address-group .info-label {{
            color: #add8e6; /* 青系のハイライト */
        }}

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
            .account-info-section {{
                padding: 1.5rem;
                margin-top: 1.5rem;
                max-width: 95%; /* モバイルではほぼ全体幅に */
            }}
            .info-item {{
                flex-direction: column;
                align-items: flex-start;
                gap: 0.5rem;
            }}
            .info-label, .info-value {{
                flex-basis: auto;
                width: 100%;
                text-align: left;
            }}
            .info-value {{
                padding-left: 1rem; /* インデント */
            }}
             .section-title {{
                font-size: 1.5rem;
            }}
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
                    <a href="exhibition.cgi" class="btn btn-primary">出品する</a>
                </div>
            </div>
        </div>
    </header>

    <main>
        <div class="container">
            <section class="account-info-section section">
                <h2 class="section-title">アカウント情報</h2>
                
                <div class="info-card">
                    <div class="info-item">
                        <span class="info-label">ユーザー名:</span>
                        <span class="info-value">{html.escape(user_details['username'])}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">メールアドレス:</span>
                        <span class="info-value">{html.escape(user_details['email'])}</span>
                    </div>
                </div>

                <div class="info-card address-group">
                    <h3 class="section-title" style="font-size: 1.5rem; margin-top: 0; margin-bottom: 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding-bottom: 0.5rem; text-align: center;">住所情報</h3>
                    <div class="info-item">
                        <span class="info-label">郵便番号:</span>
                        <span class="info-value">{html.escape(user_details['postal_code'] if user_details['postal_code'] else '未登録')}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">都道府県:</span>
                        <span class="info-value">{html.escape(user_details['prefecture'] if user_details['prefecture'] else '未登録')}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">市区町村:</span>
                        <span class="info-value">{html.escape(user_details['city'] if user_details['city'] else '未登録')}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">番地:</span>
                        <span class="info-value">{html.escape(user_details['street'] if user_details['street'] else '未登録')}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">建物名:</span>
                        <span class="info-value">{html.escape(user_details['building'] if user_details['building'] else 'なし')}</span>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 2rem;">
                    <a href="address_edit.cgi" class="btn btn-primary">住所情報を編集</a>
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
