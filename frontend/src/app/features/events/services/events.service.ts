import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { environment } from 'src/environments/environment';
import {
  EventCreateRequest,
  EventInterface,
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
}
