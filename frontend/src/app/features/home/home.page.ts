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
      title: 'Літній музичний фестиваль 2026',
      city: 'Центральний парк',
      date: '15 червня 2026 • 18:00',
      uid: 'home:music-fest-2026',
      description: 'Відкритий фестиваль з лайнапом локальних артистів, фудкортом і зоною відпочинку.',
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
      uid: 'home:modern-art',
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
      uid: 'home:openair-cinema',
      description:
        'Класика кіно під зірками. Візьміть плед і приходьте завчасно — місця обмежені.',
      theme: 'cinema',
      price: 0,
      availableSeats: 120,
      tag: 'кіно',
    },
  ];

  constructor(private router: Router) {}


}
