import type { PurchaseOrder } from "../types";

export default function PoList({ pos }: { pos: PurchaseOrder[] }) {
  if (pos.length === 0) return <p>Belum ada PO.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>No PO</th>
          <th>SKU</th>
          <th>Vendor</th>
          <th>Qty</th>
          <th>Total</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {pos.map((po) => (
          <tr key={po.po_no}>
            <td>{po.po_no}</td>
            <td>{po.sku}</td>
            <td>{po.vendor_id}</td>
            <td>{po.qty}</td>
            <td>${po.total_value.toFixed(2)}</td>
            <td>{po.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}