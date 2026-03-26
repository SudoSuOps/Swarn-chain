// In production (IPFS via swarmchain.eth.limo), API lives at api.swarmchain.eth.limo
// In dev, Vite proxies /api to localhost:8000
const BASE = import.meta.env.VITE_API_URL || "/api";

async function request<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText} — ${path}`);
  }
  return res.json();
}

// ─── Block types ───────────────────────────────────────────────

export interface Block {
  block_id: string;
  task_id: string;
  domain: string;
  status: "open" | "solved" | "exhausted";
  reward_pool: number;
  max_attempts: number;
  time_limit_sec: number;
  start_time: string;
  end_time: string | null;
  total_energy: number;
  attempt_count: number;
  winning_attempt_id: string | null;
  winning_node_id: string | null;
  final_score: number | null;
  elimination_summary: Record<string, unknown> | null;
  task_payload: TaskPayload | null;
  metadata: Record<string, unknown> | null;
}

export interface TaskPayload {
  input_grid?: number[][];
  expected_output?: number[][];
  description?: string;
  [key: string]: unknown;
}

export interface Attempt {
  attempt_id: string;
  block_id: string;
  node_id: string;
  parent_attempt_id: string | null;
  method: string;
  strategy_family: string;
  output_json: Record<string, unknown>;
  score: number;
  valid: boolean;
  energy_cost: number;
  latency_ms: number;
  promoted: boolean;
  pruned: boolean;
  created_at: string;
  metadata: Record<string, unknown> | null;
}

export interface Reward {
  block_id: string;
  node_id: string;
  reward_type: string;
  reward_amount: number;
  score_basis: number;
  created_at: string;
}

export interface RewardSummary {
  block_id: string;
  total_pool: number;
  solver_pool: number;
  lineage_pool: number;
  exploration_pool: number;
  efficiency_pool: number;
  rewards: Reward[];
}

export interface LineageEdge {
  parent: string;
  child: string;
  delta_score: number;
}

export interface BlockArtifact {
  artifact_type: string;
  artifact_json: Record<string, unknown>;
  created_at: string;
}

// ─── Node types ────────────────────────────────────────────────

export interface Node {
  node_id: string;
  node_type: string;
  hardware_class: string;
  active: boolean;
  reputation_score: number;
  total_energy_used: number;
  total_attempts: number;
  total_solves: number;
  total_rewards: number;
  registered_at: string;
  metadata: Record<string, unknown> | null;
}

export interface NodeStats {
  node_id: string;
  total_attempts: number;
  total_solves: number;
  total_rewards: number;
  total_energy_used: number;
  avg_score: number;
  efficiency: number;
  blocks_participated: number;
}

// ─── System types ──────────────────────────────────────────────

export interface Metrics {
  blocks: {
    total: number;
    open: number;
    solved: number;
    exhausted: number;
  };
  attempts: { total: number };
  nodes: { total: number; active: number };
  total_energy: number;
}

export interface Health {
  status: string;
  service: string;
}

// ─── Validator types ──────────────────────────────────────────

export interface ValidatorDecision {
  validator_name: string;
  domain: string;
  confidence: number;
  verdict: "approved" | "flagged" | "rejected" | "needs_review" | "error";
  critique: string | null;
  flags: string[];
  repair_suggestion: string | null;
  objective_score: number;
  objective_overridden: boolean;
  raw_output: Record<string, unknown>;
  created_at: string;
}

export interface BlockValidations {
  block_id: string;
  domain: string;
  has_validator: boolean;
  decisions: ValidatorDecision[];
}

// ─── Block endpoints ───────────────────────────────────────────

export async function fetchBlocks(status?: string): Promise<Block[]> {
  const qs = status && status !== "all" ? `?status=${status}` : "";
  const data = await request<{ blocks: Block[]; total: number }>(`/blocks${qs}`);
  return data.blocks;
}

export function fetchBlock(id: string): Promise<Block> {
  return request<Block>(`/blocks/${id}`);
}

export async function fetchBlockAttempts(id: string): Promise<Attempt[]> {
  const data = await request<{ attempts: Attempt[]; total: number }>(`/attempts/block/${id}`);
  return data.attempts;
}

export async function fetchTopAttempts(id: string): Promise<Attempt[]> {
  const data = await request<{ attempts: Attempt[]; total: number }>(`/attempts/block/${id}/top`);
  return data.attempts;
}

export function fetchBlockRewards(id: string): Promise<RewardSummary> {
  return request<RewardSummary>(`/blocks/${id}/rewards`);
}

export function fetchBlockArtifacts(id: string): Promise<BlockArtifact[]> {
  return request<BlockArtifact[]>(`/blocks/${id}/artifacts`);
}

export async function fetchBlockLineage(id: string): Promise<LineageEdge[]> {
  const data = await request<{ block_id: string; edges: LineageEdge[] }>(`/attempts/block/${id}/lineage`);
  return data.edges;
}

// ─── Node endpoints ────────────────────────────────────────────

export function fetchNodes(): Promise<Node[]> {
  return request<Node[]>(`/nodes`);
}

export function fetchNode(id: string): Promise<Node> {
  return request<Node>(`/nodes/${id}`);
}

export function fetchNodeStats(id: string): Promise<NodeStats> {
  return request<NodeStats>(`/nodes/${id}/stats`);
}

// ─── Validator endpoints ──────────────────────────────────────

export function fetchBlockValidations(id: string): Promise<BlockValidations> {
  return request<BlockValidations>(`/blocks/${id}/validations`);
}

export function fetchValidators(): Promise<{ validators: { domain: string; name: string }[] }> {
  return request(`/validators`);
}

// ─── System endpoints ──────────────────────────────────────────

export function fetchMetrics(): Promise<Metrics> {
  return request<Metrics>(`/metrics`);
}

export function fetchHealth(): Promise<Health> {
  return request<Health>(`/health`);
}
