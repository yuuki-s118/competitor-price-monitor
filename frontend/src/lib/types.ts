export interface UserRead {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface Retailer {
  id: number;
  name: string;
  slug: string;
  base_url: string;
}

export interface TrackedProduct {
  id: number;
  retailer_id: number;
  external_product_id: string;
  name: string;
  product_url: string;
  image_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TrackedProductCreateInput {
  retailer_id: number;
  external_product_id: string;
  name: string;
  product_url: string;
  image_url?: string;
}

export interface PriceSnapshot {
  id: number;
  tracked_product_id: number;
  price: string;
  currency: string;
  scraped_at: string;
}

export type AlertRuleType = "price_below" | "price_drop_percent";

export interface PriceAlert {
  id: number;
  tracked_product_id: number;
  rule_type: AlertRuleType;
  threshold_value: string;
  is_active: boolean;
  created_at: string;
}

export interface PriceAlertCreateInput {
  rule_type: AlertRuleType;
  threshold_value: string;
}

export interface NotificationLog {
  id: number;
  price_alert_id: number;
  price_snapshot_id: number;
  channel: "email";
  sent_at: string;
}
