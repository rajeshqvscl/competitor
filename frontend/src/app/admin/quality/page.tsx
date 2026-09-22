"use client";

import { useEffect, useState } from "react";
import { getDataQuality } from "@/lib/api";

export default function DataQualityPage() {
  const [quality, setQuality] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDataQuality()
      .then(setQuality)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-gray-500">Loading...</div>;
  if (!quality) return <div className="text-red-500">Failed to load data quality</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Data Quality Dashboard</h1>
      <p className="text-gray-500 mb-6">Monitor completeness, coverage, and source quality</p>

      {/* Overview */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        {Object.entries(quality.overview).map(([key, val]) => (
          <div key={key} className="card p-4 text-center">
            <div className="text-2xl font-bold text-blue-600">{val as number}</div>
            <div className="text-sm text-gray-500 capitalize">{key.replace(/_/g, " ")}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Completeness */}
        <div className="card p-4">
          <h2 className="font-semibold mb-4">Data Completeness</h2>
          <div className="space-y-4">
            {Object.entries(quality.completeness).map(([key, val]: [string, any]) => (
              <div key={key}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="capitalize">{key.replace(/_/g, " ")}</span>
                  <span className="text-gray-500">{val.count}/{val.total} ({val.percent}%)</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      val.percent >= 80 ? "bg-green-500" :
                      val.percent >= 50 ? "bg-yellow-500" : "bg-red-500"
                    }`}
                    style={{ width: `${val.percent}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Coverage */}
        <div className="card p-4">
          <h2 className="font-semibold mb-4">Coverage</h2>
          <div className="space-y-4">
            {Object.entries(quality.coverage).map(([key, val]: [string, any]) => (
              <div key={key}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="capitalize">{key.replace(/_/g, " ")}</span>
                  <span className="text-gray-500">{val.count}/{val.total} ({val.percent}%)</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      val.percent >= 80 ? "bg-green-500" :
                      val.percent >= 50 ? "bg-yellow-500" : "bg-red-500"
                    }`}
                    style={{ width: `${val.percent}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sources */}
      <div className="card p-4">
        <h2 className="font-semibold mb-4">Source Quality</h2>
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold">{quality.sources.total}</div>
            <div className="text-sm text-gray-500">Total Sources</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{quality.sources.high}</div>
            <div className="text-sm text-gray-500">High Confidence</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">{quality.sources.medium}</div>
            <div className="text-sm text-gray-500">Medium Confidence</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{quality.sources.low}</div>
            <div className="text-sm text-gray-500">Low Confidence</div>
          </div>
        </div>
      </div>
    </div>
  );
}
