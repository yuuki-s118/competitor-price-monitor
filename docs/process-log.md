# 開発プロセスログ

このプロジェクトの技術的な意思決定・実装・トラブルシューティングを、発生したタイミングで都度記録する。1エントリ = 1つの意思決定/出来事。

---

## 2026-09-10 — 要件定義・プロジェクト構想

**背景**
バックエンド開発の実績として、認証・非同期処理・DB設計・インフラまでを一通り含む、本格的なWebアプリケーションを作る必要があった。

**決定**
競合の価格・トレンドを監視するSaaSを作ることに決定。ECサイト(Amazon・楽天など)やSNSから商品価格・キーワード投稿数を定期収集し、グラフで可視化、価格変動時に通知する。想定スタックとして FastAPI/Django(要検討)、JWT認証、PostgreSQL/MySQL、Celery+Redis、Docker、AWS/Render、GitHub Actions を挙げた。

**理由**
認証・非同期バッチ処理・DB設計・インフラ構築を一つのプロジェクトに自然な形で組み込める題材として、価格監視SaaSを選んだ。

**保留にした点**: フレームワーク選定、スクレイピング対象サイト、デプロイ先 — 次セッションで決定することにした。

---

## 2026-09-10 — セッション1: 技術選定

**背景**
実装に着手する前に、バックエンドフレームワーク・スクレイピング対象・デプロイ方針を確定する必要があった。

**決定**
- バックエンド: **FastAPI**
- スクレイピング対象: **楽天市場**からスタート
- デプロイ: まず **Render** で動かし、後で **AWS(EC2/RDS/S3)** へ段階移行

**理由**
- FastAPI: 非同期処理・Pydanticによる型安全なバリデーション・OpenAPI/Swaggerの自動生成が強み。Djangoのように認証やCRUDをフレームワークの規約に任せる部分が少ない分、JWT認証やCelery連携の設計を自分で組み立てることになり、バックエンド設計の幅を見せやすい。
- 楽天市場: Amazonはスクレイピングが利用規約で禁止されており、公開リポジトリとして見せるにはリスクがある。楽天は公式の楽天ウェブサービスAPIがあり、規約に沿ったデータ取得ができる。
- デプロイ段階移行: Renderで素早くデプロイして動作確認のサイクルを回し、ある程度形になった段階でAWSへ移行する。移行自体を設計判断の記録として残せる。

---

## 2026-09-10 — セッション1: 依存関係管理

**背景**
Pythonの依存管理として poetry / uv も候補にあったが、開発環境にどちらも未導入だった。

**決定**
pip + `requirements.txt`(`requirements.txt` / `requirements-dev.txt` の2本立て)を採用。

**理由**
クローンしてすぐ動かせるシンプルさを優先。将来 uv 等モダンなツールへの移行余地は残す。

---

## 2026-09-10 — セッション1: 最小スケルトンの実装と動作確認

**背景**
技術選定を踏まえ、実際に動くところまで確認する必要があった。

**決定**
FastAPI + SQLAlchemy 2.0(async)+ asyncpg + PostgreSQL + Redis の docker-compose 構成を作成し、`GET /api/health` と `GET /api/health/db` を実装した。

**詰まった箇所と解決**
`sqlalchemy` を async extra なしでインストールしたところ `ValueError: the greenlet library is required to use this function` が発生。`requirements.txt` を `sqlalchemy[asyncio]` に変更して解決した(SQLAlchemyのasync APIはgreenletに依存するが、明示的な extra 指定がないと入らない)。

**確認結果**
`docker compose up --build` でDB・Redis・backendが起動し、`/api/health`・`/api/health/db` がともに200を返すことを確認。pytest 1件成功。ローカルgitリポジトリを初期化(`main`ブランチ)。

---

## 2026-09-10 — 記録方針の変更

**背景**
開発過程そのものをポートフォリオコンテンツとして扱うにあたり、まとめて後から書く方式では「なぜこの設計にしたか」の解像度が失われると判断した。

**決定**
記録先をこの `docs/process-log.md` に統一。1エントリ=1意思決定/出来事とし、発生したタイミングで都度追記する方式に変更。過去の意思決定(要件定義・技術選定)もこのログに書き起こした。

**理由**
このログを時系列の「マップ」としてフリーランスエージェントや直接クライアントへの説明材料に使う想定のため、第三者が読んで意思決定の経緯を理解できる粒度で残す必要がある。

---

## 2026-09-11 — セッション2: データモデル設計(v1)

**背景**
認証やスクレイピングの実装に入る前に、DBスキーマを固める必要があった。JWT認証・CRUD・価格の時系列保存・通知という要件を満たす形を検討した。

