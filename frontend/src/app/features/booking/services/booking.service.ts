import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from 'src/environments/environment';

export interface TicketBooked {
  id: number;
  ticket_id: string;
  code: string;
  event_id: number;
  user_id: number;
  quantity: number;
  seat?: string;
  ticket_hash: string;
  blockchain_tx_hash?: string;
  status: string;
  used?: boolean;
  created_at?: string;
  event_name?: string;
  event_start_date?: string;
  event_location?: string;
  event_city?: string;
}

interface BookBatchPayload {
  event_id: number;
  attendee_names: string[];
}

interface BookBatchResponse {
  tickets: TicketBooked[];
}

interface MyTicketsResponse {
  items: TicketBooked[];
}

@Injectable({
  providedIn: 'root',
})
export class BookingService {
  private http = inject(HttpClient);

  bookTickets(eventId: number, attendeeNames: string[]): Observable<BookBatchResponse> {
    const payload: BookBatchPayload = {
      event_id: eventId,
      attendee_names: attendeeNames,
    };
    return this.http.post<BookBatchResponse>(
      `${environment.apiBaseUrl}/tickets/book/batch`,
      payload,
    );
  }

  getMyTickets(): Observable<MyTicketsResponse> {
    return this.http.get<MyTicketsResponse>(`${environment.apiBaseUrl}/tickets/me`);
  }
}

