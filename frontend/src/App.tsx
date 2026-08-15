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
    try {
      const [pendingList, poList] = await Promise.all([api.listPending(), api.listPos()]);
      setPending(pendingList);
      setPos(poList);
    } catch {
      setMessage("Gagal terhubung ke backend. Coba lagi nanti.");
    }
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 10000);
    return () => clearInterval(id);
  }, []);

  async function handleScan() {
    try {
      await api.scan();
      setMessage("Scan selesai.");
      await refresh();
    } catch {
      setMessage("Scan gagal. Coba lagi nanti.");
    }
  }

  async function handleApprove(poNo: string) {
    try {
      await api.approvePo(poNo);
      setMessage(`PO ${poNo} disetujui.`);
      await refresh();
    } catch {
      setMessage(`Persetujuan PO ${poNo} gagal. Coba lagi nanti.`);
    }
  }

  async function handleReject(poNo: string, note: string) {
    try {
      await api.rejectPo(poNo, note);
      setMessage(`PO ${poNo} ditolak.`);
      await refresh();
    } catch {
      setMessage(`Penolakan PO ${poNo} gagal. Coba lagi nanti.`);
    }
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