// ═══════════════════════════════════════════════════════
// Component 3 — Report Center
// Generate / preview / manage reports built entirely from real
// optimization_results data (same source as the History tab and Firestore).
// No mock or random data anywhere in this file.
// ═══════════════════════════════════════════════════════
import React, { useState, useEffect, useRef, useCallback } from "react";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import {
  generateReport, listReports, getReport, deleteReport, getReportFilterOptions,
} from "../services/api";
import translations from "../translations";
import { logActivity } from "../activityLog";
import { F, G, GL, GLL, GB, METHOD_META, getSafetyMeta } from "../theme";
import { Donut, BarChart, HBar } from "../components/Charts";
import ToastStack, { useToasts } from "../components/Toast";
import ConfirmDialog from "../components/ConfirmDialog";

const PAGE_SIZE = 8;
const REPORT_TYPE_KEY = { Summary: "typeSummary", Safety: "typeSafety", Efficiency: "typeEfficiency", "Material Breakdown": "typeMaterial" };

function fmtDate(iso, withTime = false) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
      + (withTime ? ", " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : "");
  } catch { return "—"; }
}

function csvEscape(v) {
  const s = v === null || v === undefined ? "" : String(v);
  return `"${s.replace(/"/g, '""')}"`;
}

export default function Reports({ lang = "EN", darkMode = false }) {
  const t = translations[lang];
  const [subTab, setSubTab] = useState("overview"); // overview | generate | preview | history
  const [reports, setReports] = useState([]);
  const [loadingReports, setLoadingReports] = useState(true);
  const [filterOptions, setFilterOptions] = useState({ materials: [], waste_types: [], safety_statuses: [], report_types: [] });
  const [activeReport, setActiveReport] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [formError, setFormError] = useState(null);
  const [form, setForm] = useState({
    reportType: "Summary", title: "", dateFrom: "", dateTo: "",
    wasteType: "", materialName: "", safetyStatus: "", createdBy: "",
  });
  const [confirmState, setConfirmState] = useState({ open: false, id: null });
  const [histSearch, setHistSearch] = useState("");
  const [histTypeFilter, setHistTypeFilter] = useState("");
  const [histPage, setHistPage] = useState(1);
  const { toasts, push, dismiss } = useToasts();
  const previewRef = useRef(null);

  const loadReports = useCallback(async () => {
    setLoadingReports(true);
    try {
      const d = await listReports(50);
      setReports(d.reports || []);
    } catch {
      push(t.toastLoadFailed, "error");
    } finally {
      setLoadingReports(false);
    }
  }, [push, t]);

  useEffect(() => {
    loadReports();
    getReportFilterOptions().then(setFilterOptions).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setField = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleGenerate = async () => {
    if (form.dateFrom && form.dateTo && form.dateFrom > form.dateTo) {
      setFormError("The 'From' date must be before the 'To' date.");
      return;
    }
    setFormError(null);
    setGenerating(true);
    try {
      const payload = {
        report_type: form.reportType,
        title: form.title || undefined,
        date_from: form.dateFrom ? new Date(form.dateFrom).toISOString() : undefined,
        date_to: form.dateTo ? new Date(form.dateTo + "T23:59:59").toISOString() : undefined,
        waste_type: form.wasteType || undefined,
        material_name: form.materialName || undefined,
        safety_status: form.safetyStatus || undefined,
        created_by: form.createdBy || undefined,
      };
      const report = await generateReport(payload);
      setActiveReport(report);
      setReports(r => [{ ...report, rows: undefined }, ...r]);
      push(t.toastGenerated, "success");
      logActivity("report", `Report "${report.title}" generated (${report.summary?.total_batches ?? 0} batches)`);
      setSubTab("preview");
    } catch {
      push(t.toastGenFailed, "error");
    } finally {
      setGenerating(false);
    }
  };

  const handleOpenReport = async (id) => {
    try {
      const report = await getReport(id);
      setActiveReport(report);
      setSubTab("preview");
    } catch {
      push(t.toastLoadFailed, "error");
    }
  };

  const handleRegenerate = async () => {
    if (!activeReport) return;
    setGenerating(true);
    try {
      const payload = { report_type: activeReport.report_type, title: activeReport.title, created_by: activeReport.created_by, ...activeReport.filters };
      const fresh = await generateReport(payload);
      setActiveReport(fresh);
      setReports(r => [{ ...fresh, rows: undefined }, ...r]);
      push(t.toastGenerated, "success");
    } catch {
      push(t.toastGenFailed, "error");
    } finally {
      setGenerating(false);
    }
  };

  const requestDelete = (id) => setConfirmState({ open: true, id });
  const confirmDelete = async () => {
    const id = confirmState.id;
    const deletedTitle = reports.find(r => r.id === id)?.title || "Report";
    setConfirmState({ open: false, id: null });
    try {
      await deleteReport(id);
      setReports(r => r.filter(x => x.id !== id));
      if (activeReport && activeReport.id === id) { setActiveReport(null); setSubTab("history"); }
      push(t.toastDeleted, "success");
      logActivity("report-delete", `Report "${deletedTitle}" deleted`);
    } catch {
      push(t.toastDelFailed, "error");
    }
  };

  const handleDownloadPdf = async () => {
    if (!previewRef.current || !activeReport) return;
    try {
      const canvas = await html2canvas(previewRef.current, { scale: 2, backgroundColor: "#ffffff", useCORS: true });
      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "pt", "a4");
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const imgWidth = pageWidth;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let heightLeft = imgHeight, position = 0;
      pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;
      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }
      pdf.save(`${(activeReport.title || "report").replace(/\s+/g, "_")}.pdf`);
      push(t.toastPdfReady, "success");
    } catch {
      push(t.toastPdfFailed, "error");
    }
  };

  const handlePrint = () => window.print();

  const handleExportCsv = (report) => {
    const r = report || activeReport;
    if (!r || !r.rows || r.rows.length === 0) { push(t.insightNoRecords, "error"); return; }
    const headers = Object.keys(r.rows[0]);
    const lines = [headers.join(","), ...r.rows.map(row => headers.map(h => csvEscape(row[h])).join(","))];
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${(r.title || "report").replace(/\s+/g, "_")}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    push(t.toastCsvReady, "success");
  };

  const handleDownloadFromHistory = async (id) => {
    try {
      const full = await getReport(id);
      handleExportCsv(full);
    } catch {
      push(t.toastLoadFailed, "error");
    }
  };

  // ── Derived data ──
  const latestReport = reports[0];
  const recentReports = reports.slice(0, 5);

  const filteredHistory = reports.filter(r => {
    const q = histSearch.trim().toLowerCase();
    const matchesSearch = !q || (r.title || "").toLowerCase().includes(q) || (r.report_type || "").toLowerCase().includes(q);
    const matchesType = !histTypeFilter || r.report_type === histTypeFilter;
    return matchesSearch && matchesType;
  });
  const totalPages = Math.max(1, Math.ceil(filteredHistory.length / PAGE_SIZE));
  const pageSafe = Math.min(histPage, totalPages);
  const pagedHistory = filteredHistory.slice((pageSafe - 1) * PAGE_SIZE, pageSafe * PAGE_SIZE);

  const NAV_ITEMS = [
    { id: "overview", icon: "📊", label: t.navOverview },
    { id: "generate", icon: "⚡", label: t.navGenerate },
    { id: "history", icon: "📜", label: t.navHistory },
  ];

  return (
    <div className="fade-up">
      <style>{`
        @media print {
          body * { visibility: hidden !important; }
          #report-print-area, #report-print-area * { visibility: visible !important; }
          #report-print-area { position: absolute; left: 0; top: 0; width: 100%; }
          .no-print { display: none !important; }
        }
        .rpt-input:focus, .rpt-select:focus { outline: none; border-color: ${GL}; }
      `}</style>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
      <ConfirmDialog
        open={confirmState.open}
        title={t.confirmDeleteTitle}
        message={t.confirmDeleteMsg}
        confirmLabel={t.confirmDeleteBtn}
        cancelLabel={t.cancelBtn}
        danger
        onConfirm={confirmDelete}
        onCancel={() => setConfirmState({ open: false, id: null })}
      />

      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 18, fontWeight: 700, color: G, fontFamily: F }}>{t.reportsTitle}</div>
        <div style={{ fontSize: 13, color: "#9E9E9E", fontFamily: F, marginTop: 2 }}>{t.reportsSub}</div>
      </div>

      {/* Sub-nav pills */}
      <div className="no-print" style={{ display: "flex", gap: 8, marginBottom: 22, flexWrap: "wrap" }}>
        {NAV_ITEMS.map(n => (
          <button key={n.id} onClick={() => setSubTab(n.id)} style={{
            padding: "9px 18px", borderRadius: 20, cursor: "pointer", fontFamily: F, fontSize: 13,
            border: `1.5px solid ${subTab === n.id ? GL : "#E0E0E0"}`,
            background: subTab === n.id ? GB : "#FFFFFF",
            color: subTab === n.id ? G : "#757575",
            fontWeight: subTab === n.id ? 700 : 400,
            display: "flex", alignItems: "center", gap: 7,
          }}>
            <span>{n.icon}</span>{n.label}
          </button>
        ))}
        {activeReport && (
          <button onClick={() => setSubTab("preview")} style={{
            padding: "9px 18px", borderRadius: 20, cursor: "pointer", fontFamily: F, fontSize: 13,
            border: `1.5px solid ${subTab === "preview" ? GL : "#E0E0E0"}`,
            background: subTab === "preview" ? GB : "#FFFFFF",
            color: subTab === "preview" ? G : "#757575",
            fontWeight: subTab === "preview" ? 700 : 400,
          }}>
            👁 {t.prevPreview}
          </button>
        )}
      </div>

      {subTab === "overview" && (
        <OverviewView t={t} reports={reports} loading={loadingReports} latestReport={latestReport}
          recentReports={recentReports} onCreate={() => setSubTab("generate")} onOpen={handleOpenReport} />
      )}

      {subTab === "generate" && (
        <GenerateView t={t} form={form} setField={setField} formError={formError}
          filterOptions={filterOptions} generating={generating} onGenerate={handleGenerate} />
      )}

      {subTab === "preview" && (
        activeReport
          ? <PreviewView t={t} report={activeReport} previewRef={previewRef}
              onBack={() => setSubTab(reports.length ? "history" : "overview")}
              onDownload={handleDownloadPdf} onPrint={handlePrint}
              onExport={() => handleExportCsv(activeReport)}
              onRegenerate={handleRegenerate} onDelete={() => requestDelete(activeReport.id)}
              generating={generating} darkMode={darkMode} />
          : <EmptyState t={t} onCreate={() => setSubTab("generate")} />
      )}

      {subTab === "history" && (
        <HistoryView t={t} darkMode={darkMode} reports={pagedHistory} totalCount={filteredHistory.length} loading={loadingReports}
          search={histSearch} setSearch={(v) => { setHistSearch(v); setHistPage(1); }}
          typeFilter={histTypeFilter} setTypeFilter={(v) => { setHistTypeFilter(v); setHistPage(1); }}
          reportTypes={filterOptions.report_types} page={pageSafe} totalPages={totalPages} setPage={setHistPage}
          onView={handleOpenReport} onDownload={handleDownloadFromHistory} onDelete={requestDelete}
          onCreate={() => setSubTab("generate")} />
      )}
    </div>
  );
}

