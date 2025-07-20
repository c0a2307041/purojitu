#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import cgitb
import mysql.connector
import html
import os
from http import cookies # クッキーを扱うために追加
from datetime import datetime # セッションの期限切れチェックのため追加

cgitb.enable()

DB_CONFIG = {
    'host': 'localhost', 'user': 'user1', 'passwd': 'passwordA1!',
    'db': 'Free', 'charset': 'utf8'
}
# CURRENT_USER_ID は認証後に動的に設定されるため、削除します

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


def get_transaction_details(cursor, purchase_id, current_user_id):
    # カーソルが辞書形式なので、結果も辞書で返る
    query = "SELECT p.item_id, i.title, i.price, p.buyer_id, buyer.username AS buyer_name, i.user_id AS seller_id, seller.username AS seller_name, p.status FROM purchases p JOIN items i ON p.item_id = i.item_id JOIN users buyer ON p.buyer_id = buyer.user_id JOIN users seller ON i.user_id = seller.user_id WHERE p.purchase_id = %s AND (p.buyer_id = %s OR i.user_id = %s)"
    cursor.execute(query, (purchase_id, current_user_id, current_user_id))
    return cursor.fetchone()

def get_messages(cursor, item_id):
    # カーソルが辞書形式なので、結果も辞書で返る
    query = "SELECT sender_id, content, sent_at FROM messages WHERE item_id = %s ORDER BY sent_at ASC"
    cursor.execute(query, (item_id,))
    return cursor.fetchall()

def post_message(cursor, sender_id, receiver_id, item_id, content):
    query = "INSERT INTO messages (sender_id, receiver_id, item_id, content) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (sender_id, receiver_id, item_id, content))

def update_transaction_status(cursor, purchase_id, new_status):
    query = "UPDATE purchases SET status = %s WHERE purchase_id = %s"
    cursor.execute(query, (new_status, purchase_id))

def post_review(cursor, item_id, reviewer_id, reviewee_id, content):
    query = "INSERT INTO user_reviews (item_id, reviewer_id, reviewee_id, content) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (item_id, reviewer_id, reviewee_id, content))

def get_reviews_for_trade(cursor, item_id):
    # カーソルが辞書形式なので、結果も辞書で返る
    query = "SELECT reviewer_id, reviewee_id FROM user_reviews WHERE item_id = %s"
    cursor.execute(query, (item_id,))
    return cursor.fetchall()

def generate_messages_html(messages, current_user_id):
    if not messages: return "<p style='text-align:center; opacity:0.8;'>まだメッセージはありません。</p>"
    html_parts = []
    for msg in messages:
        # 辞書形式でキーを指定してアクセス
        sender_id, content, sent_at = msg['sender_id'], msg['content'], msg['sent_at']
        msg_class = "sent" if sender_id == current_user_id else "received"
        html_parts.append(f'<div class="message-bubble {msg_class}"><div class="message-content">{html.escape(content).replace(chr(10), "<br>")}</div><div class="message-time">{sent_at.strftime("%m/%d %H:%M")}</div></div>')
    return "".join(html_parts)

def generate_action_form_html(data, user_reviews, current_user_id):
    # dataは辞書なので、キーでアクセス
    purchase_id = data['purchase_id']
    item_id = data['item_id']
    buyer_id = data['buyer_id']
    seller_id = data['seller_id']
    status = data['status']

    # user_reviewsも辞書形式で返るため、修正
    reviewers = [r['reviewer_id'] for r in user_reviews]

    if current_user_id == seller_id: # 出品者の場合
        if status == 'shipping_pending':
            return f'<div class="action-panel"><form action="trade.cgi?purchase_id={purchase_id}" method="post"><input type="hidden" name="action" value="notify_shipment"><button type="submit" class="btn-action">発送しました</button></form></div>'
        # 出品者からのレビューがまだで、かつ購入者からのレビューがある場合
        if status == 'completed' and buyer_id in reviewers and seller_id not in reviewers:
            return f'<div class="action-panel review-panel"><h2 class="panel-title">購入者の評価</h2><form action="trade.cgi?purchase_id={purchase_id}" method="post"><input type="hidden" name="action" value="submit_review"><textarea name="review_comment" rows="4" placeholder="購入者の評価を記入してください" required></textarea><button type="submit" class="btn-action">評価を投稿する</button></form></div>'
    
    if current_user_id == buyer_id: # 購入者の場合
        if status == 'shipped':
            return f'<div class="action-panel review-panel"><h2 class="panel-title">商品の受取評価</h2><form action="trade.cgi?purchase_id={purchase_id}" method="post"><input type="hidden" name="action" value="submit_review"><textarea name="review_comment" rows="4" placeholder="取引相手へのメッセージや感想を記入しましょう。" required></textarea><div class="receipt-check"><input type="checkbox" id="receipt" name="receipt" required><label for="receipt">商品が届きました</label></div><button type="submit" class="btn-action">評価を投稿して取引を完了する</button></form></div>'
    
    # 両者からのレビューが揃っている場合（取引完了）
    if status == 'completed' and seller_id in reviewers and buyer_id in reviewers:
        return '<div class="action-panel"><p class="panel-title">取引は完了しました</p></div>'
    
    return ""


