import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchEpoch, type EpochDetail as EpochDetailType } from "../../api";
import StatusBadge from "../../components/StatusBadge";

export default function EpochDetail() {
  const { epochId } = useParams<{ epochId: string }>();
  const [epoch, setEpoch] = useState<EpochDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!epochId) return;
    fetchEpoch(epochId)
      .then((data) => {
        setEpoch(data);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [epochId]);

  useEffect(() => {
    load();
  }, [load]);

  // Auto-refresh for open epochs
  useEffect(() => {
    if (epoch?.status === "open") {
      const interval = setInterval(load, 5000);
      return () => clearInterval(interval);
    }
  }, [epoch?.status, load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-3 text-gray-500">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading epoch...
        </div>
      </div>
    );
  }

  if (error || !epoch) {
    return (
      <div className="p-6">
        <div className="p-4 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400">
          {error ?? "Epoch not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-full space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link to="/" className="hover:text-gray-300 transition-colors">
          Epochs
        </Link>
        <span>/</span>
        <span className="text-gray-300 font-mono">{epoch.epoch_id}</span>
      </div>

      {/* Header */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-xl font-bold text-white font-mono">
                {epoch.epoch_id}
              </h1>
              <StatusBadge status={epoch.status} />
              <span className="px-2.5 py-0.5 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded-full text-xs font-semibold uppercase">
                {epoch.tier}
              </span>
            </div>
            <p className="text-gray-400 text-sm">
              {epoch.sealed_at
                ? `Sealed ${new Date(epoch.sealed_at).toLocaleString()}`
                : `Started ${new Date(epoch.started_at).toLocaleString()}`}
            </p>
          </div>
          {epoch.status === "open" && (
            <div className="flex items-center gap-2 text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-lg px-3 py-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-400 pulse-dot" />
              Live -- refreshing
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Total Attempts</p>
            <p className="text-sm text-white font-mono">{epoch.total_attempts}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Total Energy</p>
            <p className="text-sm text-white font-mono">{epoch.total_energy.toFixed(2)}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Convergence Delta</p>
            <p className={`text-sm font-mono ${epoch.convergence_delta < 0 ? "text-green-400" : "text-amber-400"}`}>
              {epoch.convergence_delta > 0 ? "+" : ""}
              {epoch.convergence_delta.toFixed(6)}
            </p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Started</p>
            <p className="text-sm text-white">
              {new Date(epoch.started_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>

      {/* Yield summary - 3 big number cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-gray-800/40 border border-amber-500/30 rounded-xl p-6 text-center">
          <p className="text-4xl font-bold text-amber-400 font-mono">
            {epoch.honey_count}
          </p>
          <p className="text-sm text-gray-400 mt-2">Honey</p>
          <p className="text-xs text-gray-600 mt-1">Top-tier verified outputs</p>
        </div>
        <div className="bg-gray-800/40 border border-yellow-500/30 rounded-xl p-6 text-center">
          <p className="text-4xl font-bold text-yellow-300 font-mono">
            {epoch.jelly_count}
          </p>
          <p className="text-sm text-gray-400 mt-2">Jelly</p>
          <p className="text-xs text-gray-600 mt-1">Partial-quality outputs</p>
        </div>
        <div className="bg-gray-800/40 border border-orange-500/30 rounded-xl p-6 text-center">
          <p className="text-4xl font-bold text-orange-400 font-mono">
            {epoch.propolis_count}
          </p>
          <p className="text-sm text-gray-400 mt-2">Propolis</p>
          <p className="text-xs text-gray-600 mt-1">Failed / low-score outputs</p>
        </div>
      </div>

      {/* Economics section */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Economics</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-gray-900/50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-emerald-400 font-mono">
              {epoch.cost_per_honey.toFixed(4)}
            </p>
            <p className="text-xs text-gray-500 mt-1">Cost / Honey</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-cyan-400 font-mono">
              {epoch.energy_per_honey.toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-1">Energy / Honey</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-purple-400 font-mono">
              {epoch.attempts_per_honey.toFixed(1)}
            </p>
            <p className="text-xs text-gray-500 mt-1">Attempts / Honey</p>
          </div>
        </div>
      </div>

      {/* Findings */}
      {epoch.findings.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Findings ({epoch.findings.length})
          </h2>
          <div className="space-y-2">
            {epoch.findings.map((finding, i) => (
              <div
                key={i}
                className="flex items-start gap-3 bg-gray-900/40 rounded-lg px-4 py-3"
              >
                <span className="text-xs text-gray-600 font-mono mt-0.5">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <p className="text-sm text-gray-300">{finding}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {epoch.recommendations.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Recommendations ({epoch.recommendations.length})
          </h2>
          <div className="space-y-2">
            {epoch.recommendations.map((rec, i) => (
              <div
                key={i}
                className="flex items-start gap-3 bg-cyan-500/5 border border-cyan-500/10 rounded-lg px-4 py-3"
              >
                <span className="text-xs text-cyan-600 font-mono mt-0.5">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <p className="text-sm text-cyan-300">{rec}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation links */}
      <div className="flex gap-4">
        <Link
          to={`/epoch/${epoch.epoch_id}/yield`}
          className="flex-1 bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 hover:bg-gray-800/60 transition-colors text-center"
        >
          <p className="text-sm font-semibold text-white">View Yield Breakdown</p>
          <p className="text-xs text-gray-500 mt-1">
            All artifacts with type filtering
          </p>
        </Link>
        <Link
          to={`/epoch/${epoch.epoch_id}/ladder`}
          className="flex-1 bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 hover:bg-gray-800/60 transition-colors text-center"
        >
          <p className="text-sm font-semibold text-white">Silicon Ladder</p>
          <p className="text-xs text-gray-500 mt-1">
            Model efficiency rankings
          </p>
        </Link>
      </div>
    </div>
  );
}
