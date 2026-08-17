export interface InventoryItem {
  sku: string;
  name: string;
  vendor_id: string;
  stock_level: number;
  safety_stock: number;
  unit_price: number;
  reorder_point: number;
  avg_daily_usage: number;
}

export type POStatus = "draft" | "pending_approval" | "submitted" | "rejected";

export interface PurchaseOrder {
  po_no: string;
  sku: string;
  vendor_id: string;
  qty: number;
  unit_price: number;
  total_value: number;
  status: POStatus;
  basis: string;
  explanation: string;
  thread_id: string;
  erp_po_no: string | null;
  created_at: string | null;
}

export interface POEvent {
  id: number;
  po_no: string;
  timestamp: string;
  node: string;
  actor: string;
  note: string;
}
