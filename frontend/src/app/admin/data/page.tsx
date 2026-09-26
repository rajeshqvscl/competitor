"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  RefreshCw, Globe, FileText, Upload, FileSpreadsheet, Loader2,
  CheckCircle2, AlertTriangle, PlayCircle, Download, Database, Info,
  Link2, Save, Eye,
} from "lucide-react";
import { PageHeader } from "@/components/ui";
import {
  getIngestCompanies, startIngest, getIngestStatus,
  importPreview, importCommit,
  startScan, getScanStatus, saveScan,
} from "@/lib/api";

// ---------------------------------------------------------------- scrape card

type IngestCompany = { slug: string; name: string; website: string; in_db: boolean };
type JobStatus = {
  running: boolean;
  started_at: string | null;
  finished_at: string | null;
  log: { time: string; level: string; message: string }[];
  summary: Record<string, number>;
};
type ScanProduct = {
  name: string;
  brand: string | null;
  description: string | null;
  subcategory: string | null;
  pack_size: number | null;
  unit: string | null;
  mrp: number | null;
  selling_price: number | null;
  source_url: string | null;
};
type ScanStatus = {
  running: boolean;
  url: string | null;
  error: string | null;
  log: { time: string; level: string; message: string }[];
  report: {
    scanned_url: string;
    host: string;
    company_name: string | null;
    description: string | null;
    pages_crawled: number;
    confidence: string;
    brands: string[];
    products: ScanProduct[];
    distributors: { name: string; type: string | null; state: string | null }[];
    notes: string[];
    errors: string[];
  } | null;
};

