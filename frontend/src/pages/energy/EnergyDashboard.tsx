import { useEffect, useState, useCallback } from "react";
import {
  fetchEnergyLive,
  fetchSiliconLadder,
  fetchEnergyTrend,
  type LiveEnergy,
  type SiliconLadderEntry,
  type TrendPoint,
} from "../../api";

const HW_STYLES: Record<string, string> = {
  cpu: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  "gpu-mid": "bg-purple-500/20 text-purple-400 border-purple-500/30",
  "gpu-heavy": "bg-pink-500/20 text-pink-400 border-pink-500/30",
  edge: "bg-teal-500/20 text-teal-400 border-teal-500/30",
};

export default function EnergyDashboard() {
  const [live, setLive] = useState<LiveEnergy | null>(null);
  const [ladder, setLadder] = useState<SiliconLadderEntry[]>([]);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([
      fetchEnergyLive().catch(() => null),
      fetchSiliconLadder().catch(() => []),
      fetchEnergyTrend().catch(() => []),
    ])
      .then(([liveData, ladderData, trendData]) => {
        if (liveData) setLive(liveData);
        setLadder(ladderData as SiliconLadderEntry[]);
        setTrend(trendData as TrendPoint[]);
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

  // Max efficiency for bar scaling
  const maxEfficiency = ladder.length > 0
    ? Math.max(...ladder.map((e) => e.efficiency_score), 0.01)
    : 1;

  // Max cost for trend chart
  const maxCost = trend.length > 0
    ? Math.max(...trend.map((t) => t.cost_per_honey), 0.001)
    : 1;

  return (
    <div className="p-6 max-w-full space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Energy Dashboard</h1>
        <p className="text-sm text-gray-400 mt-1">
          Live compute economics and node efficiency
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && !live && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-gray-500">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading energy data...
          </div>
        </div>
      )}

      {/* Live stats */}
      {live && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-gray-800/40 border border-emerald-500/30 rounded-xl p-5 text-center">
            <p className="text-3xl font-bold text-emerald-400 font-mono">
              {live.attempts_per_min.toFixed(1)}
            </p>
            <p className="text-xs text-gray-400 mt-2">Attempts / Min</p>
          </div>
          <div className="bg-gray-800/40 border border-cyan-500/30 rounded-xl p-5 text-center">
            <p className="text-3xl font-bold text-cyan-400 font-mono">
              {live.energy_per_min.toFixed(2)}
            </p>
            <p className="text-xs text-gray-400 mt-2">Energy / Min</p>
          </div>
          <div className="bg-gray-800/40 border border-blue-500/30 rounded-xl p-5 text-center">
            <p className="text-3xl font-bold text-blue-400 font-mono">
              {live.active_nodes}
            </p>
            <p className="text-xs text-gray-400 mt-2">Active Nodes</p>
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-5 text-center">
            <p className="text-lg font-bold text-gray-300 font-mono">
              {live.current_epoch}
            </p>
            <p className="text-xs text-gray-400 mt-2">Current Epoch</p>
            <p className="text-[10px] text-gray-600 mt-1">
              Uptime: {Math.floor(live.uptime_sec / 3600)}h{" "}
              {Math.floor((live.uptime_sec % 3600) / 60)}m
            </p>
          </div>
        </div>
      )}

      {/* Cost trend chart */}
      {trend.length > 1 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-4">
            Cost Per Honey Over Time
          </p>
          <div className="flex items-end gap-1 h-24">
            {trend.map((point, i) => {
              const height = (point.cost_per_honey / maxCost) * 100;
              return (
                <div
                  key={i}
                  className="flex-1 min-w-[3px] max-w-[20px] rounded-t transition-all"
                  style={{
                    height: `${Math.max(height, 3)}%`,
                    backgroundColor:
                      point.cost_per_honey <= maxCost * 0.5
                        ? "#10b981"
                        : point.cost_per_honey <= maxCost * 0.75
                        ? "#f59e0b"
                        : "#ef4444",
                  }}
                  title={`${new Date(point.timestamp).toLocaleDateString()}: ${point.cost_per_honey.toFixed(4)}`}
                />
              );
            })}
          </div>
          <div className="flex justify-between mt-1 text-[10px] text-gray-600">
            <span>{trend.length > 0 ? new Date(trend[0].timestamp).toLocaleDateString() : ""}</span>
            <span>
              {trend.length > 0
                ? new Date(trend[trend.length - 1].timestamp).toLocaleDateString()
                : ""}
            </span>
          </div>
        </div>
      )}

      {/* Silicon ladder table */}
      {ladder.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Silicon Ladder
          </h2>
          <div className="space-y-2 mb-6">
            {ladder.slice(0, 8).map((entry, i) => (
              <div key={entry.model_name} className="flex items-center gap-3">
                <span className="text-xs text-gray-600 font-mono w-6 text-right">
                  #{i + 1}
                </span>
                <span className="text-xs text-gray-300 w-36 truncate" title={entry.model_name}>
                  {entry.model_name}
                </span>
                <span
                  className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                    HW_STYLES[entry.hardware_class] ??
                    "bg-gray-500/20 text-gray-400 border-gray-500/30"
                  }`}
                >
                  {entry.hardware_class}
                </span>
                <div className="flex-1 h-5 bg-gray-800 rounded overflow-hidden">
                  <div
                    className="h-full bg-emerald-600/60 rounded transition-all duration-500"
                    style={{
                      width: `${(entry.efficiency_score / maxEfficiency) * 100}%`,
                    }}
                  />
                </div>
                <span className="text-xs font-mono text-gray-300 w-14 text-right">
                  {entry.efficiency_score.toFixed(2)}
                </span>
              </div>
            ))}
          </div>

          {/* Full table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/50">
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Model
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Hardware
                  </th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Honey
                  </th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Honey Rate
                  </th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Energy/Honey
                  </th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Efficiency
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/30">
                {ladder.map((entry) => (
                  <tr key={entry.model_name} className="table-row-hover">
                    <td className="px-3 py-2 text-sm text-white">{entry.model_name}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${
                          HW_STYLES[entry.hardware_class] ??
                          "bg-gray-500/20 text-gray-400 border-gray-500/30"
                        }`}
                      >
                        {entry.hardware_class}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-amber-400">
                      {entry.honey_count}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-green-400">
                      {(entry.honey_rate * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-gray-300">
                      {entry.energy_per_honey.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-white font-semibold">
                      {entry.efficiency_score.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="text-xs text-gray-500 px-1">
        Auto-refreshing every 10s
      </div>
    </div>
  );
}
