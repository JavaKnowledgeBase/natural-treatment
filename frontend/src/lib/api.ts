const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8080";

export type CachedItem = {
  id: string;
  label: string;
  source: string;
  category?: string | null;
  confidence?: number;
  ts: number;
};

export type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  ts: number;
};

export type Suggestion = { id?: string; label: string; category?: string };

export type Recommendation = {
  herb_id: string;
  herb_name: string;
  score: number;
  confidence_band: string;
  reason: string;
  evidence_level: string;
  safety_note?: string | null;
  curation_status: string;
};

export type HerbDetail = {
  history: string;
  features: string;
  pros: string[];
  cons: string[];
  references: { title: string; url: string }[];
};

export type SessionState = {
  meta: { session_id: string; current_step: string };
  chat: ChatMessage[];
  symptoms: CachedItem[];
  causes: CachedItem[];
  recommendations: Recommendation[];
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${GATEWAY_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`${resp.status}: ${body}`);
  }
  return resp.json();
}

export const api = {
  createSession: (language?: string) =>
    request<{ session_id: string; greeting: string }>("/session", {
      method: "POST",
      body: JSON.stringify({ language }),
    }),

  getState: (sid: string) => request<SessionState>(`/session/${sid}`),

  sendMessage: (sid: string, text: string) =>
    request<{
      assistant_message: string;
      current_step: string;
      symptoms: CachedItem[];
      causes: CachedItem[];
      suggestions: Suggestion[];
    }>(`/session/${sid}/message`, { method: "POST", body: JSON.stringify({ text }) }),

  addItem: (sid: string, kind: "symptom" | "cause", label: string, id?: string, category?: string) =>
    request<{ status: string; id: string }>(`/session/${sid}/add-item`, {
      method: "POST",
      body: JSON.stringify({ kind, id, label, category }),
    }),

  removeItem: (sid: string, kind: "symptom" | "cause", id: string) =>
    request<{ status: string }>(`/session/${sid}/remove-item`, {
      method: "POST",
      body: JSON.stringify({ kind, id }),
    }),

  advanceToCauses: (sid: string) =>
    request<{ current_step: string; assistant_message: string }>(`/session/${sid}/advance-to-causes`, {
      method: "POST",
    }),

  analyze: (sid: string) =>
    request<{ current_step: string; reasoning: string | null; recommendations: Recommendation[] }>(
      `/session/${sid}/analyze`,
      { method: "POST" }
    ),

  requestEmail: (sid: string, to: string) =>
    request<{ verification_token: string; mock_mode: boolean }>(`/session/${sid}/email/request`, {
      method: "POST",
      body: JSON.stringify({ to }),
    }),

  confirmEmail: (sid: string, verification_token: string, code: string) =>
    request<{ email: { status: string }; purged_keys: number }>(`/session/${sid}/email/confirm`, {
      method: "POST",
      body: JSON.stringify({ verification_token, code }),
    }),

  endSession: (sid: string) =>
    request<{ status: string; purged_keys: number }>(`/session/${sid}/end`, { method: "POST" }),

  contact: (herb_name: string, email: string, message: string, name?: string) =>
    request<{ status: string; id: string | null }>("/contact", {
      method: "POST",
      body: JSON.stringify({ herb_name, email, message, name }),
    }),

  getHerbDetail: (herbId: string, language: string) =>
    request<HerbDetail>(`/herbs/${herbId}/detail?language=${language}`),
};