// ═══════════════════════════ Overview ═══════════════════════════
function StatCard({ icon, val, label, sub, col, bg }) {
  return (
    <div className="card" style={{ background: "#FFFFFF", borderRadius: 10, border: "1px solid #E8E8E8", padding: 20, boxShadow: "0 1px 4px rgba(0,0,0,0.05)" }}>
      <div style={{ width: 40, height: 40, borderRadius: 8, background: bg, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, marginBottom: 12 }}>{icon}</div>
      <div style={{ fontSize: 26, fontWeight: 700, color: col, fontFamily: F }}>{val}</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A", fontFamily: F, marginTop: 2 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: "#9E9E9E", fontFamily: F, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function StatusBadge({ status, t }) {
  const ok = status === "completed";
  return (
    <span style={{
      padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, fontFamily: F,
      color: ok ? G : "#D97706", background: ok ? GB : "#FFF5DF", border: `1px solid ${ok ? GLL + "70" : "#F3C878"}`,
    }}>
      {ok ? "✅" : "⚠️"} {ok ? "Completed" : "No Data"}
    </span>
  );
}

function OverviewView({ t, reports, loading, latestReport, recentReports, onCreate, onOpen }) {
  if (loading) return <LoadingBlock t={t} />;
  if (reports.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "80px", background: "#FFFFFF", borderRadius: 10, border: "1px solid #E0E0E0" }}>
        <div style={{ fontSize: 48, marginBottom: 12, opacity: 0.2 }}>📄</div>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#BDBDBD", fontFamily: F, marginBottom: 6 }}>{t.ovNoReports}</div>
        <div style={{ fontSize: 13, color: "#BDBDBD", fontFamily: F, marginBottom: 18 }}>{t.ovNoReportsSub}</div>
        <button onClick={onCreate} style={{ padding: "12px 28px", borderRadius: 8, border: "none", background: `linear-gradient(135deg,${GL},${G})`, color: "#fff", fontFamily: F, fontSize: 14, fontWeight: 700, cursor: "pointer" }}>{t.ovCreateFirst}</button>
      </div>
    );
  }

  const s = latestReport?.summary || {};
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 16, marginBottom: 24 }}>
        <StatCard icon="📄" val={reports.length} label={t.ovTotalReports} sub={t.reportsTitle} col={GL} bg={GB} />
        <StatCard icon="🕐" val={fmtDate(latestReport?.generated_at)} label={t.ovRecentReports} sub={latestReport?.title} col="#00695C" bg="#E0F2F1" />
        <StatCard icon="📦" val={s.total_batches ?? "—"} label={t.ovTotalBatches} sub={latestReport?.title} col="#6A1B9A" bg="#F3E5F5" />
        <StatCard icon="📈" val={s.avg_efficiency_pct != null ? `${s.avg_efficiency_pct}%` : "—"} label={t.ovAvgEfficiency} sub={latestReport?.title} col="#E65100" bg="#FFF3E0" />
      </div>

      <div className="card" style={{ background: "#FFFFFF", borderRadius: 10, border: "1px solid #E0E0E0", padding: "20px 22px", boxShadow: "0 1px 4px rgba(0,0,0,0.05)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#1A1A1A", fontFamily: F }}>{t.ovRecentReports}</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {recentReports.map(r => (
            <div key={r.id} onClick={() => onOpen(r.id)} className="hist-row" style={{
              display: "flex", alignItems: "center", gap: 14, padding: "12px 14px", borderRadius: 8,
              border: "1px solid #F0F0F0", cursor: "pointer",
            }}>
              <span style={{ fontSize: 18 }}>📄</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A", fontFamily: F, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.title}</div>
                <div style={{ fontSize: 11, color: "#9E9E9E", fontFamily: F }}>{r.report_type} · {fmtDate(r.generated_at, true)}</div>
              </div>
              <StatusBadge status={r.status} t={t} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function LoadingBlock({ t }) {
  return (
    <div className="card" style={{ textAlign: "center", padding: "80px", background: "#FFFFFF", borderRadius: 10, border: "1px solid #E0E0E0" }}>
      <div className="pulse" style={{ fontSize: 32, color: GL }}>●</div>
      <div style={{ fontSize: 13, color: "#9E9E9E", fontFamily: F, marginTop: 10 }}>Loading…</div>
    </div>
  );
}

function EmptyState({ t, onCreate }) {
  return (
    <div className="card" style={{ textAlign: "center", padding: "80px", background: "#FFFFFF", borderRadius: 10, border: "1px solid #E0E0E0" }}>
      <div style={{ fontSize: 48, marginBottom: 12, opacity: 0.2 }}>👁</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: "#BDBDBD", fontFamily: F, marginBottom: 6 }}>{t.ovNoReports}</div>
      <button onClick={onCreate} style={{ marginTop: 8, padding: "12px 28px", borderRadius: 8, border: "none", background: `linear-gradient(135deg,${GL},${G})`, color: "#fff", fontFamily: F, fontSize: 14, fontWeight: 700, cursor: "pointer" }}>{t.ovCreateFirst}</button>
    </div>
  );
}

// ═══════════════════════════ Generate ═══════════════════════════
function FieldLabel({ children }) {
  return <div style={{ fontSize: 10, fontWeight: 700, color: GL, letterSpacing: "0.1em", fontFamily: F, marginBottom: 7 }}>{children}</div>;
}
const selectStyle = { width: "100%", padding: "10px 12px", borderRadius: 8, border: "1px solid #E0E0E0", background: "#FAFAFA", color: "#1A1A1A", fontSize: 13, fontFamily: F, outline: "none" };
const inputStyle = { ...selectStyle };

function GenerateView({ t, form, setField, formError, filterOptions, generating, onGenerate }) {
  return (
    <div className="card" style={{ background: "#FFFFFF", borderRadius: 10, border: "1px solid #E0E0E0", padding: "26px 28px", maxWidth: 720, boxShadow: "0 1px 4px rgba(0,0,0,0.05)" }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: "#1A1A1A", fontFamily: F, marginBottom: 4 }}>{t.genTitle}</div>
      <div style={{ fontSize: 12, color: "#9E9E9E", fontFamily: F, marginBottom: 22 }}>{t.genSub}</div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <FieldLabel>{t.genReportType}</FieldLabel>
          <select className="rpt-select" value={form.reportType} onChange={e => setField("reportType", e.target.value)} style={selectStyle}>
            {(filterOptions.report_types?.length ? filterOptions.report_types : ["Summary", "Safety", "Efficiency", "Material Breakdown"]).map(rt => (
              <option key={rt} value={rt}>{t[REPORT_TYPE_KEY[rt]] || rt}</option>
            ))}
          </select>
        </div>
        <div>
          <FieldLabel>{t.genTitleLabel}</FieldLabel>
          <input className="rpt-input" value={form.title} onChange={e => setField("title", e.target.value)} placeholder={t.genTitlePh} style={inputStyle} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <FieldLabel>{t.genDateFrom}</FieldLabel>
          <input className="rpt-input" type="date" value={form.dateFrom} onChange={e => setField("dateFrom", e.target.value)} style={inputStyle} />
        </div>
        <div>
          <FieldLabel>{t.genDateTo}</FieldLabel>
          <input className="rpt-input" type="date" value={form.dateTo} onChange={e => setField("dateTo", e.target.value)} style={inputStyle} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <FieldLabel>{t.genWasteType}</FieldLabel>
          <select className="rpt-select" value={form.wasteType} onChange={e => setField("wasteType", e.target.value)} style={selectStyle}>
            <option value="">{t.genAllOption}</option>
            {filterOptions.waste_types?.map(w => <option key={w} value={w}>{w}</option>)}
          </select>
        </div>
        <div>
          <FieldLabel>{t.genMaterial}</FieldLabel>
          <select className="rpt-select" value={form.materialName} onChange={e => setField("materialName", e.target.value)} style={selectStyle}>
            <option value="">{t.genAllOption}</option>
            {filterOptions.materials?.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <div>
          <FieldLabel>{t.genSafetyStatus}</FieldLabel>
          <select className="rpt-select" value={form.safetyStatus} onChange={e => setField("safetyStatus", e.target.value)} style={selectStyle}>
            <option value="">{t.genAllOption}</option>
            {filterOptions.safety_statuses?.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      <div style={{ marginBottom: 22 }}>
        <FieldLabel>{t.genCreatedBy}</FieldLabel>
        <input className="rpt-input" value={form.createdBy} onChange={e => setField("createdBy", e.target.value)} placeholder={t.genCreatedByPh} style={{ ...inputStyle, maxWidth: 320 }} />
      </div>

      {formError && (
        <div style={{ padding: "10px 14px", borderRadius: 8, background: "#FFEBEE", border: "1px solid #EF9A9A", color: "#B71C1C", fontSize: 12, fontFamily: F, marginBottom: 16 }}>🚨 {formError}</div>
      )}

      <button className="gen-btn" onClick={onGenerate} disabled={generating} style={{
        padding: "14px 30px", borderRadius: 8, border: "none", cursor: generating ? "not-allowed" : "pointer",
        background: generating ? "#BDBDBD" : `linear-gradient(135deg,${GL},${G})`,
        color: "#FFFFFF", fontSize: 14, fontFamily: F, fontWeight: 700,
        display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
      }}>
        {generating ? (<><span className="pulse">●</span><span className="pulse" style={{ animationDelay: "0.2s" }}>●</span><span className="pulse" style={{ animationDelay: "0.4s" }}>●</span><span style={{ marginLeft: 6 }}>{t.genGenerating}</span></>) : t.genGenerateBtn}
      </button>
    </div>
  );
}

// ═══════════════════════════ Preview (the report document) ═══════════════════════════
function ActionBtn({ onClick, children, primary, danger, disabled }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "9px 16px", borderRadius: 8, cursor: disabled ? "not-allowed" : "pointer", fontFamily: F, fontSize: 12.5, fontWeight: 700,
      border: `1.5px solid ${danger ? "#EF9A9A" : primary ? GL : "#E0E0E0"}`,
      background: danger ? "#FFEBEE" : primary ? `linear-gradient(135deg,${GL},${G})` : "#FFFFFF",
      color: danger ? "#B71C1C" : primary ? "#FFFFFF" : "#555",
      opacity: disabled ? 0.6 : 1,
    }}>{children}</button>
  );
}

