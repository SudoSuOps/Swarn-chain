import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  fetchBlock,
  fetchBlockAttempts,
  fetchTopAttempts,
  fetchBlockRewards,
  fetchBlockArtifacts,
  fetchBlockLineage,
  fetchBlockValidations,
  type Block,
  type Attempt,
  type Reward,
  type RewardSummary,
  type BlockArtifact,
  type LineageEdge,
  type BlockValidations,
} from "../api";
import StatusBadge from "../components/StatusBadge";
import ScoreBar from "../components/ScoreBar";
import GridRenderer from "../components/GridRenderer";

export default function BlockDetail() {
  const { blockId } = useParams<{ blockId: string }>();
  const [block, setBlock] = useState<Block | null>(null);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [topAttempts, setTopAttempts] = useState<Attempt[]>([]);
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [rewardSummary, setRewardSummary] = useState<RewardSummary | null>(null);
  const [artifacts, setArtifacts] = useState<BlockArtifact[]>([]);
  const [lineage, setLineage] = useState<LineageEdge[]>([]);
  const [validations, setValidations] = useState<BlockValidations | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedArtifact, setExpandedArtifact] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!blockId) return;
    Promise.all([
      fetchBlock(blockId),
      fetchBlockAttempts(blockId),
      fetchTopAttempts(blockId),
      fetchBlockRewards(blockId).catch(() => null),
      fetchBlockArtifacts(blockId).catch(() => []),
      fetchBlockLineage(blockId).catch(() => []),
      fetchBlockValidations(blockId).catch(() => null),
    ])
      .then(([b, att, top, rew, art, lin, val]) => {
        setBlock(b);
        setAttempts(att);
        setTopAttempts(top);
        setRewardSummary(rew);
        setRewards(rew?.rewards ?? []);
        setArtifacts(art);
        setLineage(lin);
        setValidations(val);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [blockId]);

  useEffect(() => {
    load();
  }, [load]);

  // Auto-refresh every 3 seconds if block is open
  useEffect(() => {
    if (block?.status === "open") {
      const interval = setInterval(load, 3000);
      return () => clearInterval(interval);
    }
  }, [block?.status, load]);

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
          Loading block...
        </div>
      </div>
    );
  }

  if (error || !block) {
    return (
      <div className="p-6">
        <div className="p-4 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400">
          {error ?? "Block not found"}
        </div>
      </div>
    );
  }

  // Compute elimination summary from attempts
  const eliminationSummary = {
    total_attempts: attempts.length,
    pruned: attempts.filter((a) => a.pruned).length,
    promoted: attempts.filter((a) => a.promoted).length,
    avg_score:
      attempts.length > 0
        ? attempts.reduce((s, a) => s + a.score, 0) / attempts.length
        : 0,
    max_score:
      attempts.length > 0
        ? Math.max(...attempts.map((a) => a.score))
        : 0,
  };

  return (
    <div className="p-6 max-w-full space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link to="/" className="hover:text-gray-300 transition-colors">
          Blocks
        </Link>
        <span>/</span>
        <span className="text-gray-300 font-mono">{block.block_id}</span>
      </div>

      {/* Header */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-xl font-bold text-white font-mono">
                {block.block_id}
              </h1>
              <StatusBadge status={block.status} />
            </div>
            <p className="text-gray-400 text-sm max-w-2xl">
              {block.task_payload?.description ?? block.task_id}
            </p>
          </div>
          {block.status === "open" && (
            <div className="flex items-center gap-2 text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-lg px-3 py-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-400 pulse-dot" />
              Live -- refreshing
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Domain</p>
            <p className="text-sm text-white font-medium">{block.domain}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Attempts</p>
            <p className="text-sm text-white font-mono">
              {block.attempt_count} / {block.max_attempts}
            </p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Energy</p>
            <p className="text-sm text-white font-mono">
              {block.total_energy.toFixed(2)} / {block.reward_pool.toFixed(1)}
            </p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Created</p>
            <p className="text-sm text-white">
              {new Date(block.start_time).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Task Payload -- Grids */}
      {block.task_payload && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Task Payload
          </h2>
          <div className="flex flex-wrap gap-8">
            {block.task_payload.input_grid && (
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wider mb-2 font-semibold">
                  Input Grid
                </p>
                <GridRenderer grid={block.task_payload.input_grid} />
              </div>
            )}
            {block.task_payload?.expected_output && (
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wider mb-2 font-semibold">
                  Expected Output
                </p>
                <GridRenderer grid={block.task_payload?.expected_output} />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Top Attempts */}
      {topAttempts.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Top Attempts
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {topAttempts.map((a, i) => (
              <div
                key={a.attempt_id}
                className={`bg-gray-900/60 rounded-lg p-4 border ${
                  i === 0
                    ? "border-yellow-500/40"
                    : "border-gray-700/30"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-gray-400">
                    #{i + 1}
                  </span>
                  {i === 0 && (
                    <span className="text-xs text-yellow-400 font-semibold">
                      Best
                    </span>
                  )}
                </div>
                <ScoreBar score={a.score} height={6} />
                <div className="mt-2 space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Node</span>
                    <Link
                      to={`/nodes/${a.node_id}`}
                      className="text-blue-400 hover:underline font-mono"
                    >
                      {a.node_id.slice(0, 10)}...
                    </Link>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Method</span>
                    <span className="text-gray-300">{a.method}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Strategy</span>
                    <span className="text-gray-300">{a.strategy_family}</span>
                  </div>
                </div>
                {(a.output_json as any)?.grid && (
                  <div className="mt-3">
                    <GridRenderer grid={(a.output_json as any)?.grid} cellSize={16} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Attempts Table */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">
          Attempts ({attempts.length})
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700/50">
                <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Attempt
                </th>
                <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Node
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
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/30">
              {attempts.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-3 py-8 text-center text-gray-500"
                  >
                    No attempts yet
                  </td>
                </tr>
              ) : (
                attempts.map((a) => (
                  <tr key={a.attempt_id} className="table-row-hover">
                    <td className="px-3 py-2">
                      <span className="font-mono text-xs text-gray-400">
                        {a.attempt_id.slice(0, 8)}...
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/nodes/${a.node_id}`}
                        className="font-mono text-xs text-blue-400 hover:underline"
                      >
                        {a.node_id.slice(0, 10)}...
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      <ScoreBar score={a.score} height={6} />
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-300">
                      {a.method}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-300">
                      {a.strategy_family}
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
                          <span className="text-gray-600 text-[10px]">--</span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs text-gray-400">
                      {a.energy_cost.toFixed(2)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Lineage */}
      {lineage.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Lineage ({lineage.length} edges)
          </h2>
          <div className="space-y-2">
            {lineage.map((edge, i) => (
              <div
                key={i}
                className="flex items-center gap-3 bg-gray-900/40 rounded-lg px-4 py-2.5"
              >
                <span className="font-mono text-xs text-gray-400 min-w-[80px]">
                  {edge.parent.slice(0, 8)}...
                </span>
                <div className="flex items-center gap-2">
                  <svg
                    className="w-4 h-4 text-gray-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M13 7l5 5m0 0l-5 5m5-5H6"
                    />
                  </svg>
                </div>
                <span className="font-mono text-xs text-gray-400 min-w-[80px]">
                  {edge.child.slice(0, 8)}...
                </span>
                <span
                  className={`ml-auto text-xs font-mono font-semibold ${
                    edge.delta_score > 0
                      ? "text-green-400"
                      : edge.delta_score < 0
                      ? "text-red-400"
                      : "text-gray-500"
                  }`}
                >
                  {edge.delta_score > 0 ? "+" : ""}
                  {edge.delta_score.toFixed(4)}
                </span>
                <span className="text-xs text-gray-500 ml-2">
                  {edge.delta_score > 0 ? 'improve' : 'regress'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rewards */}
      {rewards.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Reward Distribution
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/50">
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Node
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Score Basis
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/30">
                {rewards.map((r, i) => (
                  <tr key={i} className="table-row-hover">
                    <td className="px-3 py-2">
                      <Link
                        to={`/nodes/${r.node_id}`}
                        className="font-mono text-xs text-blue-400 hover:underline"
                      >
                        {r.node_id.slice(0, 12)}...
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          r.reward_type === "solve"
                            ? "bg-green-500/20 text-green-400"
                            : r.reward_type === "improvement"
                            ? "bg-blue-500/20 text-blue-400"
                            : "bg-gray-700/50 text-gray-300"
                        }`}
                      >
                        {r.reward_type}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-white">
                      {r.reward_amount.toFixed(4)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-gray-400">
                      {r.score_basis.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Domain Validator Decisions */}
      {validations && validations.decisions.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Domain Validator Decisions
          </h2>
          <div className="space-y-4">
            {validations.decisions.map((d, i) => (
              <div
                key={i}
                className={`bg-gray-900/60 rounded-lg p-4 border ${
                  d.verdict === "approved"
                    ? "border-green-500/30"
                    : d.verdict === "flagged"
                    ? "border-amber-500/30"
                    : d.verdict === "rejected"
                    ? "border-red-500/30"
                    : "border-blue-500/30"
                }`}
              >
                {/* Validator header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded text-xs font-semibold">
                      {d.validator_name}
                    </span>
                    <span className="text-xs text-gray-500">{d.domain}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                        d.verdict === "approved"
                          ? "bg-green-500/20 text-green-400 border border-green-500/30"
                          : d.verdict === "flagged"
                          ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                          : d.verdict === "rejected"
                          ? "bg-red-500/20 text-red-400 border border-red-500/30"
                          : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                      }`}
                    >
                      {d.verdict}
                    </span>
                    <span className="text-xs text-gray-400 font-mono">
                      {(d.confidence * 100).toFixed(1)}% confidence
                    </span>
                  </div>
                </div>

                {/* Confidence bar */}
                <div className="w-full h-2 bg-gray-700 rounded-full mb-3">
                  <div
                    className={`h-full rounded-full transition-all ${
                      d.confidence >= 0.8
                        ? "bg-green-500"
                        : d.confidence >= 0.5
                        ? "bg-amber-500"
                        : "bg-red-500"
                    }`}
                    style={{ width: `${d.confidence * 100}%` }}
                  />
                </div>

                {/* Critique */}
                {d.critique && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1 font-semibold">
                      Critique
                    </p>
                    <p className="text-sm text-gray-300">{d.critique}</p>
                  </div>
                )}

                {/* Flags */}
                {d.flags && d.flags.length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1 font-semibold">
                      Flags
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {d.flags.map((flag, fi) => (
                        <span
                          key={fi}
                          className="px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded text-xs font-mono"
                        >
                          {flag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Repair Suggestion */}
                {d.repair_suggestion && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1 font-semibold">
                      Repair Suggestion
                    </p>
                    <p className="text-sm text-cyan-300 bg-cyan-500/5 border border-cyan-500/10 rounded-lg px-3 py-2">
                      {d.repair_suggestion}
                    </p>
                  </div>
                )}

                {/* Objective anchor notice */}
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-700/30">
                  <span className="text-[10px] text-gray-500">
                    Objective score: {d.objective_score.toFixed(4)}
                  </span>
                  {d.objective_overridden && (
                    <span className="px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 rounded text-[10px] font-semibold">
                      VALIDATOR OVERRIDDEN BY OBJECTIVE
                    </span>
                  )}
                  {!d.objective_overridden && (
                    <span className="text-[10px] text-gray-600">
                      Objective verification is truth
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Elimination Summary */}
      {(block.status === "solved" || block.status === "exhausted") &&
        attempts.length > 0 && (
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">
              Elimination Summary
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
              <div className="bg-gray-900/50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-white font-mono">
                  {eliminationSummary.total_attempts}
                </p>
                <p className="text-xs text-gray-500 mt-1">Total Attempts</p>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-red-400 font-mono">
                  {eliminationSummary.pruned}
                </p>
                <p className="text-xs text-gray-500 mt-1">Pruned</p>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-green-400 font-mono">
                  {eliminationSummary.promoted}
                </p>
                <p className="text-xs text-gray-500 mt-1">Promoted</p>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-white font-mono">
                  {eliminationSummary.avg_score.toFixed(3)}
                </p>
                <p className="text-xs text-gray-500 mt-1">Avg Score</p>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-yellow-400 font-mono">
                  {eliminationSummary.max_score.toFixed(3)}
                </p>
                <p className="text-xs text-gray-500 mt-1">Max Score</p>
              </div>
            </div>
          </div>
        )}

      {/* Artifacts */}
      {artifacts.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Artifacts ({artifacts.length})
          </h2>
          <div className="space-y-3">
            {artifacts.map((art) => (
              <div
                key={art.artifact_type}
                className="bg-gray-900/50 border border-gray-700/30 rounded-lg overflow-hidden"
              >
                <button
                  onClick={() =>
                    setExpandedArtifact(
                      expandedArtifact === art.artifact_type
                        ? null
                        : art.artifact_type
                    )
                  }
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-800/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded text-xs font-medium">
                      {art.artifact_type}
                    </span>
                    <span className="font-mono text-xs text-gray-400">
                      {art.artifact_type.slice(0, 12)}...
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      {new Date(art.created_at).toLocaleString()}
                    </span>
                    <svg
                      className={`w-4 h-4 text-gray-500 transition-transform ${
                        expandedArtifact === art.artifact_type
                          ? "rotate-180"
                          : ""
                      }`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                </button>
                {expandedArtifact === art.artifact_type && (
                  <div className="border-t border-gray-700/30 p-4">
                    <pre className="text-xs text-gray-300 bg-gray-950 rounded-lg p-4 overflow-x-auto max-h-96">
                      {JSON.stringify(art.artifact_json, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
