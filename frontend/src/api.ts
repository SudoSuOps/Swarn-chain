const BASE = "/api";

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
  domain: string;
  status: "open" | "solved" | "exhausted";
  attempt_count: number;
  total_energy: number;
  final_score: number | null;
  winning_node_id: string | null;
  task_description: string;
  task_payload: TaskPayload | null;
  created_at: string;
  solved_at: string | null;
  energy_budget: number;
  max_attempts: number;
}

export interface TaskPayload {
  input_grid: number[][];
  output_grid: number[][];
  metadata?: Record<string, unknown>;
}

export interface Attempt {
  attempt_id: string;
  block_id: string;
  node_id: string;
  score: number;
  method: string;
  strategy: string;
  promoted: boolean;
  pruned: boolean;
  energy_cost: number;
  parent_attempt_id: string | null;
  output_grid: number[][] | null;
  created_at: string;
}

export interface Reward {
  node_id: string;
  reward_type: string;
  amount: number;
  score_basis: number;
}

export interface LineageEdge {
  parent_attempt_id: string;
  child_attempt_id: string;
  delta_score: number;
  method: string;
}

export interface BlockArtifact {
  artifact_id: string;
  block_id: string;
  artifact_type: string;
  data: unknown;
  created_at: string;
}

export interface EliminationSummary {
  total_attempts: number;
  pruned: number;
  promoted: number;
  avg_score: number;
  max_score: number;
}

// ─── Node types ────────────────────────────────────────────────

export interface Node {
  node_id: string;
  node_type: string;
  hardware_class: string;
  total_attempts: number;
  total_solves: number;
  total_rewards: number;
  reputation_score: number;
  registered_at: string;
}

export interface NodeStats {
  node_id: string;
  attempts: number;
  solves: number;
  rewards: number;
  efficiency: number;
  blocks_participated: number;
  recent_attempts: Attempt[];
}

// ─── System types ──────────────────────────────────────────────

export interface Metrics {
  total_blocks: number;
  open_blocks: number;
  solved_blocks: number;
  exhausted_blocks: number;
  total_attempts: number;
  total_nodes: number;
  total_energy_spent: number;
}

export interface Health {
  status: string;
  uptime: number;
  version: string;
}

// ─── Block endpoints ───────────────────────────────────────────

export function fetchBlocks(status?: string): Promise<Block[]> {
  const qs = status && status !== "all" ? `?status=${status}` : "";
  return request<Block[]>(`/blocks${qs}`);
}

export function fetchBlock(id: string): Promise<Block> {
  return request<Block>(`/blocks/${id}`);
}

export function fetchBlockAttempts(id: string): Promise<Attempt[]> {
  return request<Attempt[]>(`/blocks/${id}/attempts`);
}

export function fetchTopAttempts(id: string): Promise<Attempt[]> {
  return request<Attempt[]>(`/blocks/${id}/top-attempts`);
}

export function fetchBlockRewards(id: string): Promise<Reward[]> {
  return request<Reward[]>(`/blocks/${id}/rewards`);
}

export function fetchBlockArtifacts(id: string): Promise<BlockArtifact[]> {
  return request<BlockArtifact[]>(`/blocks/${id}/artifacts`);
}

export function fetchBlockLineage(id: string): Promise<LineageEdge[]> {
  return request<LineageEdge[]>(`/blocks/${id}/lineage`);
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

// ─── System endpoints ──────────────────────────────────────────

export function fetchMetrics(): Promise<Metrics> {
  return request<Metrics>(`/metrics`);
}

export function fetchHealth(): Promise<Health> {
  return request<Health>(`/health`);
}
