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
import type { PriceSnapshot, TrackedProduct } from "@/lib/types";

export default function ProductDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const productId = Number(params.id);

  const [product, setProduct] = useState<TrackedProduct | null>(null);
  const [snapshots, setSnapshots] = useState<PriceSnapshot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCollecting, setIsCollecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      const [productData, snapshotData] = await Promise.all([
        api.getTrackedProduct(productId),
        api.listPriceSnapshots(productId),
      ]);
      setProduct(productData);
      setSnapshots([...snapshotData].reverse());
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
        </>
      )}
    </main>
  );
}
