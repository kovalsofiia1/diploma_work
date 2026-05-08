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
  seat_id?: string;
  attendee_name?: string;
  price_amount?: number;
  price_currency?: string;
  ticket_hash: string;
  blockchain_tx_hash?: string;
  status: string;
  used?: boolean;
  created_at?: string;
  event_name?: string;
  event_start_date?: string;
  event_location?: string;
  event_city?: string;
  qr_token?: string;
}

interface BookBatchPayload {
  event_id: number;
  attendee_names?: string[];
  items?: Array<{
    attendee_name: string;
    seat_id?: string;
    seat_label?: string;
  }>;
}

interface BookBatchResponse {
  tickets: TicketBooked[];
}

interface MyTicketsResponse {
  items: TicketBooked[];
}

interface OccupiedSeatsResponse {
  seat_ids: string[];
}

export interface VerifyTicketResponse {
  status: 'VALID' | 'INVALID' | string;
  reason?: string;
  ticket?: TicketBooked;
}

export interface CheckinResponse {
  status: 'ok' | string;
}

@Injectable({
  providedIn: 'root',
})
export class BookingService {
  private http = inject(HttpClient);

  bookTickets(
    eventId: number,
    attendeeNames: string[],
    seatItems?: Array<{ attendee_name: string; seat_id?: string; seat_label?: string }>,
  ): Observable<BookBatchResponse> {
    const payload: BookBatchPayload = {
      event_id: eventId,
      attendee_names: attendeeNames,
      ...(seatItems?.length ? { items: seatItems } : {}),
    };
    return this.http.post<BookBatchResponse>(
      `${environment.apiBaseUrl}/tickets/book/batch`,
      payload,
    );
  }

  getMyTickets(): Observable<MyTicketsResponse> {
    return this.http.get<MyTicketsResponse>(`${environment.apiBaseUrl}/tickets/me`);
  }

  cancelMyTicket(ticketId: number): Observable<void> {
    return this.http.delete<void>(`${environment.apiBaseUrl}/tickets/me/${ticketId}`);
  }

  getOccupiedSeats(eventId: number): Observable<OccupiedSeatsResponse> {
    return this.http.get<OccupiedSeatsResponse>(
      `${environment.apiBaseUrl}/tickets/events/${eventId}/occupied-seats`,
    );
  }

  verifyTicket(qrToken: string): Observable<VerifyTicketResponse> {
    return this.http.post<VerifyTicketResponse>(`${environment.apiBaseUrl}/tickets/verify`, {
      qr_token: qrToken,
    });
  }

  checkinTicket(qrToken: string): Observable<CheckinResponse> {
    return this.http.post<CheckinResponse>(`${environment.apiBaseUrl}/checkin`, {
      qr_token: qrToken,
    });
  }
}