function PreviewView({ t, report, previewRef, onBack, onDownload, onPrint, onExport, onRegenerate, onDelete, generating }) {
  const s = report.summary || {};
  const rows = report.rows || [];
  const periodFrom = report.filters?.date_from || s.date_range?.from;
  const periodTo = report.filters?.date_to || s.date_range?.to;

  const methodData = Object.entries(s.method_breakdown || {}).map(([k, v]) => ({
    label: k, value: v.pct, display: `${v.pct}%`, color: (METHOD_META[k] || {}).color || GL,
  }));
  const materialData = Object.entries(s.material_breakdown || {}).sort((a, b) => b[1].count - a[1].count).slice(0, 6);
  const topMaterial = materialData[0]?.[0];
  const safetyEntries = Object.entries(s.safety_breakdown || {});

  const insights = [];
  if (s.total_batches > 0) {
    const securePct = s.safety_breakdown?.SECURE?.pct || 0;
    insights.push(`${securePct}% ${t.insightHighSafety}`);
    if (topMaterial) insights.push(`${topMaterial} ${t.insightTopMaterial}`);
    insights.push(`A ${s.avg_efficiency_pct}% ${t.insightAvgEff}`);
  } else {
    insights.push(t.insightNoRecords);
  }

  return (
    <div>
      <div className="no-print" style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 18, alignItems: "center" }}>
        <button onClick={onBack} style={{ background: "none", border: "none", color: G, fontFamily: F, fontSize: 13, fontWeight: 700, cursor: "pointer" }}>{t.prevBack}</button>
        <div style={{ flex: 1 }} />
        <ActionBtn onClick={onDownload} primary>{t.prevDownload}</ActionBtn>
        <ActionBtn onClick={onPrint}>{t.prevPrint}</ActionBtn>
        <ActionBtn onClick={onExport}>{t.prevExport}</ActionBtn>
        <ActionBtn onClick={onRegenerate} disabled={generating}>{t.prevRegenerate}</ActionBtn>
        <ActionBtn onClick={onDelete} danger>{t.prevDelete}</ActionBtn>
      </div>

      <div id="report-print-area" ref={previewRef} style={{
        background: "#FFFFFF", borderRadius: 10, border: "1px solid #E0E0E0", boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
        padding: "40px 48px", maxWidth: 880, margin: "0 auto", color: "#1A1A1A",
      }}>
        {/* Cover / header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: `3px solid ${G}`, paddingBottom: 20, marginBottom: 28 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 46, height: 46, borderRadius: 10, background: GB, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24 }}>♻</div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: G, fontFamily: F }}>{t.prevOrgName}</div>
              <div style={{ fontSize: 10.5, color: "#9E9E9E", fontFamily: F }}>{t.prevSystemLine}</div>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <StatusBadge status={report.status} t={t} />
          </div>
        </div>

        <div style={{ fontSize: 24, fontWeight: 700, color: "#1A1A1A", fontFamily: F, marginBottom: 6 }}>{report.title}</div>
        <div style={{ fontSize: 12, color: "#9E9E9E", fontFamily: F, marginBottom: 20 }}>{t[REPORT_TYPE_KEY[report.report_type]] || report.report_type} {t.reportsTitle}</div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, padding: "16px 20px", background: "#FAFAFA", borderRadius: 8, border: "1px solid #F0F0F0", marginBottom: 30, fontFamily: F }}>
          <div><div style={{ fontSize: 10, color: "#9E9E9E", marginBottom: 3 }}>{t.prevGeneratedOn}</div><div style={{ fontSize: 13, fontWeight: 700 }}>{fmtDate(report.generated_at, true)}</div></div>
          <div><div style={{ fontSize: 10, color: "#9E9E9E", marginBottom: 3 }}>{t.prevReportingPeriod}</div><div style={{ fontSize: 13, fontWeight: 700 }}>{periodFrom || periodTo ? `${fmtDate(periodFrom)} – ${fmtDate(periodTo)}` : t.prevAllTime}</div></div>
          <div><div style={{ fontSize: 10, color: "#9E9E9E", marginBottom: 3 }}>{t.genCreatedBy}</div><div style={{ fontSize: 13, fontWeight: 700 }}>{report.created_by}</div></div>
        </div>

        {/* Executive summary */}
        <SectionTitle>{t.prevSummarySec}</SectionTitle>
        <p style={{ fontSize: 13, color: "#444", fontFamily: F, lineHeight: 1.7, marginBottom: 24 }}>
          {s.total_batches > 0
            ? `This report covers ${s.total_batches} optimization ${s.total_batches === 1 ? "batch" : "batches"}, totalling ${s.total_weight_kg} kg of material and ${s.total_energy_kwh} kWh of energy. The average recycling efficiency across all included batches was ${s.avg_efficiency_pct}%, with an average processing time of ${s.avg_processing_time_min} minutes per batch.`
            : t.insightNoRecords}
        </p>

        {/* Key metrics */}
        <SectionTitle>{t.prevKeyMetrics}</SectionTitle>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 10, marginBottom: 28 }}>
          {[
            { label: t.metricBatches, val: s.total_batches, col: GL, bg: GB },
            { label: t.metricWeight, val: `${s.total_weight_kg ?? 0} kg`, col: "#37474F", bg: "#ECEFF1" },
            { label: t.metricEnergy, val: `${s.total_energy_kwh ?? 0} kWh`, col: "#E65100", bg: "#FFF3E0" },
            { label: t.metricEfficiency, val: `${s.avg_efficiency_pct ?? 0}%`, col: G, bg: GB },
            { label: t.metricTime, val: `${s.avg_processing_time_min ?? 0} min`, col: "#6A1B9A", bg: "#F3E5F5" },
          ].map(m => (
            <div key={m.label} style={{ background: m.bg, borderRadius: 8, padding: "12px 10px", textAlign: "center" }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: m.col, fontFamily: F }}>{m.val}</div>
              <div style={{ fontSize: 9.5, color: "#757575", fontFamily: F, marginTop: 3 }}>{m.label}</div>
            </div>
          ))}
        </div>

        {/* Charts */}
        {s.total_batches > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 28 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: GL, letterSpacing: "0.08em", fontFamily: F, marginBottom: 10 }}>{t.secMethodSplit}</div>
              {methodData.length > 0 ? <BarChart data={methodData} height={100} /> : <NoChartData />}
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: GL, letterSpacing: "0.08em", fontFamily: F, marginBottom: 10 }}>{t.secSafetySplit}</div>
              <div style={{ display: "flex", gap: 18, justifyContent: "flex-start" }}>
                {safetyEntries.length > 0 ? safetyEntries.map(([k, v]) => (
                  <Donut key={k} pct={v.pct} color={getSafetyMeta(k).color} label={`${k} (${v.count})`} size={82} />
                )) : <NoChartData />}
              </div>
            </div>
          </div>
        )}

        {materialData.length > 0 && (
          <div style={{ marginBottom: 28 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: GL, letterSpacing: "0.08em", fontFamily: F, marginBottom: 10 }}>{t.secMaterialSplit}</div>
            {materialData.map(([name, v]) => (
              <HBar key={name} value={v.pct} max={100} color={GL} label={`${name} (${v.count})`} unit="%" />
            ))}
          </div>
        )}

        {/* Detailed records table */}
        <SectionTitle>{t.prevRecordsSec}</SectionTitle>
        <div style={{ fontSize: 11, color: "#9E9E9E", fontFamily: F, marginBottom: 10 }}>{rows.length} {t.prevRecordsSub}</div>
        {rows.length > 0 ? (
          <div style={{ overflowX: "auto", marginBottom: 28, border: "1px solid #E8E8E8", borderRadius: 8 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: F, fontSize: 11.5 }}>
              <thead>
                <tr style={{ background: G }}>
                  {[t.colDate, t.colMaterial, t.colType, t.colWeight, t.colMethod, t.colEnergy, t.colEfficiency, t.colSafety].map(h => (
                    <th key={h} style={{ padding: "9px 10px", color: "#FFFFFF", fontWeight: 700, textAlign: "left", fontSize: 9.5, letterSpacing: "0.06em" }}>{h.toUpperCase()}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const sm = getSafetyMeta(r.safety_status);
                  return (
                    <tr key={r.id || i} style={{ background: i % 2 === 0 ? "#FAFAFA" : "#FFFFFF", borderTop: "1px solid #F0F0F0" }}>
                      <td style={{ padding: "8px 10px" }}>{fmtDate(r.timestamp)}</td>
                      <td style={{ padding: "8px 10px", fontWeight: 600 }}>{r.material_name}</td>
                      <td style={{ padding: "8px 10px" }}>{r.waste_type || "—"}</td>
                      <td style={{ padding: "8px 10px" }}>{r.weight_kg} kg</td>
                      <td style={{ padding: "8px 10px" }}>{r.recommended_method || "—"}</td>
                      <td style={{ padding: "8px 10px" }}>{r.energy_kwh ?? "—"} kWh</td>
                      <td style={{ padding: "8px 10px" }}>{r.recycling_efficiency_pct ?? "—"}%</td>
                      <td style={{ padding: "8px 10px" }}>
                        <span style={{ padding: "2px 8px", borderRadius: 10, fontSize: 10, fontWeight: 700, color: sm.color, background: sm.light }}>{r.safety_status || "—"}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : <NoChartData style={{ marginBottom: 28 }} />}

        {/* Insights */}
        <SectionTitle>{t.prevInsightsSec}</SectionTitle>
        <ul style={{ fontSize: 12.5, color: "#444", fontFamily: F, lineHeight: 1.9, marginBottom: 30, paddingLeft: 20 }}>
          {insights.map((ins, i) => <li key={i}>{ins}</li>)}
        </ul>

        {/* Footer */}
        <div style={{ borderTop: "1px solid #E8E8E8", paddingTop: 14, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: 10, color: "#BDBDBD", fontFamily: F, maxWidth: 560, lineHeight: 1.5 }}>{t.prevFooterNote}</div>
          <div style={{ fontSize: 10, color: "#BDBDBD", fontFamily: F }}>{t.prevPageInfo}</div>
        </div>
      </div>
    </div>
  );
}

function SectionTitle({ children }) {
  return <div style={{ fontSize: 13, fontWeight: 700, color: G, fontFamily: F, marginBottom: 12, paddingBottom: 6, borderBottom: `1px solid ${GB}` }}>{children}</div>;
}
function NoChartData({ style }) {
  return <div style={{ padding: 16, textAlign: "center", fontSize: 11, color: "#BDBDBD", fontFamily: F, background: "#FAFAFA", borderRadius: 8, ...style }}>No data for this section</div>;
}

// ═══════════════════════════ History ═══════════════════════════
function HistoryView({ t, darkMode, reports, totalCount, loading, search, setSearch, typeFilter, setTypeFilter, reportTypes, page, totalPages, setPage, onView, onDownload, onDelete, onCreate }) {
  if (loading) return <LoadingBlock t={t} />;

  const panelBg = darkMode ? "#17231F" : "#FFFFFF";
  const panelBorder = darkMode ? "#315348" : "#E0E0E0";
  const rowBg = darkMode ? ["#17231F", "#1B2B25"] : ["#FFFFFF", "#FAFAFA"];
  const primaryText = darkMode ? "#F0F7F3" : "#1A1A1A";
  const secondaryText = darkMode ? "#B8C9C1" : "#555";
  const rowBorder = darkMode ? "#315348" : "#F0F0F0";
  const btnStyle = {
    width: 30, height: 30, borderRadius: 6, cursor: "pointer", fontSize: 13,
    display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F,
    border: `1px solid ${darkMode ? "#477563" : "#E0E0E0"}`,
    background: darkMode ? "#20332B" : "#FFFFFF",
    color: primaryText,
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 18, flexWrap: "wrap" }}>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder={t.reportHistSearch}
          className="rpt-input" style={{ ...inputStyle, flex: 1, minWidth: 220 }} />
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="rpt-select" style={{ ...selectStyle, width: 200 }}>
          <option value="">{t.reportHistFilter}</option>
          {reportTypes?.map(rt => <option key={rt} value={rt}>{t[REPORT_TYPE_KEY[rt]] || rt}</option>)}
        </select>
      </div>

      {totalCount === 0 ? (
        <div style={{ textAlign: "center", padding: "70px", background: panelBg, borderRadius: 10, border: `1px solid ${panelBorder}` }}>
          <div style={{ fontSize: 44, marginBottom: 10, opacity: 0.2 }}>🔍</div>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#BDBDBD", fontFamily: F, marginBottom: 6 }}>{t.reportHistEmpty}</div>
          <div style={{ fontSize: 13, color: "#BDBDBD", fontFamily: F, marginBottom: 16 }}>{t.reportHistEmptySub}</div>
          <button onClick={onCreate} style={{ padding: "10px 22px", borderRadius: 8, border: "none", background: `linear-gradient(135deg,${GL},${G})`, color: "#fff", fontFamily: F, fontSize: 13, fontWeight: 700, cursor: "pointer" }}>{t.ovCreateFirst}</button>
        </div>
      ) : (
        <>
          <div style={{ background: panelBg, borderRadius: 10, border: `1px solid ${panelBorder}`, overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 760 }}>
                <thead>
                  <tr style={{ background: G }}>
                    {[t.reportHistCName, t.reportHistCType, t.reportHistCCreated, t.reportHistCPeriod, t.reportHistCStatus, t.reportHistCBy, t.reportHistCActions].map(h => (
                      <th key={h} style={{ padding: "11px 16px", color: "#FFFFFF", fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", fontFamily: F, textAlign: "left" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {reports.map((r, i) => (
                    <tr key={r.id} style={{ background: rowBg[i % 2], borderBottom: `1px solid ${rowBorder}` }}>
                      <td style={{ padding: "12px 16px", fontSize: 13, fontWeight: 600, color: primaryText, fontFamily: F }}>{r.title}</td>
                      <td style={{ padding: "12px 16px", fontSize: 12, color: secondaryText, fontFamily: F }}>{t[REPORT_TYPE_KEY[r.report_type]] || r.report_type}</td>
                      <td style={{ padding: "12px 16px", fontSize: 12, color: secondaryText, fontFamily: F }}>{fmtDate(r.generated_at)}</td>
                      <td style={{ padding: "12px 16px", fontSize: 12, color: secondaryText, fontFamily: F }}>
                        {r.filters?.date_from || r.filters?.date_to
                          ? `${fmtDate(r.filters?.date_from)} – ${fmtDate(r.filters?.date_to)}`
                          : t.prevAllTime}
                      </td>
                      <td style={{ padding: "12px 16px" }}><StatusBadge status={r.status} t={t} /></td>
                      <td style={{ padding: "12px 16px", fontSize: 12, color: secondaryText, fontFamily: F }}>{r.created_by}</td>
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ display: "flex", gap: 6 }}>
                          <button title={t.reportHistView} onClick={() => onView(r.id)} style={btnStyle}>👁</button>
                          <button title={t.reportHistDl} onClick={() => onDownload(r.id)} style={btnStyle}>⬇</button>
                          <button title={t.reportHistDel} onClick={() => onDelete(r.id)} style={{ ...btnStyle, color: "#B71C1C" }}>🗑</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {totalPages > 1 && (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 14, marginTop: 16 }}>
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} style={{ ...btnStyle, width: "auto", padding: "6px 14px", opacity: page <= 1 ? 0.4 : 1 }}>{t.reportHistPrev}</button>
              <span style={{ fontSize: 12, color: secondaryText, fontFamily: F }}>{(t.reportHistPageOf || "Page {p} of {t}").replace("{p}", page).replace("{t}", totalPages)}</span>
              <button disabled={page >= totalPages} onClick={() => setPage(page + 1)} style={{ ...btnStyle, width: "auto", padding: "6px 14px", opacity: page >= totalPages ? 0.4 : 1 }}>{t.reportHistNext}</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
