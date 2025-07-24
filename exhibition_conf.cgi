#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import cgitb
import os
import html
import time
import random
import mysql.connector
from http import cookies # セッション情報を扱うために追加

# --- 設定 ---
UPLOAD_DIR = "/var/www/html/purojitu/uploads/"

# MySQL設定
DB_CONFIG = {
    'host': 'localhost',
    'user': 'user1',
    'password': 'passwordA1!',
    'database': 'Free',
    'charset': 'utf8mb4',
}

cgitb.enable() # デバッグ用。本番環境では無効にするか、エラーログにのみ出力する設定を推奨

form = cgi.FieldStorage()

# HTML出力の前にヘッダーを出力する関数
def print_html_header(status_code=200, location=None):
    """
    HTTPヘッダーを出力する。リダイレクトの場合はLocationヘッダーも追加。
    """
    if location:
        print(f"Status: {status_code} Found")
        print(f"Location: {location}")
        print() # ヘッダーの終わりを示す空行
    else:
        print("Content-Type: text/html; charset=utf-8")
        print() # ヘッダーの終わりを示す空行


# ---------- HTMLテンプレート関数 ----------
def print_html_head(title="出品確認 - フリマ"):
    print(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; margin: 0; padding: 0; display: flex; flex-direction: column; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; width: 100%; box-sizing: border-box; }}
        header {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 1rem 0; position: sticky; top: 0; z-index: 100; }}
        .header-content {{ display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-size: 2rem; font-weight: bold; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }}
        .btn-primary {{ background: linear-gradient(45deg, #ff6b6b, #ff8e8e); color: white; }}
        .btn:hover {{ transform: translateY(-2px); }}
        .section-title {{ text-align: center; font-size: 2rem; margin: 2rem 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .section {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin: 2rem 0; border: 1px solid rgba(255, 255, 255, 0.2); flex-grow: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
        .form-group {{ margin-bottom: 1.5rem; text-align: left; width: 100%; }}
        .form-label {{ font-weight: 600; margin-bottom: 0.5rem; display: block; }}
        footer {{ text-align: center; padding: 2rem 0; margin-top: auto; background: rgba(0,0,0,0.2); }}
        .button-group {{ display: flex; justify-content: center; gap: 15px; margin-top: 2rem; width: 100%; }}
        .btn-back {{ background: rgba(255, 255, 255, 0.2); color: white; }}
        .item-image-preview {{ max-width: 100%; height: auto; border-radius: 15px; margin-top: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }}
    </style>
</head>
<body>""")

def print_header_content():
    print("""
<header>
    <div class="container">
        <div class="header-content">
            <div class="logo">🛍️ メル仮</div>
            <a href="/purojitu" class="btn btn-primary">トップへ戻る</a>
        </div>
    </div>
</header>""")

def print_footer():
    print("""<footer><div class="container"><p>&copy; 2025 フリマ. All rights reserved.</p></div></footer></body></html>""")


# ---------- ファイル保存 ----------
def save_uploaded_file(form_field):
    file_item = form[form_field]
    if file_item.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        _, ext = os.path.splitext(file_item.filename)
        ext = ext.lower()

        while True:
            random_number = random.randint(10000000, 99999999)
            unique_filename = f"{random_number}{ext}"
            filepath = os.path.join(UPLOAD_DIR, unique_filename)
            if not os.path.exists(filepath):
                break

        try:
            with open(filepath, 'wb') as f:
                f.write(file_item.file.read())
            return os.path.join("/purojitu/uploads/", unique_filename)
        except Exception as e:
            # ファイル書き込みエラーをログに記録するか、適切に処理
            print_error_page(f"ファイルの保存中にエラーが発生しました: {html.escape(str(e))}", "/purojitu/exhibit.cgi")
            return None
    return None

# エラーページ関数 (以前のものを再利用)
def print_error_page(message, back_link="/purojitu/top.cgi"):
    print_html_header() # エラーページもヘッダーを出力
    print_html_head(title="エラー")
    print_header_content()
    print(f"""
    <div class="container">
        <h2 class="section-title" style="color:#ff6b6b;">エラーが発生しました</h2>
        <section class="section">
            <p>{html.escape(message)}</p>
            <a href="{html.escape(back_link)}" class="btn btn-primary">戻る</a>
        </section>
    </div>
    """)
    print_footer()
    exit()


# ---------- DB ----------
def get_user_id(username):
    # セッションからuser_idを取得するように変更するのが理想的
    # 今回は既存のDB接続部分を修正
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        return result[0] if result else None
    except mysql.connector.Error as err:
        print_error_page(f"データベースエラー (ユーザー取得): {html.escape(str(err))}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_user_id_from_session(session_id):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM sessions WHERE session_id = %s AND expires_at > NOW()", (session_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except mysql.connector.Error as err:
        print_error_page(f"データベースエラー (セッションユーザー取得): {html.escape(str(err))}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


def insert_item(user_id, title, description, price, image_path):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        sql = "INSERT INTO items (user_id, title, description, price, image_path) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (user_id, title, description, price, image_path))
        conn.commit()
    except mysql.connector.Error as err:
        print_error_page(f"データベースエラー (出品登録): {html.escape(str(err))}", "/purojitu/exhibit.cgi")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ---------- メイン処理 ----------
def main():
    # セッションIDをクッキーから取得
    sid_cookie = cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
    session_id = None
    if "session_id" in sid_cookie:
        session_id = sid_cookie["session_id"].value

    if not session_id:
        # セッションがない場合はログインページへリダイレクト
        print_html_header(status_code=302, location="/purojitu/login.html")
        exit()

    user_id = get_user_id_from_session(session_id)
    if not user_id:
        # 有効なセッションユーザーがいない場合はログインページへリダイレクト
        print_html_header(status_code=302, location="/purojitu/login.html")
        exit()

    # POSTメソッドかつconfirm='yes'の場合は出品確定処理
    if os.environ.get('REQUEST_METHOD') == 'POST' and form.getvalue('confirm') == 'yes':
        try:
            # 各値を取得し、エスケープは後で表示する際に適用
            title = form.getvalue('title', '')
            description = form.getvalue('description', '')
            price = int(form.getvalue('price', 0)) # 数値に変換
            # sellerはhiddenフィールドから来るが、セッションのuser_idを使うべき
            # seller_name = form.getvalue('seller', '')
            image_url = form.getvalue('image_url', '')

            # DBに登録
            insert_item(user_id, title, description, price, image_url)

            # 登録成功後、完了ページへリダイレクト (PRGパターン)
            print_html_header(status_code=302, location="/purojitu/exhibition_complete.cgi")

        except ValueError:
            print_error_page("価格が不正な値です。", "/purojitu/exhibit.cgi")
        except Exception as e:
            print_error_page(f"出品処理中に予期せぬエラーが発生しました: {html.escape(str(e))}", "/purojitu/exhibit.cgi")

    elif os.environ.get('REQUEST_METHOD') == 'POST':
        # POSTでconfirm='yes'以外 (最初の確認画面表示)
        # ファイルアップロード処理
        image_url = save_uploaded_file('image')
        if image_url is None:
            # save_uploaded_file内でエラーハンドリングされているはずだが念のため
            print_error_page("画像ファイルのアップロードに失敗しました。", "/purojitu/exhibit.cgi")

        title = html.escape(form.getvalue('title', ''))
        category = html.escape(form.getvalue('category', ''))
        # 価格は数値変換前にエスケープせず、表示時にエスケープする
        price_str = form.getvalue('price', '')
        try:
            price = int(price_str)
            price_display = f"¥{price:,}" # 表示用のカンマ区切り
        except ValueError:
            print_error_page("価格が不正な値です。", "/purojitu/exhibit.cgi")
            return # エラーページ表示後、処理を終了

        description = html.escape(form.getvalue('description', ''))
        seller_name = html.escape(form.getvalue('seller_name', '')) # exhibit.cgiから渡される表示用の出品者名

        print_html_header() # 確認画面表示前にヘッダーを出力
        print_html_head(title="出品内容確認")
        print_header_content()

        print(f"""
        <div class="container">
            <h2 class="section-title">内容確認</h2>
            <section class="section">
                <div class="form-group"><span class="form-label">商品名:</span> {title}</div>
                <div class="form-group"><span class="form-label">カテゴリー:</span> {category}</div>
                <div class="form-group"><span class="form-label">価格:</span> {price_display}</div>
                <div class="form-group"><span class="form-label">説明:</span><pre style="white-space: pre-wrap;">{description}</pre></div>
                <div class="form-group"><span class="form-label">出品者:</span> {seller_name}</div>
                <div class="form-group">
                    <span class="form-label">商品画像:</span><br>
                    <img src="{html.escape(image_url)}" class="item-image-preview" alt="商品画像">
                </div>

                <form action="exhibition_conf.cgi" method="POST">
                    <input type="hidden" name="title" value="{html.escape(title)}">
                    <input type="hidden" name="description" value="{html.escape(description)}">
                    <input type="hidden" name="price" value="{html.escape(str(price))}">
                    <input type="hidden" name="image_url" value="{html.escape(image_url)}">
                    <input type="hidden" name="confirm" value="yes">
                    <div class="button-group">
                        <button type="submit" class="btn btn-primary">この内容で出品</button>
                        <a href="/purojitu/exhibit.cgi" class="btn btn-back">修正する</a>
                    </div>
                </form>
            </section>
        </div>
        """)
    else:
        # POSTメソッド以外での直接アクセスは不正とする
        print_error_page("不正なアクセスです。", "/purojitu/top.cgi")

    print_footer()

if __name__ == '__main__':
    main()
