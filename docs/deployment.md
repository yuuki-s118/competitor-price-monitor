# デプロイ手順(Render)

このリポジトリ直下の [`render.yaml`](../render.yaml) が Render の Blueprint 定義になっており、以下のサービスを一括で作成する。

| サービス | 種類 | 役割 |
| --- | --- | --- |
| `competitor-price-monitor-db` | Postgres(Free) | メインDB |
| `competitor-price-monitor-backend` | Web(Free, Docker) | FastAPI本体 |
| `competitor-price-monitor-frontend` | Web(Free, Docker) | Next.jsダッシュボード |

すべてFreeプランで構成しているため費用は発生しない。

## 毎時の価格収集の仕組み(本番とローカルで異なる)

ローカル(`docker-compose.yml`)では Celery + Redis + beat で常時稼働のワーカーが毎時タスクを処理する構成のままにしている。

しかしRenderのFreeプランでは、Background Worker(常時稼働プロセス)自体が実質有料($7/月〜)で、Cron Job機能も実行時間に応じた従量課金があり(Blueprint適用時に支払い情報の登録を求められた)、どちらもFreeプランのみで組む方針に合わなかった。

そのため本番では、常時稼働のプロセスを一切使わず、`POST /api/internal/collect-all-prices`(`X-Internal-Secret` ヘッダーの共有シークレットで認証)というエンドポイントを追加し、GitHub Actions(`.github/workflows/collect-prices.yml`、パブリックリポジトリなので実行時間は無料)のスケジュール実行(毎時)から直接叩く方式にした。呼び出されたら、有効な監視対象商品すべての価格をその場で順に取得する。

Celery + Redisによる非同期タスクキューの実装自体は、ローカル環境・テスト・コードとして引き続き存在している(本番の定期収集経路としては使っていない)。

## 手順

1. **Renderアカウントを作成し、GitHubリポジトリを接続する**
   Renderダッシュボード → *New* → *Blueprint* → このリポジトリ(`yuuki-s118/competitor-price-monitor`)を選択すると、`render.yaml` の内容を読み込んで作成するサービス一覧が表示される。内容を確認し、Apply する。

2. **手動で環境変数を入力する**
   `render.yaml` 内で `sync: false` にしている項目は値をリポジトリに含めていないため、Blueprint適用後に `competitor-price-monitor-backend` サービスの *Environment* タブ(環境変数グループ `competitor-price-monitor-shared`)から入力する。

   | 変数名 | 値 |
   | --- | --- |
   | `JWT_SECRET_KEY` | 本番用に新しく生成する(`python -c "import secrets; print(secrets.token_hex(32))"`)。ローカルの開発用シークレットは流用しない |
   | `RAKUTEN_APP_ID` / `RAKUTEN_ACCESS_KEY` | ローカルの `.env` と同じ値 |
   | `RAKUTEN_ALLOWED_ORIGIN` | 楽天ウェブサービスの管理画面で Allowed websites に登録済みのドメイン |
   | `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM_EMAIL` | メール送信に使うSMTPサーバーの情報(例: Gmailなら送信元アドレスと[アプリパスワード](https://myaccount.google.com/apppasswords)) |
   | `INTERNAL_TASK_SECRET` | GitHub Actionsからの定期収集呼び出し用の共有シークレット(`python -c "import secrets; print(secrets.token_hex(32))"` などで生成) |

3. **フロントエンドのURLを確認し、必要ならCORS設定を更新する**
   `render.yaml` はサービス名から決まる既定のURL(`https://competitor-price-monitor-frontend.onrender.com` など)を前提に `CORS_ORIGINS` と `NEXT_PUBLIC_API_BASE_URL` を設定している。実際に発行されたURLが異なる場合は、それぞれの値を実URLに合わせて修正する。

4. **GitHub ActionsにSecrets/Variablesを設定する**
   リポジトリの *Settings* → *Secrets and variables* → *Actions* で以下を追加する。

   | 種類 | 名前 | 値 |
   | --- | --- | --- |
   | Variable | `BACKEND_URL` | 例: `https://competitor-price-monitor-backend.onrender.com` |
   | Secret | `INTERNAL_TASK_SECRET` | 手順2でRenderに設定したものと同じ値 |

5. **デプロイ完了後の確認**
   - `https://<backend>.onrender.com/api/health` が200を返すこと
   - フロントエンドから新規登録・ログイン・商品登録・価格取得ができること
   - GitHub Actionsの `Collect prices` ワークフローを手動実行(*Actions* タブ → *Run workflow*)し、成功すること・対象商品の価格スナップショットが増えること

## 既知の制約

- **Postgres(Free)は作成から30日で有効期限が切れる**(その後14日の猶予期間を過ぎるとデータごと削除される)。ポートフォリオとして公開し続ける場合は、期限が近づいたらRenderダッシュボードから有料プランへのアップグレードが必要(当初の計画通り、最終的にはAWS RDSへの移行で恒久対応する想定)。
- Freeプランの Web サービスは無操作でスピンダウンするため、しばらくアクセスがないと次回アクセス時の初回応答が遅くなる(GitHub Actionsからの毎時アクセスにより、backendサービス自体はスピンダウンしにくくなる副次効果はある)。
- **Freeプランの Web サービスは外向きのSMTP通信(ポート25/465/587)がブロックされている**(2025年9月のRenderの仕様変更)ため、`aiosmtplib` によるメール送信自体はローカル環境で実際に届くところまで検証済みだが、現在の本番(Render Free)ではSMTP接続がタイムアウトし送信できない。アラート評価・重複通知防止・通知履歴への記録といったアプリ側のロジックはすべて正常に動作しており、送信経路のみがホスティング側の制約に該当する。本番で実際に送信するには、Renderを有料インスタンスへアップグレードするか、SMTPではなくHTTPS経由のメールAPI(Resend・SendGridなど)に送信方式を切り替える必要がある。
