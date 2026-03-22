import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, NavController, ToastController } from '@ionic/angular';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import {
  EventInterface,
  EventKind,
} from 'src/app/features/events/interfaces/events.interface';
import { Store } from '@ngrx/store';
import {
  addFavoriteEvent,
  deleteFavoriteEvent,
} from '../../redux/events.actions';

@Component({
  selector: 'app-event-detail',
  templateUrl: './event-detail.page.html',
  styleUrls: ['./event-detail.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule, RouterModule],
})
export class EventDetailPage implements OnInit {
  uid: string = '';
  event?: EventInterface;
  saved = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private navCtrl: NavController,
    private toastCtrl: ToastController,
    private store: Store,
  ) {}

  ngOnInit(): void {
    const rawUid = this.route.snapshot.paramMap.get('uid') ?? '';
    this.uid = decodeURIComponent(rawUid);

    // Prefer navigation state when available
    const state =
      (this.router.getCurrentNavigation()?.extras?.state as any) ?? {};
    const raw = (state?.item ?? (history.state?.item as any)) as
      | Partial<EventInterface>
      | undefined;

    this.event = this.normalizeEvent(this.uid, raw);
    this.saved = this.event.isSaved || false;
  }

  back(): void {
    this.navCtrl.back();
  }

  async toggleSaved(): Promise<void> {
    this.saved = !this.saved;

    console.log(this.saved);
    this.store.dispatch(
      this.saved
        ? addFavoriteEvent({ id: this.uid })
        : deleteFavoriteEvent({ id: this.uid }),
    );
    const toast = await this.toastCtrl.create({
      message: this.saved ? 'Додано в улюблені.' : 'Прибрано з улюблених.',
      duration: 1200,
      position: 'top',
      color: this.saved ? 'success' : undefined,
    });
    await toast.present();
  }

  async share(): Promise<void> {
    const toast = await this.toastCtrl.create({
      message: 'Поширення буде додано незабаром.',
      duration: 1200,
      position: 'top',
    });
    await toast.present();
  }

  get isExternal(): boolean {
    if (!this.event) return false;
    if (this.event.kind === EventKind.external) return true;
    const src = (this.event.source ?? '').toLowerCase();
    return src === 'concert.ua' || src === 'karabas.com' || src === 'dou.ua';
  }

  get eventTypeLabel(): string {
    const type = this.event?.type?.trim();
    if (type) return type;
    return this.isExternal ? 'Зовнішня подія' : 'Внутрішня подія';
  }

  get locationLabel(): string {
    const place = this.event?.location_name?.trim();
    if (place) return place;
    return this.event?.city?.trim() || 'Локація уточнюється';
  }

  get websiteUrl(): string | null {
    const url = this.event?.url?.trim();
    return url || null;
  }

  get bookingUrl(): string | null {
    const orderUrl = this.event?.order_url?.trim();
    if (orderUrl) return orderUrl;
    return this.websiteUrl;
  }

  get priceLabel(): string {
    const low = this.toNumber(this.event?.price_low);
    const high = this.toNumber(this.event?.price_high);
    const currency = this.event?.price_currency?.trim() || '₴';

    if (low === null && high === null) return 'Безкоштовно';
    if (low !== null && high !== null && low !== high) {
      return `${currency}${low} - ${currency}${high}`;
    }
    const single = low ?? high;
    if (single === null || single <= 0) return 'Безкоштовно';
    return `${single}${currency}`;
  }

  get dateLabel(): string {
    const parsed = this.parseDate(this.event?.startDate);
    if (!parsed) return 'Дата уточнюється';
    return new Intl.DateTimeFormat('uk-UA', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    }).format(parsed);
  }

  get timeLabel(): string {
    const parsed = this.parseDate(this.event?.startDate);
    if (!parsed) return 'Час уточнюється';
    return new Intl.DateTimeFormat('uk-UA', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(parsed);
  }

  get descriptionText(): string {
    return (
      this.event?.description?.trim() ||
      'Опис події тимчасово недоступний. Спробуйте відкрити подію зі списку або оновіть сторінку.'
    );
  }

  async openWebsite(): Promise<void> {
    if (!this.websiteUrl) return;
    window.open(this.websiteUrl, '_blank', 'noopener,noreferrer');
  }

  async book(): Promise<void> {
    if (!this.event) return;

    if (this.isExternal) {
      const url = this.bookingUrl;
      if (!url) {
        const toast = await this.toastCtrl.create({
          message: 'Посилання для бронювання недоступне.',
          duration: 1400,
          position: 'top',
        });
        await toast.present();
        return;
      }
      window.open(url, '_blank', 'noopener,noreferrer');
      return;
    }

    await this.router.navigate(['/tabs/tickets'], {
      queryParams: { eventUid: this.event.uid ?? '' },
      state: { event: this.event },
    });
  }

  private normalizeEvent(
    uid: string,
    raw?: Partial<EventInterface>,
  ): EventInterface {
    return {
      uid: raw?.uid ?? uid,
      name: raw?.name ?? 'Подія',
      type: raw?.type ?? undefined,
      url: raw?.url ?? undefined,
      order_url: raw?.order_url ?? undefined,
      startDate: raw?.startDate ?? undefined,
      endDate: raw?.endDate ?? undefined,
      location_name: raw?.location_name ?? undefined,
      city: raw?.city ?? undefined,
      price_low: raw?.price_low ?? undefined,
      price_high: raw?.price_high ?? undefined,
      price_currency: raw?.price_currency ?? '₴',
      image: raw?.image ?? 'assets/shapes.svg',
      source: raw?.source ?? undefined,
      verified: raw?.verified ?? true,
      description: raw?.description ?? undefined,
      id: raw?.id ?? undefined,
      kind: raw?.kind ?? undefined,
      isSaved: raw?.isSaved ?? false,
    };
  }

  private parseDate(value: string | undefined): Date | null {
    const raw = (value ?? '').trim();
    if (!raw) return null;
    const candidate = raw.includes(' ') ? raw.replace(' ', 'T') : raw;
    const parsed = new Date(candidate);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  private toNumber(value: string | undefined): number | null {
    if (!value && value !== '0') return null;
    const n = Number(value);
    if (!Number.isFinite(n)) return null;
    return Math.round(n);
  }
}
