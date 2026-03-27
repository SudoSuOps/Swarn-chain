import { Link } from "react-router-dom";

export default function WhitepaperViewer() {
  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-8">
        <Link to="/" className="hover:text-gray-300 transition-colors">
          Protocol
        </Link>
        <span>/</span>
        <span className="text-gray-300">Whitepaper</span>
      </div>

      {/* Whitepaper content */}
      <article className="prose prose-invert max-w-none">
        {/* Title */}
        <div className="text-center mb-12 pb-8 border-b border-gray-800">
          <h1 className="text-3xl font-bold text-white mb-3">
            SwarmChain: A Proof-of-Work Protocol for Competitive Intelligence Synthesis
          </h1>
          <p className="text-gray-400 text-sm">
            v1.0 -- SwarmChain Foundation
          </p>
        </div>

        {/* Abstract */}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-white mb-4 pb-2 border-b border-gray-800">
            Abstract
          </h2>
          <p className="text-gray-300 leading-relaxed mb-4">
            SwarmChain introduces a novel proof-of-work protocol where heterogeneous compute
            nodes compete to solve structured intelligence tasks through iterative elimination.
            Unlike traditional consensus mechanisms that select a single winner, SwarmChain
            treats every attempt as a contribution to a convergent search process. The protocol
            produces three classes of yield -- honey (verified high-quality outputs), jelly
            (partial-quality outputs suitable for refinement), and propolis (failed attempts
            that inform future strategy) -- all anchored to an immutable provenance chain via
            Merkle roots on Hedera Hashgraph.
          </p>
        </section>

        {/* Section 1 */}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-white mb-4 pb-2 border-b border-gray-800">
            1. Introduction
          </h2>
          <p className="text-gray-300 leading-relaxed mb-4">
            The fundamental challenge of distributed compute is not speed -- it is quality
            assurance. When multiple nodes produce competing outputs for the same task, the
            system must determine which outputs meet a quality threshold and which should be
            eliminated. SwarmChain formalizes this as a proof-of-work problem.
          </p>
          <p className="text-gray-300 leading-relaxed mb-4">
            Each task is wrapped in a <span className="text-cyan-400 font-mono">Block</span>,
            which defines the search parameters: maximum attempts, time limits, energy budgets,
            and reward pools. Compute nodes submit attempts, each scored by deterministic
            validators. The elimination engine prunes low-scoring attempts and promotes
            high-scoring ones, creating a lineage tree that converges toward the optimal solution.
          </p>
          <div className="bg-gray-800/40 border-l-4 border-cyan-500 rounded-r-lg p-4 my-6">
            <p className="text-cyan-300 italic">
              &ldquo;Search becomes data. Elimination becomes integrity. Finality creates value.&rdquo;
            </p>
          </div>
        </section>

        {/* Section 2 */}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-white mb-4 pb-2 border-b border-gray-800">
            2. Block Lifecycle
          </h2>
          <p className="text-gray-300 leading-relaxed mb-4">
            A block transitions through three states:
          </p>
          <div className="space-y-3 mb-4">
            <div className="flex items-start gap-3 bg-gray-800/30 rounded-lg p-3">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-blue-500/20 text-blue-400 border-blue-500/30 flex-shrink-0">
                open
              </span>
              <p className="text-gray-300 text-sm">
                The block accepts attempts from any registered node. Attempts are scored in
                real-time and the elimination engine prunes below-threshold entries.
              </p>
            </div>
            <div className="flex items-start gap-3 bg-gray-800/30 rounded-lg p-3">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-green-500/20 text-green-400 border-green-500/30 flex-shrink-0">
                solved
              </span>
              <p className="text-gray-300 text-sm">
                A winning attempt has been identified. The reward pool is distributed according
                to the reward function, crediting the solver, lineage contributors, and
                efficiency bonuses.
              </p>
            </div>
            <div className="flex items-start gap-3 bg-gray-800/30 rounded-lg p-3">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-amber-500/20 text-amber-400 border-amber-500/30 flex-shrink-0">
                exhausted
              </span>
              <p className="text-gray-300 text-sm">
                The block has reached its maximum attempts or time limit without a satisfactory
                solution. The energy record is preserved as propolis for future strategy
                refinement.
              </p>
            </div>
          </div>
        </section>

        {/* Section 3 */}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-white mb-4 pb-2 border-b border-gray-800">
            3. Yield Classification
          </h2>
          <p className="text-gray-300 leading-relaxed mb-4">
            Every attempt produces data. The protocol classifies outputs into three tiers:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
            <div className="bg-gray-800/40 border border-amber-500/30 rounded-xl p-4">
              <h3 className="text-amber-400 font-semibold mb-2">Honey</h3>
              <p className="text-gray-400 text-sm">
                Verified, high-quality outputs that pass all validators with scores above the
                honey threshold. These are the primary economic output of the protocol.
              </p>
            </div>
            <div className="bg-gray-800/40 border border-yellow-500/30 rounded-xl p-4">
              <h3 className="text-yellow-300 font-semibold mb-2">Jelly</h3>
              <p className="text-gray-400 text-sm">
                Partial-quality outputs that show promise but fail one or more validators.
                Jelly feeds the self-healing pipeline and can be promoted to honey through
                refinement.
              </p>
            </div>
            <div className="bg-gray-800/40 border border-orange-500/30 rounded-xl p-4">
              <h3 className="text-orange-400 font-semibold mb-2">Propolis</h3>
              <p className="text-gray-400 text-sm">
                Failed attempts that nonetheless contribute to the search tree. Propolis data
                trains future strategy selection and prevents repeated failures.
              </p>
            </div>
          </div>
        </section>

        {/* Section 4 */}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-white mb-4 pb-2 border-b border-gray-800">
            4. Silicon Ladder
          </h2>
          <p className="text-gray-300 leading-relaxed mb-4">
            The silicon ladder ranks compute models by their efficiency score -- honey produced
            per unit of energy consumed. This creates a meritocratic hierarchy where small,
            efficient models can outperform expensive large models.
          </p>
          <p className="text-gray-300 leading-relaxed mb-4">
            The efficiency score is defined as:
          </p>
          <div className="bg-gray-950 border border-gray-700/50 rounded-lg p-4 my-4 font-mono text-sm text-center">
            <span className="text-cyan-400">efficiency</span>
            <span className="text-gray-500"> = </span>
            <span className="text-green-400">honey_count</span>
            <span className="text-gray-500"> / </span>
            <span className="text-red-400">total_energy</span>
            <span className="text-gray-500"> * </span>
            <span className="text-purple-400">honey_rate</span>
          </div>
          <p className="text-gray-300 leading-relaxed">
            Models falling below the cost frontier for three consecutive epochs face
            allocation reduction via the softmax allocation function, which redistributes
            compute budget toward more efficient models.
          </p>
        </section>

        {/* Section 5 */}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-white mb-4 pb-2 border-b border-gray-800">
            5. Convergence and Anchoring
          </h2>
          <p className="text-gray-300 leading-relaxed mb-4">
            Each epoch is sealed when its convergence criteria are met: the cost-per-honey
            delta must fall below a configurable threshold, or the epoch reaches its time
            limit. Upon sealing:
          </p>
          <ol className="list-decimal list-inside space-y-2 text-gray-300 mb-4">
            <li>All yield is classified (honey, jelly, propolis)</li>
            <li>A Merkle tree is computed over all block artifacts</li>
            <li>The Merkle root is submitted to the Hedera Hashgraph consensus service</li>
            <li>The epoch becomes immutable and verifiable</li>
          </ol>
          <p className="text-gray-300 leading-relaxed">
            Anyone can independently verify an epoch by recomputing the Merkle root from
            the raw data and comparing it against the anchored hash on Hedera. This provides
            trustless provenance for every piece of yield the protocol produces.
          </p>
        </section>

        {/* Section 6 */}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-white mb-4 pb-2 border-b border-gray-800">
            6. Reward Function
          </h2>
          <p className="text-gray-300 leading-relaxed mb-4">
            The reward pool for each solved block is distributed across four channels:
          </p>
          <div className="overflow-x-auto mb-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/50">
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase">
                    Channel
                  </th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-gray-400 uppercase">
                    Share
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-400 uppercase">
                    Description
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/30">
                <tr>
                  <td className="px-3 py-2 text-green-400 font-medium">Solver</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-300">50%</td>
                  <td className="px-3 py-2 text-gray-400">The node that submitted the winning attempt</td>
                </tr>
                <tr>
                  <td className="px-3 py-2 text-blue-400 font-medium">Lineage</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-300">20%</td>
                  <td className="px-3 py-2 text-gray-400">Nodes whose attempts formed the lineage chain leading to the solution</td>
                </tr>
                <tr>
                  <td className="px-3 py-2 text-purple-400 font-medium">Exploration</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-300">20%</td>
                  <td className="px-3 py-2 text-gray-400">Distributed among all participating nodes proportional to energy spent</td>
                </tr>
                <tr>
                  <td className="px-3 py-2 text-amber-400 font-medium">Efficiency</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-300">10%</td>
                  <td className="px-3 py-2 text-gray-400">Bonus for the most energy-efficient attempt relative to score</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Footer */}
        <div className="border-t border-gray-800 pt-8 mt-12 text-center">
          <p className="text-gray-500 text-sm">
            SwarmChain Protocol v1.0
          </p>
          <p className="text-gray-600 text-xs mt-2">
            Anchored on Hedera Hashgraph. Verified by elimination. Valued by convergence.
          </p>
        </div>
      </article>
    </div>
  );
}
