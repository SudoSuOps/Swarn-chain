import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchEpochLadder, type SiliconLadderEntry } from "../../api";

const HW_STYLES: Record<string, string> = {
  cpu: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  "gpu-mid": "bg-purple-500/20 text-purple-400 border-purple-500/30",
  "gpu-heavy": "bg-pink-500/20 text-pink-400 border-pink-500/30",
  edge: "bg-teal-500/20 text-teal-400 border-teal-500/30",
};

export default function SiliconLadder() {
  const { epochId } = useParams<{ epochId: string }>();
  const [ladder, setLadder] = useState<SiliconLadderEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!epochId) return;
    fetchEpochLadder(epochId)
      .then((data) => {
        setLadder(data);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [epochId]);

  useEffect(() => {
    load();
  }, [load]);

  // Compute max efficiency for bar scaling
  const maxEfficiency = ladder.length > 0
    ? Math.max(...ladder.map((e) => e.efficiency_score), 0.01)
    : 1;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-3 text-gray-500">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading silicon ladder...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="p-4 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400">
          {error}
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
        <Link
          to={`/epoch/${epochId}`}
          className="hover:text-gray-300 transition-colors font-mono"
        >
          {epochId}
        </Link>
        <span>/</span>
        <span className="text-gray-300">Silicon Ladder</span>
      </div>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Silicon Ladder</h1>
        <p className="text-sm text-gray-400 mt-1">
          Model efficiency rankings for epoch {epochId}
        </p>
      </div>

      {/* Efficiency chart */}
      {ladder.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-4">
            Relative Efficiency
          </p>
          <div className="space-y-3">
            {ladder.map((entry, i) => (
              <div key={entry.model_name} className="flex items-center gap-3">
                <span className="text-xs text-gray-600 font-mono w-6 text-right">
                  #{i + 1}
                </span>
                <span className="text-xs text-gray-300 w-40 truncate" title={entry.model_name}>
                  {entry.model_name}
                </span>
                <div className="flex-1 h-6 bg-gray-800 rounded overflow-hidden">
                  <div
                    className={`h-full rounded transition-all duration-500 ${
                      i === 0
                        ? "bg-gradient-to-r from-amber-500 to-yellow-400"
                        : i === 1
                        ? "bg-gradient-to-r from-gray-400 to-gray-300"
                        : i === 2
                        ? "bg-gradient-to-r from-amber-700 to-amber-600"
                        : "bg-blue-600/60"
                    }`}
                    style={{
                      width: `${(entry.efficiency_score / maxEfficiency) * 100}%`,
                    }}
                  />
                </div>
                <span className="text-xs font-mono text-gray-300 w-16 text-right">
                  {entry.efficiency_score.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ranked table */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Rank
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Model
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Hardware
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Honey
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Honey Rate
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Energy/Honey
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Efficiency
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/30">
              {ladder.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                    No models ranked
                  </td>
                </tr>
              ) : (
                ladder.map((entry, i) => (
                  <tr key={entry.model_name} className="table-row-hover">
                    <td className="px-4 py-3">
                      <span
                        className={`font-mono text-sm font-bold ${
                          i === 0
                            ? "text-amber-400"
                            : i === 1
                            ? "text-gray-300"
                            : i === 2
                            ? "text-amber-600"
                            : "text-gray-500"
                        }`}
                      >
                        #{i + 1}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-white text-sm font-medium">
                        {entry.model_name}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${
                          HW_STYLES[entry.hardware_class] ??
                          "bg-gray-500/20 text-gray-400 border-gray-500/30"
                        }`}
                      >
                        {entry.hardware_class}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-amber-400">
                      {entry.honey_count}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="font-mono text-green-400">
                        {(entry.honey_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-300">
                      {entry.energy_per_honey.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-white font-semibold">
                      {entry.efficiency_score.toFixed(2)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {ladder.length > 0 && (
        <div className="mt-3 text-xs text-gray-500 px-1">
          {ladder.length} model{ladder.length !== 1 ? "s" : ""} ranked
        </div>
      )}
    </div>
  );
}
