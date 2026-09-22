"use client";

import { useEffect, useState } from "react";
import { getCategories, getSubcategories } from "@/lib/api";

export default function CategoriesPage() {
  const [categories, setCategories] = useState<any[]>([]);
  const [selectedCat, setSelectedCat] = useState<number | null>(null);
  const [subcategories, setSubcategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCategories()
      .then(setCategories)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedCat) {
      getSubcategories(selectedCat).then(setSubcategories).catch(console.error);
    }
  }, [selectedCat]);

  const categoryIcons: Record<string, string> = {
    "Milk": "&#129472;",
    "Fermented Dairy": "&#129472;",
    "Dairy Fats": "&#129361;",
    "Fresh Dairy": "&#129472;",
    "Cheese": "&#129472;",
    "Frozen Dairy": "&#127846;",
    "Dairy Sweets": "&#127856;",
    "Dairy Ingredients": "&#129371;",
  };

  if (loading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Dairy Product Taxonomy</h1>
      <p className="text-gray-500 mb-6">Browse the dairy product hierarchy from categories to subcategories</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCat(selectedCat === cat.id ? null : cat.id)}
            className={`card p-4 text-left transition-all ${
              selectedCat === cat.id
                ? "ring-2 ring-blue-600 shadow-md bg-blue-50"
                : "hover:shadow-md"
            }`}
          >
            <div
              className="text-2xl mb-2"
              dangerouslySetInnerHTML={{ __html: categoryIcons[cat.name] || "&#127970;" }}
            />
            <div className="font-semibold">{cat.name}</div>
            {cat.description && (
              <div className="text-sm text-gray-500 mt-1">{cat.description}</div>
            )}
          </button>
        ))}
      </div>

      {selectedCat && subcategories.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">
              {categories.find((c) => c.id === selectedCat)?.name} — Subcategories
            </h2>
            <span className="text-sm text-gray-500">{subcategories.length} subcategories</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {subcategories.map((sub) => (
              <div key={sub.id} className="card p-4 hover:shadow-md transition-shadow">
                <div className="font-medium">{sub.name}</div>
                {sub.description && (
                  <div className="text-sm text-gray-500 mt-1">{sub.description}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedCat && subcategories.length === 0 && (
        <div className="text-gray-400 text-center py-8">
          Loading subcategories...
        </div>
      )}
    </div>
  );
}
