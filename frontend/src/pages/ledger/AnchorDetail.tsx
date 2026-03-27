import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  fetchAnchorTimeline,
  fetchAnchorVerify,
  type AnchorRecord,
  type VerifyResult,
} from "../../api";

export default function AnchorDetail() {
  const { window: windowParam } = useParams<{ window: string }>();
  const windowNum = Number(windowParam);
  const [anchor, setAnchor] = useState<AnchorRecord | null>(null);
  const [verification, setVerification] = useState<VerifyResult | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (isNaN(windowNum)) return;
    fetchAnchorTimeline()
      .then((anchors) => {
        const found = anchors.find((a) => a.window === windowNum);
        if (found) {
          setAnchor(found);
          setError(null);
        } else {
          setError(`Anchor window ${windowNum} not found`);
        }
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [windowNum]);

  useEffect(() => {
    load();
  }, [load]);

  const handleVerify = () => {
    setVerifying(true);
    fetchAnchorVerify(windowNum)
      .then((result) => {
        setVerification(result);
      })
      .catch((e: Error) => {
        setVerification({
          window: windowNum,
          verified: false,
          merkle_root: anchor?.merkle_root ?? "",
          hedera_match: false,
          computed_root: "",
          message: e.message,
        });
      })
      .finally(() => setVerifying(false));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-3 text-gray-500">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading anchor...
        </div>
      </div>
    );
  }

  if (error || !anchor) {
    return (
      <div className="p-6">
        <div className="p-4 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400">
          {error ?? "Anchor not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-full space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link to="/" className="hover:text-gray-300 transition-colors">
          Timeline
        </Link>
        <span>/</span>
        <span className="text-gray-300 font-mono">Window {anchor.window}</span>
      </div>

      {/* Header */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-xl font-bold text-white font-mono">
                Anchor Window {anchor.window}
              </h1>
              {anchor.anchored ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-green-500/20 text-green-400 border-green-500/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                  Anchored
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-gray-500/20 text-gray-400 border-gray-500/30">
                  Pending
                </span>
              )}
            </div>
            <p className="text-gray-400 text-sm">
              Sealed {new Date(anchor.sealed_at).toLocaleString()}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Total Honey</p>
            <p className="text-sm text-amber-400 font-mono font-semibold">{anchor.total_honey}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Total Energy</p>
            <p className="text-sm text-white font-mono">{anchor.total_energy.toFixed(2)}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Cost/Honey</p>
            <p className="text-sm text-emerald-400 font-mono">{anchor.cost_per_honey.toFixed(4)}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Solve Rate</p>
            <p className="text-sm text-green-400 font-mono">
              {(anchor.solve_rate * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      </div>

      {/* Merkle + Hedera details */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Provenance Data</h2>
        <div className="space-y-4">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">
              Merkle Root
            </p>
            <p className="font-mono text-sm text-blue-400 bg-gray-900/50 rounded-lg px-4 py-2 break-all">
              {anchor.merkle_root}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">
                Hedera Topic
              </p>
              <p className="font-mono text-sm text-gray-300 bg-gray-900/50 rounded-lg px-4 py-2">
                {anchor.hedera_topic ?? "Not anchored"}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">
                Hedera Timestamp
              </p>
              <p className="font-mono text-sm text-gray-300 bg-gray-900/50 rounded-lg px-4 py-2">
                {anchor.hedera_timestamp
                  ? new Date(anchor.hedera_timestamp).toLocaleString()
                  : "Not anchored"}
              </p>
            </div>
          </div>

          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">
              Convergence Delta
            </p>
            <p
              className={`font-mono text-sm ${
                anchor.convergence_delta < 0 ? "text-green-400" : "text-amber-400"
              }`}
            >
              {anchor.convergence_delta > 0 ? "+" : ""}
              {anchor.convergence_delta.toFixed(6)}
            </p>
          </div>
        </div>
      </div>

      {/* Verification section */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Verification</h2>
        <p className="text-sm text-gray-400 mb-4">
          Re-compute the Merkle root from stored data and verify against the anchored hash.
        </p>

        <button
          onClick={handleVerify}
          disabled={verifying}
          className={`px-6 py-2.5 rounded-lg text-sm font-semibold transition-colors ${
            verifying
              ? "bg-gray-700 text-gray-400 cursor-not-allowed"
              : "bg-amber-600 hover:bg-amber-500 text-white"
          }`}
        >
          {verifying ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Verifying...
            </span>
          ) : (
            "Verify Anchor"
          )}
        </button>

        {verification && (
          <div
            className={`mt-4 p-4 rounded-lg border ${
              verification.verified
                ? "bg-green-900/20 border-green-500/30"
                : "bg-red-900/20 border-red-500/30"
            }`}
          >
            <div className="flex items-center gap-3 mb-3">
              {verification.verified ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold border bg-green-500/20 text-green-400 border-green-500/30">
                  VERIFIED
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold border bg-red-500/20 text-red-400 border-red-500/30">
                  FAILED
                </span>
              )}
              {verification.hedera_match && (
                <span className="text-xs text-green-400">Hedera match confirmed</span>
              )}
            </div>
            <p className="text-sm text-gray-300 mb-2">{verification.message}</p>
            {verification.computed_root && (
              <div className="mt-2">
                <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">
                  Computed Root
                </p>
                <p className="font-mono text-xs text-gray-400 break-all">
                  {verification.computed_root}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
