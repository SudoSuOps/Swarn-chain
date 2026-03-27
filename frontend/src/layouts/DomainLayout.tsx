import { NavLink, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { fetchMetrics, fetchHealth, type Metrics, type Health } from "../api";

export interface NavItem {
  to: string;
  label: string;
  icon: string;
}

interface DomainLayoutProps {
  domainName: string;
  subtitle: string;
  accentColor: string;
  navSection: string;
  navItems: NavItem[];
  children: React.ReactNode;
  showSystemStatus?: boolean;
  pollingInterval?: number;
}

const ACCENT_MAP: Record<string, { bg: string; text: string; dot: string }> = {
  blue: { bg: "bg-blue-600", text: "text-blue-400", dot: "bg-blue-400" },
  purple: { bg: "bg-purple-600", text: "text-purple-400", dot: "bg-purple-400" },
  amber: { bg: "bg-amber-600", text: "text-amber-400", dot: "bg-amber-400" },
  emerald: { bg: "bg-emerald-600", text: "text-emerald-400", dot: "bg-emerald-400" },
  cyan: { bg: "bg-cyan-600", text: "text-cyan-400", dot: "bg-cyan-400" },
};

export default function DomainLayout({
  domainName,
  subtitle,
  accentColor,
  navSection,
  navItems,
  children,
  showSystemStatus = false,
  pollingInterval = 10000,
}: DomainLayoutProps) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const accent = ACCENT_MAP[accentColor] ?? ACCENT_MAP.blue;

  useEffect(() => {
    if (!showSystemStatus) return;
    const load = () => {
      fetchMetrics().then(setMetrics).catch(() => {});
      fetchHealth().then(setHealth).catch(() => {});
    };
    load();
    const interval = setInterval(load, pollingInterval);
    return () => clearInterval(interval);
  }, [showSystemStatus, pollingInterval]);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-950 border-r border-gray-800 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-800">
          <Link to="/" className="flex items-center gap-3">
            <div
              className={`w-9 h-9 ${accent.bg} rounded-lg flex items-center justify-center text-white font-bold text-lg`}
            >
              {domainName.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-lg font-bold text-white leading-tight">
                {domainName}
              </h1>
              <p className="text-xs text-gray-500">{subtitle}</p>
            </div>
          </Link>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1">
          <p className="text-xs text-gray-600 uppercase tracking-wider font-semibold mb-3 px-4">
            {navSection}
          </p>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? `bg-blue-600/20 ${accent.text} border border-blue-500/30`
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
                }`
              }
            >
              <span className="text-lg">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* System status */}
        <div className="p-4 border-t border-gray-800">
          <div className="bg-gray-900 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Status</span>
              <span
                className={`flex items-center gap-1.5 text-xs font-medium ${
                  health?.status === "healthy"
                    ? "text-green-400"
                    : "text-yellow-400"
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    health?.status === "healthy"
                      ? "bg-green-400 pulse-dot"
                      : "bg-yellow-400"
                  }`}
                />
                {health?.status === "healthy" ? "Online" : "Connecting..."}
              </span>
            </div>
            {showSystemStatus && metrics && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Blocks</span>
                  <span className="text-xs text-gray-300 font-mono">
                    {metrics.blocks.total}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Open</span>
                  <span className="text-xs text-blue-400 font-mono">
                    {metrics.blocks.open}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Nodes</span>
                  <span className="text-xs text-gray-300 font-mono">
                    {metrics.nodes.total}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto bg-gray-900">{children}</main>
    </div>
  );
}
