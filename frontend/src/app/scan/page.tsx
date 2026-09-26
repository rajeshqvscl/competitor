"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ScanSearch, Globe, Loader2, AlertTriangle, PlayCircle, CheckCircle2,
  Mail, Phone, MapPin, Package, Tag, Truck, FileText, Save, Info,
  Building2, ExternalLink,
} from "lucide-react";
import { PageHeader, EmptyState } from "@/components/ui";
import { startScan, getScanStatus, saveScan } from "@/lib/api";

type ScanReport = {
  scanned_url: string;
  host: string;
  pages_crawled: number;
  confidence: "high" | "medium" | "low";
  company_name: string | null;
  description: string | null;
  logo_url: string | null;
  emails: string[];
  phones: string[];
  socials: string[];
  states_mentioned: string[];
  brands: string[];
  products: {
    name: string; brand: string | null; description: string | null;
    subcategory: string | null; pack_size: number | null; unit: string | null;
    mrp: number | null; selling_price: number | null; source_url: string | null;
  }[];
  distributors: { name: string; type: string | null; state: string | null }[];
  pdf_links: string[];
  pages: { url: string; title: string | null; kind: string }[];
  errors: string[];
  notes: string[];
};

type JobStatus = {
  running: boolean;
  url: string | null;
  error: string | null;
  log: { time: string; level: string; message: string }[];
  report: ScanReport | null;
};

