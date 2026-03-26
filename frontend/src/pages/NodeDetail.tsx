import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  fetchNode,
  fetchNodeStats,
  type Node,
  type NodeStats,
} from "../api";
import ScoreBar from "../components/ScoreBar";

export default function NodeDetail() {
  const { nodeId } = useParams<{ nodeId: string }>();
  const [node, setNode] = useState<Node | null>(null);
  const [stats, setStats] = useState<NodeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!nodeId) return;
    Promise.all([
      fetchNode(nodeId),
      fetchNodeStats(nodeId).catch(() => null),
    ])
      .then(([n, s]) => {
        setNode(n);
        setStats(s);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [nodeId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-3 text-gray-500">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
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
          Loading node...
        </div>
      </div>
    );
  }

  if (error || !node) {
    return (
      <div className="p-6">
        <div className="p-4 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400">
          {error ?? "Node not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-full space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link to="/nodes" className="hover:text-gray-300 transition-colors">
          Nodes
        </Link>
        <span>/</span>
        <span className="text-gray-300 font-mono">{node.node_id}</span>
      </div>

      {/* Header */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-white font-mono mb-1">
              {node.node_id}
            </h1>
            <div className="flex items-center gap-3">
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                  node.node_type === "gpu"
                    ? "bg-purple-500/20 text-purple-400 border-purple-500/30"
                    : node.node_type === "cpu"
                    ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                    : "bg-gray-500/20 text-gray-400 border-gray-500/30"
                }`}
              >
                {node.node_type.toUpperCase()}
              </span>
              <span className="text-sm text-gray-400">
                {node.hardware_class}
              </span>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500 mb-1">Registered</p>
            <p className="text-sm text-gray-300">
              {new Date(node.registered_at).toLocaleString()}
            </p>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mt-6">
          <div className="bg-gray-900/50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-white font-mono">
              {stats?.attempts ?? node.total_attempts}
            </p>
            <p className="text-xs text-gray-500 mt-1">Attempts</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-green-400 font-mono">
              {stats?.solves ?? node.total_solves}
            </p>
            <p className="text-xs text-gray-500 mt-1">Solves</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-yellow-400 font-mono">
              {(stats?.rewards ?? node.total_rewards).toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-1">Rewards</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-blue-400 font-mono">
              {stats?.efficiency != null
                ? `${(stats.efficiency * 100).toFixed(1)}%`
                : "--"}
            </p>
            <p className="text-xs text-gray-500 mt-1">Efficiency</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-purple-400 font-mono">
              {stats?.blocks_participated ?? "--"}
            </p>
            <p className="text-xs text-gray-500 mt-1">Blocks</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-white font-mono">
              {node.reputation_score.toFixed(3)}
            </p>
            <p className="text-xs text-gray-500 mt-1">Reputation</p>
          </div>
        </div>
      </div>

      {/* Reputation bar */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-3">
          Reputation Score
        </h2>
        <div className="h-4 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(node.reputation_score * 100, 100)}%`,
              background:
                "linear-gradient(90deg, #3b82f6, #06b6d4, #10b981)",
            }}
          />
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-500">
          <span>0.0</span>
          <span>{node.reputation_score.toFixed(4)}</span>
          <span>1.0</span>
        </div>
      </div>

      {/* Recent Attempts */}
      {stats?.recent_attempts && stats.recent_attempts.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Recent Attempts ({stats.recent_attempts.length})
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/50">
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Attempt
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Block
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider min-w-[140px]">
                    Score
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Method
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Strategy
                  </th>
                  <th className="text-center px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Energy
                  </th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Time
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/30">
                {stats.recent_attempts.map((a) => (
                  <tr key={a.attempt_id} className="table-row-hover">
                    <td className="px-3 py-2">
                      <span className="font-mono text-xs text-gray-400">
                        {a.attempt_id.slice(0, 8)}...
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/blocks/${a.block_id}`}
                        className="font-mono text-xs text-blue-400 hover:underline"
                      >
                        {a.block_id.slice(0, 10)}...
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      <ScoreBar score={a.score} height={6} />
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-300">
                      {a.method}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-300">
                      {a.strategy}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <div className="flex items-center justify-center gap-1">
                        {a.promoted && (
                          <span className="px-1.5 py-0.5 bg-green-500/20 text-green-400 border border-green-500/30 rounded text-[10px] font-semibold">
                            PROMOTED
                          </span>
                        )}
                        {a.pruned && (
                          <span className="px-1.5 py-0.5 bg-red-500/20 text-red-400 border border-red-500/30 rounded text-[10px] font-semibold">
                            PRUNED
                          </span>
                        )}
                        {!a.promoted && !a.pruned && (
                          <span className="text-gray-600 text-[10px]">
                            --
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs text-gray-400">
                      {a.energy_cost.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right text-xs text-gray-500">
                      {new Date(a.created_at).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