function ScrapeCard() {
  const [companies, setCompanies] = useState<IngestCompany[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [allSelected, setAllSelected] = useState(true);
  const [sources, setSources] = useState<string[]>(["website", "report"]);
  const [dryRun, setDryRun] = useState(true);
  const [starting, setStarting] = useState(false);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // custom URL scan
  const [customUrl, setCustomUrl] = useState("");
  const [scanStarting, setScanStarting] = useState(false);
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const [savingScan, setSavingScan] = useState(false);
  const [scanSaved, setScanSaved] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const scanPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getIngestCompanies().then((cs) => {
      setCompanies(cs);
      setSelected(cs.map((c: IngestCompany) => c.slug));
    }).catch(() => setError("Could not load company list — is the backend running?"));
  }, []);

  const poll = useCallback(async () => {
    try {
      const s: JobStatus = await getIngestStatus();
      setStatus(s);
      if (!s.running && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch { /* backend hiccup — retry next tick */ }
  }, []);

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(poll, 2000);
    poll();
  }, [poll]);

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (scanPollRef.current) clearInterval(scanPollRef.current);
  }, []);

  const pollScan = useCallback(async () => {
    try {
      const s: ScanStatus = await getScanStatus();
      setScanStatus(s);
      if (!s.running && scanPollRef.current) {
        clearInterval(scanPollRef.current);
        scanPollRef.current = null;
      }
    } catch { /* retry next tick */ }
  }, []);

  const startScanPolling = useCallback(() => {
    if (scanPollRef.current) clearInterval(scanPollRef.current);
    scanPollRef.current = setInterval(pollScan, 1500);
    pollScan();
  }, [pollScan]);

  const run = async () => {
    setError(null);
    setStarting(true);
    try {
      await startIngest({
        companies: allSelected ? null : selected,
        sources,
        dry_run: dryRun,
      });
      startPolling();
    } catch (e: any) {
      const msg = String(e?.message || e);
      setError(msg.includes("409") ? "A scrape job is already running — see live log below." : msg);
    } finally {
      setStarting(false);
    }
  };

  const toggleSource = (s: string) =>
    setSources((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]);

  const toggleCompany = (slug: string) => {
    setAllSelected(false);
    setSelected((prev) => prev.includes(slug) ? prev.filter((x) => x !== slug) : [...prev, slug]);
  };

  const runUrlScan = async () => {
    const url = customUrl.trim();
    if (!url) return;
    setScanError(null);
    setScanSaved(null);
    setShowPreview(false);
    setScanStarting(true);
    try {
      await startScan(url.startsWith("http") ? url : `https://${url}`);
      startScanPolling();
    } catch (e: any) {
      const msg = String(e?.message || e);
      setScanError(msg.includes("409") ? "A scan is already running — see live log below." : msg);
    } finally {
      setScanStarting(false);
    }
  };

  const saveUrlScan = async () => {
    if (!scanStatus?.report) return;
    setSavingScan(true);
    setScanError(null);
    try {
      const res = await saveScan({
        url: scanStatus.report.scanned_url,
        company_name: scanStatus.report.company_name || undefined,
      });
      setScanSaved(res.company);
    } catch (e: any) {
      setScanError(String(e?.message || e));
    } finally {
      setSavingScan(false);
    }
  };

  const running = status?.running ?? false;
  const summary = status?.summary ?? {};
  const scanRunning = scanStatus?.running ?? false;
  const scanReport = scanStatus?.report ?? null;

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2.5 mb-1">
        <span className="w-8 h-8 rounded-lg bg-brand-50 text-brand-600 ring-1 ring-brand-100 flex items-center justify-center">
          <RefreshCw className="w-4 h-4" />
        </span>
        <h2 className="font-semibold text-slate-900">Scrape live data</h2>
        {running && (
          <span className="ml-auto flex items-center gap-1.5 text-xs font-medium text-amber-600">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> running…
          </span>
        )}
      </div>
      <p className="text-sm text-slate-500 mb-5">
        Runs the built-in pipeline: company websites + annual-report PDFs → DB with provenance.
        Anything ambiguous lands in the Review Queue.
      </p>

      {/* Sources */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="text-xs font-medium text-slate-500 w-20">Sources</span>
        {[
          { id: "website", label: "Websites", icon: Globe },
          { id: "report", label: "Annual reports", icon: FileText },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => toggleSource(id)}
            disabled={running}
            className={`chip flex items-center gap-1.5 ${sources.includes(id) ? "chip-active" : ""}`}
          >
            <Icon className="w-3.5 h-3.5" /> {label}
          </button>
        ))}
      </div>

      {/* Custom URL scan */}
      <div className="mb-3 p-3 rounded-lg bg-slate-50 ring-1 ring-slate-100">
        <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 mb-2">
          <Link2 className="w-3.5 h-3.5" /> Or scrape any live URL
        </div>
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="input flex items-center gap-2 flex-1 !py-1.5">
            <Globe className="w-4 h-4 text-slate-400 shrink-0" />
            <input
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !scanRunning && !scanStarting && runUrlScan()}
              placeholder="https://company-website.com"
              className="flex-1 outline-none bg-transparent text-sm"
              disabled={scanRunning || scanStarting}
            />
          </div>
          <button
            onClick={runUrlScan}
            disabled={scanRunning || scanStarting || !customUrl.trim() || running}
            className="btn-secondary flex items-center justify-center gap-1.5 !py-1.5 text-sm"
          >
            {scanRunning || scanStarting
              ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Scanning…</>
              : <><PlayCircle className="w-3.5 h-3.5" /> Scan URL</>}
          </button>
        </div>

        {scanError && (
          <div className="mt-2 text-xs text-rose-600 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" /> {scanError}
          </div>
        )}

        {scanRunning && scanStatus && scanStatus.log.length > 0 && (
          <div className="mt-2 max-h-32 overflow-y-auto rounded-md bg-slate-900 p-2 font-mono text-[10px] leading-4">
            {scanStatus.log.slice(-20).map((l, i) => (
              <div key={i} className={
                l.level === "error" ? "text-rose-400" :
                l.level === "success" ? "text-emerald-400" : "text-slate-300"
              }>
                <span className="text-slate-500">{l.time.slice(11, 19)} </span>{l.message}
              </div>
            ))}
          </div>
        )}

        {!scanRunning && scanReport && (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span className="chip text-emerald-600 ring-emerald-200 bg-emerald-50">
              {scanReport.pages_crawled} pages · {scanReport.products.length} products · {scanReport.brands.length} brands
            </span>
            <span className="text-slate-400">{scanReport.host}</span>
            <div className="flex items-center gap-1.5 ml-auto">
              <button
                onClick={() => setShowPreview((v) => !v)}
                className="btn-ghost !py-1 px-2.5 text-xs flex items-center gap-1"
              >
                <Eye className="w-3 h-3" /> {showPreview ? "Hide preview" : "Preview"}
              </button>
              <button
                onClick={saveUrlScan}
                disabled={savingScan}
                className="btn-primary !py-1 px-2.5 text-xs flex items-center gap-1"
              >
                {savingScan ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                Save to DB
              </button>
            </div>
          </div>
        )}

        {/* Preview panel */}
        {!scanRunning && scanReport && showPreview && (
          <div className="mt-2 rounded-lg bg-white ring-1 ring-slate-200 p-3 space-y-3 text-xs animate-fade-in">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="font-semibold text-slate-900 text-sm truncate">
                  {scanReport.company_name || scanReport.host}
                </div>
                <p className="text-slate-500 mt-0.5 line-clamp-2">
                  {scanReport.description || "No description found."}
                </p>
              </div>
              <span className={`badge shrink-0 ${
                scanReport.confidence === "high" ? "badge-green" :
                scanReport.confidence === "medium" ? "badge-yellow" : "badge-red"
              }`}>
                {scanReport.confidence}
              </span>
            </div>

            {scanReport.brands.length > 0 && (
              <div>
                <div className="font-medium text-slate-600 mb-1">Brands ({scanReport.brands.length})</div>
                <div className="flex flex-wrap gap-1">
                  {scanReport.brands.map((b) => <span key={b} className="chip">{b}</span>)}
                </div>
              </div>
            )}

            <div>
              <div className="font-medium text-slate-600 mb-1">Products ({scanReport.products.length})</div>
              {scanReport.products.length === 0 ? (
                <p className="text-slate-400">No products extracted.</p>
              ) : (
                <div className="max-h-48 overflow-y-auto rounded-md ring-1 ring-slate-100">
                  <table className="table-clean w-full">
                    <thead>
                      <tr>
                        <th>Product</th><th>Brand</th><th>Pack</th><th>MRP</th><th>Price</th>
                      </tr>
                    </thead>
                    <tbody>
                      {scanReport.products.map((p, i) => (
                        <tr key={i}>
                          <td className="font-medium text-slate-800">{p.name}</td>
                          <td className="text-slate-500">{p.brand || "—"}</td>
                          <td className="tabular-nums text-slate-500">
                            {p.pack_size ? `${p.pack_size}${p.unit ?? ""}` : "—"}
                          </td>
                          <td className="tabular-nums">{p.mrp != null ? `₹${p.mrp}` : "—"}</td>
                          <td className="tabular-nums">{p.selling_price != null ? `₹${p.selling_price}` : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {scanReport.distributors.length > 0 && (
              <div>
                <div className="font-medium text-slate-600 mb-1">Distributors ({scanReport.distributors.length})</div>
                <div className="flex flex-wrap gap-1">
                  {scanReport.distributors.map((d, i) => (
                    <span key={i} className="chip">{d.name}{d.state ? ` · ${d.state}` : ""}</span>
                  ))}
                </div>
              </div>
            )}

            {(scanReport.notes.length > 0 || scanReport.errors.length > 0) && (
              <div>
                <div className="font-medium text-slate-600 mb-1">Notes</div>
                <ul className="space-y-0.5 text-slate-500 list-disc list-inside">
                  {scanReport.notes.map((n, i) => <li key={i}>{n}</li>)}
                  {scanReport.errors.map((e, i) => <li key={`e${i}`} className="text-amber-600">{e}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}

        {scanSaved && (
          <div className="mt-2 text-xs text-emerald-600 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> Saved “{scanSaved}” to database.
          </div>
        )}
      </div>

      {/* Companies */}
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-medium text-slate-500 w-20">Companies</span>
          <label className="flex items-center gap-1.5 text-xs cursor-pointer">
            <input
              type="checkbox"
              checked={allSelected}
              disabled={running}
              onChange={(e) => { setAllSelected(e.target.checked); if (e.target.checked) setSelected(companies.map((c) => c.slug)); }}
              className="accent-brand-600"
            />
            All {companies.length || ""}
          </label>
          {!allSelected && (
            <span className="text-xs text-slate-400">{selected.length} selected</span>
          )}
        </div>
        {!allSelected && (
          <div className="max-h-40 overflow-y-auto grid grid-cols-2 gap-1.5 p-2 bg-slate-50 rounded-lg ring-1 ring-slate-100">
            {companies.map((c) => (
              <label key={c.slug} className="flex items-center gap-2 text-xs cursor-pointer truncate">
                <input
                  type="checkbox"
                  checked={selected.includes(c.slug)}
                  disabled={running}
                  onChange={() => toggleCompany(c.slug)}
                  className="accent-brand-600"
                />
                <span className="truncate" title={c.name}>{c.name}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Dry run */}
      <label className="flex items-center gap-2 text-sm mb-4 cursor-pointer">
        <input type="checkbox" checked={dryRun} disabled={running}
               onChange={(e) => setDryRun(e.target.checked)} className="accent-brand-600" />
        Dry run <span className="text-xs text-slate-400">(preview only — nothing saved)</span>
      </label>

      <div className="flex items-center gap-2">
        <button onClick={run} disabled={running || starting || (!allSelected && selected.length === 0) || sources.length === 0}
                className="btn-primary flex items-center gap-2">
          {running || starting ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
          {running ? "Scraping…" : dryRun ? "Run dry-run" : "Start scrape"}
        </button>
        {(running || status) && !dryRun && (
          <Link href="/admin/review" className="btn-ghost text-sm">Review Queue →</Link>
        )}
      </div>

      {error && (
        <div className="mt-3 text-sm text-rose-600 flex items-center gap-1.5">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}

      {/* Summary */}
      {status && Object.keys(summary).length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {Object.entries(summary).map(([k, v]) => (
            <span key={k} className={`chip text-xs ${k === "errors" && v > 0 ? "text-rose-600 ring-rose-200 bg-rose-50" : ""}`}>
              {k.replace(/_/g, " ")}: <b>{v}</b>
            </span>
          ))}
        </div>
      )}

      {/* Live log */}
      {status && status.log.length > 0 && (
        <div className="mt-4">
          <div className="text-xs font-medium text-slate-500 mb-1.5">Live log</div>
          <div className="max-h-56 overflow-y-auto rounded-lg bg-slate-900 p-3 font-mono text-[11px] leading-5">
            {status.log.slice(-100).map((l, i) => (
              <div key={i} className={
                l.level === "error" ? "text-rose-400" :
                l.level === "success" ? "text-emerald-400" : "text-slate-300"
              }>
                <span className="text-slate-500">{l.time.slice(11, 19)} </span>{l.message}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- import card

const TABLES: { id: string; label: string; required: string[]; hint: string }[] = [
  { id: "skus", label: "SKUs", required: ["product", "variant", "pack_size", "unit", "packaging_type", "mrp", "selling_price", "status"], hint: "Product must exist. Existing (product+variant+pack) rows are updated, new ones created." },
  { id: "products", label: "Products", required: ["name", "slug", "brand", "subcategory"], hint: "Brand and subcategory must exist (match by name)." },
  { id: "brands", label: "Brands", required: ["company", "brand_name", "brand_slug"], hint: "Company must exist." },
  { id: "sku_retailers", label: "SKU availability", required: ["sku_product", "sku_variant", "retailer", "region", "channel", "available"], hint: "Links every pack size of the product+variant to the retailer." },
  { id: "price_history", required: ["sku_product", "sku_variant", "mrp", "selling_price", "recorded_date"], label: "Price history", hint: "recorded_date format: YYYY-MM-DD. Creates a price snapshot per SKU." },
  { id: "distributors", label: "Distributors", required: ["name", "type", "territory", "city", "state", "district", "channel"], hint: "New distributors are created; existing names are skipped." },
];

type PreviewResult = {
  table: string; filename: string; total_rows: number;
  columns: string[]; required_columns: string[]; missing_columns: string[];
  row_errors: { row: number; column: string; issue: string }[];
  fk_errors: { row: number; column: string; value: string; issue: string }[];
  sample: Record<string, string>[];
};
type CommitResult = { table: string; dry_run: boolean; created: number; updated: number; skipped: number; errors: number; error_details: string[]; status: string };

function ImportCard() {
  const [table, setTable] = useState("skus");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [result, setResult] = useState<CommitResult | null>(null);
  const [busy, setBusy] = useState<"preview" | "dry" | "commit" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const tableCfg = TABLES.find((t) => t.id === table)!;
  const valid = preview && preview.table === table && preview.missing_columns.length === 0
    && preview.row_errors.length === 0 && preview.fk_errors.length === 0;

  const pick = (f: File | null) => {
    setFile(f);
    setPreview(null);
    setResult(null);
    setError(null);
  };

  const doPreview = async () => {
    if (!file) return;
    setBusy("preview"); setError(null); setResult(null);
    try {
      setPreview(await importPreview(table, file));
    } catch (e: any) {
      setError(String(e?.message || e)); setPreview(null);
    } finally { setBusy(null); }
  };

  const doCommit = async (dry: boolean) => {
    if (!file) return;
    setBusy(dry ? "dry" : "commit"); setError(null);
    try {
      setResult(await importCommit(table, file, dry));
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally { setBusy(null); }
  };

  const downloadTemplate = () => {
    const header = tableCfg.required.join(",");
    const example = tableCfg.required.map((c) => c === "status" ? "active" : c === "available" ? "true" : c === "recorded_date" ? "2026-09-23" : `<${c}>`).join(",");
    const blob = new Blob([header + "\n" + example + "\n"], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${table}-template.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2.5 mb-1">
        <span className="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 ring-1 ring-violet-100 flex items-center justify-center">
          <Upload className="w-4 h-4" />
        </span>
        <h2 className="font-semibold text-slate-900">Import CSV</h2>
      </div>
      <p className="text-sm text-slate-500 mb-5">
        Upload your own data — validate, dry-run, then commit. Existing rows are updated, never duplicated.
      </p>

      {/* Table select */}
      <div className="grid sm:grid-cols-2 gap-3 mb-3">
        <div>
          <label className="text-xs font-medium text-slate-500 block mb-1.5">Data type</label>
          <select value={table} onChange={(e) => { setTable(e.target.value); pick(null); }} className="input w-full">
            {TABLES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-slate-500 block mb-1.5">CSV file</label>
          <label className="input flex items-center gap-2 cursor-pointer !py-2">
            <FileSpreadsheet className="w-4 h-4 text-slate-400 shrink-0" />
            <span className={`text-sm truncate ${file ? "text-slate-700" : "text-slate-400"}`}>
              {file ? file.name : "Choose file…"}
            </span>
            <input type="file" accept=".csv,text/csv" className="hidden"
                   onChange={(e) => pick(e.target.files?.[0] ?? null)} />
          </label>
        </div>
      </div>

      <div className="text-xs text-slate-400 mb-1.5">
        Required columns: {tableCfg.required.map((c) => (
          <code key={c} className="mr-1 px-1 py-0.5 bg-slate-100 rounded text-[10px] text-slate-600">{c}</code>
        ))}
      </div>
      <div className="text-xs text-slate-500 mb-3 flex items-start gap-1.5">
        <Info className="w-3.5 h-3.5 shrink-0 mt-px" /> {tableCfg.hint}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button onClick={doPreview} disabled={!file || busy !== null} className="btn-secondary flex items-center gap-2">
          {busy === "preview" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
          Validate
        </button>
        <button onClick={() => doCommit(true)} disabled={!file || busy !== null} className="btn-ghost flex items-center gap-2">
          {busy === "dry" ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
          Dry run
        </button>
        <button onClick={() => doCommit(false)} disabled={!valid || busy !== null} className="btn-primary flex items-center gap-2">
          {busy === "commit" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          Import now
        </button>
        <button onClick={downloadTemplate} className="btn-ghost flex items-center gap-1.5 text-xs ml-auto">
          <Download className="w-3.5 h-3.5" /> Template
        </button>
      </div>

      {error && (
        <div className="mt-3 text-sm text-rose-600 flex items-center gap-1.5">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}

      {/* Validation report */}
      {preview && preview.table === table && (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap gap-1.5 text-xs">
            <span className="chip">{preview.total_rows} rows</span>
            {preview.missing_columns.length === 0
              ? <span className="chip text-emerald-600 ring-emerald-200 bg-emerald-50">columns OK</span>
              : <span className="chip text-rose-600 ring-rose-200 bg-rose-50">missing: {preview.missing_columns.join(", ")}</span>}
            {preview.row_errors.length > 0 && <span className="chip text-amber-600 ring-amber-200 bg-amber-50">{preview.row_errors.length} row errors</span>}
            {preview.fk_errors.length > 0 && <span className="chip text-amber-600 ring-amber-200 bg-amber-50">{preview.fk_errors.length} reference errors</span>}
          </div>

          {preview.missing_columns.length === 0 && preview.row_errors.length === 0 && preview.fk_errors.length === 0 && (
            <div className="text-sm text-emerald-600 flex items-center gap-1.5 font-medium">
              <CheckCircle2 className="w-4 h-4" /> Ready to import — press “Import now”.
            </div>
          )}

          {preview.row_errors.slice(0, 8).map((e, i) => (
            <div key={`r${i}`} className="text-xs text-amber-700">Row {e.row}: “{e.column}” is empty</div>
          ))}
          {preview.fk_errors.slice(0, 8).map((e, i) => (
            <div key={`f${i}`} className="text-xs text-amber-700">Row {e.row}: “{e.value}” in {e.column} — {e.issue}</div>
          ))}
        </div>
      )}

      {/* Commit result */}
      {result && (
        <div className={`mt-4 rounded-lg p-3 text-sm ${result.errors > 0 ? "bg-amber-50 text-amber-800 ring-1 ring-amber-200" : "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200"}`}>
          <div className="font-medium flex items-center gap-1.5">
            {result.status === "rolled_back" ? "Dry-run result (nothing saved):" : "Imported!"}
          </div>
          <div className="mt-1 text-xs">
            created <b>{result.created}</b> · updated <b>{result.updated}</b> · skipped <b>{result.skipped}</b> · errors <b>{result.errors}</b>
          </div>
          {result.error_details.length > 0 && (
            <div className="mt-1 text-[11px] opacity-80">{result.error_details.slice(0, 5).join(" · ")}</div>
          )}
          {result.status === "committed" && (
            <Link href="/admin/quality" className="text-xs underline mt-1 inline-block">Check Data Quality →</Link>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- page

export default function DataManagerPage() {
  return (
    <div className="max-w-5xl mx-auto">
      <PageHeader
        title="Data Manager"
        subtitle="Load real data without the terminal — scrape configured companies or import your own CSVs."
      />
      <div className="grid gap-5 lg:grid-cols-2 items-start">
        <ScrapeCard />
        <ImportCard />
      </div>
    </div>
  );
}
