import { Observable, firstValueFrom } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { inject, Injectable, NgZone } from '@angular/core';
import { environment } from 'src/environments/environment';
import { TokenStorageService } from 'src/app/core/token-storage.service';
import {
  EventCreateRequest,
  EventInterface,
  EventMember,
  EventMembersUpsertRequest,
  EventMembersUpsertResponse,
  EventsApiResponse,
  EventsParams,
  OrganizerStatsResponse,
} from '../interfaces/events.interface';

@Injectable({
  providedIn: 'root',
})
export class EventsService {
  private http = inject(HttpClient);
  private tokenStorage = inject(TokenStorageService);
  private ngZone = inject(NgZone);

  getEvents(params: EventsParams): Observable<EventsApiResponse> {
    if ((params.city ?? '').trim()) {
      return this.streamCityEvents(params);
    }

    return this.http.get<EventsApiResponse>(
      `${environment.apiBaseUrl}/events/all`,
      {
        params: {
          ...params,
          skip: params.skip ?? 0,
          limit: params.limit ?? 20,
        },
      },
    );
  }

  private streamCityEvents(params: EventsParams): Observable<EventsApiResponse> {
    return new Observable<EventsApiResponse>((subscriber) => {
      const abortController = new AbortController();
      let isCancelled = false;

      const run = async () => {
        try {
          const token = await firstValueFrom(this.tokenStorage.getToken$());
          const query = this.buildQueryString({
            ...params,
            skip: params.skip ?? 0,
            limit: params.limit ?? 20,
          });

          const response = await fetch(
            `${environment.apiBaseUrl}/events/all?${query}`,
            {
              method: 'GET',
              headers: {
                Accept: 'application/x-ndjson',
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
              },
              signal: abortController.signal,
            },
          );

          if (!response.ok) {
            throw new Error(`Failed to load events (${response.status})`);
          }
          if (!response.body) {
            throw new Error('Streaming is not supported in this environment');
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          while (!isCancelled) {
            const { done, value } = await reader.read();
            if (done) {
              break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() ?? '';

            for (const rawLine of lines) {
              const line = rawLine.trim();
              if (!line) {
                continue;
              }

              const payload = JSON.parse(line) as {
                items?: EventsApiResponse['items'];
                total?: number;
                error?: string;
                done?: boolean;
              };

              if (payload.error) {
                throw new Error(payload.error);
              }

              const items = payload.items;
              if (items) {
                this.ngZone.run(() => {
                  subscriber.next({
                    items,
                    total: payload.total ?? items.length,
                    done: payload.done ?? false,
                  });
                });
              }

              if (payload.done) {
                this.ngZone.run(() => {
                  subscriber.complete();
                });
                return;
              }
            }
          }

          if (!isCancelled) {
            this.ngZone.run(() => {
              subscriber.complete();
            });
          }
        } catch (error) {
          if (!isCancelled) {
            this.ngZone.run(() => {
              subscriber.error(error);
            });
          }
        }
      };

      void run();

      return () => {
        isCancelled = true;
        abortController.abort();
      };
    });
  }

  private buildQueryString(params: EventsParams): string {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === '') {
        continue;
      }
      query.set(key, String(value));
    }
    return query.toString();
  }

  getEvent(id: number): Observable<EventInterface> {
    return this.http.get<EventInterface>(
      `${environment.apiBaseUrl}/events/${id}`,
    );
  }

  getEventByUid(uid: string): Observable<EventInterface> {
    return this.http.get<EventInterface>(
      `${environment.apiBaseUrl}/events/lookup/${encodeURIComponent(uid)}`,
    );
  }

  getPopularEvents(limit: number = 12): Observable<EventsApiResponse> {
    return this.http.get<EventsApiResponse>(
      `${environment.apiBaseUrl}/events/popular`,
      {
        params: { limit },
      },
    );
  }

  createEvent(
    data: EventCreateRequest,
    imageFile?: File,
  ): Observable<EventInterface> {
    const formData = new FormData();

    Object.keys(data).forEach((key) => {
      const value = (data as any)[key];
      if (value !== undefined && value !== null) {
        formData.append(key, value.toString());
      }
    });

    // Append the file if it exists
    if (imageFile) {
      formData.append('image', imageFile);
    }

    // Pass formData as the body
    return this.http.post<EventInterface>(
      `${environment.apiBaseUrl}/events`,
      formData,
    );
  }

  updateEvent(
    id: number,
    params: EventCreateRequest,
  ): Observable<EventInterface> {
    return this.http.put<EventInterface>(
      `${environment.apiBaseUrl}/events/${id}`,
      params,
    );
  }

  updateEventImage(id: number, imageFile: File): Observable<EventInterface> {
    const formData = new FormData();
    formData.append('image', imageFile);
    return this.http.put<EventInterface>(
      `${environment.apiBaseUrl}/events/${id}/image`,
      formData,
    );
  }

  deleteEvent(id: number): Observable<void> {
    return this.http.delete<void>(`${environment.apiBaseUrl}/events/${id}`);
  }

  getCities(): Observable<string[]> {
    return this.http.get<string[]>(`${environment.apiBaseUrl}/cities`);
  }

  getFavoriteEvents(params: EventsParams): Observable<EventsApiResponse> {
    return this.http.get<EventsApiResponse>(
      `${environment.apiBaseUrl}/events/me/favorites`,
      {
        params: {
          ...params,
          skip: params.skip ?? 0,
          limit: params.limit ?? 20,
        },
      },
    );
  }

  addFavoriteEvent(id: string): Observable<EventInterface> {
    return this.http.post<EventInterface>(
      `${environment.apiBaseUrl}/events/me/favorites/${id}`,
      {},
    );
  }

  deleteFavoriteEvent(id: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBaseUrl}/events/me/favorites/${id}`,
    );
  }

  getAssignedEvents(params: EventsParams): Observable<EventsApiResponse> {
    return this.http.get<EventsApiResponse>(
      `${environment.apiBaseUrl}/events/me/assigned`,
      {
        params: {
          ...params,
          skip: params.skip ?? 0,
          limit: params.limit ?? 20,
        },
      },
    );
  }

  addEventMembers(
    uid: string,
    payload: EventMembersUpsertRequest,
  ): Observable<EventMembersUpsertResponse> {
    return this.http.post<EventMembersUpsertResponse>(
      `${environment.apiBaseUrl}/events/${encodeURIComponent(uid)}/members`,
      payload,
    );
  }

  getEventMembers(uid: string): Observable<EventMember[]> {
    return this.http.get<EventMember[]>(
      `${environment.apiBaseUrl}/events/${encodeURIComponent(uid)}/members`,
    );
  }

  deleteEventMember(uid: string, memberUserId: number): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBaseUrl}/events/${encodeURIComponent(uid)}/members/${memberUserId}`,
    );
  }

  getOrganizerStats(): Observable<OrganizerStatsResponse> {
    return this.http.get<OrganizerStatsResponse>(
      `${environment.apiBaseUrl}/events/me/stats`,
    );
  }
}
