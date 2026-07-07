export type Depth = "quick" | "standard" | "deep" | "deeper";

export interface Source {
  url: string;
  title: string;
  snippet?: string;
  content?: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  confidence?: number;
  timestamp?: number;
}

export interface Conversation {
  id: string;
  query: string;
  depth: Depth;
  messages: Message[];
  sources: Source[];
  createdAt: number;
  updatedAt?: number;
  status: "active" | "done" | "error";
}

export interface ResearchTask {
  research_id: string;
  status: string;
  depth: Depth;
  message: string;
}

export interface ResearchStatus {
  status: string;
  depth: Depth;
  progress: number;
  current_step: string;
  final_answer?: string;
  sources?: Source[];
  confidence_score?: number;
  search_results?: any[];
  error?: string;
}

export interface ResearchResult {
  research_id: string;
  query: string;
  depth: Depth;
  final_answer: string;
  sources: Source[];
  confidence_score: number;
  timestamps: Record<string, number>;
  total_time: number;
}

export const DEPTH_LABELS: Record<Depth, string> = {
  quick: "Quick",
  standard: "Standard",
  deep: "Deep",
  deeper: "Deeper",
};

export const DEPTH_HINTS: Record<Depth, string> = {
  quick: "~4 sources · Fast overview",
  standard: "~15 sources · Balanced depth",
  deep: "~30 sources · Maximum thoroughness",
  deeper: "~100+ sources · Extreme depth",
};

export const PIPELINE_STEPS = [
  "planner",
  "search",
  "extract",
  "reason",
  "synthesize",
] as const;

export type PipelineStep = (typeof PIPELINE_STEPS)[number];

export const STAGE_ORDER: Record<PipelineStep, number> = {
  planner: 0,
  search: 1,
  extract: 2,
  reason: 3,
  synthesize: 4,
};

export interface StatusEvent {
  step: string;
  stage: PipelineStep | "initializing" | "complete";
  message: string;
  progress: number;
  timestamp: number;
}

export const STEP_LABELS: Record<string, PipelineStep> = {
  initializing: "planner",
  planning: "planner",
  planning_complete: "planner",
  query_generation: "search",
  query_generation_complete: "search",
  searching: "search",
  web_search_complete: "search",
  chunking: "extract",
  chunking_complete: "extract",
  ranking: "extract",
  ranking_complete: "extract",
  vector_db: "extract",
  vector_db_complete: "extract",
  reasoning: "reason",
  gap_detection: "reason",
  synthesizing: "synthesize",
  final_answer: "synthesize",
  research_complete: "synthesize",
  complete: "synthesize",
};
