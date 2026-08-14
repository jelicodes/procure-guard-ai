export interface InventoryRow {
  sku: string;
  name: string;
  vendor_id: string;
  stock_level: number;
  safety_stock: number;
  is_critical: boolean;
}

export default function InventoryTable({ items }: { items: InventoryRow[] }) {
  if (items.length === 0) return <p>Belum ada data inventori.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>SKU</th>
          <th>Nama</th>
          <th>Vendor</th>
          <th>Stok</th>
          <th>Safety Stock</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.sku}>
            <td>{item.sku}</td>
            <td>{item.name}</td>
            <td>{item.vendor_id}</td>
            <td>{item.stock_level}</td>
            <td>{item.safety_stock}</td>
            <td>{item.is_critical ? "KRITIS" : "Normal"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}