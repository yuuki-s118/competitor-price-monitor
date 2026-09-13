# デプロイ手順(Render)

このリポジトリ直下の [`render.yaml`](../render.yaml) が Render の Blueprint 定義になっており、以下のサービスを一括で作成する。

| サービス | 種類 | 役割 |
| --- | --- | --- |
| `competitor-price-monitor-db` | Postgres(Free) | メインDB |
| `competitor-price-monitor-redis` | Key Value(Free, Valkey) | Celeryのブローカー |
| `competitor-price-monitor-backend` | Web(Free, Docker) | FastAPI本体 |
| `competitor-price-monitor-celery-worker` | Background Worker(Free, Docker) | 価格取得タスクの実行 |
| `competitor-price-monitor-celery-beat` | Background Worker(Free, Docker) | 毎時、価格取得タスクをキューに積むスケジューラ |
| `competitor-price-monitor-frontend` | Web(Free, Docker) | Next.jsダッシュボード |

すべてFreeプランで構成しているため費用は発生しない。ローカル(`docker-compose.yml`)と同じ構成(Celery worker + beat)をそのまま本番でも動かしている。

なお、Renderの Cron Job 機能は実行時間に応じた従量課金があり(Freeプランの対象外)、Blueprint適用時に支払い情報の登録を求められたため使わなかった。

## 手順

1. **Renderアカウントを作成し、GitHubリポジトリを接続する**
   Renderダッシュボード → *New* → *Blueprint* → このリポジトリ(`yuuki-s118/competitor-price-monitor`)を選択すると、`render.yaml` の内容を読み込んで作成するサービス一覧が表示される。内容を確認し、Apply する。

2. **手動で環境変数を入力する**
   `render.yaml` 内で `sync: false` にしている項目は値をリポジトリに含めていないため、Blueprint適用後に各サービスの *Environment* タブから入力する(`competitor-price-monitor-backend` / `celery-worker` / `celery-beat` の3サービス共通の環境変数グループ `competitor-price-monitor-shared` にまとめて入力すれば全サービスに反映される)。

   | 変数名 | 値 |
   | --- | --- |
   | `JWT_SECRET_KEY` | 本番用に新しく生成する(`python -c "import secrets; print(secrets.token_hex(32))"`)。ローカルの開発用シークレットは流用しない |
   | `RAKUTEN_APP_ID` / `RAKUTEN_ACCESS_KEY` | ローカルの `.env` と同じ値 |
   | `RAKUTEN_ALLOWED_ORIGIN` | 楽天ウェブサービスの管理画面で Allowed websites に登録済みのドメイン |
   | `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM_EMAIL` | メール送信に使うSMTPサーバーの情報(例: Gmailなら送信元アドレスと[アプリパスワード](https://myaccount.google.com/apppasswords)) |

3. **フロントエンドのURLを確認し、必要ならCORS設定を更新する**
   `render.yaml` はサービス名から決まる既定のURL(`https://competitor-price-monitor-frontend.onrender.com` など)を前提に `CORS_ORIGINS` と `NEXT_PUBLIC_API_BASE_URL` を設定している。実際に発行されたURLが異なる場合は、それぞれの値を実URLに合わせて修正する。

4. **デプロイ完了後の確認**
   - `https://<backend>.onrender.com/api/health` が200を返すこと
   - フロントエンドから新規登録・ログイン・商品登録・価格取得ができること
   - `celery-beat` のログに毎時のスケジュール実行が、`celery-worker` のログに価格取得の実行結果が出ていること(Renderダッシュボードの各サービスの *Logs* タブで確認)

## 既知の制約

- **Postgres(Free)は作成から30日で有効期限が切れる**(その後14日の猶予期間を過ぎるとデータごと削除される)。ポートフォリオとして公開し続ける場合は、期限が近づいたらRenderダッシュボードから有料プランへのアップグレードが必要(当初の計画通り、最終的にはAWS RDSへの移行で恒久対応する想定)。
- Freeプランの Web サービスは無操作でスピンダウンするため、しばらくアクセスがないと次回アクセス時の初回応答が遅くなる。
