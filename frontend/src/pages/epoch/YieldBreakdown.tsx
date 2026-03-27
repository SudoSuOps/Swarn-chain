import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchEpochYield, type EpochArtifact } from "../../api";

type TypeFilter = "all" | "honey" | "jelly" | "propolis";

const TABS: { key: TypeFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "honey", label: "Honey" },
  { key: "jelly", label: "Jelly" },
  { key: "propolis", label: "Propolis" },
];

const TYPE_STYLES: Record<string, string> = {
  honey: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  jelly: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  propolis: "bg-orange-500/20 text-orange-400 border-orange-500/30",
};

export default function YieldBreakdown() {
  const { epochId } = useParams<{ epochId: string }>();
  const [artifacts, setArtifacts] = useState<EpochArtifact[]>([]);
  const [filter, setFilter] = useState<TypeFilter>("all");
  const [groupBy, setGroupBy] = useState<"none" | "transform" | "model">("none");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!epochId) return;
    setLoading(true);
    fetchEpochYield(epochId, filter === "all" ? undefined : filter)
      .then((data) => {
        setArtifacts(data);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [epochId, filter]);

  useEffect(() => {
    load();
  }, [load]);

  // Group artifacts
  const grouped: Record<string, EpochArtifact[]> = {};
  if (groupBy !== "none") {
    for (const art of artifacts) {
      const key = groupBy === "transform" ? art.transform : art.model;
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(art);
    }
  }

  const renderTable = (items: EpochArtifact[]) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/50">
            <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Artifact ID
            </th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Type
            </th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Task
            </th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Model
            </th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Node
            </th>
            <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Score
            </th>
            <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Energy
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700/30">
          {items.length === 0 ? (
            <tr>
              <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                No artifacts found
              </td>
            </tr>
          ) : (
            items.map((art) => (
              <tr key={art.artifact_id} className="table-row-hover">
                <td className="px-4 py-3">
                  <span className="font-mono text-blue-400 text-xs">
                    {art.artifact_id.length > 12
                      ? `${art.artifact_id.slice(0, 12)}...`
                      : art.artifact_id}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${
                      TYPE_STYLES[art.type] ?? "bg-gray-500/20 text-gray-400 border-gray-500/30"
                    }`}
                  >
                    {art.type}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="font-mono text-xs text-gray-300">
                    {art.task_id.length > 12
                      ? `${art.task_id.slice(0, 12)}...`
                      : art.task_id}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-300">{art.model}</td>
                <td className="px-4 py-3">
                  <span className="font-mono text-xs text-gray-400">
                    {art.node.length > 10
                      ? `${art.node.slice(0, 10)}...`
                      : art.node}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-12 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          art.score >= 0.8
                            ? "bg-green-500"
                            : art.score >= 0.5
                            ? "bg-yellow-500"
                            : "bg-red-500"
                        }`}
                        style={{ width: `${Math.min(art.score * 100, 100)}%` }}
                      />
                    </div>
                    <span className="font-mono text-xs text-gray-300 min-w-[2.5rem] text-right">
                      {art.score.toFixed(3)}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-mono text-xs text-gray-400">
                  {art.energy.toFixed(2)}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="p-6 max-w-full">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
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
        <span className="text-gray-300">Yield</span>
      </div>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Yield Breakdown</h1>
        <p className="text-sm text-gray-400 mt-1">
          Artifacts produced in epoch {epochId}
        </p>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        {/* Filter tabs */}
        <div className="flex gap-1 bg-gray-800/50 rounded-lg p-1">
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

        {/* Group by toggle */}
        <div className="flex gap-1 bg-gray-800/50 rounded-lg p-1">
          <button
            onClick={() => setGroupBy("none")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              groupBy === "none"
                ? "bg-gray-700 text-white shadow"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            No Grouping
          </button>
          <button
            onClick={() => setGroupBy("transform")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              groupBy === "transform"
                ? "bg-gray-700 text-white shadow"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            By Transform
          </button>
          <button
            onClick={() => setGroupBy("model")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              groupBy === "model"
                ? "bg-gray-700 text-white shadow"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            By Model
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && artifacts.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-gray-500">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading yield data...
          </div>
        </div>
      )}

      {/* Table(s) */}
      {groupBy === "none" ? (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl overflow-hidden">
          {renderTable(artifacts)}
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped)
            .sort(([, a], [, b]) => b.length - a.length)
            .map(([groupKey, items]) => (
              <div key={groupKey}>
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-sm font-semibold text-white">{groupKey}</h3>
                  <span className="text-xs text-gray-500">
                    {items.length} artifact{items.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl overflow-hidden">
                  {renderTable(items)}
                </div>
              </div>
            ))}
        </div>
      )}

      {artifacts.length > 0 && (
        <div className="mt-3 text-xs text-gray-500 px-1">
          {artifacts.length} artifact{artifacts.length !== 1 ? "s" : ""} shown
        </div>
      )}
    </div>
  );
}
