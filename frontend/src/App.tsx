import { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { fetchInventory, fetchPurchaseOrders, runInventoryScan, approvePO, rejectPO, fetchEvents } from './api';
import { InventoryItem, PurchaseOrder, POEvent } from './types';
import { Card, CardContent, CardHeader, CardTitle } from './components/Card';
import { Button } from './components/Button';
import { Badge } from './components/Badge';
import { Activity, AlertTriangle, CheckCircle, ChevronDown, ChevronUp, Clock, PackageSearch, RefreshCw, ShieldAlert, ShoppingCart, Terminal, ArrowUpDown, ArrowUp, ArrowDown, X } from 'lucide-react';
import { cn } from './utils';

const APPROVAL_THRESHOLD = 50_000_000;

export function formatRupiah(value: number): string {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value);
}

export default function App() {
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [events, setEvents] = useState<POEvent[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  const [actionFor, setActionFor] = useState<PurchaseOrder | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'reject'>('approve');
  const [actionReviewer, setActionReviewer] = useState("manager");
  const [actionNote, setActionNote] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  // Data Grid & Telemetry States
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [filter, setFilter] = useState<'all'|'critical'|'approaching'|'healthy'>('all');
  const [sortConfig, setSortConfig] = useState<{key: keyof InventoryItem | 'health', dir: 'asc'|'desc'} | null>(null);

  const itemNames = useMemo(() => {
    const map: Record<string, string> = {};
    for (const item of inventory) map[item.sku] = item.name;
    return map;
  }, [inventory]);

  const loadData = async () => {
    try {
      const [inv, pos, evs] = await Promise.all([
        fetchInventory(),
        fetchPurchaseOrders(),
        fetchEvents()
      ]);
      setInventory(inv);
      setPurchaseOrders(pos);
      setEvents(evs);
      setLastSync(new Date());
    } catch (err) {
      console.error("Failed to load data", err);
      setScanMessage("Failed to connect to backend. Is the API running?");
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // Polling for updates
    return () => clearInterval(interval);
  }, []);

  const getHealthStatus = (item: InventoryItem) => {
    if (item.stock_level < item.safety_stock) return 'critical';
    if (item.stock_level < item.safety_stock * 1.5) return 'approaching';
    return 'healthy';
  };

  const filteredAndSortedInventory = useMemo(() => {
    let result = [...inventory];
    if (filter !== 'all') {
      result = result.filter(item => getHealthStatus(item) === filter);
    }
    if (sortConfig) {
      result.sort((a, b) => {
        let aValue: number | string = a[sortConfig.key as keyof InventoryItem];
        let bValue: number | string = b[sortConfig.key as keyof InventoryItem];

        if (sortConfig.key === 'health') {
            const healthScore = { critical: 0, approaching: 1, healthy: 2 };
            aValue = healthScore[getHealthStatus(a)];
            bValue = healthScore[getHealthStatus(b)];
        }

        if (aValue < bValue) return sortConfig.dir === 'asc' ? -1 : 1;
        if (aValue > bValue) return sortConfig.dir === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return result;
  }, [inventory, filter, sortConfig]);

  const handleSort = (key: keyof InventoryItem | 'health') => {
      setSortConfig(current => {
          if (current?.key === key) {
              if (current.dir === 'asc') return { key, dir: 'desc' };
              return null; // reset
          }
          return { key, dir: 'asc' };
      });
  };

  const SortIcon = ({ columnKey }: { columnKey: string }) => {
    if (sortConfig?.key !== columnKey) return <ArrowUpDown className="h-4 w-4 text-slate-400 opacity-50 hover:opacity-100 transition-opacity" />;
    return sortConfig.dir === 'asc' ? <ArrowUp className="h-4 w-4 text-slate-900" /> : <ArrowDown className="h-4 w-4 text-slate-900" />;
  };

  const handleScan = async () => {
    setIsScanning(true);
    setShowLogs(true);
    setScanMessage("Agent initializing...");
    try {
      const res = await runInventoryScan();
      if (res.po_no) {
        setScanMessage(`Scan complete. PO ${res.po_no} created.`);
      } else {
        setScanMessage("Scan complete. No critical stock found.");
      }
      await loadData();
    } catch (err) {
      console.error(err);
      setScanMessage("Scan failed. Check backend connectivity.");
    } finally {
      setIsScanning(false);
      // We explicitly leave showLogs(true) here so the audit trail remains visible.
      setTimeout(() => setScanMessage(null), 3000);
    }
  };

  const openAction = (po: PurchaseOrder, type: 'approve' | 'reject') => {
    setActionType(type);
    setActionReviewer("manager");
    setActionNote("");
    setActionError(null);
    setActionFor(po);
  };

  const confirmAction = async () => {
    if (!actionFor) return;
    try {
      if (actionType === 'approve') {
        await approvePO(actionFor.po_no, actionReviewer || "manager", actionNote);
      } else {
        if (!actionNote.trim()) {
          setActionError("A rejection note is required.");
          return;
        }
        await rejectPO(actionFor.po_no, actionNote);
      }
      setActionFor(null);
      await loadData();
    } catch (err) {
      console.error(err);
      setActionError("Action failed. Check backend connectivity.");
    }
  };

  const criticalStockCount = inventory.filter(i => i.stock_level < i.safety_stock).length;
  const pendingApprovalsCount = purchaseOrders.filter(p => p.status === 'pending_approval').length;
  const submittedCount = purchaseOrders.filter(p => p.status === 'submitted').length;
  const totalPipelineValue = purchaseOrders
    .filter(p => p.status !== 'rejected')
    .reduce((sum, p) => sum + p.total_value, 0);

  return (
    <div className="min-h-screen bg-[#f3f4f6] text-slate-900 font-sans selection:bg-blue-300 p-4 md:p-8">

      {/* HEADER */}
      <header className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-8 gap-6 lg:gap-4 border-b-2 border-slate-300 pb-6">
        <div>
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-black uppercase tracking-tighter flex items-start sm:items-center gap-2 md:gap-3">
            <ShieldAlert className="w-8 h-8 md:w-10 md:h-10 text-red-500 shrink-0 mt-0.5 sm:mt-0" strokeWidth={3} />
            <span className="flex flex-wrap items-center gap-x-2 leading-none">
              <span>Procure Guard</span>
              <span className="text-red-500">AI</span>
            </span>
          </h1>
          <p className="font-bold text-gray-600 mt-3 text-xs sm:text-sm md:text-xl uppercase tracking-wider max-w-xl leading-snug">
            Supply Chain Governance & Crisis Console
          </p>
        </div>
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3 md:gap-4 w-full lg:w-auto">
          <div className="flex items-center justify-between md:justify-start gap-2 text-[10px] md:text-xs font-bold uppercase tracking-widest text-slate-500 bg-white border-2 border-slate-200 px-3 py-2 md:py-1.5 rounded-sm shadow-[2px_2px_0_0_#e2e8f0] order-2 md:order-1">
            <div className="flex items-center">
              <div className={cn("relative flex h-2 w-2 mr-2", lastSync && "opacity-100")}>
                <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", lastSync ? "bg-emerald-400" : "bg-red-400")}></span>
                <span className={cn("relative inline-flex rounded-full h-2 w-2", lastSync ? "bg-emerald-500" : "bg-red-500")}></span>
              </div>
              <span className="truncate">Backend{lastSync ? "" : ": Offline"}</span>
            </div>
            <div className="flex items-center">
              <span className="text-slate-300 mx-2">|</span>
              <span>{lastSync ? lastSync.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Syncing...'}</span>
            </div>
          </div>
          <Button
            size="lg"
            variant="primary"
            onClick={handleScan}
            disabled={isScanning}
            className="text-base sm:text-lg md:text-xl relative overflow-hidden whitespace-nowrap order-1 md:order-2"
          >
            {isScanning ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center justify-center w-full"
              >
                <RefreshCw className="mr-2 h-5 w-5 md:h-6 md:w-6 animate-spin" /> Scanning...
                <motion.div
                  className="absolute inset-0 bg-yellow-300 opacity-20"
                  animate={{ x: ["-100%", "100%"] }}
                  transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                />
              </motion.div>
            ) : (
              <span className="flex items-center justify-center w-full">
                <PackageSearch className="mr-2 h-5 w-5 md:h-6 md:w-6" /> Run Inventory Scan
              </span>
            )}
          </Button>
        </div>
      </header>

      {/* UNIFIED LAYOUT CONTAINER (Allows `order-*` on mobile, Grid on desktop) */}
      <div className="flex flex-col lg:grid lg:grid-cols-12 lg:grid-rows-[auto_auto_1fr] gap-8 items-start">

        {/* 1. METRICS (Mobile: Order 2, Desktop: Row 1 Full Width) */}
        <div className="order-2 lg:order-1 lg:col-span-12 w-full">
          <motion.div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
            initial="hidden"
            animate="visible"
            variants={{
              hidden: { opacity: 0 },
              visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
            }}
          >
            <motion.div variants={{ hidden: { opacity: 0, y: 15 }, visible: { opacity: 1, y: 0 } }}>
              <MetricCard title="Critical Stock" value={criticalStockCount} icon={<AlertTriangle />} alert={criticalStockCount > 0} />
            </motion.div>
            <motion.div variants={{ hidden: { opacity: 0, y: 15 }, visible: { opacity: 1, y: 0 } }}>
              <MetricCard title="Pending Approvals" value={pendingApprovalsCount} icon={<Clock />} alert={pendingApprovalsCount > 0} />
            </motion.div>
            <motion.div variants={{ hidden: { opacity: 0, y: 15 }, visible: { opacity: 1, y: 0 } }}>
              <MetricCard title="Submitted POs" value={submittedCount} icon={<ShoppingCart />} />
            </motion.div>
            <motion.div variants={{ hidden: { opacity: 0, y: 15 }, visible: { opacity: 1, y: 0 } }}>
              <MetricCard title="Pipeline Value" value={formatRupiah(totalPipelineValue)} icon={<Activity />} />
            </motion.div>
          </motion.div>
        </div>

        {/* 2. AGENT OBSERVABILITY (Mobile: Order 1 (TOP), Desktop: Row 2, Col 1-7) */}
        <div className="order-1 lg:order-2 lg:col-span-7 lg:col-start-1 w-full">
          <Card className="bg-[#e0e7ff] border-blue-600 shadow-[4px_4px_0_0_#2563eb] transition-all overflow-hidden p-0 gap-0">
            <CardHeader
              className="flex flex-row items-center justify-between p-5 cursor-pointer hover:bg-blue-200 transition-colors"
              onClick={() => setShowLogs(!showLogs)}
            >
              <CardTitle className="flex items-center gap-2 text-blue-900 text-lg m-0">
                <Terminal className={cn("h-6 w-6", isScanning ? "animate-pulse" : "")} />
                Live Agent Observability {isScanning ? "(Running)" : "(Standby)"}
              </CardTitle>
              {showLogs ? (
                <ChevronUp className="h-6 w-6 text-blue-900" />
              ) : (
                <ChevronDown className="h-6 w-6 text-blue-900" />
              )}
            </CardHeader>
            <AnimatePresence>
              {showLogs && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2, ease: "easeInOut" }}
                >
                  <CardContent className="pt-0 border-t-2 border-blue-600 p-5">
                    <div className="font-mono text-sm bg-black text-green-400 p-4 border-2 border-black max-h-64 overflow-y-auto shadow-inner rounded-sm">
                      {events.length === 0 && !isScanning ? (
                        <div className="text-gray-500">No agent logs available. Run a scan.</div>
                      ) : (
                        events.slice(-8).map((ev) => (
                          <div key={ev.id} className="mb-2">
                            <span className="text-gray-500">[{new Date(ev.timestamp).toLocaleTimeString()}]</span>{" "}
                            <span className="text-blue-400 font-bold">[{ev.node}]</span>{" "}
                            <span className="text-gray-200">{ev.note}</span>
                          </div>
                        ))
                      )}
                      {isScanning && <div className="animate-pulse text-gray-400 mt-2">_</div>}
                    </div>
                  </CardContent>
                </motion.div>
              )}
            </AnimatePresence>
          </Card>
        </div>

        {/* BOTTOM LEFT COLUMN: Critical Inventory Monitor & Audit Trail */}
        <div className="lg:col-span-7 lg:col-start-1 flex flex-col gap-8 order-3 lg:order-3">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <CardTitle className="text-xl leading-tight">Critical Inventory Monitor</CardTitle>
                <div className="grid grid-cols-2 sm:flex sm:flex-row bg-slate-100 border-2 border-slate-300 rounded-sm p-1 gap-1 w-full md:w-auto">
                  {(['all', 'critical', 'approaching', 'healthy'] as const).map(f => (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className={cn(
                        "px-2 md:px-3 py-2 md:py-1.5 text-[10px] md:text-xs font-bold uppercase tracking-wider rounded-sm transition-colors whitespace-nowrap",
                        filter === f ? "bg-white shadow-[2px_2px_0_0_#000] border-2 border-black text-black" : "text-slate-500 hover:text-slate-800 hover:bg-slate-200 border-2 border-transparent"
                      )}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="relative hidden md:block">
                <div className="overflow-x-auto rounded-sm border-2 border-black relative z-10">
                  <table className="w-full text-left border-collapse min-w-[600px]">
                    <thead>
                      <tr className="bg-slate-200 border-b-2 border-black text-xs font-bold uppercase tracking-wider text-slate-700">
                        <th className="p-0 border-r-2 border-black">
                          <button onClick={() => handleSort('sku')} className="w-full flex items-center justify-between p-3 hover:bg-slate-300 transition-colors">
                            SKU <SortIcon columnKey="sku" />
                          </button>
                        </th>
                        <th className="p-0 border-r-2 border-black">
                          <button onClick={() => handleSort('name')} className="w-full flex items-center justify-between p-3 hover:bg-slate-300 transition-colors">
                            Item <SortIcon columnKey="name" />
                          </button>
                        </th>
                        <th className="p-0 border-r-2 border-black text-right">
                          <button onClick={() => handleSort('stock_level')} className="w-full flex items-center justify-end gap-2 p-3 hover:bg-slate-300 transition-colors">
                            <SortIcon columnKey="stock_level" /> Stock Level
                          </button>
                        </th>
                        <th className="p-0">
                          <button onClick={() => handleSort('health')} className="w-full flex items-center justify-between p-3 hover:bg-slate-300 transition-colors">
                            Status <SortIcon columnKey="health" />
                          </button>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredAndSortedInventory.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="p-8 text-center text-slate-500 font-bold bg-slate-50">
                            No items match the current filter.
                          </td>
                        </tr>
                      ) : filteredAndSortedInventory.map((item) => {
                        const isCritical = item.stock_level < item.safety_stock;
                        const isApproaching = item.stock_level < item.safety_stock * 1.5 && !isCritical;
                        const healthPercent = Math.min(100, (item.stock_level / (item.safety_stock * 2)) * 100);

                        return (
                          <tr key={item.sku} className="border-b-2 border-black last:border-0 hover:bg-white transition-colors bg-slate-50">
                            <td className="p-3 border-r-2 border-black font-mono text-sm font-semibold">{item.sku}</td>
                            <td className="p-3 border-r-2 border-black font-semibold">{item.name}</td>
                             <td className="p-3 border-r-2 border-black">
                              <div className="flex flex-col gap-1.5 items-end">
                                <div className="flex items-center gap-2 tabular-nums">
                                  <motion.span
                                    className={cn("font-black text-lg", isCritical ? "text-red-600" : "")}
                                    animate={isCritical ? { scale: [1, 1.1, 1] } : {}}
                                    transition={{ repeat: Infinity, duration: 2 }}
                                  >
                                    {item.stock_level}
                                  </motion.span>
                                  <span className="text-slate-400 text-sm">/ {item.safety_stock}</span>
                                </div>
                                <div className="w-32 h-1.5 bg-slate-200 rounded-none overflow-hidden border border-slate-300">
                                  <motion.div
                                    className={cn("h-full", isCritical ? "bg-red-500" : isApproaching ? "bg-yellow-400" : "bg-emerald-400")}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${healthPercent}%` }}
                                    transition={{ duration: 1, ease: "easeOut" }}
                                  />
                                </div>
                              </div>
                            </td>
                            <td className="p-3">
                              {isCritical ? (
                                <Badge variant="destructive">Critical</Badge>
                              ) : isApproaching ? (
                                <Badge variant="warning">Approaching</Badge>
                              ) : (
                                <Badge variant="success">Healthy</Badge>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Mobile Card List View */}
              <div className="md:hidden flex flex-col gap-4">
                {filteredAndSortedInventory.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 font-bold bg-slate-50 border-2 border-black rounded-sm">
                    No items match the current filter.
                  </div>
                ) : filteredAndSortedInventory.map((item) => {
                  const isCritical = item.stock_level < item.safety_stock;
                  const isApproaching = item.stock_level < item.safety_stock * 1.5 && !isCritical;
                  const healthPercent = Math.min(100, (item.stock_level / (item.safety_stock * 2)) * 100);

                  return (
                    <div key={item.sku} className="flex flex-col bg-white border-2 border-black rounded-sm p-4 shadow-[4px_4px_0_0_#000]">
                      <div className="flex justify-between items-start mb-3">
                        <div className="font-mono text-[10px] font-bold text-slate-500 bg-slate-100 border border-slate-300 px-2 py-1 rounded-sm uppercase tracking-wider">{item.sku}</div>
                        {isCritical ? (
                          <Badge variant="destructive" className="text-[10px] px-2 py-0">Critical</Badge>
                        ) : isApproaching ? (
                          <Badge variant="warning" className="text-[10px] px-2 py-0">Approaching</Badge>
                        ) : (
                          <Badge variant="success" className="text-[10px] px-2 py-0">Healthy</Badge>
                        )}
                      </div>
                      <div className="font-black text-lg leading-tight mb-5 text-slate-900">{item.name}</div>
                      <div className="flex flex-col gap-2 pt-3 border-t-2 border-slate-100">
                        <div className="flex justify-between items-end">
                          <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Stock Level</span>
                          <div className="flex items-center gap-1.5 tabular-nums">
                            <motion.span
                              className={cn("font-black text-2xl tracking-tighter leading-none", isCritical ? "text-red-600" : "text-slate-900")}
                              animate={isCritical ? { scale: [1, 1.05, 1] } : {}}
                              transition={{ repeat: Infinity, duration: 2 }}
                            >
                              {item.stock_level}
                            </motion.span>
                            <span className="text-slate-400 text-sm font-bold leading-none mb-0.5">/ {item.safety_stock}</span>
                          </div>
                        </div>
                        <div className="w-full h-2.5 bg-slate-100 rounded-none overflow-hidden border border-slate-300 mt-1">
                          <motion.div
                            className={cn("h-full", isCritical ? "bg-red-500" : isApproaching ? "bg-yellow-400" : "bg-emerald-400")}
                            initial={{ width: 0 }}
                            animate={{ width: `${healthPercent}%` }}
                            transition={{ duration: 1, ease: "easeOut" }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
             <CardHeader className="pb-4">
               <CardTitle>Purchase Order Audit Trail</CardTitle>
             </CardHeader>
             <CardContent>
                <div className="relative">
                  {/* Subtle fade at the bottom to indicate more content */}
                  <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white to-transparent z-10 pointer-events-none" />

                  <div className="overflow-y-auto max-h-[400px] flex flex-col gap-3 pr-2 -mr-2 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-slate-400">
                    <AnimatePresence initial={false}>
                      {purchaseOrders.slice().reverse().map(po => (
                        <motion.div
                          layout
                          key={po.po_no}
                          initial={{ opacity: 0, height: 0, scale: 0.95 }}
                          animate={{ opacity: 1, height: "auto", scale: 1 }}
                          transition={{ duration: 0.3, ease: "easeOut" }}
                          className="p-3 sm:p-4 border-2 border-black bg-white flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 sm:gap-4 hover:bg-slate-50 transition-colors shadow-[2px_2px_0_0_#000] cursor-pointer shrink-0"
                        >
                          <div className="flex flex-col w-full sm:w-auto min-w-0">
                            <div className="font-black font-mono text-slate-800 text-sm sm:text-base">{po.po_no}</div>
                            <div className="text-xs font-semibold text-slate-500 truncate w-full">{po.sku} - {itemNames[po.sku] ?? po.sku}</div>
                          </div>
                          <div className="flex flex-row items-center justify-between sm:justify-end w-full sm:w-auto gap-3 pt-2 sm:pt-0 border-t-2 sm:border-t-0 border-slate-100 mt-1 sm:mt-0">
                            <div className="font-black text-lg sm:text-xl tabular-nums tracking-tight text-slate-900">{formatRupiah(po.total_value)}</div>
                            <Badge
                              variant={
                                po.status === 'submitted' ? 'success' :
                                po.status === 'pending_approval' ? 'warning' :
                                po.status === 'rejected' ? 'destructive' : 'default'
                              }
                              className="text-[9px] sm:text-[10px] px-1.5 py-0.5 sm:px-2"
                            >
                              {po.status.replace(/_/g, ' ')}
                            </Badge>
                          </div>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                    {purchaseOrders.length === 0 && (
                       <div className="text-center py-8 text-slate-500 font-semibold text-sm">
                         No purchase orders on record.
                       </div>
                    )}
                  </div>
                </div>
            </CardContent>
          </Card>
        </div>

        {/* RIGHT COLUMN: Governance Approval (Sticky) */}
        <div className="lg:col-span-5 lg:col-start-8 lg:row-span-2 flex flex-col gap-8 lg:sticky lg:top-8 h-fit order-2 lg:order-2">
          <Card className="bg-[#fef08a] border-yellow-600 shadow-[4px_4px_0_0_#ca8a04] p-0 overflow-hidden">
            <CardHeader className="bg-yellow-300 border-b-2 border-yellow-600 p-5">
              <CardTitle className="text-yellow-900 text-xl flex items-center gap-2">
                <AlertTriangle className="h-6 w-6" strokeWidth={3} />
                Governance Action Required
              </CardTitle>
              <p className="font-semibold text-yellow-800 text-sm mt-1">Review pending Purchase Orders &ge; {formatRupiah(APPROVAL_THRESHOLD)}</p>
            </CardHeader>
            <CardContent className="p-5 bg-[#fef08a]">
              {pendingApprovalsCount === 0 ? (
                <div className="text-center py-10 border-2 border-dashed border-yellow-500 bg-yellow-100/50 text-yellow-800 font-bold rounded-sm">
                  <CheckCircle className="h-10 w-10 mx-auto mb-3 opacity-60" />
                  No pending approvals.
                </div>
              ) : (
                <div className="flex flex-col gap-5">
                  <AnimatePresence mode="popLayout">
                    {purchaseOrders.filter(p => p.status === 'pending_approval').map(po => (
                      <motion.div
                        layout
                        key={po.po_no}
                        initial={{ opacity: 0, scale: 0.95, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, x: 50, transition: { duration: 0.2 } }}
                        transition={{ type: "spring", bounce: 0.2, duration: 0.5 }}
                        className="bg-white border-2 border-black p-5 shadow-[4px_4px_0_0_#000] flex flex-col gap-4"
                      >
                        {/* Header of Dossier */}
                        <div className="flex justify-between items-start pb-4 border-b-2 border-slate-200">
                          <div className="flex flex-col gap-1">
                            <h4 className="font-black text-xl font-mono text-slate-900">{po.po_no}</h4>
                            <p className="font-bold text-slate-500 text-sm">{po.vendor_id} &bull; {po.sku}</p>
                          </div>
                          <div className="text-2xl font-black tabular-nums tracking-tight text-red-600 bg-red-50 px-3 py-1 border-2 border-red-200 shadow-inner">
                            {formatRupiah(po.total_value)}
                          </div>
                        </div>

                        {/* Body of Dossier */}
                        <div className="bg-slate-50 border-2 border-slate-200 p-4 rounded-sm flex flex-col gap-3">
                          <div className="font-bold uppercase text-slate-400 text-xs flex justify-between items-center tracking-widest">
                            <span>AI Reasoning & SOP Basis</span>
                            <Badge variant={po.basis === 'verified_sop' ? 'success' : 'warning'} className="text-[10px] px-1.5 py-0">
                              {po.basis === 'verified_sop' ? 'Verified SOP' : 'RAG / Fallback'}
                            </Badge>
                          </div>
                          <p className="font-medium text-slate-700 text-sm leading-relaxed">{po.explanation}</p>
                          <div className="mt-2 pt-3 border-t-2 border-dashed border-slate-300 grid grid-cols-2 gap-x-4 gap-y-2 text-sm bg-slate-100 p-3 rounded-sm border">
                            <div className="flex justify-between">
                              <span className="text-slate-500 font-semibold">Qty:</span>
                              <span className="font-black tabular-nums">{po.qty}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500 font-semibold">Unit Price:</span>
                              <span className="font-black tabular-nums">{formatRupiah(po.unit_price)}</span>
                            </div>
                            {po.erp_po_no && (
                              <div className="col-span-2 flex justify-between">
                                <span className="text-slate-500 font-semibold">ERP Ref:</span>
                                <span className="font-black tabular-nums">{po.erp_po_no}</span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex gap-4 mt-2">
                          <Button variant="success" className="flex-1 text-sm py-3" onClick={() => openAction(po, 'approve')}>
                            Approve
                          </Button>
                          <Button variant="outline" className="flex-1 text-sm py-3 hover:bg-red-50 hover:text-red-600 border-slate-300" onClick={() => openAction(po, 'reject')}>
                            Reject
                          </Button>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ACTION MODAL (Approve/Reject with reviewer + mandatory note) */}
      <AnimatePresence>
        {actionFor && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 p-4"
            onClick={() => setActionFor(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ type: "spring", bounce: 0.2, duration: 0.4 }}
              className="w-full max-w-md bg-white border-2 border-black shadow-[6px_6px_0_0_#000] p-6 flex flex-col gap-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-black text-xl uppercase tracking-tight">
                    {actionType === 'approve' ? 'Approve' : 'Reject'} PO
                  </h3>
                  <p className="font-mono font-bold text-slate-500 text-sm mt-1">{actionFor.po_no}</p>
                </div>
                <button onClick={() => setActionFor(null)} aria-label="Close" className="p-1 border-2 border-black hover:bg-slate-100 transition-colors">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Reviewer</label>
                <input
                  data-testid="reviewer-input"
                  value={actionReviewer}
                  onChange={(e) => setActionReviewer(e.target.value)}
                  placeholder="Nama reviewer"
                  className="border-2 border-black p-2.5 font-bold focus:outline-none focus:ring-2 focus:ring-black"
                />
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-widest text-slate-500">
                  {actionType === 'reject' ? 'Rejection note (required)' : 'Note (optional)'}
                </label>
                <textarea
                  data-testid="note-input"
                  value={actionNote}
                  onChange={(e) => setActionNote(e.target.value)}
                  placeholder={actionType === 'reject' ? "Alasan penolakan wajib diisi" : "Catatan opsional"}
                  rows={3}
                  className="border-2 border-black p-2.5 font-medium focus:outline-none focus:ring-2 focus:ring-black resize-none"
                />
              </div>

              {actionError && (
                <div className="bg-red-100 border-2 border-red-500 text-red-800 font-bold text-sm p-3">
                  {actionError}
                </div>
              )}

              <div className="flex gap-3 mt-2">
                <Button
                  data-testid="confirm-action"
                  variant={actionType === 'approve' ? 'success' : 'danger'}
                  className="flex-1"
                  onClick={confirmAction}
                >
                  {actionType === 'approve' ? 'Confirm Approve' : 'Confirm Reject'}
                </Button>
                <Button variant="outline" onClick={() => setActionFor(null)}>Cancel</Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* GLOBAL TOAST NOTIFICATION (Fixed Position to Prevent Layout Shifts) */}
      <AnimatePresence mode="wait">
        {scanMessage && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className={cn(
              "fixed bottom-6 right-6 md:bottom-10 md:right-10 z-[100] flex items-center justify-center gap-3 text-xs md:text-sm font-bold font-mono uppercase tracking-widest px-4 py-3 md:px-6 md:py-4 border-2 border-black rounded-sm shadow-[4px_4px_0_0_#000]",
              scanMessage.toLowerCase().includes("failed") ? "bg-red-300 text-red-950" :
              scanMessage.toLowerCase().includes("complete") ? "bg-emerald-300 text-emerald-950" :
              "bg-[#e0e7ff] text-blue-900"
            )}
          >
            {scanMessage.toLowerCase().includes("initializing") || scanMessage.toLowerCase().includes("scanning") ? (
              <RefreshCw className="w-4 h-4 md:w-5 md:h-5 animate-spin shrink-0" />
            ) : scanMessage.toLowerCase().includes("failed") ? (
              <AlertTriangle className="w-4 h-4 md:w-5 md:h-5 shrink-0" />
            ) : (
              <CheckCircle className="w-4 h-4 md:w-5 md:h-5 shrink-0" />
            )}
            <span className="truncate">{scanMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}

function MetricCard({ title, value, icon, alert = false }: { title: string, value: string | number, icon: React.ReactNode, alert?: boolean }) {
  return (
    <Card className={cn("p-5 flex flex-col justify-between gap-4 h-full", alert ? "bg-red-500 text-white shadow-[4px_4px_0_0_#7f1d1d] border-red-900" : "")}>
      <CardHeader className="flex flex-row items-center justify-between pb-0">
        <CardTitle className={cn("text-sm font-bold uppercase tracking-widest leading-tight", alert ? "text-red-100" : "text-slate-500")}>{title}</CardTitle>
        <div className={cn("p-2 border-2 border-black shadow-[2px_2px_0_0_#000] bg-white text-black rounded-sm")}>
          {icon}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="text-4xl font-black tabular-nums tracking-tight">{value}</div>
      </CardContent>
    </Card>
  );
}
