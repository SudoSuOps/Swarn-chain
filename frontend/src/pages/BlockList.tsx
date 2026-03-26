import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fetchBlocks, type Block } from "../api";
import StatusBadge from "../components/StatusBadge";
import ScoreBar from "../components/ScoreBar";

type StatusFilter = "all" | "open" | "solved" | "exhausted";

const TABS: { key: StatusFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "open", label: "Open" },
  { key: "solved", label: "Solved" },
  { key: "exhausted", label: "Exhausted" },
];

export default function BlockList() {
  const navigate = useNavigate();
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchBlocks(filter)
      .then((data) => {
        setBlocks(data);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filter]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  // Auto-refresh every 5 seconds when viewing open blocks or all
  useEffect(() => {
    if (filter === "open" || filter === "all") {
      const interval = setInterval(load, 5000);
      return () => clearInterval(interval);
    }
  }, [filter, load]);

  return (
    <div className="p-6 max-w-full">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Blocks</h1>
        <p className="text-sm text-gray-400 mt-1">
          Browse and monitor SwarmChain blocks
        </p>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-6 bg-gray-800/50 rounded-lg p-1 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              filter === tab.key
                ? "bg-gray-700 text-white shadow"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Block ID
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Domain
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Attempts
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Energy
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider min-w-[160px]">
                  Score
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Winner
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/30">
              {loading && blocks.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center">
                    <div className="flex items-center justify-center gap-3 text-gray-500">
                      <svg
                        className="animate-spin h-5 w-5"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                          fill="none"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                      </svg>
                      Loading blocks...
                    </div>
                  </td>
                </tr>
              ) : blocks.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-12 text-center text-gray-500"
                  >
                    No blocks found
                  </td>
                </tr>
              ) : (
                blocks.map((block) => (
                  <tr
                    key={block.block_id}
                    onClick={() => navigate(`/blocks/${block.block_id}`)}
                    className="table-row-hover cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <span className="font-mono text-blue-400 text-xs">
                        {block.block_id.length > 12
                          ? `${block.block_id.slice(0, 12)}...`
                          : block.block_id}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 bg-gray-700/50 rounded text-xs text-gray-300">
                        {block.domain}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={block.status} />
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-300">
                      {block.attempt_count}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-300">
                      {block.total_energy.toFixed(1)}
                    </td>
                    <td className="px-4 py-3">
                      {block.final_score !== null ? (
                        <ScoreBar score={block.final_score} />
                      ) : (
                        <span className="text-gray-600 text-xs">--</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {block.winning_node_id ? (
                        <span className="font-mono text-xs text-green-400">
                          {block.winning_node_id.length > 10
                            ? `${block.winning_node_id.slice(0, 10)}...`
                            : block.winning_node_id}
                        </span>
                      ) : (
                        <span className="text-gray-600 text-xs">--</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer info */}
      {blocks.length > 0 && (
        <div className="mt-3 text-xs text-gray-500 px-1">
          {blocks.length} block{blocks.length !== 1 ? "s" : ""} shown
          {(filter === "open" || filter === "all") && (
            <span className="ml-2 text-gray-600">
              -- auto-refreshing every 5s
            </span>
          )}
        </div>
      )}
    </div>
  );
}
