"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Building2, Swords, Columns3, Truck, FolderTree,
  Search, Sparkles, ArrowLeftRight, Bookmark, Bell, ShieldCheck,
  ClipboardCheck, Milk, DatabaseZap, ScanSearch,
} from "lucide-react";

const NAV = [
  {
    section: "Intelligence",
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard },
      { href: "/companies", label: "Companies", icon: Building2 },
      { href: "/analysis", label: "Competitor Analysis", icon: Swords },
      { href: "/compare", label: "Compare", icon: Columns3 },
      { href: "/distributors", label: "Distributors", icon: Truck },
      { href: "/categories", label: "Categories", icon: FolderTree },
    ],
  },
  {
    section: "Research",
    items: [
      { href: "/scan", label: "Website Scanner", icon: ScanSearch },
      { href: "/search", label: "Search", icon: Search },
      { href: "/ai-search", label: "AI Search", icon: Sparkles },
      { href: "/changes", label: "Change Feed", icon: ArrowLeftRight },
      { href: "/saved-analyses", label: "Saved Analyses", icon: Bookmark },
    ],
  },
  {
    section: "Admin",
    items: [
      { href: "/admin/data", label: "Data Manager", icon: DatabaseZap },
      { href: "/admin/alerts", label: "Alerts", icon: Bell },
      { href: "/admin/quality", label: "Data Quality", icon: ShieldCheck },
      { href: "/admin/review", label: "Review Queue", icon: ClipboardCheck },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside className="w-64 shrink-0 bg-brand-950 text-white flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-3 px-5 py-5 border-b border-white/10">
        <div className="w-9 h-9 rounded-xl bg-brand-500/20 ring-1 ring-brand-400/30 flex items-center justify-center">
          <Milk className="w-5 h-5 text-brand-300" />
        </div>
        <div className="leading-tight">
          <div className="font-semibold tracking-tight">DairyLens</div>
          <div className="text-[11px] text-brand-300/70">Competitor Intelligence</div>
        </div>
      </Link>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {NAV.map((group) => (
          <div key={group.section}>
            <div className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-widest text-brand-300/50">
              {group.section}
            </div>
            <div className="space-y-0.5">
              {group.items.map(({ href, label, icon: Icon }) => {
                const active = isActive(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                      active
                        ? "bg-white/10 text-white font-medium shadow-inner"
                        : "text-brand-100/70 hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${active ? "text-brand-300" : "text-brand-300/60"}`} />
                    <span className="truncate">{label}</span>
                    {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-400" />}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-white/10 text-[11px] text-brand-300/60">
        <div className="flex items-center justify-between">
          <span>v0.4.0</span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            API online
          </span>
        </div>
      </div>
    </aside>
  );
}
