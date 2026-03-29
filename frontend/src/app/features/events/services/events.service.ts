import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { environment } from 'src/environments/environment';
import {
  EventCreateRequest,
  EventInterface,
  EventMember,
  EventMembersUpsertRequest,
  EventMembersUpsertResponse,
  EventsApiResponse,
  EventsParams,
} from '../interfaces/events.interface';

@Injectable({
  providedIn: 'root',
})
export class EventsService {
  private http = inject(HttpClient);

  getEvents(params: EventsParams): Observable<EventsApiResponse> {
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
}
