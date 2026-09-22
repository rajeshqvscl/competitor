"use client";

import { useState } from "react";

const INDIA_STATES: Record<string, { x: number; y: number; region: string }> = {
  "Delhi NCR": { x: 38, y: 32, region: "North" },
  "Punjab": { x: 32, y: 28, region: "North" },
  "Haryana": { x: 36, y: 30, region: "North" },
  "Uttar Pradesh": { x: 45, y: 35, region: "North" },
  "Rajasthan": { x: 30, y: 38, region: "North" },
  "Maharashtra": { x: 32, y: 55, region: "West" },
  "Gujarat": { x: 22, y: 48, region: "West" },
  "Madhya Pradesh": { x: 40, y: 45, region: "West" },
  "Goa": { x: 28, y: 60, region: "West" },
  "Karnataka": { x: 32, y: 65, region: "South" },
  "Tamil Nadu": { x: 38, y: 72, region: "South" },
  "Andhra Pradesh": { x: 42, y: 62, region: "South" },
  "Telangana": { x: 40, y: 58, region: "South" },
  "Kerala": { x: 30, y: 72, region: "South" },
  "West Bengal": { x: 58, y: 42, region: "East" },
  "Bihar": { x: 55, y: 35, region: "East" },
  "Odisha": { x: 55, y: 52, region: "East" },
};

interface GeoMapProps {
  companyRegions: Record<string, string[]>; // company name -> state names
  selectedCompany?: string;
  onStateClick?: (state: string) => void;
}

export default function GeoMap({ companyRegions, selectedCompany, onStateClick }: GeoMapProps) {
  const [hoveredState, setHoveredState] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; state: string; companies: string[] } | null>(null);

  const stateCompanyMap: Record<string, string[]> = {};
  for (const [company, states] of Object.entries(companyRegions)) {
    for (const state of states) {
      if (!stateCompanyMap[state]) stateCompanyMap[state] = [];
      stateCompanyMap[state].push(company);
    }
  }

  const getStateColor = (state: string) => {
    const companies = stateCompanyMap[state] || [];
    if (companies.length === 0) return "#e5e7eb";
    if (companies.length === 1) return "#93c5fd";
    if (companies.length <= 3) return "#3b82f6";
    return "#1d4ed8";
  };

  const handleMouseMove = (e: React.MouseEvent, state: string) => {
    const companies = stateCompanyMap[state] || [];
    setHoveredState(state);
    setTooltip({ x: e.clientX, y: e.clientY, state, companies });
  };

  return (
    <div className="card p-4">
      <h3 className="font-semibold text-sm mb-3">Geographic Presence</h3>

      <div className="relative" style={{ height: 400 }}>
        <svg viewBox="0 0 80 90" className="w-full h-full">
          {Object.entries(INDIA_STATES).map(([state, pos]) => {
            const companies = stateCompanyMap[state] || [];
            const isHighlighted = selectedCompany && companies.includes(selectedCompany);
            return (
              <g key={state}>
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={Math.min(2 + companies.length * 0.8, 5)}
                  fill={getStateColor(state)}
                  stroke={isHighlighted ? "#f59e0b" : "#fff"}
                  strokeWidth={isHighlighted ? 1.5 : 0.5}
                  className="cursor-pointer transition-all hover:opacity-80"
                  onMouseMove={(e) => handleMouseMove(e, state)}
                  onMouseLeave={() => { setHoveredState(null); setTooltip(null); }}
                  onClick={() => onStateClick?.(state)}
                />
                {companies.length > 0 && (
                  <text
                    x={pos.x}
                    y={pos.y + 6}
                    textAnchor="middle"
                    fontSize="2.5"
                    fill="#374151"
                    className="pointer-events-none"
                  >
                    {state.length > 10 ? state.slice(0, 8) + "..." : state}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {tooltip && (
          <div
            className="fixed z-50 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg pointer-events-none"
            style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}
          >
            <div className="font-medium mb-1">{tooltip.state}</div>
            {tooltip.companies.length > 0 ? (
              tooltip.companies.map((c, i) => <div key={i} className="text-gray-300">• {c}</div>)
            ) : (
              <div className="text-gray-400">No companies</div>
            )}
          </div>
        )}
      </div>

      <div className="flex gap-4 mt-3 text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-gray-200" /> No presence
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-blue-300" /> 1 company
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-blue-500" /> 2-3 companies
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-blue-700" /> 4+ companies
        </div>
      </div>
    </div>
  );
}
