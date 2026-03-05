import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { PopularEventItem } from 'src/app/shared/interfaces/events/events.interface';

@Component({
  selector: 'app-home',
  templateUrl: 'home.page.html',
  styleUrls: ['home.page.scss'],
  standalone: false,

})
export class HomePage {
  organizedEventsCount = 15000;

  popularEvents: PopularEventItem[] = [
    {
      title: 'Майстер-клас з живопису',
      city: 'Арт-студія "Кольоровий світ"',
      date: '2026-11-15 10:00',
      uid: 'home:painting',
      description:
        'Долучайтеся до майстер-класу з живопису для початківців! Всі матеріали надаються.',
      theme: 'art',
    },
    {
      title: 'Вечір ігрових настільних ігор',
      city: 'Кафе "Гра на грані"',
      date: '2026-11-20 19:00',
      uid: 'home:boardgames',
      description:
        'Запрошуємо всіх любителів настільних ігор! Приєднуйтеся до нашої спільноти та грайте у нові хіти.',
      theme: 'games',
    },
    {
      title: 'Кінопоказ під відкритим небом',
      city: 'Площа перед міським парком',
      date: '2026-11-15 20:30',
      uid: 'home:openair-cinema',
      description:
        'Запрошуємо вас на безкоштовний кінопоказ класичних фільмів під зірками. Візьміть з собою плед!',
      theme: 'cinema',
    },
  ];

  constructor(private router: Router) {}


}