def main():
    connection = None
    user_id = None # 認証後に設定されるユーザーID

    try:
        connection = get_db_connection()
        # カーソルを辞書形式に設定
        cursor = connection.cursor(dictionary=True)

        # --- セッション認証ロジック ---
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
                return # 処理を終了

            user_id = valid_user_id # 認証されたユーザーIDを設定
            # user_name = get_user_info(cursor, user_id) # 必要であればユーザー名も取得
        else:
            # クッキーに必要な情報がない場合もログインページへ
            print("Status: 302 Found")
            print("Location: login.html")
            print()
            return # 処理を終了
        # --- セッション認証ロジック 終わり ---


        form = cgi.FieldStorage()
        purchase_id = form.getfirst('purchase_id')
        new_message_content = form.getfirst('message')
        action = form.getfirst('action')

        if not purchase_id:
            print("Content-Type: text/html; charset=utf-8\n")
            print("<h1>エラー</h1><p>取引IDが指定されていません。</p>")
            return

        # アクション処理（メッセージ送信、ステータス更新、評価投稿）
        if action == 'notify_shipment':
            update_transaction_status(cursor, purchase_id, 'shipped')
            connection.commit()
        elif action == 'submit_review':
            review_comment = form.getfirst('review_comment')
            if review_comment:
                trans_data = get_transaction_details(cursor, purchase_id, user_id) # user_idを使用
                if trans_data:
                    # 辞書アクセスに修正
                    item_id = trans_data['item_id']
                    buyer_id = trans_data['buyer_id']
                    seller_id = trans_data['seller_id']

                    # どちらが評価者かによって、評価される相手を決定
                    reviewee_id = seller_id if user_id == buyer_id else buyer_id
                    post_review(cursor, item_id, user_id, reviewee_id, review_comment) # user_idを使用

                    # 購入者からの評価の場合のみ取引ステータスを完了にする
                    if user_id == buyer_id:
                        update_transaction_status(cursor, purchase_id, 'completed')
                    connection.commit()
        
        if new_message_content and new_message_content.strip() != "":
            trans_data = get_transaction_details(cursor, purchase_id, user_id) # user_idを使用
            if trans_data:
                # 辞書アクセスに修正
                item_id = trans_data['item_id']
                buyer_id = trans_data['buyer_id']
                seller_id = trans_data['seller_id']

                # メッセージの受信者を決定
                receiver_id = seller_id if user_id == buyer_id else buyer_id
                post_message(cursor, user_id, receiver_id, item_id, new_message_content.strip()) # user_idを使用
                connection.commit()

        # アクションやメッセージ送信後はリダイレクト
        if action or (new_message_content and new_message_content.strip() != ""):
            print(f"Location: trade.cgi?purchase_id={purchase_id}\n")
            return

        # 取引詳細の取得（認証された user_id を使用）
        transaction = get_transaction_details(cursor, purchase_id, user_id)
        if not transaction:
            print("Content-Type: text/html; charset=utf-8\n")
            print("<h1>エラー</h1><p>指定された取引は存在しないか、アクセス権がありません。</p>")
            return

        # 辞書アクセスに修正
        item_id = transaction['item_id']
        item_title = transaction['title']
        buyer_id = transaction['buyer_id']
        buyer_name = transaction['buyer_name']
        seller_id = transaction['seller_id']
        seller_name = transaction['seller_name']
        status = transaction['status']

        messages = get_messages(cursor, item_id)
        user_reviews = get_reviews_for_trade(cursor, item_id)
        
        messages_html = generate_messages_html(messages, user_id) # user_idを使用
        
        # generate_action_form_htmlに渡すデータは辞書形式にする
        action_data = {
            'purchase_id': purchase_id,
            'item_id': item_id,
            'buyer_id': buyer_id,
            'seller_id': seller_id,
            'status': status
        }
        action_form_html = generate_action_form_html(action_data, user_reviews, user_id) # user_idを使用

        print("Content-Type: text/html; charset=utf-8\n")
        print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8"><title>取引画面 - フリマ</title>
    <style>
        body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); min-height:100vh; color:white; margin:0; padding:20px; }}
        .container {{ max-width:800px; margin:0 auto; display:flex; flex-direction:column; height:calc(100vh - 40px); background:rgba(255,255,255,0.1); backdrop-filter:blur(10px); border-radius:20px; border:1px solid rgba(255,255,255,0.2); }}
        
        /* ヘッダーの新しいスタイル */
        .page-header {{ 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            padding: 1rem; 
            border-bottom: 1px solid rgba(255,255,255,0.2); 
            gap: 1rem; /* 要素間のスペース */
        }}
        .item-info-center {{
            flex-grow: 1; /* 中央の要素が利用可能なスペースを占有 */
            text-align: center;
        }}
        .item-info-center h1 {{ font-size:1.2rem; margin:0; }}
        .item-info-center p {{ font-size:0.9rem; margin:0.5rem 0 0; opacity:0.8; }} /* 取引相手の情報を調整 */

        .btn-back-to-mypage {{ 
            background:rgba(255,255,255,0.2); 
            color:white; 
            padding:0.5rem 1rem; 
            border-radius:25px; 
            text-decoration:none; 
            font-size:0.9rem;
            white-space: nowrap; /* ボタン内のテキストが改行されないように */
        }}
        /* レイアウト調整用のダミー要素 */
        .header-placeholder {{
            width: 100px; /* btn-back-to-mypageと同じくらいの幅を確保 */
            visibility: hidden; /* 見えないがスペースは確保 */
        }}

        .messages-area {{ flex-grow:1; padding:1rem; overflow-y:auto; }}
        .message-bubble {{ max-width:70%; margin-bottom:1rem; padding:0.8rem 1rem; border-radius:20px; line-height:1.5; }}
        .message-bubble.sent {{ background:#8e83f3; margin-left:auto; border-bottom-right-radius:5px; }}
        .message-bubble.received {{ background:rgba(0,0,0,0.2); margin-right:auto; border-bottom-left-radius:5px; }}
        .message-time {{ font-size:0.75rem; text-align:right; opacity:0.7; margin-top:0.3rem; }}
        .message-form {{ display:flex; padding:1rem; border-top:1px solid rgba(255,255,255,0.2); }}
        .message-form textarea {{ flex-grow:1; resize:none; padding:0.8rem; border:none; border-radius:15px; background:rgba(255,255,255,0.9); color:#333; }}
        .message-form button {{ margin-left:1rem; border:none; background:#ff6b6b; color:white; border-radius:15px; padding:0 1.5rem; font-weight:bold; cursor:pointer; }}
        .action-panel {{ padding:1.5rem; border-bottom:1px solid rgba(255,255,255,0.2); background:rgba(0,0,0,0.1); }}
        .panel-title {{ font-size:1.1rem; text-align:center; margin-bottom:1rem; }}
        .btn-action {{ width:100%; padding:0.8rem; border:none; border-radius:10px; background:linear-gradient(45deg,#ff6b6b,#ff8e8e); color:white; font-size:1rem; font-weight:bold; cursor:pointer; }}
        .review-panel textarea {{ width:100%; padding:0.8rem; border:none; border-radius:10px; background:rgba(255,255,255,0.9); margin-bottom:1rem; color:#333; }}
        .receipt-check {{ margin-bottom:1rem; display:flex; align-items:center; }}
        .receipt-check input[type="checkbox"] {{ margin-right: 0.5rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="page-header">
            <a href="account.cgi" class="btn-back-to-mypage">マイページへ戻る</a>
            <div class="item-info-center">
                <h1>{html.escape(item_title)}</h1>
                <p>取引相手: {html.escape(seller_name if user_id == buyer_id else buyer_name)}さん</p>
            </div>
            <div class="header-placeholder"></div> </div>
        {action_form_html}
        <main class="messages-area">{messages_html}</main>
        <footer class="message-form"><form action="trade.cgi?purchase_id={purchase_id}" method="post" style="display:contents;"><textarea name="message" rows="2" placeholder="メッセージを入力..."></textarea><button type="submit">送信</button></form></footer>
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
