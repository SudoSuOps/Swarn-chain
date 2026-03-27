import { useEffect, useState, useCallback } from "react";
import { fetchTransformEconomics, type TransformStat } from "../../api";

export default function TransformEconomics() {
  const [transforms, setTransforms] = useState<TransformStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchTransformEconomics()
      .then((data) => {
        // Sort by solve_rate descending
        setTransforms(data.sort((a, b) => b.solve_rate - a.solve_rate));
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const getSolveRateColor = (rate: number): string => {
    if (rate >= 0.2) return "text-green-400";
    if (rate >= 0.05) return "text-yellow-400";
    return "text-red-400";
  };

  const getSolveRateBg = (rate: number): string => {
    if (rate >= 0.2) return "bg-green-500/20 border-green-500/20";
    if (rate >= 0.05) return "bg-yellow-500/20 border-yellow-500/20";
    return "bg-red-500/20 border-red-500/20";
  };

  // Max attempts for bar scaling
  const maxAttempts = transforms.length > 0
    ? Math.max(...transforms.map((t) => t.attempts), 1)
    : 1;

  return (
    <div className="p-6 max-w-full space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Transform Economics</h1>
        <p className="text-sm text-gray-400 mt-1">
          Per-transform solve rates and energy economics
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-gray-500">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading transform economics...
          </div>
        </div>
      )}

      {/* Summary cards */}
      {transforms.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-white font-mono">
              {transforms.length}
            </p>
            <p className="text-xs text-gray-400 mt-1">Transforms</p>
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-blue-400 font-mono">
              {transforms.reduce((s, t) => s + t.attempts, 0).toLocaleString()}
            </p>
            <p className="text-xs text-gray-400 mt-1">Total Attempts</p>
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-amber-400 font-mono">
              {transforms.reduce((s, t) => s + t.honey, 0).toLocaleString()}
            </p>
            <p className="text-xs text-gray-400 mt-1">Total Honey</p>
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-emerald-400 font-mono">
              {transforms.length > 0
                ? (
                    transforms.reduce((s, t) => s + t.solve_rate, 0) /
                    transforms.length *
                    100
                  ).toFixed(1)
                : "0"}
              %
            </p>
            <p className="text-xs text-gray-400 mt-1">Avg Solve Rate</p>
          </div>
        </div>
      )}

      {/* Volume chart */}
      {transforms.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-4">
            Attempt Volume by Transform
          </p>
          <div className="space-y-2">
            {transforms.map((t) => (
              <div key={t.transform} className="flex items-center gap-3">
                <span className="text-xs text-gray-300 w-40 truncate" title={t.transform}>
                  {t.transform}
                </span>
                <div className="flex-1 h-4 bg-gray-800 rounded overflow-hidden">
                  <div
                    className="h-full rounded transition-all duration-500"
                    style={{
                      width: `${(t.attempts / maxAttempts) * 100}%`,
                      backgroundColor:
                        t.solve_rate >= 0.2
                          ? "#10b981"
                          : t.solve_rate >= 0.05
                          ? "#f59e0b"
                          : "#ef4444",
                    }}
                  />
                </div>
                <span className="text-xs font-mono text-gray-400 w-16 text-right">
                  {t.attempts.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Table */}
      {transforms.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/50">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Transform
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Attempts
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Honey
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Solve Rate
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Avg Energy/Honey
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/30">
                {transforms.map((t) => (
                  <tr key={t.transform} className="table-row-hover">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">{t.transform}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-300">
                      {t.attempts.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-amber-400">
                      {t.honey.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-mono font-semibold ${getSolveRateBg(
                          t.solve_rate
                        )} ${getSolveRateColor(t.solve_rate)}`}
                      >
                        {(t.solve_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-300">
                      {t.avg_energy_per_honey.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Legend */}
      {transforms.length > 0 && (
        <div className="flex items-center gap-4 text-xs text-gray-500 px-1">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-green-500/40" />
            <span>&gt;20% solve (efficient)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-yellow-500/40" />
            <span>5-20% solve (moderate)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-red-500/40" />
            <span>&lt;5% solve (costly)</span>
          </div>
        </div>
      )}
    </div>
  );
}
