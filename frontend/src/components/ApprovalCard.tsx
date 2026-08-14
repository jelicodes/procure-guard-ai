import { useState } from "react";
import type { PurchaseOrder } from "../types";

interface Props {
  po: PurchaseOrder;
  onApprove: (poNo: string) => Promise<void>;
  onReject: (poNo: string, note: string) => Promise<void>;
}

export default function ApprovalCard({ po, onApprove, onReject }: Props) {
  const [note, setNote] = useState("");

  return (
    <div data-testid="approval-card">
      <h3>PO {po.po_no} menunggu persetujuan</h3>
      <dl>
        <dt>SKU</dt>
        <dd>{po.sku}</dd>
        <dt>Vendor</dt>
        <dd>{po.vendor_id}</dd>
        <dt>Kuantitas</dt>
        <dd>{po.qty}</dd>
        <dt>Nilai Total</dt>
        <dd>${po.total_value.toFixed(2)}</dd>
        <dt>Dasar Kalkulasi</dt>
        <dd>{po.basis}</dd>
        <dt>Penjelasan</dt>
        <dd>{po.explanation}</dd>
      </dl>
      <input
        aria-label="Catatan"
        placeholder="Catatan (opsional)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <button onClick={() => onApprove(po.po_no)}>Setujui</button>
      <button onClick={() => onReject(po.po_no, note)}>Tolak</button>
    </div>
  );
}