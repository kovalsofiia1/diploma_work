import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, NavController, ToastController } from '@ionic/angular';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { AppHeaderComponent } from 'src/app/shared/components/app-header/app-header.component';
import { PopularEventItem } from 'src/app/shared/interfaces/events/events.interface';

interface EventDetailViewModel {
  uid: string;
  title: string;
  description: string;
  city: string;
  place: string;
  organizer: string;
  image: string;
  tags: string[];
  rating: number;
  price: number;
  booked: { current: number; total: number };
  dateLabel: string;
  timeLabel: string;
}

@Component({
  selector: 'app-event-detail',
  templateUrl: './event-detail.page.html',
  styleUrls: ['./event-detail.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule, RouterModule, AppHeaderComponent],
})
export class EventDetailPage implements OnInit {
  uid: string = '';
  event?: EventDetailViewModel;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private navCtrl: NavController,
    private toastCtrl: ToastController
  ) {}

  ngOnInit(): void {
    this.uid = this.route.snapshot.paramMap.get('uid') ?? '';
    // Prefer navigation state when available
    const state = (this.router.getCurrentNavigation()?.extras?.state as any) ?? {};
    const raw = (state?.item ?? (history.state?.item as any)) as Partial<
      PopularEventItem & {
        image?: string;
        place?: string;
        organizer?: string;
        price?: number;
        rating?: number;
        tags?: string[];
        booked?: { current: number; total: number };
      }
    >;

    this.event = this.buildViewModel(this.uid, raw);
  }

  back(): void {
    this.navCtrl.back();
  }

  async save(): Promise<void> {
    const toast = await this.toastCtrl.create({
      message: 'Збережено (демо).',
      duration: 1200,
      position: 'top',
      color: 'success',
    });
    await toast.present();
  }

  async book(): Promise<void> {
    const toast = await this.toastCtrl.create({
      message: 'Бронювання буде доступне незабаром.',
      duration: 1500,
      position: 'top',
    });
    await toast.present();
  }

  async edit(): Promise<void> {
    const toast = await this.toastCtrl.create({
      message: 'Редагування буде додано незабаром.',
      duration: 1500,
      position: 'top',
    });
    await toast.present();
  }

  async remove(): Promise<void> {
    const toast = await this.toastCtrl.create({
      message: 'Видалення буде додано незабаром.',
      duration: 1500,
      position: 'top',
      color: 'danger',
    });
    await toast.present();
  }

  private buildViewModel(uid: string, raw?: Partial<any>): EventDetailViewModel | undefined {
    const fallback = this.fallbackByUid(uid);
    const base: any = raw && Object.keys(raw).length ? raw : fallback;
    if (!base) return undefined;

    const { dateLabel, timeLabel } = this.formatDateTime(base.date);

    const theme = (base.theme ?? 'art') as PopularEventItem['theme'];
    const defaultTags =
      base.title && typeof base.title === 'string'
        ? this.makeTags(base.title, theme)
        : this.makeTags('Подія', theme);

    const booked = base.booked ?? { current: 5, total: 20 };

    return {
      uid: base.uid ?? uid,
      title: base.title ?? 'Подія',
      description:
        base.description ??
        'Опис події тимчасово недоступний. Спробуйте відкрити подію зі списку або оновіть сторінку.',
      city: base.city ?? '—',
      place: base.place ?? base.city ?? '—',
      organizer: base.organizer ?? 'Sofi Kovals',
      image: base.image ?? 'assets/shapes.svg',
      tags: base.tags ?? defaultTags,
      rating: Number.isFinite(base.rating) ? base.rating : 4.75,
      price: Number.isFinite(base.price) ? base.price : 300,
      booked: {
        current: Math.max(0, Number(booked.current ?? 5) || 0),
        total: Math.max(1, Number(booked.total ?? 20) || 20),
      },
      dateLabel,
      timeLabel,
    };
  }

  private fallbackByUid(uid: string): Partial<PopularEventItem> & any {
    const map: Record<string, Partial<PopularEventItem> & any> = {
      'events:painting': {
        uid,
        title: 'Майстер-клас з живопису',
        city: 'Арт-студія "Кольоровий світ"',
        date: '2026-11-15 18:00',
        description:
          'Долучайтеся до майстер-класу з живопису для початківців! Всі матеріали надаються. Навчіться основам живопису разом з професійним художником і створіть свій перший шедевр.',
        theme: 'art',
        organizer: 'Sofi Kovals',
        place: 'Арт-студія "Кольоровий світ", вул. Бандери, 30A',
        booked: { current: 5, total: 20 },
        price: 300,
        rating: 4.75,
        tags: ['#майстер_клас', '#живопис', '#креативність', '#арт'],
        image: 'assets/shapes.svg',
      },
    };
    return map[uid] ?? { uid, title: 'Подія', city: '—', date: '' };
  }

  private formatDateTime(input: string | undefined): { dateLabel: string; timeLabel: string } {
    const raw = (input ?? '').toString().trim();
    if (!raw) return { dateLabel: '—', timeLabel: '—' };

    // Accept "YYYY-MM-DD HH:mm" or ISO.
    const parts = raw.split(' ');
    const d = parts[0] ?? raw;
    const t = parts.length > 1 ? parts[1] : '';

    const dateObj = new Date(d);
    const dateLabel = Number.isNaN(dateObj.getTime())
      ? d
      : new Intl.DateTimeFormat('uk-UA', { day: 'numeric', month: 'long', year: 'numeric' }).format(
          dateObj
        );

    const timeLabel = t ? t : parts.length > 1 ? parts.slice(1).join(' ') : '—';
    return { dateLabel, timeLabel };
  }

  private makeTags(title: string, theme: PopularEventItem['theme']): string[] {
    const base = title
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s]+/gu, ' ')
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => `#${w}`);

    const byTheme: Record<PopularEventItem['theme'], string[]> = {
      art: ['#арт', '#творчість'],
      games: ['#ігри', '#настілки'],
      cinema: ['#кіно', '#показ'],
    };
    return [...new Set([...byTheme[theme], ...base])].slice(0, 6);
  }
}


