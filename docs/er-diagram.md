# ER図(v1: 楽天市場の価格監視のみ)

SNSキーワード監視は将来拡張として設計上は考慮するが、テーブルはまだ作らない(まずは楽天市場の価格監視だけで一通り動かす)。

```mermaid
erDiagram
    USERS ||--o{ TRACKED_PRODUCTS : "追跡登録する"
    RETAILERS ||--o{ TRACKED_PRODUCTS : "掲載する"
    TRACKED_PRODUCTS ||--o{ PRICE_SNAPSHOTS : "価格履歴を持つ"
    TRACKED_PRODUCTS ||--o{ PRICE_ALERTS : "通知条件を持つ"
    PRICE_ALERTS ||--o{ NOTIFICATION_LOGS : "発火すると記録される"
    PRICE_SNAPSHOTS ||--o{ NOTIFICATION_LOGS : "きっかけになる"

    USERS {
        int id PK
        string email UK
        string hashed_password
        bool is_active
        datetime created_at
        datetime updated_at
    }

    RETAILERS {
        int id PK
        string name
        string slug UK
        string base_url
    }

    TRACKED_PRODUCTS {
        int id PK
        int user_id FK
        int retailer_id FK
        string external_product_id "楽天の itemCode"
        string name
        string product_url
        string image_url
        bool is_active
        datetime created_at
        datetime updated_at
    }

    PRICE_SNAPSHOTS {
        int id PK
        int tracked_product_id FK
        numeric price
        string currency
        datetime scraped_at
    }

    PRICE_ALERTS {
        int id PK
        int tracked_product_id FK
        enum rule_type "price_below / price_drop_percent"
        numeric threshold_value
        bool is_active
        datetime created_at
    }

    NOTIFICATION_LOGS {
        int id PK
        int price_alert_id FK
        int price_snapshot_id FK
        enum channel "email"
        datetime sent_at
    }
```

## 設計判断

- **`tracked_products` はユーザーに紐づける**: 「競合の商品を自分が監視対象として登録する」形にすることで、JWT認証・CRUD要件を自然に満たせる。複数ユーザーが同じ商品を登録しても別レコードとして扱う(シンプルさ優先。将来、商品マスタとユーザーの追跡設定を分離するリファクタは選択肢として残す)。
- **`retailers` をテーブルとして独立させる**: 現時点では楽天市場のみだが、対象ECサイトが増える前提を見せるために正規化しておく。`slug` を業務キーとして使う。
- **価格は `price_snapshots` に時系列で貯める**(`tracked_products` に最新価格を持たせない): グラフ描画・変動率計算に生データが必要なため。最新価格は「直近の1件を取得するクエリ」で出す設計にする。
- **アラート条件と通知履歴を分離する**(`price_alerts` / `notification_logs`): 「条件」と「実際に送った記録」を分けることで、通知の再送防止・監査ログとしての利用がしやすくなる。
