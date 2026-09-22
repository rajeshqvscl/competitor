import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dairy Competitor Intelligence",
  description: "Dairy competitor analysis and intelligence platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen">
          <nav className="w-64 bg-gray-900 text-white p-4 flex flex-col">
            <h1 className="text-lg font-bold mb-8 px-2">Dairy Intelligence</h1>
            <div className="space-y-1">
              <NavLink href="/" label="Dashboard" />
              <NavLink href="/companies" label="Companies" />
              <NavLink href="/analysis" label="Competitor Analysis" />
              <NavLink href="/compare" label="Compare" />
              <NavLink href="/distributors" label="Distributors" />
              <NavLink href="/categories" label="Categories" />
              <NavLink href="/search" label="Search" />
              <NavLink href="/ai-search" label="AI Search" />
              <NavLink href="/changes" label="Changes" />
              <NavLink href="/saved-analyses" label="Saved Analyses" />
              <div className="pt-4 mt-4 border-t border-gray-700">
                <div className="text-xs text-gray-500 px-3 mb-2">Admin</div>
                <NavLink href="/admin/alerts" label="Alerts" />
                <NavLink href="/admin/quality" label="Data Quality" />
                <NavLink href="/admin/review" label="Review Queue" />
              </div>
            </div>
            <div className="mt-auto text-xs text-gray-500 px-2">
              v0.4.0 Sprint 5
            </div>
          </nav>
          <main className="flex-1 p-6 overflow-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}

function NavLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      className="block px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
    >
      {label}
    </a>
  );
}
