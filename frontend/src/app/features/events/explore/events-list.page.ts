import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { PopularEventItem } from 'src/app/shared/interfaces/events/events.interface';
import { AppHeaderComponent } from 'src/app/shared/components/app-header/app-header.component';
import { EventsListComponent } from 'src/app/shared/components/events-list/events-list.component';

@Component({
  selector: 'app-events-list-page',
  templateUrl: './events-list.page.html',
  styleUrls: ['./events-list.page.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, IonicModule, AppHeaderComponent, EventsListComponent],
})
export class EventsListPage {
  query = '';
  showSavedOnly = false;

  private savedUids = new Set<string>(['events:painting', 'events:openair-cinema']);

  allEvents: PopularEventItem[] = [
    {
      title: 'Літній музичний фестиваль 2026',
      city: 'Центральний парк',
      date: '15 червня 2026 • 18:00',
      uid: 'events:painting',
      description:
        'Відкритий фестиваль з лайнапом локальних артистів, фудкортом і зоною відпочинку.',
      theme: 'games',
      featured: true,
      price: 75,
      availableSeats: 450,
      tag: 'музика',
    },
    {
      title: 'Виставка сучасного мистецтва',
      city: 'Музей сучасного мистецтва',
      date: '20 квітня 2026 • 10:00',
      uid: 'events:boardgames',
      description: 'Нова експозиція сучасних митців, інсталяції та кураторські екскурсії.',
      theme: 'art',
      featured: true,
      price: 25,
      availableSeats: 200,
      tag: 'арт',
    },
    {
      title: 'Кінопоказ під відкритим небом',
      city: 'Міський парк (головна сцена)',
      date: '12 липня 2026 • 21:00',
      uid: 'events:openair-cinema',
      description:
        'Класика кіно під зірками. Візьміть плед і приходьте завчасно — місця обмежені.',
      theme: 'cinema',
      price: 0,
      availableSeats: 120,
      tag: 'кіно',
    },
    {
      title: 'Воркшоп з йоги',
      city: 'Фітнес-центр "Енергія"',
      date: '15 грудня 2026 • 18:00',
      uid: 'events:yoga',
      description:
        'Розпочніть свій день з йоги! Воркшоп підходить для всіх рівнів. Попередня реєстрація обов’язкова.',
      theme: 'art',
      price: 120,
      availableSeats: 50,
      tag: 'здоров’я',
    },
    {
      title: 'Відкриття сезону у парку',
      city: 'Парк "Зелена долина"',
      date: '25 листопада 2026 • 12:00',
      uid: 'events:park-season',
      description: 'Святкуємо відкриття нового сезону в парку з іграми, музикою та частуваннями!',
      theme: 'games',
      price: 0,
      availableSeats: 900,
      tag: 'сім’я',
    },
    {
      title: 'Нічний показ короткометражок',
      city: 'Кінотеатр "Сіті"',
      date: '3 грудня 2026 • 21:00',
      uid: 'events:short-films-night',
      description: 'Добірка сучасних короткометражних фільмів із обговоренням після показу.',
      theme: 'cinema',
      price: 90,
      availableSeats: 80,
      tag: 'кіно',
    },
  ];

  constructor() {}

  get visibleEvents(): PopularEventItem[] {
    const q = this.query.trim().toLowerCase();
    let items = this.allEvents;

    if (this.showSavedOnly) {
      items = items.filter((i) => this.savedUids.has(i.uid));
    }

    if (!q) return items;

    return items.filter((i) => {
      const hay = `${i.title} ${i.city} ${i.description}`.toLowerCase();
      return hay.includes(q);
    });
  }

  toggleSavedOnly(): void {
    this.showSavedOnly = !this.showSavedOnly;
  }
}

