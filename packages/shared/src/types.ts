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
  country?: string;
  country_name?: string;
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
  area: string;
  category: string;
  category_label: string;
  sensitivity: Sensitivity;
  pii_score: number;
  pii_types: string[];
  indexed: boolean;
  created_at: string;
}

export interface NotebookSource {
  id: string;
  filename: string;
  area: string;
  sensitivity: Sensitivity;
}

export interface Notebook {
  id: string;
  name: string;
  document_ids: string[];
  sources: NotebookSource[];
  created_at: string;
}

export interface NotebookAnswer {
  content: string;
  route: string;
  citations: { filename: string; text: string; score: number; sensitivity: string }[];
  empty?: boolean;
  message?: string;
  blocked?: boolean;
}

export interface FlowNode {
  id: string;
  type: "start" | "step" | "decision" | "end" | "danger";
  title: string;
  detail?: string;
  next?: string;
  branches?: { label: string; to: string }[];
}

export interface FlowchartSummary {
  id: string;
  title: string;
  description: string;
}

export interface Flowchart extends FlowchartSummary {
  note?: string;
  start: string;
  nodes: FlowNode[];
}

export interface DocumentCategory {
  id: string;
  key: string;
  label: string;
  description: string;
  system: boolean;
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
  request_id?: string;
  event_metadata?: string;
}

export interface RecipeInput {
  key: string;
  type: "document" | "text" | "email" | "mailbox" | "choice" | "textarea" | "number" | "date" | "area" | "region";
  label: string;
  required?: boolean;
  options?: string[];
  placeholder?: string;
  help?: string;
}

export interface CompanyArea {
  name: string;
  responsible: string;
  email: string;
}

export interface CompanyProfile {
  industry: string;
  company_size: string;
  description: string;
  audience: string;
  value_prop: string;
  goals: string;
  tone: string;
  website: string;
  areas: CompanyArea[];
  tech_stack: string[];
  completed: boolean;
  completion: number;
  missing_required?: string[];
  required_complete?: boolean;
  company_name?: string;
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
  rag_category?: string;
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
