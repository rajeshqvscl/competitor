"use client";

import type { ReactNode } from "react";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-7">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}

const STAT_COLORS = {
  blue: "bg-sky-50 text-sky-600 ring-sky-100",
  green: "bg-emerald-50 text-emerald-600 ring-emerald-100",
  purple: "bg-violet-50 text-violet-600 ring-violet-100",
  yellow: "bg-amber-50 text-amber-600 ring-amber-100",
  pink: "bg-rose-50 text-rose-600 ring-rose-100",
  indigo: "bg-indigo-50 text-indigo-600 ring-indigo-100",
} as const;

export function StatCard({
  label,
  value,
  color = "blue",
  icon,
  loading = false,
}: {
  label: string;
  value: number | string | null | undefined;
  color?: keyof typeof STAT_COLORS;
  icon?: ReactNode;
  loading?: boolean;
}) {
  const c = STAT_COLORS[color];
  return (
    <div className="card card-hover p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] font-medium text-slate-500">{label}</span>
        {icon && (
          <span className={`w-8 h-8 rounded-lg ring-1 flex items-center justify-center ${c}`}>
            {icon}
          </span>
        )}
      </div>
      {loading ? (
        <div className="skeleton h-8 w-16" />
      ) : (
        <div className="text-3xl font-bold tracking-tight text-slate-900">{value ?? "—"}</div>
      )}
    </div>
  );
}

export function SkeletonBlock({ className = "h-40" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function EmptyState({
  icon,
  title,
  subtitle,
}: {
  icon?: ReactNode;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="card p-10 text-center">
      {icon && (
        <div className="mx-auto mb-3 w-12 h-12 rounded-xl bg-slate-50 ring-1 ring-slate-200 flex items-center justify-center text-slate-400">
          {icon}
        </div>
      )}
      <div className="font-medium text-slate-700">{title}</div>
      {subtitle && <div className="text-sm text-slate-400 mt-1">{subtitle}</div>}
    </div>
  );
}

export function ProgressRow({
  label,
  count,
  pct,
  barClass = "bg-brand-500",
}: {
  label: string;
  count?: number | string;
  pct: number;
  barClass?: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1.5">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-400">
          {count !== undefined && count !== "" ? `${count} · ` : ""}
          {Math.round(pct)}%
        </span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
        <div
          className={`h-2 rounded-full ${barClass} transition-all duration-500`}
          style={{ width: `${Math.max(2, Math.min(100, pct))}%` }}
        />
      </div>
    </div>
  );
}
