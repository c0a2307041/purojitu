#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use HTML::Entities;
use POSIX qw(strftime);
use Encode qw(decode encode);

# CGIオブジェクトの作成
my $cgi = CGI->new;

# データベース接続設定
my $db_user = "root";
my $db_pass = "passwordA1!";
my $db_name = "Free";
my $db_host = "localhost";

# HTTPヘッダーの出力
print $cgi->header(-type => 'text/html', -charset => 'UTF-8');

# URLパラメータから出品者のuser_idを取得
my $seller_id = $cgi->param('user_id');

# user_idが指定されていない場合のエラーハンドリング
if (!$seller_id || $seller_id !~ /^\d+$/) {
    print_error_page("無効なユーザーIDです。");
    exit;
}

# データベースに接続（mysqlコマンドを使用）
sub execute_mysql_query {
    my ($query) = @_;
    
    # UTF-8でエンコーディングを指定
    my $cmd = "mysql -h$db_host -u$db_user -p$db_pass $db_name --default-character-set=utf8mb4 -e \"$query\" 2>/dev/null";
    
    # コマンドの実行
    my @results = `$cmd`;
    
    # 各行をUTF-8でデコード
    for my $i (0..$#results) {
        chomp $results[$i];
        # バイト列をUTF-8文字列に変換
        eval {
            $results[$i] = decode('utf8', $results[$i]);
        };
        if ($@) {
            # デコードに失敗した場合はそのまま使用
            chomp $results[$i];
        }
    }
    
    return @results;
}

# 出品者情報を取得
my $seller_info = get_seller_info($seller_id);
if (!$seller_info) {
    print_error_page("指定されたユーザーが見つかりません。");
    exit;
}

# 各セクションのデータを取得
my $items_for_sale = get_items_for_sale($seller_id);
my $sold_items = get_sold_items($seller_id);
my $reviews = get_reviews($seller_id);

# HTMLページを出力
print_html_page($seller_info, $items_for_sale, $sold_items, $reviews);

# ========== サブルーチン ==========

# 出品者情報取得
sub get_seller_info {
    my ($user_id) = @_;
    
    my $query = "SELECT u.user_id, u.username, u.created_at, a.prefecture, a.city FROM users u LEFT JOIN addresses a ON u.address_id = a.address_id WHERE u.user_id = $user_id";
    my @results = execute_mysql_query($query);
    
    return undef if @results < 2;  # ヘッダー行がない場合
    
    my $data_line = $results[1];
    my @fields = split(/\t/, $data_line);
    
    return {
        user_id => $fields[0] || '',
        username => $fields[1] || '',
        created_at => $fields[2] || '',
        prefecture => $fields[3] || '',
        city => $fields[4] || ''
    };
}

# 出品中の商品一覧取得
sub get_items_for_sale {
    my ($user_id) = @_;
    
    my $query = "SELECT i.item_id, i.title, i.description, i.price, i.image_path, i.created_at FROM items i LEFT JOIN purchases p ON i.item_id = p.item_id WHERE i.user_id = $user_id AND p.purchase_id IS NULL ORDER BY i.created_at DESC";
    my @results = execute_mysql_query($query);
    
    my @items = ();
    for my $i (1..$#results) {  # ヘッダー行をスキップ
        my @fields = split(/\t/, $results[$i]);
        push @items, {
            item_id => $fields[0] || '',
            title => $fields[1] || '',
            description => $fields[2] || '',
            price => $fields[3] || '',
            image_path => $fields[4] || '',
            created_at => $fields[5] || ''
        };
    }
    
    return \@items;
}

# 売却済み商品一覧取得
sub get_sold_items {
    my ($user_id) = @_;
    
    my $query = "SELECT i.item_id, i.title, i.price, i.image_path, p.purchased_at, u.username as buyer_name FROM items i JOIN purchases p ON i.item_id = p.item_id JOIN users u ON p.buyer_id = u.user_id WHERE i.user_id = $user_id ORDER BY p.purchased_at DESC";
    my @results = execute_mysql_query($query);
    
    my @items = ();
    for my $i (1..$#results) {  # ヘッダー行をスキップ
        my @fields = split(/\t/, $results[$i]);
        push @items, {
            item_id => $fields[0] || '',
            title => $fields[1] || '',
            price => $fields[2] || '',
            image_path => $fields[3] || '',
            purchased_at => $fields[4] || '',
            buyer_name => $fields[5] || ''
        };
    }
    
    return \@items;
}

# レビュー取得
sub get_reviews {
    my ($user_id) = @_;
    
    my $query = "SELECT r.content, r.created_at, u.username as reviewer_name, i.title as item_title FROM reviews r JOIN items i ON r.item_id = i.item_id JOIN users u ON r.reviewer_id = u.user_id WHERE i.user_id = $user_id ORDER BY r.created_at DESC";
    my @results = execute_mysql_query($query);
    
    my @reviews = ();
    for my $i (1..$#results) {  # ヘッダー行をスキップ
        my @fields = split(/\t/, $results[$i]);
        push @reviews, {
            content => $fields[0] || '',
            created_at => $fields[1] || '',
            reviewer_name => $fields[2] || '',
            item_title => $fields[3] || ''
        };
    }
    
    return \@reviews;
}

# エラーページ表示
sub print_error_page {
    my ($message) = @_;
    
    print qq{
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>エラー - フリマサイト</title>
</head>
<body>
    <h1>エラー</h1>
    <p>$message</p>
    <p><a href="/">トップページに戻る</a></p>
</body>
</html>
    };
}

