import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { PopularEventItem } from '../../interfaces/events/events.interface';

@Component({
  selector: 'app-event-card',
  templateUrl: './event-card.component.html',
  styleUrls: ['./event-card.component.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule]
})
export class EventCardComponent  implements OnInit {

  @Input() item!: PopularEventItem;

  constructor(private router: Router) { }

  ngOnInit() {}

  getThemeLabel(theme: PopularEventItem['theme']): string {
    switch (theme) {
      case 'art':
        return 'Мистецтво';
      case 'games':
        return 'Ігри';
      case 'cinema':
        return 'Кіно';
      default:
        return 'Подія';
    }
  }

  getTagLabel(item: PopularEventItem): string {
    if (item.tag?.trim()) return item.tag.trim();
    const theme = this.getThemeLabel(item.theme);
    return theme.toLowerCase();
  }

  formatPrice(price: PopularEventItem['price']): string | null {
    if (price === null || price === undefined) return null;
    const v = Number(price);
    if (!Number.isFinite(v) || v <= 0) return 'Безкоштовно';
    return `₴${Math.round(v)}`;
  }

  getCoverBackground(item: PopularEventItem): string {
    const img = (item.imageUrl?.trim() || 'assets/shapes.svg').replace(/"/g, '\\"');
    return `linear-gradient(180deg, rgba(15, 23, 42, 0.05), rgba(15, 23, 42, 0.45)), url("${img}")`;
  }

  openEvent(item: PopularEventItem): void {
    this.router.navigate(['/tabs/explore', encodeURIComponent(item.uid)], {
      state: {
        item: {
          ...item,
          image: item.imageUrl?.trim() || 'assets/shapes.svg',
        } as any,
      },
    });
  }
}
