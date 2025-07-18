#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import cgitb
import mysql.connector
import html
import os

cgitb.enable()

DB_CONFIG = {
    'host': 'localhost', 'user': 'user1', 'passwd': 'passwordA1!',
    'db': 'Free', 'charset': 'utf8'
}
CURRENT_USER_ID = 1

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def get_transaction_details(cursor, purchase_id, current_user_id):
    query = "SELECT p.item_id, i.title, i.price, p.buyer_id, buyer.username AS buyer_name, i.user_id AS seller_id, seller.username AS seller_name, p.status FROM purchases p JOIN items i ON p.item_id = i.item_id JOIN users buyer ON p.buyer_id = buyer.user_id JOIN users seller ON i.user_id = seller.user_id WHERE p.purchase_id = %s AND (p.buyer_id = %s OR i.user_id = %s)"
    cursor.execute(query, (purchase_id, current_user_id, current_user_id))
    return cursor.fetchone()

def get_messages(cursor, item_id):
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
    query = "SELECT reviewer_id, reviewee_id FROM user_reviews WHERE item_id = %s"
    cursor.execute(query, (item_id,))
    return cursor.fetchall()

def generate_messages_html(messages, current_user_id):
    if not messages: return "<p style='text-align:center; opacity:0.8;'>まだメッセージはありません。</p>"
    html_parts = []
    for msg in messages:
        sender_id, content, sent_at = msg
        msg_class = "sent" if sender_id == current_user_id else "received"
        html_parts.append(f'<div class="message-bubble {msg_class}"><div class="message-content">{html.escape(content).replace(chr(10), "<br>")}</div><div class="message-time">{sent_at.strftime("%m/%d %H:%M")}</div></div>')
    return "".join(html_parts)

def generate_action_form_html(data, user_reviews, current_user_id):
    purchase_id, item_id, buyer_id, seller_id, status = data
    reviewers = [r[0] for r in user_reviews]
    if current_user_id == seller_id:
        if status == 'shipping_pending':
            return f'<div class="action-panel"><form action="trade.cgi?purchase_id={purchase_id}" method="post"><input type="hidden" name="action" value="notify_shipment"><button type="submit" class="btn-action">発送しました</button></form></div>'
        if status == 'completed' and buyer_id in reviewers and seller_id not in reviewers:
            return f'<div class="action-panel review-panel"><h2 class="panel-title">購入者の評価</h2><form action="trade.cgi?purchase_id={purchase_id}" method="post"><input type="hidden" name="action" value="submit_review"><textarea name="review_comment" rows="4" placeholder="購入者の評価を記入してください" required></textarea><button type="submit" class="btn-action">評価を投稿する</button></form></div>'
    if current_user_id == buyer_id and status == 'shipped':
        return f'<div class="action-panel review-panel"><h2 class="panel-title">商品の受取評価</h2><form action="trade.cgi?purchase_id={purchase_id}" method="post"><input type="hidden" name="action" value="submit_review"><textarea name="review_comment" rows="4" placeholder="取引相手へのメッセージや感想を記入しましょう。" required></textarea><div class="receipt-check"><input type="checkbox" id="receipt" name="receipt" required><label for="receipt">商品が届きました</label></div><button type="submit" class="btn-action">評価を投稿して取引を完了する</button></form></div>'
    if status == 'completed' and seller_id in reviewers and buyer_id in reviewers:
        return '<div class="action-panel"><p class="panel-title">取引は完了しました</p></div>'
    return ""

def main():
    form = cgi.FieldStorage()
    purchase_id = form.getfirst('purchase_id')
    new_message_content = form.getfirst('message')
    action = form.getfirst('action')

    if not purchase_id:
        print("Content-Type: text/html; charset=utf-8\n")
        print("<h1>エラー</h1><p>取引IDが指定されていません。</p>")
        return

    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if action == 'notify_shipment':
            update_transaction_status(cursor, purchase_id, 'shipped')
            connection.commit()
        elif action == 'submit_review':
            review_comment = form.getfirst('review_comment')
            if review_comment:
                trans_data = get_transaction_details(cursor, purchase_id, CURRENT_USER_ID)
                item_id, _, _, buyer_id, _, seller_id, _, _ = trans_data
                reviewee_id = seller_id if CURRENT_USER_ID == buyer_id else buyer_id
                post_review(cursor, item_id, CURRENT_USER_ID, reviewee_id, review_comment)
                if CURRENT_USER_ID == buyer_id:
                    update_transaction_status(cursor, purchase_id, 'completed')
                connection.commit()
        if new_message_content:
            trans_data = get_transaction_details(cursor, purchase_id, CURRENT_USER_ID)
            if trans_data:
                item_id, _, _, buyer_id, _, seller_id, _, _ = trans_data
                receiver_id = seller_id if CURRENT_USER_ID == buyer_id else buyer_id
                post_message(cursor, CURRENT_USER_ID, receiver_id, item_id, new_message_content)
                connection.commit()

        if action or new_message_content:
            print(f"Location: trade.cgi?purchase_id={purchase_id}\n")
            return

        transaction = get_transaction_details(cursor, purchase_id, CURRENT_USER_ID)
        if not transaction:
            print("Content-Type: text/html; charset=utf-8\n")
            print("<h1>エラー</h1><p>指定された取引は存在しないか、アクセス権がありません。</p>")
            return

        item_id, item_title, _, buyer_id, buyer_name, seller_id, seller_name, status = transaction
        messages = get_messages(cursor, item_id)
        user_reviews = get_reviews_for_trade(cursor, item_id)
        
        messages_html = generate_messages_html(messages, CURRENT_USER_ID)
        action_data = (purchase_id, item_id, buyer_id, seller_id, status)
        action_form_html = generate_action_form_html(action_data, user_reviews, CURRENT_USER_ID)

        print("Content-Type: text/html; charset=utf-8\n")
        print(f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8"><title>取引画面 - フリマ</title>
    <style>
        body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); min-height:100vh; color:white; margin:0; padding:20px; }}
        .container {{ max-width:800px; margin:0 auto; display:flex; flex-direction:column; height:calc(100vh - 40px); background:rgba(255,255,255,0.1); backdrop-filter:blur(10px); border-radius:20px; border:1px solid rgba(255,255,255,0.2); }}
        .item-header {{ text-align:center; padding:1rem; border-bottom:1px solid rgba(255,255,255,0.2); }}
        .item-header h1 {{ font-size:1.2rem; margin:0; }}
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
        .receipt-check {{ margin-bottom:1rem; }}
    </style>
</head>
<body>
    <div class="container">
        <header class="item-header"><h1>{html.escape(item_title)}</h1><p>取引相手: {html.escape(seller_name if CURRENT_USER_ID == buyer_id else buyer_name)}さん</p></header>
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
