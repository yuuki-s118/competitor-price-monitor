"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";
import type { Retailer, TrackedProduct } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const [products, setProducts] = useState<TrackedProduct[]>([]);
  const [retailers, setRetailers] = useState<Retailer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [productUrl, setProductUrl] = useState("");
  const [externalProductId, setExternalProductId] = useState("");
  const [retailerId, setRetailerId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  async function loadData() {
    setIsLoading(true);
    setError(null);
    try {
      const [productList, retailerList] = await Promise.all([
        api.listTrackedProducts(),
        api.listRetailers(),
      ]);
      setProducts(productList);
      setRetailers(retailerList);
      if (retailerList.length > 0) setRetailerId((prev) => prev ?? retailerList[0].id);
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

  async function handleAddProduct(event: React.FormEvent) {
    event.preventDefault();
    if (retailerId === null) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await api.createTrackedProduct({
        retailer_id: retailerId,
        external_product_id: externalProductId,
        name,
        product_url: productUrl,
      });
      setName("");
      setProductUrl("");
      setExternalProductId("");
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "商品の登録に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-8 px-4 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">監視対象商品</h1>
        <button onClick={handleLogout} className="text-sm text-slate-600 underline">
          ログアウト
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <section className="rounded-lg border border-slate-200 p-4">
        <h2 className="mb-3 text-sm font-medium text-slate-700">商品を追加</h2>
        <form onSubmit={handleAddProduct} className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
          <select
            value={retailerId ?? ""}
            onChange={(e) => setRetailerId(Number(e.target.value))}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
          >
            {retailers.map((retailer) => (
              <option key={retailer.id} value={retailer.id}>
                {retailer.name}
              </option>
            ))}
          </select>
          <input
            placeholder="商品名"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="min-w-48 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
          />
          <input
            placeholder="商品コード(例: shop:1234)"
            required
            value={externalProductId}
            onChange={(e) => setExternalProductId(e.target.value)}
            className="min-w-48 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
          />
          <input
            placeholder="商品URL"
            required
            type="url"
            value={productUrl}
            onChange={(e) => setProductUrl(e.target.value)}
            className="min-w-48 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
          />
          <button
            type="submit"
            disabled={isSubmitting || retailerId === null}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            追加
          </button>
        </form>
      </section>

      <section className="flex flex-col gap-2">
        {isLoading && <p className="text-sm text-slate-500">読み込み中...</p>}
        {!isLoading && products.length === 0 && (
          <p className="text-sm text-slate-500">まだ監視対象の商品がありません。</p>
        )}
        {products.map((product) => (
          <Link
            key={product.id}
            href={`/dashboard/${product.id}`}
            className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3 hover:border-slate-400"
          >
            <div>
              <p className="font-medium text-slate-900">{product.name}</p>
              <p className="text-xs text-slate-500">{product.external_product_id}</p>
            </div>
            <span
              className={`rounded-full px-2 py-1 text-xs ${
                product.is_active ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"
              }`}
            >
              {product.is_active ? "監視中" : "停止中"}
            </span>
          </Link>
        ))}
      </section>
    </main>
  );
}
