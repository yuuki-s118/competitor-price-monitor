"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, ApiError } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type {
  AlertRuleType,
  NotificationLog,
  PriceAlert,
  PriceSnapshot,
  TrackedProduct,
} from "@/lib/types";

const RULE_TYPE_LABELS: Record<AlertRuleType, string> = {
  price_below: "指定価格を下回ったら通知",
  price_drop_percent: "前回比で指定%以上下落したら通知",
};

export default function ProductDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const productId = Number(params.id);

  const [product, setProduct] = useState<TrackedProduct | null>(null);
  const [snapshots, setSnapshots] = useState<PriceSnapshot[]>([]);
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [notificationLogs, setNotificationLogs] = useState<NotificationLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCollecting, setIsCollecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [newRuleType, setNewRuleType] = useState<AlertRuleType>("price_below");
  const [newThreshold, setNewThreshold] = useState("");
  const [isCreatingAlert, setIsCreatingAlert] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId, router]);

  async function loadData() {
    setIsLoading(true);
    setError(null);
    try {
      const [productData, snapshotData, alertData, logData] = await Promise.all([
        api.getTrackedProduct(productId),
        api.listPriceSnapshots(productId),
        api.listPriceAlerts(productId),
        api.listNotificationLogs(productId),
      ]);
      setProduct(productData);
      setSnapshots([...snapshotData].reverse());
      setAlerts(alertData);
      setNotificationLogs(logData);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login");
        return;
      }
      setError(err instanceof ApiError ? err.message : "読み込みに失敗しました");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreateAlert(e: React.FormEvent) {
    e.preventDefault();
    setIsCreatingAlert(true);
    setError(null);
    try {
      await api.createPriceAlert(productId, {
        rule_type: newRuleType,
        threshold_value: newThreshold,
      });
      setNewThreshold("");
      const alertData = await api.listPriceAlerts(productId);
      setAlerts(alertData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "アラートの作成に失敗しました");
    } finally {
      setIsCreatingAlert(false);
    }
  }

  async function handleToggleAlert(alert: PriceAlert) {
    setError(null);
    try {
      await api.updatePriceAlert(productId, alert.id, { is_active: !alert.is_active });
      const alertData = await api.listPriceAlerts(productId);
      setAlerts(alertData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "アラートの更新に失敗しました");
    }
  }

  async function handleDeleteAlert(alertId: number) {
    setError(null);
    try {
      await api.deletePriceAlert(productId, alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "アラートの削除に失敗しました");
    }
  }

  async function handleCollectPrice() {
    setIsCollecting(true);
    setError(null);
    try {
      await api.collectPrice(productId);
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "価格の取得に失敗しました");
    } finally {
      setIsCollecting(false);
    }
  }

  const chartData = snapshots.map((snapshot) => ({
    scraped_at: new Date(snapshot.scraped_at).toLocaleString("ja-JP", {
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
    price: Number(snapshot.price),
  }));

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 px-4 py-10">
      <Link href="/dashboard" className="text-sm text-slate-600 underline">
        ← 一覧に戻る
      </Link>

      {isLoading && <p className="text-sm text-slate-500">読み込み中...</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {product && (
        <>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-slate-900">{product.name}</h1>
              <a
                href={product.product_url}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-slate-500 underline"
              >
                商品ページを開く
              </a>
            </div>
            <button
              onClick={handleCollectPrice}
              disabled={isCollecting}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {isCollecting ? "取得中..." : "今すぐ価格を取得"}
            </button>
          </div>

          <section className="rounded-lg border border-slate-200 p-4">
            <h2 className="mb-4 text-sm font-medium text-slate-700">価格推移</h2>
            {chartData.length === 0 ? (
              <p className="text-sm text-slate-500">
                まだ価格データがありません。「今すぐ価格を取得」を押してください。
              </p>
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="scraped_at" tick={{ fontSize: 12 }} />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      domain={["auto", "auto"]}
                      tickFormatter={(value: number) => `¥${value.toLocaleString()}`}
                    />
                    <Tooltip
                      formatter={(value) => [`¥${Number(value).toLocaleString()}`, "価格"]}
                    />
                    <Line type="monotone" dataKey="price" stroke="#0f172a" strokeWidth={2} dot />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </section>

          <section className="flex flex-col gap-1">
            <h2 className="text-sm font-medium text-slate-700">取得履歴</h2>
            <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200">
              {snapshots
                .slice()
                .reverse()
                .map((snapshot) => (
                  <li
                    key={snapshot.id}
                    className="flex justify-between px-4 py-2 text-sm text-slate-700"
                  >
                    <span>{new Date(snapshot.scraped_at).toLocaleString("ja-JP")}</span>
                    <span>¥{Number(snapshot.price).toLocaleString()}</span>
                  </li>
                ))}
            </ul>
          </section>

          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-slate-700">価格アラート</h2>

            <form onSubmit={handleCreateAlert} className="flex flex-wrap items-end gap-2">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-500">条件</label>
                <select
                  value={newRuleType}
                  onChange={(e) => setNewRuleType(e.target.value as AlertRuleType)}
                  className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                >
                  <option value="price_below">指定価格を下回ったら通知</option>
                  <option value="price_drop_percent">前回比で指定%以上下落したら通知</option>
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-500">
                  {newRuleType === "price_below" ? "価格(円)" : "下落率(%)"}
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={newThreshold}
                  onChange={(e) => setNewThreshold(e.target.value)}
                  className="w-32 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                />
              </div>
              <button
                type="submit"
                disabled={isCreatingAlert}
                className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
              >
                追加
              </button>
            </form>

            {alerts.length === 0 ? (
              <p className="text-sm text-slate-500">アラートは設定されていません。</p>
            ) : (
              <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200">
                {alerts.map((alert) => (
                  <li
                    key={alert.id}
                    className="flex items-center justify-between px-4 py-2 text-sm text-slate-700"
                  >
                    <span>
                      {RULE_TYPE_LABELS[alert.rule_type]} (
                      {alert.rule_type === "price_below"
                        ? `¥${Number(alert.threshold_value).toLocaleString()}`
                        : `${Number(alert.threshold_value)}%`}
                      )
                    </span>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleToggleAlert(alert)}
                        className="text-xs text-slate-500 underline"
                      >
                        {alert.is_active ? "無効にする" : "有効にする"}
                      </button>
                      <button
                        onClick={() => handleDeleteAlert(alert.id)}
                        className="text-xs text-red-600 underline"
                      >
                        削除
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="flex flex-col gap-1">
            <h2 className="text-sm font-medium text-slate-700">通知履歴</h2>
            {notificationLogs.length === 0 ? (
              <p className="text-sm text-slate-500">まだ通知は送信されていません。</p>
            ) : (
              <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200">
                {notificationLogs.map((log) => (
                  <li key={log.id} className="px-4 py-2 text-sm text-slate-700">
                    {new Date(log.sent_at).toLocaleString("ja-JP")} にメール通知を送信しました
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </main>
  );
}
