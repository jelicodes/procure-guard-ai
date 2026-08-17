import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App, { formatRupiah } from "./App";
import { InventoryItem, PurchaseOrder } from "./types";

const mockInventory: InventoryItem[] = [
  {
    sku: "SKU-001",
    name: "Bahan Baku Utama",
    vendor_id: "V001",
    stock_level: 10,
    safety_stock: 50,
    unit_price: 200000,
    reorder_point: 100,
    avg_daily_usage: 5,
  },
];

const mockPOS: PurchaseOrder[] = [
  {
    po_no: "PO-001",
    sku: "SKU-001",
    vendor_id: "V001",
    qty: 100,
    unit_price: 200000,
    total_value: 20000000,
    status: "pending_approval",
    basis: "verified_sop",
    explanation: "Stok kritis, reorder dibutuhkan.",
    thread_id: "t1",
    erp_po_no: null,
    created_at: "2026-08-17T00:00:00Z",
  },
];

vi.mock("./api", () => ({
  fetchInventory: vi.fn(async () => mockInventory),
  fetchPurchaseOrders: vi.fn(async () => mockPOS),
  fetchEvents: vi.fn(async () => []),
  runInventoryScan: vi.fn(async () => ({ thread_id: "t2", po_no: null })),
  approvePO: vi.fn(async () => ({ status: "approved" })),
  rejectPO: vi.fn(async () => ({ status: "rejected" })),
}));

import * as api from "./api";

describe("formatRupiah", () => {
  it("memformat angka dalam Rupiah", () => {
    expect(formatRupiah(20000000)).toContain("20.000.000");
  });
});

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("menampilkan metrik, inventori, dan PO dari backend", async () => {
    render(<App />);
    expect((await screen.findAllByText("SKU-001")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("PO-001")).length).toBeGreaterThan(0);
    expect(screen.getByText("Critical Stock")).toBeInTheDocument();
    expect(screen.getByText("Pending Approvals")).toBeInTheDocument();
  });

  it("menampilkan label status PO dari backend", async () => {
    render(<App />);
    expect((await screen.findAllByText(/pending approval/)).length).toBeGreaterThan(0);
  });

  it("alur approve: isi reviewer, konfirmasi, panggil approvePO", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByText("PO-001");

    await user.click(screen.getByRole("button", { name: "Approve" }));
    const reviewer = await screen.findByTestId("reviewer-input");
    await user.clear(reviewer);
    await user.type(reviewer, "Budi");
    await user.click(screen.getByTestId("confirm-action"));

    await waitFor(() => {
      expect(api.approvePO).toHaveBeenCalledWith("PO-001", "Budi", "");
    });
  });

  it("alur reject: tanpa catatan muncul error, dengan catatan panggil rejectPO", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByText("PO-001");

    await user.click(screen.getByRole("button", { name: "Reject" }));
    await user.click(screen.getByTestId("confirm-action"));
    expect(await screen.findByText("A rejection note is required.")).toBeInTheDocument();
    expect(api.rejectPO).not.toHaveBeenCalled();

    await user.type(screen.getByTestId("note-input"), "Harga tidak wajar");
    await user.click(screen.getByTestId("confirm-action"));
    await waitFor(() => {
      expect(api.rejectPO).toHaveBeenCalledWith("PO-001", "Harga tidak wajar");
    });
  });
});