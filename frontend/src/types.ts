export interface PurchaseOrder {
  po_no: string;
  sku: string;
  vendor_id: string;
  qty: number;
  unit_price: number;
  total_value: number;
  status: string;
  basis: string;
  explanation: string;
  thread_id: string;
  erp_po_no: string | null;
  created_at: string | null;
}