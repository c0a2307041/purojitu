#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import html
import os
import cgitb

cgitb.enable() # デバッグ用。本番環境では無効にするか、エラーログにのみ出力する設定を推奨

# --- HTMLテンプレート関数 (exhibition_conf.cgi と同様) ---
def print_html_head(title="出品完了 - フリマ"):
    print(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: white; margin: 0; padding: 0; display: flex; flex-direction: column; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; width: 100%; box-sizing: border-box; flex-grow: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
        header {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding: 1rem 0; position: sticky; top: 0; z-index: 100; }}
        .header-content {{ display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-size: 2rem; font-weight: bold; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .btn {{ padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }}
        .btn-primary {{ background: linear-gradient(45deg, #ff6b6b, #ff8e8e); color: white; }}
        .btn:hover {{ transform: translateY(-2px); }}
        .section-title {{ text-align: center; font-size: 2.5rem; margin: 2rem 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); color: #82E0AA; /* 成功時の色 */ }}
        .section {{ background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 2rem; margin: 2rem 0; border: 1px solid rgba(255, 255, 255, 0.2); }}
        footer {{ text-align: center; padding: 2rem 0; margin-top: auto; background: rgba(0,0,0,0.2); }}
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


# --- メイン処理 ---
print("Content-Type: text/html; charset=utf-8\n") # ヘッダーを最初に出力

print_html_head()
print_header_content()

print("""
<div class="container">
    <h2 class="section-title">✅ 出品が完了しました！</h2>
    <section class="section">
        <p>ご出品ありがとうございます。</p>
        <a href="/purojitu/top.cgi" class="btn btn-primary">トップへ戻る</a>
    </section>
</div>
""")

print_footer()
