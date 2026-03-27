import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fetchAnchorTimeline, type AnchorRecord } from "../../api";

export default function LedgerTimeline() {
  const navigate = useNavigate();
  const [anchors, setAnchors] = useState<AnchorRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchAnchorTimeline()
      .then((data) => {
        setAnchors(data);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [load]);

  // Compute max cost for convergence chart scaling
  const maxCost = anchors.length > 0
    ? Math.max(...anchors.map((a) => a.cost_per_honey), 0.001)
    : 1;

  return (
    <div className="p-6 max-w-full">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Anchor Timeline</h1>
        <p className="text-sm text-gray-400 mt-1">
          Provenance chain: Merkle-anchored epoch windows
        </p>
      </div>

      {/* Convergence curve chart */}
      {anchors.length > 1 && (
        <div className="mb-6 bg-gray-800/40 border border-gray-700/50 rounded-xl p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-3">
            Cost Per Honey Convergence
          </p>
          <div className="relative h-24">
            {/* SVG chart */}
            <svg
              viewBox={`0 0 ${anchors.length * 40} 100`}
              className="w-full h-full"
              preserveAspectRatio="none"
            >
              {/* Grid lines */}
              <line x1="0" y1="25" x2={anchors.length * 40} y2="25" stroke="#374151" strokeWidth="0.5" />
              <line x1="0" y1="50" x2={anchors.length * 40} y2="50" stroke="#374151" strokeWidth="0.5" />
              <line x1="0" y1="75" x2={anchors.length * 40} y2="75" stroke="#374151" strokeWidth="0.5" />

              {/* Line path */}
              <polyline
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
                points={anchors
                  .slice()
                  .reverse()
                  .map((a, i) => {
                    const x = i * 40 + 20;
                    const y = 95 - (a.cost_per_honey / maxCost) * 85;
                    return `${x},${y}`;
                  })
                  .join(" ")}
              />

              {/* Data points */}
              {anchors
                .slice()
                .reverse()
                .map((a, i) => {
                  const x = i * 40 + 20;
                  const y = 95 - (a.cost_per_honey / maxCost) * 85;
                  return (
                    <circle
                      key={a.window}
                      cx={x}
                      cy={y}
                      r="3"
                      fill={a.anchored ? "#10b981" : "#6b7280"}
                      className="cursor-pointer"
                      onClick={() => navigate(`/anchor/${a.window}`)}
                    >
                      <title>
                        Window {a.window}: {a.cost_per_honey.toFixed(4)}
                      </title>
                    </circle>
                  );
                })}
            </svg>
          </div>
          <div className="flex justify-between mt-1 text-[10px] text-gray-600">
            <span>Oldest Window</span>
            <span>Latest Window</span>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && anchors.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-gray-500">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading anchor timeline...
          </div>
        </div>
      )}

      {!loading && anchors.length === 0 && (
        <div className="text-center py-12 text-gray-500">No anchors found</div>
      )}

      {/* Anchor list */}
      <div className="space-y-3">
        {anchors.map((anchor) => (
          <div
            key={anchor.window}
            onClick={() => navigate(`/anchor/${anchor.window}`)}
            className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 cursor-pointer hover:bg-gray-800/60 transition-colors"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <span className="text-lg font-bold text-white font-mono">
                  Window {anchor.window}
                </span>
                {anchor.anchored ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-green-500/20 text-green-400 border-green-500/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                    Anchored
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-gray-500/20 text-gray-400 border-gray-500/30">
                    Pending
                  </span>
                )}
              </div>
              <span className="text-xs text-gray-500">
                {new Date(anchor.sealed_at).toLocaleString()}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <p className="text-[10px] text-gray-500 uppercase">Merkle Root</p>
                <p className="font-mono text-xs text-blue-400 truncate" title={anchor.merkle_root}>
                  {anchor.merkle_root.slice(0, 16)}...
                </p>
              </div>
              <div>
                <p className="text-[10px] text-gray-500 uppercase">Cost/Honey</p>
                <p className="font-mono text-xs text-gray-300">
                  {anchor.cost_per_honey.toFixed(4)}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-gray-500 uppercase">Solve Rate</p>
                <p className="font-mono text-xs text-green-400">
                  {(anchor.solve_rate * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-[10px] text-gray-500 uppercase">Total Honey</p>
                <p className="font-mono text-xs text-amber-400">
                  {anchor.total_honey}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {anchors.length > 0 && (
        <div className="mt-3 text-xs text-gray-500 px-1">
          {anchors.length} anchor{anchors.length !== 1 ? "s" : ""} shown
          <span className="ml-2 text-gray-600">-- auto-refreshing every 10s</span>
        </div>
      )}
    </div>
  );
}
