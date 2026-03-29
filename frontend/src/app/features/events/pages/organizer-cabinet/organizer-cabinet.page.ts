import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { IonicModule, ToastController } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { EventInterface } from '../../interfaces/events.interface';
import { EventsService } from '../../services/events.service';
import { LoaderComponent } from 'src/app/shared/components/loader/loader.component';

@Component({
  selector: 'app-organizer-cabinet',
  standalone: true,
  imports: [CommonModule, IonicModule, RouterModule, LoaderComponent],
  templateUrl: './organizer-cabinet.page.html',
  styleUrls: ['./organizer-cabinet.page.scss'],
})
export class OrganizerCabinetPage {
  loading = false;
  events: EventInterface[] = [];
  total = 0;
  readonly pageSize = 12;
  skip = 0;

  constructor(
    private readonly eventsService: EventsService,
    private readonly router: Router,
    private readonly toastCtrl: ToastController,
  ) {}

  ngOnInit(): void {
    this.loadEvents();
  }

  get currentPage(): number {
    return Math.floor(this.skip / this.pageSize) + 1;
  }

  get totalPages(): number {
    if (!this.total) return 1;
    return Math.max(1, Math.ceil(this.total / this.pageSize));
  }

  get canPrev(): boolean {
    return this.skip > 0;
  }

  get canNext(): boolean {
    return this.skip + this.pageSize < this.total;
  }

  openSettings(item: EventInterface): void {
    if (!item.uid) return;
    this.router.navigate(
      ['/tabs/events/organizer-cabinet', encodeURIComponent(item.uid), 'settings'],
      { state: { item } },
    );
  }

  openScanner(): void {
    this.router.navigate(['/tabs/tickets/verify']);
  }

  prevPage(): void {
    if (!this.canPrev) return;
    this.skip = Math.max(0, this.skip - this.pageSize);
    this.loadEvents();
  }

  nextPage(): void {
    if (!this.canNext) return;
    this.skip += this.pageSize;
    this.loadEvents();
  }

  roleLabel(item: EventInterface): string {
    return item.can_edit ? 'Організатор' : 'Сканер';
  }

  dateLabel(item: EventInterface): string {
    const raw = (item.startDate ?? '').trim();
    if (!raw) return 'Дата уточнюється';
    const normalized = raw.includes(' ') ? raw.replace(' ', 'T') : raw;
    const parsed = new Date(normalized);
    if (Number.isNaN(parsed.getTime())) return raw;
    return new Intl.DateTimeFormat('uk-UA', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(parsed);
  }

  private async loadEvents(): Promise<void> {
    if (this.loading) return;
    this.loading = true;
    try {
      const res = await firstValueFrom(
        this.eventsService.getAssignedEvents({
          skip: this.skip,
          limit: this.pageSize,
        }),
      );
      this.events = res.items ?? [];
      this.total = res.total ?? this.events.length;
    } catch {
      const toast = await this.toastCtrl.create({
        message: 'Не вдалося завантажити події для організатора.',
        duration: 1800,
        position: 'top',
        color: 'danger',
      });
      await toast.present();
    } finally {
      this.loading = false;
    }
  }
}
