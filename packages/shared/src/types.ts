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
  brand_name?: string;
  brand_logo_url?: string;
  brand_color?: string;
  brand_tagline?: string;
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

export interface RecipeInput {
  key: string;
  type: "document" | "text" | "email" | "choice";
  label: string;
  required?: boolean;
  options?: string[];
}

export interface Recipe {
  id: string;
  category: string;
  name: string;
  icon: string;
  description: string;
  inputs: RecipeInput[];
  connections: { provider: string; label: string }[];
  approval: "draft" | "connection";
  approve_label: string;
}

export interface RecipeConnection {
  id: string;
  provider: string;
  label?: string;
  identifier: string;
  status: "pending" | "approved" | "revoked";
}

export interface RecipeRun {
  id: string;
  recipe_id: string;
  recipe_name: string;
  status: "draft" | "needs_connection" | "completed" | "failed";
  approval: string;
  approve_label: string;
  inputs: Record<string, unknown>;
  draft: Record<string, unknown> & {
    summary?: string;
    contenido?: string;
    route?: string;
    campos?: { requisito: string; respuesta_sugerida: string }[];
  };
  result: (Record<string, unknown> & { message?: string; documento?: string }) | null;
  connections: RecipeConnection[];
}

export interface Eje {
  id: string;
  label: string;
  count: number;
}

export interface Procedure {
  id: string;
  title: string;
  problem: string;
  eje: string;
  eje_label: string;
  category: string;
  suggested_recipe: string;
  scope: string;
}

export interface AppProject {
  id: string;
  name: string;
  description: string;
  spec: string;
  status: "draft" | "built" | "pending_payment" | "deployed";
  paid: boolean;
  deploy_url: string | null;
}

export interface UsageSummary {
  total_messages: number;
  total_tokens: number;
  total_cost: number;
  by_route: Record<string, number>;
  by_agent: Record<string, number>;
}
