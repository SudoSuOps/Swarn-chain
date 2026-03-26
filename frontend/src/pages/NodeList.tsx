import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchNodes, type Node } from "../api";

export default function NodeList() {
  const navigate = useNavigate();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchNodes()
      .then((data) => {
        setNodes(data);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 max-w-full">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Nodes</h1>
        <p className="text-sm text-gray-400 mt-1">
          Registered compute nodes in the SwarmChain network
        </p>
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
                  Node ID
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Type
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Hardware
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Attempts
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Solves
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Rewards
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Reputation
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/30">
              {loading ? (
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
                      Loading nodes...
                    </div>
                  </td>
                </tr>
              ) : nodes.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-12 text-center text-gray-500"
                  >
                    No nodes registered
                  </td>
                </tr>
              ) : (
                nodes.map((node) => (
                  <tr
                    key={node.node_id}
                    onClick={() => navigate(`/nodes/${node.node_id}`)}
                    className="table-row-hover cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <span className="font-mono text-blue-400 text-xs">
                        {node.node_id.length > 16
                          ? `${node.node_id.slice(0, 16)}...`
                          : node.node_id}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          node.node_type === "gpu"
                            ? "bg-purple-500/20 text-purple-400"
                            : node.node_type === "cpu"
                            ? "bg-blue-500/20 text-blue-400"
                            : "bg-gray-700/50 text-gray-300"
                        }`}
                      >
                        {node.node_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-300">
                      {node.hardware_class}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-300">
                      {node.total_attempts}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-green-400">
                      {node.total_solves}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-yellow-400">
                      {node.total_rewards.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{
                              width: `${Math.min(
                                node.reputation_score * 100,
                                100
                              )}%`,
                            }}
                          />
                        </div>
                        <span className="font-mono text-xs text-gray-300 min-w-[2.5rem] text-right">
                          {node.reputation_score.toFixed(2)}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {nodes.length > 0 && (
        <div className="mt-3 text-xs text-gray-500 px-1">
          {nodes.length} node{nodes.length !== 1 ? "s" : ""} registered
        </div>
      )}
    </div>
  );
}
