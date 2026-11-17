import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';

import { environment } from 'src/environments/environment';
import { ChatError, ChatReply, ChatResponse } from '../interfaces/chat.interface';

export const CHAT_MESSAGE_MAX_LENGTH = 500;

@Injectable({ providedIn: 'root' })
export class ChatService {
  private http = inject(HttpClient);

  /** One question in, one answer out (the backend keeps no conversation). */
  send(message: string): Observable<ChatReply> {
    return this.http
      .post<ChatResponse>(`${environment.apiBaseUrl}/chat/messages`, { message }, { observe: 'response' })
      .pipe(
        map((res) => ({
          response: res.body as ChatResponse,
          limit: this.numberHeader(res.headers.get('X-RateLimit-Limit')),
          remaining: this.numberHeader(res.headers.get('X-RateLimit-Remaining')),
        })),
        catchError((err: HttpErrorResponse) => throwError(() => this.toChatError(err))),
      );
  }

  /** Wakes a sleeping backend (free hosting) before the first question; the result is ignored. */
  warmUp(): void {
    this.http.get(`${environment.apiBaseUrl}/health`).subscribe({ error: () => undefined });
  }

  private toChatError(err: HttpErrorResponse): ChatError {
    const detail = err.error?.detail;
    if (err.status === 429) {
      const retry = Number(detail?.retry_after_seconds ?? err.headers?.get('Retry-After'));
      return {
        kind: 'rate_limited',
        message: detail?.message ?? 'Забагато запитів до чат-бота.',
        retryAfterSeconds: Number.isFinite(retry) && retry > 0 ? retry : undefined,
      };
    }
    if (err.status === 503) {
      return {
        kind: 'unavailable',
        message: detail?.message ?? 'Чат-бот тимчасово недоступний.',
      };
    }
    if (err.status === 422) {
      return { kind: 'invalid', message: 'Запит має бути від 1 до 500 символів.' };
    }
    return { kind: 'network', message: 'Не вдалося зв’язатися із сервером.' };
  }

  private numberHeader(value: string | null): number | null {
    if (value === null || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
}
