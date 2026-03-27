import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchMetrics, type Metrics } from "../../api";

export default function ProtocolHome() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMetrics()
      .then(setMetrics)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      {/* Hero */}
      <div className="text-center py-12">
        <h1 className="text-4xl font-bold text-white mb-4">SwarmProtocol</h1>
        <p className="text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed">
          A proof-of-work protocol where heterogeneous compute nodes compete to
          solve tasks through elimination. Search becomes data. Elimination
          becomes integrity. Finality creates value.
        </p>
      </div>

      {/* Quote */}
      <div className="bg-gray-800/40 border border-cyan-500/20 rounded-xl p-8 text-center">
        <blockquote className="text-xl text-cyan-300 italic font-light leading-relaxed">
          &ldquo;Search becomes data. Elimination becomes integrity. Finality creates value.&rdquo;
        </blockquote>
        <p className="text-sm text-gray-500 mt-4">-- SwarmChain Whitepaper, Section 1</p>
      </div>

      {/* Key metrics */}
      {!loading && metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-5 text-center">
            <p className="text-3xl font-bold text-white font-mono">
              {metrics.blocks.total.toLocaleString()}
            </p>
            <p className="text-xs text-gray-400 mt-2">Total Blocks</p>
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-5 text-center">
            <p className="text-3xl font-bold text-green-400 font-mono">
              {metrics.blocks.solved.toLocaleString()}
            </p>
            <p className="text-xs text-gray-400 mt-2">Solved</p>
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-5 text-center">
            <p className="text-3xl font-bold text-blue-400 font-mono">
              {metrics.nodes.total.toLocaleString()}
            </p>
            <p className="text-xs text-gray-400 mt-2">Nodes</p>
          </div>
          <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-5 text-center">
            <p className="text-3xl font-bold text-purple-400 font-mono">
              {metrics.total_energy.toFixed(0)}
            </p>
            <p className="text-xs text-gray-400 mt-2">Total Energy</p>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="flex items-center gap-3 text-gray-500">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading metrics...
          </div>
        </div>
      )}

      {/* Protocol sections */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          to="/whitepaper"
          className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6 hover:bg-gray-800/60 transition-colors group"
        >
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">📄</span>
            <h3 className="text-lg font-semibold text-white group-hover:text-cyan-400 transition-colors">
              Whitepaper
            </h3>
          </div>
          <p className="text-sm text-gray-400">
            The full SwarmChain protocol specification. Elimination mechanics,
            reward functions, convergence guarantees, and anchoring.
          </p>
        </Link>

        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6 opacity-60">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">📊</span>
            <h3 className="text-lg font-semibold text-white">Benchmarks</h3>
          </div>
          <p className="text-sm text-gray-400">
            Protocol performance benchmarks across domains, models, and hardware
            configurations. Coming soon.
          </p>
        </div>

        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6 opacity-60">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">💰</span>
            <h3 className="text-lg font-semibold text-white">Economics</h3>
          </div>
          <p className="text-sm text-gray-400">
            Reward economics, energy pricing, and the convergence-driven cost
            reduction model. Coming soon.
          </p>
        </div>

        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6 opacity-60">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">🤝</span>
            <h3 className="text-lg font-semibold text-white">Contribute</h3>
          </div>
          <p className="text-sm text-gray-400">
            Join the SwarmChain network as a compute node, validator, or protocol
            developer. Coming soon.
          </p>
        </div>
      </div>

      {/* Core principles */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Core Principles</h2>
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 bg-blue-600/20 rounded-lg flex items-center justify-center text-blue-400 font-bold text-sm flex-shrink-0 mt-0.5">
              1
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white mb-1">
                Elimination Over Selection
              </h3>
              <p className="text-sm text-gray-400">
                Quality emerges from competitive elimination, not from picking a single best
                answer. Every attempt contributes to the search tree. Pruned attempts are not
                wasted -- they narrow the solution space.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="w-8 h-8 bg-purple-600/20 rounded-lg flex items-center justify-center text-purple-400 font-bold text-sm flex-shrink-0 mt-0.5">
              2
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white mb-1">
                Convergence As Proof
              </h3>
              <p className="text-sm text-gray-400">
                Each epoch must demonstrate measurable convergence in cost-per-honey. If
                convergence stalls, the protocol adapts allocation. The convergence delta is
                the heartbeat of the system.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="w-8 h-8 bg-emerald-600/20 rounded-lg flex items-center justify-center text-emerald-400 font-bold text-sm flex-shrink-0 mt-0.5">
              3
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white mb-1">
                Merkle-Anchored Finality
              </h3>
              <p className="text-sm text-gray-400">
                Every sealed epoch window produces a Merkle root anchored to Hedera Hashgraph.
                This creates immutable provenance for all yield: honey, jelly, and propolis.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="w-8 h-8 bg-amber-600/20 rounded-lg flex items-center justify-center text-amber-400 font-bold text-sm flex-shrink-0 mt-0.5">
              4
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white mb-1">
                Heterogeneous Compute
              </h3>
              <p className="text-sm text-gray-400">
                CPU, GPU, and edge nodes compete on the same tasks. The silicon ladder ranks
                models by efficiency, not raw power. Small models can outperform large ones
                when energy economics are accounted for.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
