import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { BookingService, TicketBooked } from './services/booking.service';

type TicketStatus = 'active' | 'used' | 'cancelled';

interface TicketItem {
  id: number;
  ticketId: string;
  code: string;
  status: TicketStatus;
  eventTitle: string;
  dateTimeLabel: string;
  locationLabel: string;
  quantity: number;
  purchaseDateLabel: string;
  chainHash: string;
  qrToken: string;
  qrDataUrl: string;
}

@Component({
  selector: 'app-booking',
  templateUrl: './booking.page.html',
  styleUrls: ['./booking.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule],
})
export class BookingPage {
  private bookingService = inject(BookingService);

  segment: TicketStatus = 'active';
  loading = false;
  loadError = '';
  private readonly fallbackQrSvgDataUrl =
    'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220"><rect width="100%" height="100%" fill="%23ffffff"/><rect x="10" y="10" width="200" height="200" fill="%23f8fafc" stroke="%23cbd5e1"/><text x="50%" y="52%" dominant-baseline="middle" text-anchor="middle" fill="%23475569" font-size="12" font-family="Arial">QR unavailable</text></svg>';

  tickets: TicketItem[] = [];

  ionViewWillEnter(): void {
    void this.loadTickets();
  }

  get activeCount(): number {
    return this.tickets.filter((t) => t.status === 'active').length;
  }

  get usedCount(): number {
    return this.tickets.filter((t) => t.status === 'used').length;
  }

  get cancelledCount(): number {
    return this.tickets.filter((t) => t.status === 'cancelled').length;
  }

  get visibleTickets(): TicketItem[] {
    return this.tickets.filter((t) => t.status === this.segment);
  }

  onSegmentChange(ev: any): void {
    const next = (ev?.detail?.value ?? '') as TicketStatus;
    if (next === 'active' || next === 'used' || next === 'cancelled') {
      this.segment = next;
    }
  }

  trackByTicket(_: number, t: TicketItem): number {
    return t.id;
  }

  statusLabel(status: TicketStatus): string {
    switch (status) {
      case 'active':
        return 'АКТИВНИЙ';
      case 'used':
        return 'ВИКОРИСТАНО';
      case 'cancelled':
        return 'СКАСОВАНО';
      default:
        return 'СТАН';
    }
  }

  private async loadTickets(): Promise<void> {
    this.loading = true;
    this.loadError = '';
    try {
      const response = await firstValueFrom(this.bookingService.getMyTickets());
      const mapped = (response.items ?? []).map((ticket) => this.mapTicket(ticket));
      this.tickets = mapped.length ? mapped : [this.createDefaultTicket()];
    } catch {
      this.tickets = [this.createDefaultTicket()];
      this.loadError = '';
    } finally {
      this.loading = false;
    }
  }

  private mapTicket(ticket: TicketBooked): TicketItem {
    return {
      id: ticket.id,
      ticketId: ticket.ticket_id,
      code: ticket.code,
      status: this.mapStatus(ticket),
      eventTitle: (ticket.event_name ?? '').trim() || `Подія #${ticket.event_id}`,
      dateTimeLabel: this.formatEventDate(ticket.event_start_date),
      locationLabel:
        (ticket.event_location ?? '').trim() ||
        (ticket.event_city ?? '').trim() ||
        'Локація уточнюється',
      quantity: Number(ticket.quantity) || 1,
      purchaseDateLabel: this.formatPurchaseDate(ticket.created_at),
      chainHash: ticket.ticket_hash,
      qrToken: (ticket.qr_token ?? '').trim(),
      qrDataUrl: this.generateQrDataUrl({
        qrToken: (ticket.qr_token ?? '').trim(),
      }),
    };
  }

  private mapStatus(ticket: TicketBooked): TicketStatus {
    if (ticket.used) return 'used';
    const status = (ticket.status ?? '').toLowerCase();
    if (status === 'failed' || status === 'failed_onchain' || status === 'cancelled') return 'cancelled';
    return 'active';
  }

  private formatEventDate(value?: string): string {
    const parsed = this.parseDate(value);
    if (!parsed) return 'Дата уточнюється';
    const date = new Intl.DateTimeFormat('uk-UA', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(parsed);
    return date;
  }

  private formatPurchaseDate(value?: string): string {
    const parsed = this.parseDate(value);
    if (!parsed) return '—';
    return new Intl.DateTimeFormat('uk-UA', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    }).format(parsed);
  }

  private parseDate(value?: string): Date | null {
    const raw = (value ?? '').trim();
    if (!raw) return null;
    const candidate = raw.includes(' ') ? raw.replace(' ', 'T') : raw;
    const parsed = new Date(candidate);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  private generateQrDataUrl(ticket: Pick<TicketItem, 'qrToken'>): string {
    const qrToken = (ticket.qrToken ?? '').trim();
    if (!qrToken) return this.fallbackQrSvgDataUrl;
    return `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(qrToken)}`;
  }

  private createDefaultTicket(): TicketItem {
    const testHash =
      '0x7f9fade1c0d57a7af66ab4ead79fade1c0d57a7af66ab4ead79f111122223333';
    return {
      id: 0,
      ticketId: 'TEST-TICKET-001',
      code: 'TKT-TEST-001',
      status: 'active',
      eventTitle: 'Тестова подія',
      dateTimeLabel: '20 квітня 2026, 18:30',
      locationLabel: 'Тестова локація',
      quantity: 1,
      purchaseDateLabel: '17 квітня 2026',
      chainHash: testHash,
      qrToken: '',
      qrDataUrl: this.generateQrDataUrl({
        qrToken: '',
      }),
    };
  }
}

