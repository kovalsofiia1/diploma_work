import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule, NavController, ToastController } from '@ionic/angular';
import { ActivatedRoute, Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { EventInterface } from '../../events/interfaces/events.interface';
import { EventsService } from '../../events/services/events.service';
import {
  BookingService,
  TicketBooked,
} from '../services/booking.service';

@Component({
  selector: 'app-booking-create',
  templateUrl: './booking-create.page.html',
  styleUrls: ['./booking-create.page.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, IonicModule],
})
export class BookingCreatePage implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private navCtrl = inject(NavController);
  private toastCtrl = inject(ToastController);
  private eventsService = inject(EventsService);
  private bookingService = inject(BookingService);

  event?: EventInterface;
  ticketCount = 1;
  attendeeNames: string[] = [''];
  isSubmitting = false;
  bookedTickets: TicketBooked[] = [];

  async ngOnInit(): Promise<void> {
    const navState =
      (this.router.getCurrentNavigation()?.extras?.state as any) ?? {};
    const stateEvent = (navState?.event ?? history.state?.event) as
      | EventInterface
      | undefined;
    const eventUidFromQuery = (this.route.snapshot.queryParamMap.get('eventUid') ?? '').trim();
    const eventUid = eventUidFromQuery || (stateEvent?.uid ?? '').trim();

    if (stateEvent) {
      this.event = stateEvent;
    }

    if (eventUid) {
      try {
        // Refresh event to get current availability counters.
        this.event = await firstValueFrom(this.eventsService.getEventByUid(eventUid));
      } catch {
        if (!stateEvent) {
          this.event = undefined;
        }
      }
    }

    this.syncTicketCountToAvailability();
  }

  back(): void {
    this.navCtrl.back();
  }

  onTicketCountChange(nextValue: number | string): void {
    const numericValue = Number(nextValue);
    const clamped = Math.min(
      this.maxBookableCount,
      Math.max(1, Number.isFinite(numericValue) ? Math.round(numericValue) : 1),
    );
    this.ticketCount = clamped;

    if (this.attendeeNames.length < clamped) {
      this.attendeeNames = [
        ...this.attendeeNames,
        ...Array.from({ length: clamped - this.attendeeNames.length }, () => ''),
      ];
      return;
    }

    if (this.attendeeNames.length > clamped) {
      this.attendeeNames = this.attendeeNames.slice(0, clamped);
    }
  }

  trackByIndex(index: number): number {
    return index;
  }

  get startDateTimeLabel(): string {
    const parsed = this.parseDate(this.event?.startDate);
    if (!parsed) return 'Дата уточнюється';
    return new Intl.DateTimeFormat('uk-UA', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(parsed);
  }

  get totalPlaces(): number | null {
    const raw = this.event?.total_places;
    return Number.isFinite(raw as number) ? Number(raw) : null;
  }

  get bookedPlaces(): number {
    const raw = this.event?.booked_places;
    if (!Number.isFinite(raw as number)) return 0;
    return Math.max(0, Number(raw));
  }

  get availablePlaces(): number | null {
    const raw = this.event?.available_places;
    if (!Number.isFinite(raw as number)) return null;
    return Math.max(0, Number(raw));
  }

  get isSoldOut(): boolean {
    return this.availablePlaces !== null && this.availablePlaces <= 0;
  }

  get maxBookableCount(): number {
    if (this.availablePlaces === null) return 10;
    return Math.max(1, Math.min(10, this.availablePlaces));
  }

  async submit(): Promise<void> {
    if (this.isSubmitting) return;
    if (!this.event?.id) {
      await this.showToast('Подію не знайдено. Відкрийте бронювання з картки події.');
      return;
    }
    if (this.isSoldOut) {
      await this.showToast('Усі місця вже заброньовані.');
      return;
    }

    const names = this.attendeeNames.map((n) => n.trim()).filter(Boolean);
    if (names.length !== this.ticketCount) {
      await this.showToast('Заповніть імена для всіх квитків.');
      return;
    }
    if (this.availablePlaces !== null && names.length > this.availablePlaces) {
      await this.showToast(`Доступно лише ${this.availablePlaces} місць.`);
      return;
    }

    this.isSubmitting = true;
    try {
      const response = await firstValueFrom(
        this.bookingService.bookTickets(this.event.id, names),
      );
      this.bookedTickets = response.tickets;
      if (this.event && this.totalPlaces !== null) {
        const updatedBooked = this.bookedPlaces + response.tickets.length;
        this.event = {
          ...this.event,
          booked_places: updatedBooked,
          available_places: Math.max(this.totalPlaces - updatedBooked, 0),
        };
      }
      this.syncTicketCountToAvailability();
      await this.showToast('Квитки успішно заброньовано.', 'success');
    } catch (error: any) {
      const detail = error?.error?.detail;
      const message =
        typeof detail === 'string' && detail.trim()
          ? detail.trim()
          : 'Не вдалося забронювати квитки. Спробуйте ще раз.';
      await this.showToast(message);
    } finally {
      this.isSubmitting = false;
    }
  }

  private async showToast(message: string, color: 'success' | 'danger' = 'danger'): Promise<void> {
    const toast = await this.toastCtrl.create({
      message,
      duration: 1800,
      position: 'top',
      color,
    });
    await toast.present();
  }

  private parseDate(value: string | undefined): Date | null {
    const raw = (value ?? '').trim();
    if (!raw) return null;
    const candidate = raw.includes(' ') ? raw.replace(' ', 'T') : raw;
    const parsed = new Date(candidate);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  private syncTicketCountToAvailability(): void {
    this.ticketCount = Math.min(this.ticketCount, this.maxBookableCount);
    this.ticketCount = Math.max(1, this.ticketCount);
    this.onTicketCountChange(this.ticketCount);
  }
}

