import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { EventInterface } from 'src/app/features/events/interfaces/events.interface';

@Component({
  selector: 'app-event-card',
  templateUrl: './event-card.component.html',
  styleUrls: ['./event-card.component.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule]
})
export class EventCardComponent  implements OnInit {

  @Input() item!: EventInterface;

  constructor(private router: Router) { }

  ngOnInit() {}

  // getThemeLabel(theme: EventInterface['theme']): string {
  //   switch (theme) {
  //     case 'art':
  //       return 'Мистецтво';
  //     case 'games':
  //       return 'Ігри';
  //     case 'cinema':
  //       return 'Кіно';
  //     default:
  //       return 'Подія';
  //   }
  // }

  // getTagLabel(item: EventInterface): string {
  //   if (item.tag?.trim()) return item.tag.trim();
  //   return theme.toLowerCase();
  // }

  formatPrice(price: EventInterface['price_low']): string | null {
    if (price === null || price === undefined) return null;
    const v = Number(price);
    if (!Number.isFinite(v) || v <= 0) return 'Безкоштовно';
    return `₴${Math.round(v)}`;
  }

  formatDate(value: EventInterface['startDate']): string {
    const raw = (value ?? '').toString().trim();
    if (!raw) return 'Дата уточнюється';

    const candidate = raw.includes(' ') ? raw.replace(' ', 'T') : raw;
    const parsed = new Date(candidate);
    if (Number.isNaN(parsed.getTime())) {
      return raw;
    }

    return new Intl.DateTimeFormat('uk-UA', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(parsed);
  }

  getCoverBackground(item: EventInterface): string {
    const img = (item.image?.trim() || 'assets/shapes.svg').replace(/"/g, '\\"');
    return `linear-gradient(180deg, rgba(15, 23, 42, 0.05), rgba(15, 23, 42, 0.45)), url("${img}")`;
  }

  openEvent(item: EventInterface): void {
    // We encode the uid because it might contain characters like ':' (e.g. 'events:painting')
    this.router.navigate(['/tabs/events', encodeURIComponent(item.uid ?? '')], {
      state: {
        item: {
          ...item,
          image: item.image?.trim() || 'assets/shapes.svg',
        } as any,
      },
    });
  }
}
