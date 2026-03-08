import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';

type TicketStatus = 'active' | 'used' | 'cancelled';

interface TicketItem {
  id: string;
  status: TicketStatus;
  eventTitle: string;
  dateTimeLabel: string;
  locationLabel: string;
  price: number;
  purchaseDateLabel: string;
  chainHash: string;
}

@Component({
  selector: 'app-booking',
  templateUrl: './booking.page.html',
  styleUrls: ['./booking.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule],
})
export class BookingPage {
  segment: TicketStatus = 'active';

  tickets: TicketItem[] = [
    {
      id: 'TKT-001',
      status: 'active',
      eventTitle: 'Літній музичний фестиваль 2026',
      dateTimeLabel: '15 червня 2026 • 18:00',
      locationLabel: 'Центральний парк',
      price: 75,
      purchaseDateLabel: '1 березня 2026',
      chainHash: '0x7f9fade1c0d57a7af66ab4ead79fade1c0d57a7af66ab4ead79f',
    },
    {
      id: 'TKT-002',
      status: 'active',
      eventTitle: 'Виставка сучасного мистецтва',
      dateTimeLabel: '20 квітня 2026 • 10:00',
      locationLabel: 'Музей сучасного мистецтва',
      price: 25,
      purchaseDateLabel: '10 березня 2026',
      chainHash: '0x33ab12e9f04c6d81a7d133ab12e9f04c6d81a7d133ab12e9f04c',
    },
    {
      id: 'TKT-003',
      status: 'used',
      eventTitle: 'Кінопоказ під відкритим небом',
      dateTimeLabel: '12 липня 2026 • 21:00',
      locationLabel: 'Міський парк',
      price: 0,
      purchaseDateLabel: '1 липня 2026',
      chainHash: '0x9d8c1aef02b44e6c9d8c1aef02b44e6c9d8c1aef02b44e6c',
    },
    {
      id: 'TKT-004',
      status: 'cancelled',
      eventTitle: 'Воркшоп з йоги',
      dateTimeLabel: '15 грудня 2026 • 18:00',
      locationLabel: 'Фітнес-центр "Енергія"',
      price: 120,
      purchaseDateLabel: '2 грудня 2026',
      chainHash: '0xb8a02f8d1ce344b9b8a02f8d1ce344b9b8a02f8d1ce344b9',
    },
  ];

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

  formatPrice(price: number): string {
    const v = Number(price);
    if (!Number.isFinite(v) || v <= 0) return 'Безкоштовно';
    return `₴${Math.round(v)}`;
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
}

