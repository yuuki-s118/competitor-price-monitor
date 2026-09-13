# Competitor Price Monitor

[![CI](https://github.com/yuuki-s118/competitor-price-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/yuuki-s118/competitor-price-monitor/actions/workflows/ci.yml)

EC サイト(まずは楽天市場)の価格を定期収集し、グラフで可視化・価格変動を通知する Web サービス。

## なぜ作っているか

フリーランスとして「本格的なバックエンド開発力」を示すためのポートフォリオプロジェクト。完成品だけでなく、設計判断の過程も成果物として [docs/process-log.md](docs/process-log.md) に記録している。

## 技術スタック

| 領域 | 選定 |
| --- | --- |
| 言語 | Python 3.14 |
| バックエンド | FastAPI (async) |
| 認証 | JWT(PyJWT + bcrypt) |
| DB | PostgreSQL + SQLAlchemy 2.0 (async) |
| マイグレーション | Alembic |
| 非同期・定期処理 | Celery + Redis(毎時、監視対象商品の価格を自動収集) |
| フロントエンド | Next.js (App Router) + TypeScript + Tailwind CSS + Recharts |
| インフラ | Docker Compose → Render → AWS(段階移行予定) |
| CI/CD | GitHub Actions(lint + test を自動実行) |

選定理由は [docs/process-log.md](docs/process-log.md) を参照。データモデルは [docs/er-diagram.md](docs/er-diagram.md) を参照。デプロイ手順は [docs/deployment.md](docs/deployment.md) を参照。

## ローカル起動

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

起動後: http://localhost:8000/api/health

初回・スキーマ変更後は別ターミナルでマイグレーションを適用する。

```bash
docker compose run --rm backend alembic upgrade head
```

楽天から実際に価格を取得するには、[楽天ウェブサービス](https://webservice.rakuten.co.jp/) でアプリ登録して取得した `RAKUTEN_APP_ID`・`RAKUTEN_ACCESS_KEY` と、アプリ登録時の Allowed websites に指定したドメイン(`RAKUTEN_ALLOWED_ORIGIN`)を `backend/.env` に設定する。

価格アラートのメール通知を実際に送信するには、`backend/.env` に `SMTP_HOST`・`SMTP_PORT`・`SMTP_USER`・`SMTP_PASSWORD`・`SMTP_FROM_EMAIL` を設定する(未設定の場合、通知はログに記録されるのみで送信は行われない)。

起動後、ダッシュボードは http://localhost:3000 (新規登録 → ログイン → 商品登録 → 価格取得 → グラフ表示、まで一通り試せる)。

## 実装済みAPI

| エンドポイント | 概要 |
| --- | --- |
| `POST /api/auth/register` | ユーザー登録 |
| `POST /api/auth/login` | ログイン(JWT発行) |
| `GET /api/auth/me` | 認証確認用 |
| `GET /api/retailers` | 対象ECサイト一覧 |
| `POST /api/tracked-products` | 監視対象商品の登録 |
| `GET・PATCH・DELETE /api/tracked-products/{id}` | 監視対象商品の参照・更新・削除 |
| `POST /api/tracked-products/{id}/collect-price` | 楽天から現在価格を取得して保存 |
| `GET /api/tracked-products/{id}/price-snapshots` | 価格履歴の取得 |
| `POST・GET /api/tracked-products/{id}/alerts` | 価格アラート条件の作成・一覧取得 |
| `PATCH・DELETE /api/tracked-products/{id}/alerts/{alert_id}` | 価格アラート条件の更新・削除 |
| `GET /api/tracked-products/{id}/notification-logs` | 通知履歴の取得 |

すべて `/docs` (Swagger UI) から実際に試せる。詳細な設計判断は [docs/process-log.md](docs/process-log.md) を参照。

`collect-price` は手動トリガー用のエンドポイントで、これとは別に Celery beat が毎時、有効な監視対象商品すべてについて同じ処理を自動実行する(`celery-worker` / `celery-beat` コンテナ)。価格取得のたびに、有効な価格アラート条件を評価し、条件を満たせばメール通知を送信して `notification_logs` に記録する。

## ディレクトリ構成

```
backend/        FastAPI アプリ本体
  app/
    core/       設定(環境変数など)
    db/         DB接続・セッション
    models/     SQLAlchemy モデル
    schemas/    Pydantic スキーマ(リクエスト/レスポンス)
    services/   外部API連携・共通ビジネスロジック
    tasks/      Celeryタスク(定期価格収集)
    api/routes/ エンドポイント
  alembic/      DBマイグレーション
  tests/
frontend/       Next.js アプリ本体
  src/
    app/        ページ(login / register / dashboard / dashboard/[id])
    lib/        APIクライアント・型定義・認証トークン管理
docs/           設計判断・開発ログ・ER図
```
