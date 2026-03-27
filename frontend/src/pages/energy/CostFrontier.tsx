import { useEffect, useState, useCallback } from "react";
import { fetchCostFrontier, type CostFrontierPoint } from "../../api";

const HW_STYLES: Record<string, string> = {
  cpu: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  "gpu-mid": "bg-purple-500/20 text-purple-400 border-purple-500/30",
  "gpu-heavy": "bg-pink-500/20 text-pink-400 border-pink-500/30",
  edge: "bg-teal-500/20 text-teal-400 border-teal-500/30",
};

export default function CostFrontier() {
  const [frontier, setFrontier] = useState<CostFrontierPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchCostFrontier()
      .then((data) => {
        setFrontier(data);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // For scatter visualization
  const maxCost = frontier.length > 0
    ? Math.max(...frontier.map((p) => p.cost_per_honey), 0.001)
    : 1;
  const maxHoney = frontier.length > 0
    ? Math.max(...frontier.map((p) => p.honey_count), 1)
    : 1;

  return (
    <div className="p-6 max-w-full space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Cost Frontier</h1>
        <p className="text-sm text-gray-400 mt-1">
          Model comparison: cost efficiency vs. output volume
        </p>
      </div>

      {/* Explainer */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4">
        <p className="text-sm text-gray-300">
          The <span className="text-emerald-400 font-semibold">cost frontier</span> identifies
          models operating at the efficiency boundary -- producing the most honey per unit of
          compute energy. Models below the frontier are candidates for elimination. Models on the
          frontier define the minimum cost required at each quality level.
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
            Loading cost frontier...
          </div>
        </div>
      )}

      {/* Scatter visualization */}
      {frontier.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-4">
            Solve Rate vs Cost Per Honey
          </p>
          <div className="relative h-64 border-l border-b border-gray-700/50">
            {/* Y axis label */}
            <span className="absolute -left-1 top-0 text-[10px] text-gray-600 -translate-x-full">
              100%
            </span>
            <span className="absolute -left-1 bottom-0 text-[10px] text-gray-600 -translate-x-full">
              0%
            </span>
            <span className="absolute -left-1 top-1/2 text-[10px] text-gray-600 -translate-x-full -translate-y-1/2">
              50%
            </span>

            {/* X axis label */}
            <span className="absolute left-0 -bottom-5 text-[10px] text-gray-600">Low Cost</span>
            <span className="absolute right-0 -bottom-5 text-[10px] text-gray-600">High Cost</span>

            {/* Grid */}
            <div className="absolute inset-0">
              <div className="absolute w-full top-1/4 border-t border-gray-800/50" />
              <div className="absolute w-full top-1/2 border-t border-gray-800/50" />
              <div className="absolute w-full top-3/4 border-t border-gray-800/50" />
              <div className="absolute h-full left-1/4 border-l border-gray-800/50" />
              <div className="absolute h-full left-1/2 border-l border-gray-800/50" />
              <div className="absolute h-full left-3/4 border-l border-gray-800/50" />
            </div>

            {/* Data points */}
            {frontier.map((point) => {
              const x = (point.cost_per_honey / maxCost) * 90 + 5;
              const y = 95 - point.solve_rate * 90;
              const size = Math.max(8, Math.min(24, (point.honey_count / maxHoney) * 24));
              return (
                <div
                  key={point.model}
                  className="absolute rounded-full border-2 border-emerald-400/60 bg-emerald-500/30 hover:bg-emerald-500/50 cursor-pointer transition-colors"
                  style={{
                    left: `${x}%`,
                    top: `${y}%`,
                    width: size,
                    height: size,
                    transform: "translate(-50%, -50%)",
                  }}
                  title={`${point.model}: cost=${point.cost_per_honey.toFixed(4)}, solve=${(point.solve_rate * 100).toFixed(1)}%, honey=${point.honey_count}`}
                />
              );
            })}
          </div>
          <div className="mt-8 text-[10px] text-gray-600 text-center">
            Bubble size = honey count. Lower-left = best efficiency.
          </div>
        </div>
      )}

      {/* Table */}
      {frontier.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/50">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Model
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Hardware
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Cost/Honey
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Solve Rate
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Honey Count
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Total Attempts
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/30">
                {frontier
                  .sort((a, b) => a.cost_per_honey - b.cost_per_honey)
                  .map((point) => (
                    <tr key={point.model} className="table-row-hover">
                      <td className="px-4 py-3 text-white font-medium">
                        {point.model}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${
                            HW_STYLES[point.hardware_class] ??
                            "bg-gray-500/20 text-gray-400 border-gray-500/30"
                          }`}
                        >
                          {point.hardware_class}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-emerald-400">
                        {point.cost_per_honey.toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          className={`font-mono ${
                            point.solve_rate >= 0.2
                              ? "text-green-400"
                              : point.solve_rate >= 0.05
                              ? "text-yellow-400"
                              : "text-red-400"
                          }`}
                        >
                          {(point.solve_rate * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-amber-400">
                        {point.honey_count}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-400">
                        {point.total_attempts}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {frontier.length > 0 && (
        <div className="text-xs text-gray-500 px-1">
          {frontier.length} model{frontier.length !== 1 ? "s" : ""} on frontier
        </div>
      )}
    </div>
  );
}
