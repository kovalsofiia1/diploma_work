import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { Router } from '@angular/router';
import { IonicModule } from '@ionic/angular';

import { ChatEvent } from 'src/app/features/chat/interfaces/chat.interface';

const FREE_WORDS = ['безкошт', 'безоплат', 'безплат', 'free', 'вільн'];
const MAX_PRICE_TEXT = 24;

/** Compact event card for chat bubbles. Everything is rendered as text; only http(s) links are offered. */
@Component({
  selector: 'app-chat-event-card',
  templateUrl: './chat-event-card.component.html',
  styleUrls: ['./chat-event-card.component.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule],
})
export class ChatEventCardComponent {
  private router = inject(Router);

  @Input({ required: true }) event!: ChatEvent;
  /** Emitted after navigating to the event page, so the widget can close itself on small screens. */
  @Output() opened = new EventEmitter<void>();

  get dateLabel(): string {
    const raw = (this.event.startDate ?? '').toString().trim();
    if (!raw) return 'Дата уточнюється';

    const parsed = new Date(raw.includes(' ') ? raw.replace(' ', 'T') : raw);
    if (Number.isNaN(parsed.getTime())) return raw;

    return new Intl.DateTimeFormat('uk-UA', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(parsed);
  }

  get place(): string {
    return [this.event.location_name, this.event.city]
      .map((part) => (part ?? '').trim())
      .filter(Boolean)
      .join(', ');
  }

  /** Prices are free text in the data ("400", "400 грн", "від 6200 грн", "безкоштовно"). */
  get priceLabel(): string | null {
    const raw = (this.event.price_low ?? '').toString().trim();
    if (!raw) return null;

    const lowered = raw.toLowerCase();
    if (FREE_WORDS.some((word) => lowered.includes(word))) return 'Безкоштовно';
    if (/^\d+$/.test(raw)) {
      const value = Number(raw);
      return value > 0 ? `₴${value}` : 'Безкоштовно';
    }
    return raw.length > MAX_PRICE_TEXT ? `${raw.slice(0, MAX_PRICE_TEXT)}…` : raw;
  }

  get tags(): string[] {
    return (this.event.type ?? '')
      .split(',')
      .map((label) => label.trim())
      .filter(Boolean)
      .slice(0, 3);
  }

  /** The ticket page when there is one, else the event's site; never anything but http(s). */
  get linkUrl(): string | null {
    return this.safeUrl(this.event.order_url) ?? this.safeUrl(this.event.url);
  }

  get linkLabel(): string {
    return this.safeUrl(this.event.order_url) ? 'Квитки' : 'Сайт';
  }

  open(): void {
    // The uid may contain ':' (e.g. 'external:12'), so it is encoded as the event page expects.
    this.router.navigate(['/tabs/events', encodeURIComponent(this.event.uid ?? '')]);
    this.opened.emit();
  }

  private safeUrl(value: string | null | undefined): string | null {
    const candidate = (value ?? '').trim();
    if (!/^https?:\/\//i.test(candidate)) return null;
    try {
      const url = new URL(candidate);
      return url.protocol === 'http:' || url.protocol === 'https:' ? url.toString() : null;
    } catch {
      return null;
    }
  }
}
