import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, OnDestroy, OnInit, Output, SimpleChanges, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { AdminUi, formatDateTime } from '../admin-ui';
import { AdminEvent, Tone } from '../admin.models';
import { AdminService } from '../admin.service';

const PAGE_SIZE = 30;

export type VisibilityFilter = 'all' | 'visible' | 'hidden';

@Component({
  selector: 'app-admin-events',
  standalone: true,
  imports: [CommonModule, IonicModule, RouterModule],
  templateUrl: './admin-events.component.html',
  styleUrls: ['../admin-shared.scss'],
})
export class AdminEventsComponent implements OnInit, OnChanges, OnDestroy {
  /** Set by the summary counter to open the tab with hidden events only. */
  @Input() visibility: VisibilityFilter = 'all';
  @Output() changed = new EventEmitter<void>();

  private api = inject(AdminService);
  private ui = inject(AdminUi);
  private searchTimer?: ReturnType<typeof setTimeout>;

  readonly formatDateTime = formatDateTime;
  readonly filters: { value: VisibilityFilter; label: string }[] = [
    { value: 'all', label: 'Усі' },
    { value: 'visible', label: 'Видимі' },
    { value: 'hidden', label: 'Приховані' },
  ];

  search = '';
  items: AdminEvent[] = [];
  total = 0;
  loading = false;
  error = false;
  busyId: number | null = null;

  ngOnInit(): void {
    void this.load();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['visibility'] && !changes['visibility'].firstChange) void this.load();
  }

  ngOnDestroy(): void {
    clearTimeout(this.searchTimer);
  }

  onSearch(value: string): void {
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.search = value.trim();
      void this.load();
    }, 350);
  }

  tone(event: AdminEvent): Tone {
    if (event.is_hidden) return 'amber';
    if (event.status === 'CANCELLED') return 'gray';
    return event.source_type === 'INTERNAL' ? 'green' : 'blue';
  }

  setVisibility(value: VisibilityFilter): void {
    if (this.visibility === value) return;
    this.visibility = value;
    void this.load();
  }

  eventLink(event: AdminEvent): string[] {
    const uid = event.uid || `${event.source_type === 'INTERNAL' ? 'internal' : 'external'}:${event.id}`;
    return ['/tabs/events', uid];
  }

  sourceLabel(event: AdminEvent): string {
    return event.source_type === 'INTERNAL' ? 'Платформа' : event.source_name || 'Зовнішнє джерело';
  }

  async load(append = false): Promise<void> {
    this.loading = true;
    this.error = false;
    try {
      const page = await firstValueFrom(
        this.api.getEvents({
          search: this.search,
          hidden: this.visibility === 'all' ? null : this.visibility === 'hidden',
          skip: append ? this.items.length : 0,
          limit: PAGE_SIZE,
        }),
      );
      this.items = append ? [...this.items, ...page.items] : page.items;
      this.total = page.total;
    } catch {
      this.error = true;
    } finally {
      this.loading = false;
    }
  }

  async hide(event: AdminEvent): Promise<void> {
    const reason = await this.ui.askReason(
      'Приховати подію',
      'Подія зникне з каталогу, пошуку й бронювання. Організатор і далі її бачитиме.',
      'Приховати',
    );
    if (!reason) return;
    await this.run(event, () => this.api.hideEvent(event.id, reason), 'Подію приховано');
  }

  async unhide(event: AdminEvent): Promise<void> {
    const ok = await this.ui.confirm('Повернути подію?', 'Подія знову зʼявиться в каталозі.', 'Повернути');
    if (!ok) return;
    await this.run(event, () => this.api.unhideEvent(event.id), 'Подію повернуто');
  }

  private async run(
    event: AdminEvent,
    action: () => ReturnType<AdminService['unhideEvent']>,
    successMessage: string,
  ): Promise<void> {
    this.busyId = event.id;
    try {
      const updated = await firstValueFrom(action());
      const stillMatches =
        this.visibility === 'all' || (this.visibility === 'hidden') === updated.is_hidden;
      if (stillMatches) {
        this.items = this.items.map((e) => (e.id === event.id ? updated : e));
      } else {
        this.items = this.items.filter((e) => e.id !== event.id);
        this.total = Math.max(0, this.total - 1);
      }
      await this.ui.toast(successMessage);
      this.changed.emit();
    } catch (err) {
      await this.ui.toast(this.ui.errorMessage(err, 'Не вдалося виконати дію'), 'danger');
      void this.load();
    } finally {
      this.busyId = null;
    }
  }
}
