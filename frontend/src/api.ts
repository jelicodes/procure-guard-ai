import type { PurchaseOrder } from "./types";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export async function scan(): Promise<{ thread_id: string; po_no: string | null }> {
  return json(await fetch("/api/scan", { method: "POST" }));
}

export async function listPos(): Promise<PurchaseOrder[]> {
  return json(await fetch("/api/pos"));
}

export async function listPending(): Promise<PurchaseOrder[]> {
  return json(await fetch("/api/approvals/pending"));
}

export async function approvePo(poNo: string): Promise<{ status: string }> {
  return json(await fetch(`/api/pos/${poNo}/approve`, { method: "POST" }));
}

export async function rejectPo(poNo: string, note: string): Promise<{ status: string }> {
  return json(
    await fetch(`/api/pos/${poNo}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note }),
    }),
  );
}