import { InventoryItem, PurchaseOrder, POEvent } from "./types";

const API_BASE = "/api";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export async function fetchInventory(): Promise<InventoryItem[]> {
  return json(await fetch(`${API_BASE}/inventory`));
}

export async function fetchPurchaseOrders(): Promise<PurchaseOrder[]> {
  return json(await fetch(`${API_BASE}/pos`));
}

export async function runInventoryScan(): Promise<{ thread_id: string; po_no: string | null }> {
  return json(await fetch(`${API_BASE}/scan`, { method: "POST" }));
}

export async function fetchEvents(): Promise<POEvent[]> {
  return json(await fetch(`${API_BASE}/events`));
}

export async function approvePO(poNo: string, reviewer: string, note?: string): Promise<{ status: string }> {
  return json(
    await fetch(`${API_BASE}/pos/${poNo}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reviewer, note }),
    }),
  );
}

export async function rejectPO(poNo: string, note: string): Promise<{ status: string }> {
  return json(
    await fetch(`${API_BASE}/pos/${poNo}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note }),
    }),
  );
}