**決定**
`users` / `retailers` / `tracked_products` / `price_snapshots` / `price_alerts` / `notification_logs` の6テーブルで v1 のER図を確定([docs/er-diagram.md](er-diagram.md))。主な設計判断:
- `tracked_products` はユーザーに紐づける(「監視対象として登録する」形にしてCRUD要件を自然に満たす)
- `retailers` を独立テーブルにする(対象ECサイトが将来増える前提の正規化。今は楽天市場のみ登録)
- 価格は `tracked_products` に最新値を持たせず、`price_snapshots` に時系列で貯める(グラフ描画・変動率計算のため生データが必要)
- 通知の「条件」(`price_alerts`)と「実際に送った記録」(`notification_logs`)を分離する(再送防止・監査ログのため)

SNSキーワード監視は今回のスキーマに含めず、将来拡張として保留した(まずは楽天市場の価格監視だけで一通り動かす方針)。

SQLAlchemy 2.0 の `Mapped` / `mapped_column` スタイルでモデルを実装し(`backend/app/models/`)、Alembic(asyncテンプレート)を導入してマイグレーションを自動生成・適用した。

**確認結果**
`docker compose run --rm backend alembic upgrade head` で6テーブルが作成されることを確認(`alembic_version` と合わせて7テーブル)。`alembic check` で差分なしを確認。pytest 1件成功。

---

## 2026-09-11 — ランタイム・依存関係を最新版へ更新

**背景**
公開ポートフォリオとして見せる以上、ランタイムと主要な依存関係は最新の安定版を使う方針とした。

**決定**
`backend/Dockerfile` のベースイメージを `python:3.13-slim` から `python:3.14-slim` に変更し、あわせて主要依存関係を更新した: `fastapi==0.141.1` / `uvicorn[standard]==0.52.4` / `sqlalchemy[asyncio]==2.0.52` / `asyncpg==0.31.0` / `alembic==1.19.2` / `pydantic==2.13.5` / `pydantic-settings==2.15.0` / `pytest==9.1.1` / `pytest-asyncio==1.4.0` / `ruff==0.16.6`。ローカル開発環境もPython 3.14に統一した。

**詰まった箇所と解決**
`python:3.14-slim` に切り替えて再ビルドしたところ、`pydantic-core`(Rust製)と `asyncpg` のビルドに失敗した。原因は、従来固定していたバージョンにはPython 3.14向けのビルド済みwheelが存在せず、pipがソースからビルドしようとしたが、slimイメージにCコンパイラがなくビルドできなかったこと。Python 3.14向けのビルド済みwheelが提供されている新しいバージョンに依存関係を更新して解決した。

**確認結果**
`docker compose up --build` → `alembic upgrade head` → `/api/health`・`/api/health/db` が200 → pytest 1件成功、まで再確認済み。

---

## 2026-09-13 — セッション3: JWT認証の実装

**背景**
データモデルが固まったので、`tracked_products` 以降のCRUD機能の前提となるユーザー認証を実装する必要があった。

**決定**
`POST /api/auth/register`(ユーザー登録)・`POST /api/auth/login`(ログイン、OAuth2 Passwordフロー準拠でJWT発行)・`GET /api/auth/me`(認証必須の動作確認用エンドポイント)を実装した。パスワードは bcrypt でハッシュ化し、平文では保存しない。トークン検証は FastAPI の `Depends` によるDI(`get_current_user`)で行い、以降のCRUDエンドポイントもこの依存関係を再利用する設計にした。

**理由**
`OAuth2PasswordBearer` / `OAuth2PasswordRequestForm` を使うことで、Swagger UI の「Authorize」から直接ログイン・認証済みリクエストを試せるようになる(動作確認・デモがしやすい)。

**詰まった箇所と解決**
1. テストが実DBに直接書き込む構成だと、同じメールアドレスで2回目以降のテスト実行が重複エラーになる。→ 1テストごとにトランザクションを張り、`db.commit()` をセーブポイントの解放として扱った上でテスト終了時にロールバックする構成(`tests/conftest.py`)にして解決。
2. 上記の対応中、pytest-asyncioがテスト関数ごとに新しいイベントループを使うため、SQLAlchemyのコネクションプールが前のテストのループに紐づいた接続を使い回そうとして `RuntimeError: ... attached to a different loop` が発生。→ テスト用エンジンは `NullPool`(接続を使い回さない設定)にして解決。
3. JWTの署名鍵が短いと `InsecureKeyLengthWarning` が出る(HS256の推奨最小長32バイト未満)。→ デフォルト値を32文字以上に変更し、`.env.example` に本番用鍵の生成コマンドを明記した。

