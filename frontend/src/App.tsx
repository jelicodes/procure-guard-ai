import { useEffect, useState } from "react";
import ApprovalCard from "./components/ApprovalCard";
import PoList from "./components/PoList";
import * as api from "./api";
import type { PurchaseOrder } from "./types";

export default function App() {
  const [pending, setPending] = useState<PurchaseOrder[]>([]);
  const [pos, setPos] = useState<PurchaseOrder[]>([]);
  const [message, setMessage] = useState("");

  async function refresh() {
    setPending(await api.listPending());
    setPos(await api.listPos());
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 10000);
    return () => clearInterval(id);
  }, []);

  async function handleScan() {
    await api.scan();
    setMessage("Scan selesai.");
    await refresh();
  }

  async function handleApprove(poNo: string) {
    await api.approvePo(poNo);
    setMessage(`PO ${poNo} disetujui.`);
    await refresh();
  }

  async function handleReject(poNo: string, note: string) {
    await api.rejectPo(poNo, note);
    setMessage(`PO ${poNo} ditolak.`);
    await refresh();
  }

  return (
    <main>
      <h1>Procure Guard AI</h1>
      {message && <p data-testid="message">{message}</p>}
      <button onClick={handleScan}>Pindai Inventori</button>

      <section>
        <h2>Menunggu Persetujuan</h2>
        {pending.length === 0 ? (
          <p>Tidak ada PO menunggu persetujuan.</p>
        ) : (
          pending.map((po) => (
            <ApprovalCard key={po.po_no} po={po} onApprove={handleApprove} onReject={handleReject} />
          ))
        )}
      </section>

      <section>
        <h2>Daftar Purchase Order</h2>
        <PoList pos={pos} />
      </section>
    </main>
  );
}