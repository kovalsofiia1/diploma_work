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
  selectedSeatTypes: string[] = [''];
  selectedSeatIds: string[] = [''];
  occupiedSeatIds = new Set<string>();
  isSubmitting = false;
  bookedTickets: TicketBooked[] = [];
  seatPricingOptions: Array<{
    seat_id: string;
    label: string;
    price: number;
    seat_type: string;
  }> = [];

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

    this.loadSeatPricingFromAdditional();
    await this.loadOccupiedSeats();
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
      this.selectedSeatIds = [
        ...this.selectedSeatIds,
        ...Array.from({ length: clamped - this.selectedSeatIds.length }, () => ''),
      ];
      this.selectedSeatTypes = [
        ...this.selectedSeatTypes,
        ...Array.from({ length: clamped - this.selectedSeatTypes.length }, () => ''),
      ];
      return;
    }

    if (this.attendeeNames.length > clamped) {
      this.attendeeNames = this.attendeeNames.slice(0, clamped);
      this.selectedSeatIds = this.selectedSeatIds.slice(0, clamped);
      this.selectedSeatTypes = this.selectedSeatTypes.slice(0, clamped);
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
    if (this.hasSeatPricing && this.availableSeatOptions.length <= 0) {
      return true;
    }
    return this.availablePlaces !== null && this.availablePlaces <= 0;
  }

  get maxBookableCount(): number {
    const capacityLimit =
      this.availablePlaces === null ? 10 : Math.max(1, Math.min(10, this.availablePlaces));
    if (!this.hasSeatPricing) {
      return capacityLimit;
    }
    return Math.max(1, Math.min(capacityLimit, this.availableSeatOptions.length));
  }

  get hasSeatPricing(): boolean {
    return this.seatPricingOptions.length > 0;
  }

  get availableSeatOptions(): Array<{ seat_id: string; label: string; price: number }> {
    return this.seatPricingOptions.filter(
      (item) => !this.occupiedSeatIds.has(item.seat_id),
    );
  }

  get ticketTypeOptions(): string[] {
    return Array.from(
      new Set(
        this.seatPricingOptions
          .map((item) => item.seat_type)
          .filter((item) => item.trim()),
      ),
    );
  }

  get ticketSummaryTotal(): number {
    if (!this.hasSeatPricing) {
      return 0;
    }
    return this.selectedSeatIds.reduce((sum, seatId) => {
      const seat = this.seatPricingOptions.find((item) => item.seat_id === seatId);
      return sum + (seat?.price ?? 0);
    }, 0);
  }

  get ticketCurrency(): string {
    return this.event?.price_currency || 'UAH';
  }

  getSeatPriceLabel(index: number): string {
    if (!this.hasSeatPricing) {
      return '';
    }
    const selected = this.seatPricingOptions.find(
      (item) => item.seat_id === this.selectedSeatIds[index],
    );
    if (!selected) {
      return 'Оберіть місце';
    }
    return `${selected.price} ${this.ticketCurrency}`;
  }

  onSeatTypeChange(rowIndex: number, value: string): void {
    const seatType = (value ?? '').toString().trim();
    this.selectedSeatTypes[rowIndex] = seatType;
    const currentSeatId = this.selectedSeatIds[rowIndex];
    if (!currentSeatId) {
      return;
    }
    const currentSeat = this.seatPricingOptions.find(
      (item) => item.seat_id === currentSeatId,
    );
    if (!currentSeat || currentSeat.seat_type !== seatType) {
      this.selectedSeatIds[rowIndex] = '';
    }
  }

  isTicketTypeUnavailableForRow(seatType: string, rowIndex: number): boolean {
    const seats = this.getSeatsByTypeForRow(rowIndex, seatType);
    return seats.length === 0;
  }

  getSeatsByTypeForRow(
    rowIndex: number,
    seatType: string,
  ): Array<{ seat_id: string; label: string; price: number; seat_type: string }> {
    return this.seatPricingOptions.filter(
      (seat) =>
        seat.seat_type === seatType &&
        !this.isSeatUnavailableForRow(seat.seat_id, rowIndex),
    );
  }

  isSeatUnavailableForRow(seatId: string, rowIndex: number): boolean {
    if (this.occupiedSeatIds.has(seatId)) {
      return true;
    }
    return this.selectedSeatIds.some(
      (selectedSeatId, selectedIndex) =>
        selectedIndex !== rowIndex && selectedSeatId === seatId,
    );
  }

  getSeatOptionsForRow(
    rowIndex: number,
  ): Array<{ seat_id: string; label: string; price: number }> {
    const selectedType = (this.selectedSeatTypes[rowIndex] ?? '').trim();
    if (!selectedType) {
      return [];
    }
    return this.getSeatsByTypeForRow(rowIndex, selectedType);
  }

  onSeatChange(rowIndex: number, value: string): void {
    const seatId = (value ?? '').toString().trim();
    if (!seatId) {
      this.selectedSeatIds[rowIndex] = '';
      return;
    }
    if (this.isSeatUnavailableForRow(seatId, rowIndex)) {
      this.selectedSeatIds[rowIndex] = '';
      void this.showToast('Це місце вже зайняте. Оберіть інше.');
      return;
    }
    this.selectedSeatIds[rowIndex] = seatId;
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
    await this.loadOccupiedSeats();

    const names = this.attendeeNames.map((n) => n.trim()).filter(Boolean);
    if (names.length !== this.ticketCount) {
      await this.showToast('Заповніть імена для всіх квитків.');
      return;
    }
    if (this.availablePlaces !== null && names.length > this.availablePlaces) {
      await this.showToast(`Доступно лише ${this.availablePlaces} місць.`);
      return;
    }
    if (this.hasSeatPricing) {
      const selectedTypes = this.selectedSeatTypes
        .map((value) => value.trim())
        .filter(Boolean);
      if (selectedTypes.length !== this.ticketCount) {
        await this.showToast('Оберіть тип квитка для кожного місця.');
        return;
      }
      const selected = this.selectedSeatIds.map((value) => value.trim()).filter(Boolean);
      if (selected.length !== this.ticketCount) {
        await this.showToast('Оберіть місце для кожного квитка.');
        return;
      }
      if (new Set(selected).size !== selected.length) {
        await this.showToast('Не можна обрати одне місце двічі.');
        return;
      }
      const nowOccupied = selected.filter((seatId) =>
        this.occupiedSeatIds.has(seatId),
      );
      if (nowOccupied.length > 0) {
        await this.showToast('Частина місць вже заброньована. Оновіть вибір.');
        return;
      }
    }

    this.isSubmitting = true;
    try {
      const seatItems = this.hasSeatPricing
        ? this.attendeeNames.map((attendeeName, index) => {
            const seatId = this.selectedSeatIds[index];
            const seatOption = this.seatPricingOptions.find(
              (item) => item.seat_id === seatId,
            );
            return {
              attendee_name: attendeeName.trim(),
              seat_id: seatId,
              seat_label: seatOption?.label ?? seatId,
            };
          })
        : undefined;
      const response = await firstValueFrom(
        this.bookingService.bookTickets(this.event.id, names, seatItems),
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
      if (this.hasSeatPricing) {
        this.selectedSeatIds = this.selectedSeatIds.map(() => '');
        this.selectedSeatTypes = this.selectedSeatTypes.map(() => '');
      }
      await this.loadOccupiedSeats();
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

  private loadSeatPricingFromAdditional(): void {
    const raw = (this.event?.additional ?? '').trim();
    if (!raw) {
      this.seatPricingOptions = [];
      return;
    }
    try {
      const parsed = JSON.parse(raw);
      const seatPricing = parsed?.seat_pricing;
      if (!Array.isArray(seatPricing)) {
        this.seatPricingOptions = [];
        return;
      }
      this.seatPricingOptions = seatPricing
        .map((item: any) => ({
          seat_id: (item?.seat_id ?? '').toString().trim(),
          label: (item?.label ?? '').toString().trim(),
          price: Number(item?.price ?? 0),
          seat_type: (item?.seat_type ?? '').toString().trim(),
        }))
        .filter(
          (item) =>
            item.seat_id &&
            item.label &&
            item.seat_type &&
            Number.isFinite(item.price) &&
            item.price >= 0,
        );
    } catch {
      this.seatPricingOptions = [];
    }
  }

  private async loadOccupiedSeats(): Promise<void> {
    if (!this.event?.id || !this.hasSeatPricing) {
      this.occupiedSeatIds = new Set<string>();
      return;
    }
    try {
      const response = await firstValueFrom(
        this.bookingService.getOccupiedSeats(this.event.id),
      );
      this.occupiedSeatIds = new Set(response.seat_ids ?? []);
      this.sanitizeSelectedSeats();
    } catch {
      this.occupiedSeatIds = new Set<string>();
    }
  }

  private sanitizeSelectedSeats(): void {
    this.selectedSeatIds = this.selectedSeatIds.map((seatId, index) =>
      this.isSeatUnavailableForRow(seatId, index) ? '' : seatId,
    );
    this.selectedSeatTypes = this.selectedSeatTypes.map((seatType, index) => {
      const selectedSeatId = this.selectedSeatIds[index];
      if (!selectedSeatId) {
        return '';
      }
      const selectedSeat = this.seatPricingOptions.find(
        (item) => item.seat_id === selectedSeatId,
      );
      if (!selectedSeat || selectedSeat.seat_type !== seatType) {
        return selectedSeat?.seat_type ?? '';
      }
      return seatType;
    });
  }
}

