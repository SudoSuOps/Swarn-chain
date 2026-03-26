import { Routes, Route, NavLink, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import BlockList from "./pages/BlockList";
import BlockDetail from "./pages/BlockDetail";
import NodeList from "./pages/NodeList";
import NodeDetail from "./pages/NodeDetail";
import { fetchMetrics, fetchHealth, type Metrics, type Health } from "./api";

function App() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    const load = () => {
      fetchMetrics().then(setMetrics).catch(() => {});
      fetchHealth().then(setHealth).catch(() => {});
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const navLink = (to: string, label: string, icon: string) => (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
            : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
        }`
      }
    >
      <span className="text-lg">{icon}</span>
      {label}
    </NavLink>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-950 border-r border-gray-800 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-800">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">
              S
            </div>
            <div>
              <h1 className="text-lg font-bold text-white leading-tight">
                SwarmChain
              </h1>
              <p className="text-xs text-gray-500">Block Explorer</p>
            </div>
          </Link>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1">
          <p className="text-xs text-gray-600 uppercase tracking-wider font-semibold mb-3 px-4">
            Explorer
          </p>
          {navLink("/", "Blocks", "\u26D3")}
          {navLink("/nodes", "Nodes", "\u2699")}
        </nav>

        {/* System status */}
        <div className="p-4 border-t border-gray-800">
          <div className="bg-gray-900 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Status</span>
              <span
                className={`flex items-center gap-1.5 text-xs font-medium ${
                  health?.status === "ok"
                    ? "text-green-400"
                    : "text-yellow-400"
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    health?.status === "ok"
                      ? "bg-green-400 pulse-dot"
                      : "bg-yellow-400"
                  }`}
                />
                {health?.status === "ok" ? "Online" : "Unknown"}
              </span>
            </div>
            {metrics && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Blocks</span>
                  <span className="text-xs text-gray-300 font-mono">
                    {metrics.total_blocks}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Open</span>
                  <span className="text-xs text-blue-400 font-mono">
                    {metrics.open_blocks}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Nodes</span>
                  <span className="text-xs text-gray-300 font-mono">
                    {metrics.total_nodes}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto bg-gray-900">
        <Routes>
          <Route path="/" element={<BlockList />} />
          <Route path="/blocks/:blockId" element={<BlockDetail />} />
          <Route path="/nodes" element={<NodeList />} />
          <Route path="/nodes/:nodeId" element={<NodeDetail />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
