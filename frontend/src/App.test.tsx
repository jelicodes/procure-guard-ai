import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as api from "./api";

vi.mock("./api", () => ({
  scan: vi.fn(),
  listPending: vi.fn(),
  listPos: vi.fn(),
  approvePo: vi.fn(),
  rejectPo: vi.fn(),
}));

const pendingPo = {
  po_no: "PO-123",
  sku: "SKU-001",
  vendor_id: "VENDOR-A",
  qty: 200,
  unit_price: 100,
  total_value: 20000,
  status: "pending_approval",
  basis: "rag",
  explanation: "max(moq=100, lead*usage-stock=90)",
  thread_id: "t1",
  erp_po_no: null,
  created_at: null,
};

beforeEach(() => {
  vi.mocked(api.listPending).mockResolvedValue([pendingPo]);
  vi.mocked(api.listPos).mockResolvedValue([pendingPo]);
});

describe("App", () => {
  it("menampilkan kartu persetujuan untuk PO pending", async () => {
    render(<App />);
    expect(await screen.findByTestId("approval-card")).toBeInTheDocument();
    expect(screen.getByText("PO PO-123 menunggu persetujuan")).toBeInTheDocument();
  });

  it("menyetujui PO dan memperbarui daftar", async () => {
    const user = userEvent.setup();
    vi.mocked(api.approvePo).mockResolvedValue({ status: "approved" });

    render(<App />);
    await screen.findByTestId("approval-card");
    vi.mocked(api.listPending).mockResolvedValue([]);
    await user.click(screen.getByRole("button", { name: "Setujui" }));
    await waitFor(() => expect(api.approvePo).toHaveBeenCalledWith("PO-123"));
    expect(screen.getByTestId("message")).toHaveTextContent("PO-123 disetujui");
  });

  it("menampilkan pesan error saat backend tidak terjangkau", async () => {
    vi.mocked(api.listPos).mockRejectedValue(new Error("HTTP 500"));
    vi.mocked(api.listPending).mockRejectedValue(new Error("HTTP 500"));

    render(<App />);
    await screen.findByTestId("message");
    expect(screen.getByTestId("message")).toHaveTextContent("Gagal terhubung ke backend");
  });

  it("menampilkan pesan error saat scan gagal", async () => {
    const user = userEvent.setup();
    vi.mocked(api.scan).mockRejectedValue(new Error("HTTP 500"));

    render(<App />);
    await user.click(screen.getByRole("button", { name: "Pindai Inventori" }));
    expect(await screen.findByTestId("message")).toHaveTextContent("Scan gagal");
  });

  it("menampilkan pesan error saat persetujuan gagal", async () => {
    const user = userEvent.setup();
    vi.mocked(api.approvePo).mockRejectedValue(new Error("HTTP 500"));

    render(<App />);
    await screen.findByTestId("approval-card");
    await user.click(screen.getByRole("button", { name: "Setujui" }));
    expect(await screen.findByTestId("message")).toHaveTextContent("Persetujuan PO PO-123 gagal");
  });

  it("menampilkan pesan error saat penolakan gagal", async () => {
    const user = userEvent.setup();
    vi.mocked(api.rejectPo).mockRejectedValue(new Error("HTTP 500"));

    render(<App />);
    await screen.findByTestId("approval-card");
    await user.click(screen.getByRole("button", { name: "Tolak" }));
    expect(await screen.findByTestId("message")).toHaveTextContent("Penolakan PO PO-123 gagal");
  });
});