/** Mirrors the backend schema of POST /chat/messages (backend/app/schemas/chat.py). */
export type ChatStatus = 'found' | 'not_found' | 'not_understood' | 'refused';

export interface ChatEvent {
  id: number;
  uid: string;
  name: string;
  type?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  city?: string | null;
  location_name?: string | null;
  price_low?: string | null;
  price_high?: string | null;
  price_currency?: string | null;
  image?: string | null;
  url?: string | null;
  order_url?: string | null;
  source?: string | null;
}

export interface ChatResponse {
  status: ChatStatus;
  reply: string;
  events: ChatEvent[];
  suggestions: string[];
  degraded: boolean;
}

/** A successful answer plus the rate-limit headers the backend sends with it. */
export interface ChatReply {
  response: ChatResponse;
  limit: number | null;
  remaining: number | null;
}

export type ChatErrorKind = 'rate_limited' | 'unavailable' | 'network' | 'invalid';

export interface ChatError {
  kind: ChatErrorKind;
  message: string;
  /** Only for `rate_limited`: seconds until the window frees up. */
  retryAfterSeconds?: number;
}

export type ChatRole = 'user' | 'bot';

/** One entry of the conversation shown in the widget. */
export interface ChatMessage {
  id: number;
  role: ChatRole;
  text: string;
  events?: ChatEvent[];
  hints?: string[];
  tone?: 'normal' | 'error';
  /** Button shown under an error: go to the regular event search, or ask the same question again. */
  action?: 'events' | 'retry';
}
