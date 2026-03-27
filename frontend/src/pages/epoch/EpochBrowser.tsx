import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fetchEpochs, type Epoch } from "../../api";
import StatusBadge from "../../components/StatusBadge";

export default function EpochBrowser() {
  const navigate = useNavigate();
  const [epochs, setEpochs] = useState<Epoch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchEpochs()
      .then((data) => {
        setEpochs(data);
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

  // Compute max convergence for bar scaling
  const maxConvergence = epochs.length > 0
    ? Math.max(...epochs.map((e) => Math.abs(e.convergence_delta)), 0.01)
    : 1;

  return (
    <div className="p-6 max-w-full">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Epochs</h1>
        <p className="text-sm text-gray-400 mt-1">
          Browse sealed and active SwarmChain epochs
        </p>
      </div>

      {/* Convergence sparkline */}
      {epochs.length > 1 && (
        <div className="mb-6 bg-gray-800/40 border border-gray-700/50 rounded-xl p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-3">
            Convergence Trend (cost_per_honey)
          </p>
          <div className="flex items-end gap-1 h-16">
            {epochs.slice().reverse().map((epoch) => {
              const maxCost = Math.max(...epochs.map((e) => e.cost_per_honey), 0.01);
              const height = (epoch.cost_per_honey / maxCost) * 100;
              return (
                <div
                  key={epoch.epoch_id}
                  className="flex-1 min-w-[4px] max-w-[24px] rounded-t transition-all hover:opacity-80 cursor-pointer"
                  style={{
                    height: `${Math.max(height, 4)}%`,
                    backgroundColor:
                      epoch.status === "sealed"
                        ? epoch.convergence_delta < 0
                          ? "#10b981"
                          : "#f59e0b"
                        : "#3b82f6",
                  }}
                  title={`${epoch.epoch_id}: ${epoch.cost_per_honey.toFixed(4)} cost/honey`}
                  onClick={() => navigate(`/epoch/${epoch.epoch_id}`)}
                />
              );
            })}
          </div>
          <div className="flex justify-between mt-1 text-[10px] text-gray-600">
            <span>Oldest</span>
            <span>Latest</span>
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
      {loading && epochs.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-gray-500">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading epochs...
          </div>
        </div>
      )}

      {/* Epoch cards */}
      {!loading && epochs.length === 0 && (
        <div className="text-center py-12 text-gray-500">No epochs found</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {epochs.map((epoch) => (
          <div
            key={epoch.epoch_id}
            onClick={() => navigate(`/epoch/${epoch.epoch_id}`)}
            className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-5 cursor-pointer hover:bg-gray-800/60 transition-colors"
          >
            {/* Top row */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="font-mono text-blue-400 text-sm font-semibold">
                  {epoch.epoch_id}
                </span>
                <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded text-[10px] font-semibold uppercase">
                  {epoch.tier}
                </span>
              </div>
              <StatusBadge status={epoch.status} />
            </div>

            {/* Yield counts */}
            <div className="grid grid-cols-3 gap-2 mb-3">
              <div className="bg-gray-900/50 rounded-lg p-2 text-center">
                <p className="text-lg font-bold text-amber-400 font-mono">
                  {epoch.honey_count}
                </p>
                <p className="text-[10px] text-gray-500">Honey</p>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-2 text-center">
                <p className="text-lg font-bold text-yellow-300 font-mono">
                  {epoch.jelly_count}
                </p>
                <p className="text-[10px] text-gray-500">Jelly</p>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-2 text-center">
                <p className="text-lg font-bold text-orange-400 font-mono">
                  {epoch.propolis_count}
                </p>
                <p className="text-[10px] text-gray-500">Propolis</p>
              </div>
            </div>

            {/* Metrics row */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Cost/Honey</span>
                <span className="font-mono text-gray-300">
                  {epoch.cost_per_honey.toFixed(4)}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Convergence</span>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        epoch.convergence_delta < 0 ? "bg-green-500" : "bg-amber-500"
                      }`}
                      style={{
                        width: `${Math.min(
                          (Math.abs(epoch.convergence_delta) / maxConvergence) * 100,
                          100
                        )}%`,
                      }}
                    />
                  </div>
                  <span
                    className={`font-mono ${
                      epoch.convergence_delta < 0 ? "text-green-400" : "text-amber-400"
                    }`}
                  >
                    {epoch.convergence_delta > 0 ? "+" : ""}
                    {epoch.convergence_delta.toFixed(4)}
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Total Energy</span>
                <span className="font-mono text-gray-300">
                  {epoch.total_energy.toFixed(1)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {epochs.length > 0 && (
        <div className="mt-3 text-xs text-gray-500 px-1">
          {epochs.length} epoch{epochs.length !== 1 ? "s" : ""} shown
          <span className="ml-2 text-gray-600">-- auto-refreshing every 10s</span>
        </div>
      )}
    </div>
  );
}