**確認結果**
`docker compose up --build` → pytest 4件成功(登録・ログイン・認証必須エンドポイントへのアクセス・不正なパスワードでの拒否・未認証アクセスの拒否)。Swagger UI(`/docs`)上で `register` → `login` → `me` の一連の流れが実際に動作することも確認した。

---

## 2026-09-13 — セッション4: 監視対象商品(tracked_products)のCRUD実装

**背景**
認証の次に、ユーザーが競合商品を登録・管理できるCRUD機能を実装する必要があった。`tracked_products` は `retailers` を外部キーで参照するため、先に対象ECサイトのマスタデータを用意する必要があった。

**決定**
- Alembicのデータマイグレーションで `retailers` に「楽天市場」の初期データを投入(`slug: rakuten`)
- `GET /api/retailers` で登録済みECサイトの一覧を取得できるようにした(`tracked_products` 作成時に `retailer_id` を指定するため)
- `tracked_products` のCRUD(`POST` / `GET` 一覧・単体 / `PATCH` / `DELETE`)を実装。すべて `get_current_user` に紐づけ、他ユーザーの商品は一覧にも出さず、直接IDを指定してアクセスしても404を返す(所有者以外には存在自体を明かさない設計)

**詰まった箇所と解決**
1. テストで独自の `retailers` レコードを作った際、Alembicで投入済みの `slug: rakuten` と重複してユニーク制約違反になった。→ テスト用データは本番シードと衝突しない別のslugを使うように修正。
2. `ruff` の `B008`(Depends をデフォルト引数で呼ぶことへの指摘)と `UP037`(TYPE_CHECKING配下のみでimportする型ヒントの引用符除去の提案)が大量に出た。前者はFastAPIの正しい使い方、後者は引用符を外すと実行時に `NameError` になる(TYPE_CHECKING配下でしかimportしていないため)ので、どちらも `pyproject.toml` でルールごと無視するよう設定した。
3. `enum.Enum` と `str` の多重継承で定義していた `AlertRuleType` / `NotificationChannel` を、Python 3.11以降で使える `enum.StrEnum` に置き換えた(ruffの `UP042` 指摘への対応)。

**確認結果**
`ruff check` 全通過、pytest 8件成功(認証4件 + CRUD4件、他ユーザーの商品にアクセスできないことを検証するテストを含む)。実際にAPI経由で `retailers` 取得 → 商品登録 → 一覧取得までの流れも確認した。

---

## 2026-09-13 — セッション4: 楽天ウェブサービスAPI連携(価格収集)

**背景**
監視対象商品を登録できるようになったので、実際に価格を取得して保存する機能(F-04・F-05)を実装する必要があった。

**決定**
`app/services/rakuten.py` に楽天ウェブサービス(商品検索API)を呼び出すクライアントを実装。`POST /api/tracked-products/{id}/collect-price` で指定商品の現在価格を取得し `price_snapshots` に保存、`GET /api/tracked-products/{id}/price-snapshots` で履歴を取得できるようにした。Celeryによる定期実行は次段階とし、まずは手動トリガーで一連の流れ(取得→保存→参照)を成立させることを優先した。

**理由**
外部APIキー(Application ID)がない状態でも、まず同期的な1コール分のロジックを固めてから非同期・定期実行の皮を被せる方が、問題の切り分けがしやすい。

**詰まった箇所と解決**
テストで実際に楽天のサーバーへ通信するわけにはいかないため、`respx` でHTTPレイヤーをモックし、正常系(価格取得)・異常系(商品が見つからない、Application ID未設定)をそれぞれ検証できるようにした。

**確認結果**
pytest 11件成功(認証4 + CRUD4 + 価格収集3)。`ruff check` 全通過。

