import { clearToken, getToken, setToken } from "./auth";
import type {
  NotificationLog,
  PriceAlert,
  PriceAlertCreateInput,
  PriceSnapshot,
  Retailer,
  TrackedProduct,
  TrackedProductCreateInput,
  TrackedProductUpdateInput,
  UserRead,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    clearToken();
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      detail?.detail ?? `リクエストに失敗しました (HTTP ${response.status})`,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  register: (email: string, password: string) =>
    request<UserRead>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    const data = await request<{ access_token: string; token_type: string }>(
      "/api/auth/login",
      { method: "POST", body },
    );
    setToken(data.access_token);
    return data;
  },

  me: () => request<UserRead>("/api/auth/me"),

  listRetailers: () => request<Retailer[]>("/api/retailers"),

  listTrackedProducts: () => request<TrackedProduct[]>("/api/tracked-products"),

  createTrackedProduct: (input: TrackedProductCreateInput) =>
    request<TrackedProduct>("/api/tracked-products", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  getTrackedProduct: (id: number) => request<TrackedProduct>(`/api/tracked-products/${id}`),

  updateTrackedProduct: (id: number, input: TrackedProductUpdateInput) =>
    request<TrackedProduct>(`/api/tracked-products/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  deleteTrackedProduct: (id: number) =>
    request<void>(`/api/tracked-products/${id}`, { method: "DELETE" }),

  collectPrice: (id: number) =>
    request<PriceSnapshot>(`/api/tracked-products/${id}/collect-price`, { method: "POST" }),

  listPriceSnapshots: (id: number) =>
    request<PriceSnapshot[]>(`/api/tracked-products/${id}/price-snapshots`),

  listPriceAlerts: (id: number) => request<PriceAlert[]>(`/api/tracked-products/${id}/alerts`),

  createPriceAlert: (id: number, input: PriceAlertCreateInput) =>
    request<PriceAlert>(`/api/tracked-products/${id}/alerts`, {
      method: "POST",
      body: JSON.stringify(input),
    }),

  updatePriceAlert: (id: number, alertId: number, input: { is_active: boolean }) =>
    request<PriceAlert>(`/api/tracked-products/${id}/alerts/${alertId}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  deletePriceAlert: (id: number, alertId: number) =>
    request<void>(`/api/tracked-products/${id}/alerts/${alertId}`, { method: "DELETE" }),

  listNotificationLogs: (id: number) =>
    request<NotificationLog[]>(`/api/tracked-products/${id}/notification-logs`),
};
