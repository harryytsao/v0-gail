const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  return res.json();
}

// Types
export interface DashboardStats {
  total_users: number;
  total_conversations: number;
  profiled_users: number;
  scored_users: number;
  total_signals: number;
}

export interface UserListItem {
  user_id: string;
  primary_language: string | null;
  current_arc: string | null;
  temperament_label: string | null;
  temperament_score: number | null;
  total_conversations: number | null;
  updated_at: string | null;
}

export interface UserListResponse {
  users: UserListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface Profile {
  user_id: string;
  temperament: {
    score: number;
    label: string;
    volatility: string;
    summary: string;
  } | null;
  communication_style: {
    formality: number;
    verbosity: number;
    technicality: number;
    structured: number;
    summary: string;
  } | null;
  sentiment_trend: {
    direction: string;
    recent_avg: number;
    frustration_rate: number;
    summary: string;
  } | null;
  life_stage: {
    stage: string;
    confidence: number;
    domain_expertise: string[];
  } | null;
  topic_interests: {
    primary: string[];
    secondary: string[];
  } | null;
  interaction_stats: Record<string, number> | null;
  primary_language: string | null;
  current_arc: string | null;
  profile_version: number;
  created_at: string | null;
  updated_at: string | null;
  scores: Record<
    string,
    { score: number; reasoning: string | null; scored_at: string | null }
  > | null;
}

export interface ScoreResponse {
  dimension: string;
  score: number;
  previous_score: number | null;
  reasoning: string | null;
  scored_at: string | null;
}

export interface ChatResponse {
  response: string;
  conversation_id: string;
  adaptations_applied: string[];
  profile_summary: Record<string, unknown>;
}

export interface AdaptationPreview {
  user_id: string;
  system_prompt_preview: string;
  adaptations: string[];
  profile_summary: Record<string, unknown>;
}

// API functions
export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchAPI<DashboardStats>("/api/profiles/dashboard/stats");
}

export async function getUsers(
  page = 1,
  pageSize = 50,
  search?: string,
  hasProfile?: boolean
): Promise<UserListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (search) params.set("search", search);
  if (hasProfile !== undefined) params.set("has_profile", String(hasProfile));
  return fetchAPI<UserListResponse>(`/api/profiles/?${params}`);
}

export async function getProfile(userId: string): Promise<Profile> {
  return fetchAPI<Profile>(`/api/profiles/${userId}`);
}

export async function getScores(
  userId: string
): Promise<{ user_id: string; scores: ScoreResponse[] }> {
  return fetchAPI(`/api/profiles/${userId}/scores`);
}

export async function sendChat(
  userId: string,
  message: string,
  conversationId?: string
): Promise<ChatResponse> {
  return fetchAPI<ChatResponse>("/api/agent/chat", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      message,
      conversation_id: conversationId,
    }),
  });
}

export async function getAdaptationPreview(
  userId: string
): Promise<AdaptationPreview> {
  return fetchAPI<AdaptationPreview>(`/api/agent/adaptation/${userId}`);
}