**注記**: 実際に楽天から価格を取得するには、[楽天ウェブサービス](https://webservice.rakuten.co.jp/) でアプリ登録して取得した Application ID を `.env` の `RAKUTEN_APP_ID` に設定する必要がある(未設定の場合は明確なエラーを返す設計にしている)。

---

## 2026-09-13 — セッション4: 楽天API基盤刷新への対応

**背景**
Application IDを取得して実際に呼び出したところ、当初実装していた旧エンドポイント(`app.rakuten.co.jp`)・旧認証方式(`applicationId`のみ)では動作しなかった。調査の結果、楽天ウェブサービスは2026年5月13日に旧APIを完全停止し、新基盤(`openapi.rakuten.co.jp`)へ移行済みであることが判明した。

**決定**
- エンドポイントを `https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701` に変更
- 認証を `applicationId` に加えて `accessKey` も必須のパラメータとして追加(`RAKUTEN_ACCESS_KEY` を新設)
- リクエストに `Origin` ヘッダー(アプリ登録時の Allowed websites に指定したドメイン)を付与する設定(`RAKUTEN_ALLOWED_ORIGIN`)を追加

**詰まった箇所と解決**
1. `accessKey` をクエリパラメータにそのまま埋め込んだ際、キーに含まれる記号がURLエンコードされておらず「Invalid Access Key」エラーになった。→ クエリパラメータは必ずURLエンコードして送るよう修正。
2. ドキュメント上は `Referer` ヘッダーで送信元ドメインを検証するとあったが、実際には `REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING` エラーが解消しなかった。第三者の実装例を調査した結果、実際の挙動は `Origin` ヘッダーでの検証に変わっていることが分かり、`Origin` に切り替えて解決した。

**確認結果**
実在の楽天市場商品(コーヒーのふるさと納税返礼品)を監視対象として登録し、`collect-price` エンドポイント経由で実際の価格(¥12,000)を取得・保存できることを確認した。pytest 11件・ruff check も引き続き全通過。

---

## 2026-09-13 — セッション5: Celeryによる価格収集の定期実行

**背景**
これまでの `collect-price` は手動トリガーのみだったため、監視対象商品の価格を自動的・定期的に収集する仕組み(NF-01の非同期・並列実行要件)を実装する必要があった。

**決定**
- 価格取得ロジックを `app/services/price_collection.py` に切り出し、APIエンドポイントとCeleryタスクの両方から共通で使えるようにした
- `app/tasks/price_collection.py` に2つのタスクを実装: `collect_price_for_product`(1商品分の取得)と `collect_all_active_prices`(有効な商品全件を1商品ずつ`collect_price_for_product`にキューイングするだけの配信役)。1商品の失敗が他に波及しないよう役割を分離した
- Celery beatで毎時実行するスケジュールを設定(`app/core/celery_app.py`)
- `docker-compose.yml` に `celery-worker` / `celery-beat` サービスを追加

**詰まった箇所と解決**
1. **APIキーがログに漏れていた**: `httpx.HTTPStatusError` の例外メッセージにはクエリパラメータ付きのURL(`accessKey`を含む)がそのまま入っており、Celeryワーカーのエラーログにそのまま出力されていた。さらに `httpx` ライブラリ自体もリクエストURLをINFOログに出していた。対応として、(1) `accessKey` はクエリパラメータではなくヘッダーで送るように変更、(2) 例外は `from None` でチェーンを断ち切り、ステータスコードだけを含む安全なメッセージに詰め替え、(3) `httpx` ロガーのレベルをWARNINGに上げてリクエストURLの自動ログ出力を止めた。`applicationId` は仕様上ヘッダーでは受け付けずクエリパラメータ必須のため残るが、`accessKey`(実質的なパスワードに相当)は完全にURLから排除した。
2. **テストで踏んだのと同じ「別イベントループ」エラーが本番相当のワーカーでも再現**: FastAPI用の `async_session_factory`(コネクションプールあり)をCeleryタスクからも使い回していたため、タスクごとに `asyncio.run()` が新しいイベントループを作るたびに接続の使い回しが壊れていた。Celeryタスク専用に `NullPool` の別エンジン(`celery_session_factory`)を `app/db/session.py` に用意して解決。

**確認結果**
実際にCeleryワーカーを起動し、複数タスクを連続投入してエラーが出ないことを確認。実在商品の価格スナップショットがワーカー経由で正しく保存されることも確認した。pytest 14件・ruff check 全通過。

---

## 2026-09-13 — セッション6: GitHub ActionsによるCI導入

**背景**
プッシュのたびに lint・テストが自動で走る状態にしておきたかった。

**決定**
`.github/workflows/ci.yml` を追加。PostgreSQL・Redisをサービスコンテナとして起動し、Python 3.14環境で `ruff check` → `alembic upgrade head` → `pytest` を実行する構成にした。

**理由**
アプリのDockerイメージ経由ではなく、GitHub Actionsのランナーに直接pip installする構成にした。CI実行時間を短縮でき、依存関係がDockerイメージのビルド手順に依存せず素直に解決できることを確認する意味もある。

**確認結果**
GitHub Actions上でまだ実行していない(リポジトリ未プッシュ)ため、同等の手順(Python 3.14の素のvenv + ローカルのPostgreSQL/Redisコンテナ)をローカルで再現して検証した。`pip install` → `ruff check` → `alembic upgrade head` → `pytest` の全手順が成功することを確認済み。