export default function ScanPage() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedResult, setSavedResult] = useState<{ company: string; brands: number; products: number; skus: number } | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const poll = useCallback(async () => {
    try {
      const s: JobStatus = await getScanStatus();
      setStatus(s);
      if (!s.running && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch { /* retry next tick */ }
  }, []);

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(poll, 1500);
    poll();
  }, [poll]);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const go = async () => {
    if (!url.trim()) return;
    setError(null);
    setSavedResult(null);
    setStarting(true);
    try {
      await startScan(url.trim());
      startPolling();
    } catch (e: any) {
      const msg = String(e?.message || e);
      setError(msg.includes("409") ? "A scan is already running — see log below." : msg);
    } finally {
      setStarting(false);
    }
  };

  const save = async () => {
    if (!status?.report) return;
    setSaving(true);
    setError(null);
    try {
      const res = await saveScan({
        url: status.report.scanned_url,
        company_name: status.report.company_name || undefined,
      });
      setSavedResult(res);
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setSaving(false);
    }
  };

  const report = status?.report ?? null;
  const running = status?.running ?? false;

  return (
    <div className="max-w-5xl mx-auto">
      <PageHeader
        title="Website Scanner"
        subtitle="Paste any company website — get its profile, products, prices, contacts and distributors in one scan."
      />

      {/* URL input */}
      <div className="card p-6 mb-5">
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="input flex items-center gap-2 flex-1">
            <Globe className="w-4 h-4 text-slate-400 shrink-0" />
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !running && go()}
              placeholder="https://company-website.com"
              className="flex-1 outline-none bg-transparent text-sm"
              disabled={running}
            />
          </div>
          <button onClick={go} disabled={running || starting || !url.trim()} className="btn-primary">
            {running || starting
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Scanning…</>
              : <><PlayCircle className="w-4 h-4" /> Scan website</>}
          </button>
        </div>
        {error && (
          <div className="mt-3 text-sm text-rose-600 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4" /> {error}
          </div>
        )}
        {running && (
          <div className="mt-4">
            <div className="text-xs font-medium text-slate-500 mb-1.5">Live log</div>
            <div className="max-h-40 overflow-y-auto rounded-lg bg-slate-900 p-3 font-mono text-[11px] leading-5">
              {(status?.log ?? []).slice(-30).map((l, i) => (
                <div key={i} className={l.level === "error" ? "text-rose-400" : l.level === "success" ? "text-emerald-400" : "text-slate-300"}>
                  <span className="text-slate-500">{l.time.slice(11, 19)} </span>{l.message}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Report */}
      {report && (
        <>
          {/* Summary header */}
          <div className="card p-6 mb-5">
            <div className="flex items-start gap-4">
              {report.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={report.logo_url} alt="" className="w-14 h-14 rounded-xl object-contain ring-1 ring-slate-200 bg-white p-1.5"
                     onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
              ) : (
                <div className="w-14 h-14 rounded-xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center">
                  <Building2 className="w-7 h-7 text-brand-500" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-lg font-bold text-slate-900">{report.company_name || report.host}</h2>
                  <span className={`badge ${report.confidence === "high" ? "badge-green" : report.confidence === "medium" ? "badge-yellow" : "badge-red"}`}>
                    {report.confidence} confidence
                  </span>
                  <a href={report.scanned_url} target="_blank" rel="noreferrer"
                     className="text-xs text-slate-400 hover:text-brand-600 inline-flex items-center gap-1">
                    {report.host} <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <p className="text-sm text-slate-600 mt-1.5 line-clamp-3">{report.description || "No description found."}</p>
                <div className="flex flex-wrap gap-1.5 mt-3 text-xs">
                  <span className="chip">{report.pages_crawled} pages crawled</span>
                  <span className="chip">{report.products.length} products</span>
                  <span className="chip">{report.brands.length} brands</span>
                  {report.distributors.length > 0 && <span className="chip">{report.distributors.length} distributors</span>}
                  {report.pdf_links.length > 0 && <span className="chip">{report.pdf_links.length} PDFs</span>}
                </div>
              </div>
              <div className="shrink-0">
                <button onClick={save} disabled={saving} className="btn-primary flex items-center gap-2">
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  Save to database
                </button>
                {savedResult && (
                  <div className="text-xs text-emerald-600 mt-2 text-right">
                    ✅ Saved: {savedResult.company} (+{savedResult.brands} brands, +{savedResult.products} products)
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Contact + presence */}
          <div className="grid md:grid-cols-2 gap-5 mb-5">
            <div className="card p-5">
              <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2 text-sm">
                <Mail className="w-4 h-4 text-brand-500" /> Contact & Social
              </h3>
              {report.emails.length === 0 && report.phones.length === 0 && report.socials.length === 0 ? (
                <p className="text-sm text-slate-400">Nothing found on crawled pages.</p>
              ) : (
                <div className="space-y-2 text-sm">
                  {report.emails.map((e) => (
                    <div key={e} className="flex items-center gap-2 text-slate-600">
                      <Mail className="w-3.5 h-3.5 text-slate-300" />
                      <a href={`mailto:${e}`} className="hover:text-brand-600 truncate">{e}</a>
                    </div>
                  ))}
                  {report.phones.map((p) => (
                    <div key={p} className="flex items-center gap-2 text-slate-600">
                      <Phone className="w-3.5 h-3.5 text-slate-300" /> {p}
                    </div>
                  ))}
                  {report.socials.map((s) => (
                    <a key={s} href={s} target="_blank" rel="noreferrer"
                       className="flex items-center gap-2 text-brand-600 hover:underline truncate">
                      <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">{s.replace(/^https?:\/\/(www\.)?/, "")}</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
            <div className="card p-5">
              <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2 text-sm">
                <MapPin className="w-4 h-4 text-brand-500" /> Regions & Documents
              </h3>
              <div className="flex flex-wrap gap-1.5 mb-3">
                {report.states_mentioned.length === 0
                  ? <span className="text-sm text-slate-400">No region signals found.</span>
                  : report.states_mentioned.map((s) => <span key={s} className="chip">{s}</span>)}
              </div>
              {report.pdf_links.length > 0 && (
                <div className="space-y-1.5">
                  {report.pdf_links.slice(0, 5).map((p) => (
                    <a key={p} href={p} target="_blank" rel="noreferrer"
                       className="flex items-center gap-2 text-xs text-brand-600 hover:underline truncate">
                      <FileText className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">{p.split("/").pop()}</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Products */}
          <div className="card p-5 mb-5">
            <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2 text-sm">
              <Package className="w-4 h-4 text-brand-500" /> Products ({report.products.length})
            </h3>
            {report.products.length === 0 ? (
              <p className="text-sm text-slate-400">No products extracted — site may be JS-rendered. Notes below.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="table-clean w-full text-sm">
                  <thead>
                    <tr>
                      <th>Product</th><th>Brand</th><th>Pack</th><th>MRP</th><th>Price</th><th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.products.slice(0, 25).map((p, i) => (
                      <tr key={i}>
                        <td className="font-medium text-slate-800">{p.name}</td>
                        <td className="text-slate-500">{p.brand || "—"}</td>
                        <td className="tabular-nums text-slate-500">{p.pack_size ? `${p.pack_size}${p.unit ?? ""}` : "—"}</td>
                        <td className="tabular-nums">{p.mrp != null ? `₹${p.mrp}` : "—"}</td>
                        <td className="tabular-nums">{p.selling_price != null ? `₹${p.selling_price}` : "—"}</td>
                        <td>{p.source_url && (
                          <a href={p.source_url} target="_blank" rel="noreferrer" className="text-slate-300 hover:text-brand-500">
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Brands */}
          {report.brands.length > 0 && (
            <div className="card p-5 mb-5">
              <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2 text-sm">
                <Tag className="w-4 h-4 text-brand-500" /> Brands ({report.brands.length})
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {report.brands.map((b) => <span key={b} className="chip">{b}</span>)}
              </div>
            </div>
          )}

          {/* Distributors */}
          {report.distributors.length > 0 && (
            <div className="card p-5 mb-5">
              <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2 text-sm">
                <Truck className="w-4 h-4 text-brand-500" /> Distributors ({report.distributors.length})
              </h3>
              <div className="grid sm:grid-cols-2 gap-2">
                {report.distributors.map((d, i) => (
                  <div key={i} className="flex items-center justify-between text-sm px-3 py-2 bg-slate-50 rounded-lg">
                    <span className="font-medium text-slate-700 truncate">{d.name}</span>
                    <span className="text-xs text-slate-400 shrink-0 ml-2">{[d.type, d.state].filter(Boolean).join(" · ") || "—"}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notes / errors */}
          {(report.notes.length > 0 || report.errors.length > 0) && (
            <div className="card p-5">
              <h3 className="font-semibold text-slate-900 mb-2 flex items-center gap-2 text-sm">
                <Info className="w-4 h-4 text-amber-500" /> Scan notes
              </h3>
              <ul className="text-sm text-slate-500 space-y-1 list-disc list-inside">
                {report.notes.map((n, i) => <li key={i}>{n}</li>)}
                {report.errors.map((e, i) => <li key={`e${i}`} className="text-amber-600">{e}</li>)}
              </ul>
            </div>
          )}
        </>
      )}

      {!report && !running && (
        <EmptyState
          icon={<ScanSearch className="w-6 h-6" />}
          title="No scan yet"
          subtitle="Enter a website URL above and press Scan. Try dodladairy.com or any dairy company site."
        />
      )}
    </div>
  );
}
