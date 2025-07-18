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
    # SQLインジェクション脆弱性があるため、実際にはDBIとプレースホルダを使用すべきです。
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>エラー - フリマサイト</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; color: white; text-align: center; }
        .error-container { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 40px; border: 1px solid rgba(255, 255, 255, 0.2); max-width: 500px; margin: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .error-container h1 { font-size: 2.5rem; margin-bottom: 20px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .error-container p { font-size: 1.1rem; margin-bottom: 30px; }
        .btn { padding: 0.7rem 1.5rem; border: none; border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; text-decoration: none; display: inline-block; text-align: center; }
        .btn-primary { background: linear-gradient(45deg, #ff6b6b, #ff8e8e); color: white; box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4); }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="error-container">
        <h1>エラー</h1>
        <p>$message</p>
        <a href="/" class="btn btn-primary">トップページに戻る</a>
    </div>
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
    
    # 統計データ
    my $items_for_sale_count = scalar @$items_for_sale;
    my $sold_items_count = scalar @$sold_items;
    my $reviews_count = scalar @$reviews;

    print qq{
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$username さんのページ - フリマサイト</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        header {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            padding: 1rem 0;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 2rem;
            font-weight: bold;
            color: white;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .nav-buttons {
            display: flex;
            gap: 1rem;
        }
        
        .btn {
            padding: 0.7rem 1.5rem;
            border: none;
            border-radius: 25px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #ff6b6b, #ff8e8e);
            color: white;
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
        }
        
        .btn-secondary {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.2);
        }
        
        .hero {
            text-align: center;
            padding: 3rem 0;
            color: white;
        }
        
        .hero h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .hero p {
            font-size: 1.2rem;
            margin-bottom: 1rem;
            opacity: 0.9;
        }
        
        .profile-section {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            margin: 2rem 0;
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
        }
        
        .profile-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .profile-info p {
            padding: 0.5rem 1rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            font-size: 1rem;
        }
        
        .section-title {
            text-align: center;
            font-size: 2rem;
            color: white;
            margin-bottom: 2rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            padding-top: 1rem;
        }

        .products-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }

        .product-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            overflow: hidden;
            transition: all 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.2);
            cursor: pointer;
        }

        .product-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        .product-image {
            width: 100%;
            height: 200px;
            background: linear-gradient(45deg, #ff9a9e, #fecfef);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            color: white;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            object-fit: cover;
        }
        
        .product-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .product-info {
            padding: 1.5rem;
            color: white;
        }

        .product-title {
            font-size: 1.1rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }

        .product-price {
            font-size: 1.3rem;
            font-weight: bold;
            color: #ff6b6b;
            margin-bottom: 0.5rem;
        }
        
        .product-description {
            font-size: 0.9rem;
            margin-bottom: 1rem;
            opacity: 0.8;
            max-height: 4.5em;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .product-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9rem;
            opacity: 0.8;
        }

        .review-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
            transition: all 0.3s ease;
        }

        .review-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }

        .review-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }

        .review-content {
            font-size: 1rem;
            line-height: 1.6;
            margin-bottom: 0.5rem;
        }

        .review-meta {
            font-size: 0.9rem;
            opacity: 0.8;
            text-align: right;
        }

        .stats {
            display: flex;
            justify-content: space-around;
            padding: 2rem 0;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            margin: 2rem 0;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .stat-item {
            text-align: center;
            color: white;
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
            display: block;
        }
        
        .stat-label {
            font-size: 0.9rem;
            opacity: 0.8;
        }

        .message-section {
            text-align: center;
            padding: 2rem 0;
            color: white;
        }

        .empty-state {
            text-align: center;
            color: white;
            opacity: 0.8;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            margin: 1rem 0;
        }

        footer {
            background: rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(10px);
            color: white;
            text-align: center;
            padding: 2rem 0;
            margin-top: 3rem;
        }
        
        \@media (max-width: 768px) {
            .hero h1 {
                font-size: 2rem;
            }
            
            .stats {
                flex-direction: column;
                gap: 1rem;
            }
            
            .header-content {
                flex-direction: column;
                gap: 1rem;
            }
            
            .profile-info {
                grid-template-columns: 1fr;
            }
            
            .products-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div class="logo">🛍️ メル仮</div>
                <div class="nav-buttons">
                    <a href="login.html" class="btn btn-secondary">ログイン</a>
                    <a href="#" class="btn btn-primary">出品する</a>
                </div>
            </div>
        </div>
    </header>

    <main>
        <div class="container">
            <section class="hero">
                <h1>$username さんのページ</h1>
                <p>出品者の商品と取引実績をご確認ください</p>
            </section>

            <section class="profile-section">
                <div class="profile-info">
                    <p><strong>👤 ニックネーム:</strong> $username</p>
                    <p><strong>📅 登録日:</strong> $created_at</p>
                    <p><strong>📍 所在地:</strong> $location</p>
                </div>
            </section>

            <section class="stats">
                <div class="stat-item">
                    <span class="stat-number">$items_for_sale_count</span>
                    <span class="stat-label">出品中</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">$sold_items_count</span>
                    <span class="stat-label">売却済み</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">$reviews_count</span>
                    <span class="stat-label">レビュー</span>
                </div>
            </section>

            <section class="products-section">
                <h2 class="section-title">出品中の商品</h2>
                <div class="products-grid">
    };
    
    if (@$items_for_sale) {
        foreach my $item (@$items_for_sale) {
            my $title = encode_entities($item->{title});
            my $description = encode_entities($item->{description});
            my $price = format_price($item->{price});
            my $image_path = encode_entities($item->{image_path});
            my $created_at_formatted = format_date($item->{created_at});
            
            print qq{
                    <div class="product-card" onclick="location.href='item_detail.cgi?item_id=$item->{item_id}'">
                        <div class="product-image">
                            <img src="$image_path" alt="$title" onerror="this.parentElement.innerHTML='🛍️'">
                        </div>
                        <div class="product-info">
                            <div class="product-title">$title</div>
                            <div class="product-price">$price</div>
                            <div class="product-description">$description</div>
                            <div class="product-meta">
                                <span>出品日: $created_at_formatted</span>
                                <span>👁️ 詳細</span>
                            </div>
                        </div>
                    </div>
            };
        }
    } else {
        print qq{<div class="empty-state">現在出品中の商品はありません。</div>};
    }
    
    print qq{
                </div>
            </section>
            
            <section class="products-section">
                <h2 class="section-title">評価・レビュー</h2>
    };
    
    if (@$reviews) {
        foreach my $review (@$reviews) {
            my $content = encode_entities($review->{content});
            my $reviewer_name = encode_entities($review->{reviewer_name});
            my $item_title = encode_entities($review->{item_title});
            my $created_at_formatted = format_date($review->{created_at});
            
            print qq{
                    <div class="review-card">
                        <div class="review-header">
                            <strong>⭐ $reviewer_name さんからのレビュー</strong>
                            <span>$created_at_formatted</span>
                        </div>
                        <div class="review-content">$content</div>
                        <div class="review-meta">商品: $item_title</div>
                    </div>
            };
        }
    } else {
        print qq{<div class="empty-state">まだレビューがありません。</div>};
    }
    
    print qq{
            </section>
            
            <section class="products-section">
                <h2 class="section-title">売却済み商品</h2>
                <div class="products-grid">
    };
    
    if (@$sold_items) {
        foreach my $item (@$sold_items) {
            my $title = encode_entities($item->{title});
            my $price = format_price($item->{price});
            my $buyer_name = encode_entities($item->{buyer_name});
            my $purchased_at_formatted = format_date($item->{purchased_at});
            my $image_path = encode_entities($item->{image_path} || '/images/no-image.jpg');
            
            print qq{
                    <div class="product-card">
                        <div class="product-image">
                            <img src="$image_path" alt="$title" onerror="this.parentElement.innerHTML='✅'">
                        </div>
                        <div class="product-info">
                            <div class="product-title">$title</div>
                            <div class="product-price">$price</div>
                            <div class="product-meta">
                                <span>購入者: $buyer_name</span>
                                <span>売却日: $purchased_at_formatted</span>
                            </div>
                        </div>
                    </div>
            };
        }
    } else {
        print qq{<div class="empty-state">売却済みの商品はありません。</div>};
    }
    
    print qq{
                </div>
            </section>

            <section class="message-section">
                <p>この出品者との取引でご不明な点がございましたら、メッセージでお問い合わせください。</p>
                <a href="messages.cgi?user_id=$seller_info->{user_id}" class="btn btn-primary">💬 メッセージを送る</a>
            </section>
            
            <div style="text-align: center; margin-top: 3rem;">
                <a href="/" class="btn btn-secondary">← トップページに戻る</a>
            </div>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2025 フリマ. All rights reserved. | 利用規約 | プライバシーポリシー</p>
        </div>
    </footer>
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
