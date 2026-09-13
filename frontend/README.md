# Frontend

競合価格監視ダッシュボード(Next.js / App Router / TypeScript / Tailwind CSS / Recharts)。

プロジェクト全体の説明・技術選定の理由は [ルートのREADME](../README.md) を参照。

## ローカル起動(単体)

```bash
npm install
cp .env.example .env.local
npm run dev
```

バックエンド(`http://localhost:8000`)が別途起動している必要がある。ルートディレクトリで `docker compose up` すれば両方同時に立ち上がる。
