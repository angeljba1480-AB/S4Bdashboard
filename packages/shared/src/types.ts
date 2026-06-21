// Shared domain types for the Private AI Platform (web + future packages).

export type Sensitivity = "public" | "internal" | "confidential" | "restricted";
export type ModelRoute = "local" | "vpc" | "open" | "premium" | "blocked";
export type Role = "super_admin" | "admin" | "user" | "security" | "devops";

export interface Me {
  id: string;
  email: string;
  name: string;
  role: Role;
  tenant_id: string;
  tenant_name: string;
  mfa_enabled: boolean;
}

export interface Agent {
  id: string;
  name: string;
  type: string;
  area: string;
  privacy_mode: string;
  requires_premium_reasoning: boolean;
  status: string;
}

export interface DocumentItem {
  id: string;
  filename: string;
  mime_type: string;
  sensitivity: Sensitivity;
  pii_score: number;
  pii_types: string[];
  indexed: boolean;
  created_at: string;
}

export interface Citation {
  document_id: string;
  filename: string;
  chunk_index: number;
  text: string;
  score: number;
  sensitivity: Sensitivity;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  content: string;
  route: ModelRoute;
  model_used: string;
  classification: Sensitivity;
  pii_types: string[];
  pii_score: number;
  redacted: boolean;
  blocked: boolean;
  reason: string;
  token_count: number;
  cost_estimate: number;
  citations: Citation[];
}

export interface AuditEvent {
  id: string;
  event_type: string;
  object_type: string;
  object_id: string;
  classification: Sensitivity | null;
  selected_route: ModelRoute | null;
  selected_model: string;
  risk_level: string;
  token_count: number;
  cost_estimate: number;
  reason: string;
  user_id: string | null;
  created_at: string;
}

export interface UsageSummary {
  total_messages: number;
  total_tokens: number;
  total_cost: number;
  by_route: Record<string, number>;
  by_agent: Record<string, number>;
}