# メインHTMLページ表示
sub print_html_page {
    my ($seller_info, $items_for_sale, $sold_items, $reviews) = @_;
    
    my $username = encode_entities($seller_info->{username});
    my $prefecture = encode_entities($seller_info->{prefecture} || '未設定');
    my $city = encode_entities($seller_info->{city} || '');
    my $created_at = format_date($seller_info->{created_at});
    my $location = $prefecture . ($city ? " $city" : '');
    
    print qq{
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>$username さんのページ - フリマサイト</title>
</head>
<body>
    <h1>$username さんのページ</h1>
    
    <h2>ユーザー情報</h2>
    <p><strong>ニックネーム:</strong> $username</p>
    <p><strong>登録日:</strong> $created_at</p>
    <p><strong>所在地:</strong> $location</p>
    
    <h2>出品中の商品一覧</h2>
    };
    
    if (@$items_for_sale) {
        foreach my $item (@$items_for_sale) {
            my $title = encode_entities($item->{title});
            my $description = encode_entities($item->{description});
            my $price = format_price($item->{price});
            my $image_path = encode_entities($item->{image_path});
            my $created_at = format_date($item->{created_at});
            
            print qq{
                <div>
                    <h3>$title</h3>
                    <p>$description</p>
                    <p>価格: $price</p>
                    <p>画像: <img src="$image_path" alt="$title" width="100" onerror="this.src='/images/no-image.jpg'"></p>
                    <p>出品日: $created_at</p>
                </div>
                <hr>
            };
        }
    } else {
        print qq{<p>現在出品中の商品はありません。</p>};
    }
    
    print qq{
    <h2>評価・レビュー</h2>
    };
    
    if (@$reviews) {
        foreach my $review (@$reviews) {
            my $content = encode_entities($review->{content});
            my $reviewer_name = encode_entities($review->{reviewer_name});
            my $item_title = encode_entities($review->{item_title});
            my $created_at = format_date($review->{created_at});
            
            print qq{
                <div>
                    <h4>$reviewer_name さんからのレビュー</h4>
                    <p>$content</p>
                    <p>商品: $item_title | 投稿日: $created_at</p>
                </div>
                <hr>
            };
        }
    } else {
        print qq{<p>まだレビューがありません。</p>};
    }
    
    print qq{
    <h2>売却済み商品一覧</h2>
    };
    
    if (@$sold_items) {
        foreach my $item (@$sold_items) {
            my $title = encode_entities($item->{title});
            my $price = format_price($item->{price});
            my $buyer_name = encode_entities($item->{buyer_name});
            my $purchased_at = format_date($item->{purchased_at});
            
            print qq{
                <div>
                    <h3>$title</h3>
                    <p>価格: $price</p>
                    <p>購入者: $buyer_name | 売却日: $purchased_at</p>
                </div>
                <hr>
            };
        }
    } else {
        print qq{<p>売却済みの商品はありません。</p>};
    }
    
    print qq{
    <h2>メッセージ</h2>
    <p>この出品者との取引でご不明な点がございましたら、メッセージでお問い合わせください。</p>
    <p><a href="messages.cgi?user_id=$seller_info->{user_id}">メッセージを送る</a></p>
    
    <p><a href="/">← トップページに戻る</a></p>
</body>
</html>
    };
}

# 日付フォーマット関数
sub format_date {
    my ($datetime) = @_;
    return '未設定' unless $datetime;
    
    # MySQLの日付形式をパース
    if ($datetime =~ /^(\d{4})-(\d{2})-(\d{2})/) {
        return "$1年$2月$3日";
    }
    return $datetime;
}

# 価格フォーマット関数
sub format_price {
    my ($price) = @_;
    return '価格未設定' unless defined $price;
    
    # 3桁区切りでカンマを追加
    $price =~ s/(\d)(?=(\d{3})+(?!\d))/$1,/g;
    return "¥$price";
}

# デバッグ用：生データを確認する関数
sub debug_mysql_output {
    my ($user_id) = @_;
    
    print "<h2>デバッグ情報</h2>\n";
    
    # 基本的な接続テスト
    my $test_cmd = "mysql -h$db_host -u$db_user -p$db_pass $db_name --default-character-set=utf8mb4 -e \"SELECT 1\" 2>&1";
    my @test_results = `$test_cmd`;
    print "<h3>接続テスト結果:</h3>\n";
    print "<pre>" . join("", @test_results) . "</pre>\n";
    
    # データベースの文字セット確認
    my $charset_cmd = "mysql -h$db_host -u$db_user -p$db_pass $db_name --default-character-set=utf8mb4 -e \"SHOW VARIABLES LIKE 'character_set%'\" 2>&1";
    my @charset_results = `$charset_cmd`;
    print "<h3>文字セット設定:</h3>\n";
    print "<pre>" . join("", @charset_results) . "</pre>\n";
    
    # usersテーブルの確認
    my $users_cmd = "mysql -h$db_host -u$db_user -p$db_pass $db_name --default-character-set=utf8mb4 -e \"SELECT * FROM users WHERE user_id = $user_id\" 2>&1";
    my @users_results = `$users_cmd`;
    print "<h3>ユーザーデータ:</h3>\n";
    print "<pre>" . join("", @users_results) . "</pre>\n";
}
