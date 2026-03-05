import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule, ToastController } from '@ionic/angular';
import { Router, RouterModule } from '@angular/router';
import { PopularEventItem } from 'src/app/shared/interfaces/events/events.interface';
import { AppHeaderComponent } from 'src/app/shared/components/app-header/app-header.component';
import { EventsListComponent } from 'src/app/shared/components/events-list/events-list.component';

@Component({
  selector: 'app-events-list-page',
  templateUrl: './events-list.page.html',
  styleUrls: ['./events-list.page.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, IonicModule, RouterModule, AppHeaderComponent, EventsListComponent],
})
export class EventsListPage {
  query = '';
  showSavedOnly = false;

  private savedUids = new Set<string>(['events:painting', 'events:openair-cinema']);

  allEvents: PopularEventItem[] = [
    {
      title: 'Майстер-клас з живопису',
      city: 'Арт-студія "Кольоровий світ"',
      date: '2026-11-15 10:00',
      uid: 'events:painting',
      description:
        'Долучайтеся до майстер-класу з живопису для початківців! Всі матеріали надаються.',
      theme: 'art',
    },
    {
      title: 'Вечір ігрових настільних ігор',
      city: 'Кафе "Гра на грані"',
      date: '2026-11-20 19:00',
      uid: 'events:boardgames',
      description:
        'Запрошуємо всіх любителів настільних ігор! Приєднуйтеся до нашої спільноти та грайте у нові хіти.',
      theme: 'games',
    },
    {
      title: 'Кінопоказ під відкритим небом',
      city: 'Площа перед міським парком',
      date: '2026-11-15 20:30',
      uid: 'events:openair-cinema',
      description:
        'Безкоштовний кінопоказ класичних фільмів під зірками. Візьміть з собою плед!',
      theme: 'cinema',
    },
    {
      title: 'Воркшоп з йоги',
      city: 'Фітнес-центр "Енергія"',
      date: '2026-12-15 18:00',
      uid: 'events:yoga',
      description:
        'Розпочніть свій день з йоги! Воркшоп підходить для всіх рівнів. Попередня реєстрація обов’язкова.',
      theme: 'art',
    },
    {
      title: 'Відкриття сезону у парку',
      city: 'Парк "Зелена долина"',
      date: '2026-11-25 12:00',
      uid: 'events:park-season',
      description:
        'Святкуємо відкриття нового сезону в парку з іграми, музикою та частуваннями!',
      theme: 'games',
    },
    {
      title: 'Нічний показ короткометражок',
      city: 'Кінотеатр "Сіті"',
      date: '2026-12-03 21:00',
      uid: 'events:short-films-night',
      description:
        'Добірка сучасних короткометражних фільмів із обговоренням після показу.',
      theme: 'cinema',
    },
  ];

  constructor(
    private toastCtrl: ToastController,
    private router: Router
  ) {}

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

  async createEvent(): Promise<void> {
    try {
      await this.router.navigate(['/tabs/events/create']);
    } catch {
      const toast = await this.toastCtrl.create({
        message: 'Не вдалося відкрити створення події.',
        duration: 1500,
        position: 'top',
      });
      await toast.present();
    }
  }
}

