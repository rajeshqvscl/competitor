const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:9001";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// Companies
export const getCompanies = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<any[]>(`/api/companies${qs}`);
};

export const getCompany = (id: number) =>
  fetchAPI<any>(`/api/companies/${id}`);

export const getCompanyBrands = (id: number) =>
  fetchAPI<any[]>(`/api/companies/${id}/brands`);

export const getCompanySkus = (id: number) =>
  fetchAPI<any[]>(`/api/companies/${id}/skus`);

export const getCompanyCompetitors = (id: number, params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<any>(`/api/companies/${id}/competitors${qs}`);
};

// Categories
export const getCategories = () =>
  fetchAPI<any[]>("/api/categories");

export const getSubcategories = (catId: number) =>
  fetchAPI<any[]>(`/api/categories/${catId}/subcategories`);

// Retailers
export const getRetailers = () =>
  fetchAPI<any[]>("/api/retailers");

// Analysis
export const postCompetitorAnalysis = (data: any) =>
  fetchAPI<any>("/api/analysis/competitors", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const postPortfolioComparison = (data: any) =>
  fetchAPI<any>("/api/analysis/portfolio", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const postSkuComparison = (data: any) =>
  fetchAPI<any>("/api/analysis/sku-comparison", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const postRetailerOverlap = (data: any) =>
  fetchAPI<any>("/api/analysis/retailer-overlap", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const postWhiteSpace = (data: any) =>
  fetchAPI<any>("/api/analysis/white-space", {
    method: "POST",
    body: JSON.stringify(data),
  });

// Dashboard
export const getDashboardStats = () =>
  fetchAPI<any>("/api/dashboard/stats");

// Search
export const search = (q: string, entityType?: string) => {
  const params: Record<string, string> = { q };
  if (entityType) params.entity_type = entityType;
  return fetchAPI<any>("/api/search?" + new URLSearchParams(params).toString());
};

// Sources / Evidence
export const getEntitySources = (entityType: string, entityId: number) =>
  fetchAPI<any>(`/api/sources/${entityType}/${entityId}`);

export const getSources = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<any[]>(`/api/sources${qs}`);
};

// Export
export const exportCsv = async (endpoint: string, data: any, filename: string) => {
  const res = await fetch(`${API_BASE}/api/export/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Export error: ${res.status}`);
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
};

// Price History
export const getSkuPriceHistory = (skuId: number) =>
  fetchAPI<any>(`/api/prices/sku/${skuId}`);

export const getCompanyPriceTrends = (companyId: number) =>
  fetchAPI<any>(`/api/prices/company/${companyId}`);

// Change Detection
export const getChanges = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<any>(`/api/changes${qs}`);
};

export const createChangeEvent = (data: any) =>
  fetchAPI<any>("/api/changes", { method: "POST", body: JSON.stringify(data) });

// Saved Analyses
export const getSavedAnalyses = () =>
  fetchAPI<any[]>("/api/analyses");

export const getSavedAnalysis = (id: number) =>
  fetchAPI<any>(`/api/analyses/${id}`);

export const saveAnalysis = (data: any) =>
  fetchAPI<any>("/api/analyses", { method: "POST", body: JSON.stringify(data) });

export const deleteAnalysis = (id: number) =>
  fetchAPI<any>(`/api/analyses/${id}`, { method: "DELETE" });

// AI Search
export const aiSearch = (query: string) =>
  fetchAPI<any>("/api/ai-search", { method: "POST", body: JSON.stringify({ query }) });

// Alerts
export const getAlerts = () =>
  fetchAPI<any[]>("/api/alerts");

export const getAlert = (id: number) =>
  fetchAPI<any>(`/api/alerts/${id}`);

export const createAlert = (data: any) =>
  fetchAPI<any>("/api/alerts", { method: "POST", body: JSON.stringify(data) });

export const updateAlert = (id: number, data: any) =>
  fetchAPI<any>(`/api/alerts/${id}`, { method: "PUT", body: JSON.stringify(data) });

export const deleteAlert = (id: number) =>
  fetchAPI<any>(`/api/alerts/${id}`, { method: "DELETE" });

export const markAlertRead = (id: number) =>
  fetchAPI<any>(`/api/alerts/${id}/mark-read`, { method: "POST" });

// Data Quality
export const getDataQuality = () =>
  fetchAPI<any>("/api/data-quality");

// Review Queue
export const getReviewQueue = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<any[]>(`/api/review-queue${qs}`);
};

export const approveReviewItem = (id: number, data?: any) =>
  fetchAPI<any>(`/api/review-queue/${id}/approve`, { method: "PUT", body: JSON.stringify(data || {}) });

export const rejectReviewItem = (id: number, data?: any) =>
  fetchAPI<any>(`/api/review-queue/${id}/reject`, { method: "PUT", body: JSON.stringify(data || {}) });

// Distributors
export const getDistributors = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<any[]>(`/api/distributors${qs}`);
};

export const getDistributor = (id: number) =>
  fetchAPI<any>(`/api/distributors/${id}`);

export const getCompanyDistributors = (companyId: number) =>
  fetchAPI<any[]>(`/api/distributors/company/${companyId}`);

export const createDistributor = (data: any) =>
  fetchAPI<any>("/api/distributors", { method: "POST", body: JSON.stringify(data) });
