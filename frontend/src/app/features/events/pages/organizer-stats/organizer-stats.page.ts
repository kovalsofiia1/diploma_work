import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { IonicModule, ToastController } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import {
  BookingsChartPoint,
  EventStatItem,
  OrganizerStatsResponse,
} from '../../interfaces/events.interface';
import { EventsService } from '../../services/events.service';
import { LoaderComponent } from 'src/app/shared/components/loader/loader.component';
import { AppHeaderComponent } from 'src/app/shared/components/app-header/app-header.component';

interface ChartBar {
  date: string;
  count: number;
  height: number;
  label: string;
}

@Component({
  selector: 'app-organizer-stats',
  standalone: true,
  imports: [CommonModule, IonicModule, RouterModule, LoaderComponent, AppHeaderComponent],
  templateUrl: './organizer-stats.page.html',
  styleUrls: ['./organizer-stats.page.scss'],
})
export class OrganizerStatsPage implements OnInit {
  private readonly eventsService = inject(EventsService);
  private readonly router = inject(Router);
  private readonly toastCtrl = inject(ToastController);

  loading = false;
  stats: OrganizerStatsResponse | null = null;

  upcomingEvents: EventStatItem[] = [];
  pastEvents: EventStatItem[] = [];
  chartBars: ChartBar[] = [];

  readonly chartHeight = 120;

  ngOnInit(): void {
    void this.loadStats();
  }

  goToEvent(uid: string): void {
    this.router.navigate(['/tabs/events/organizer-cabinet', encodeURIComponent(uid), 'settings']);
  }

  back(): void {
    this.router.navigate(['/tabs/events/organizer-cabinet']);
  }

  dateLabel(raw?: string): string {
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

  shortDateLabel(iso: string): string {
    const d = new Date(iso);
    return new Intl.DateTimeFormat('uk-UA', { day: '2-digit', month: '2-digit' }).format(d);
  }

  fillColor(rate?: number): string {
    if (rate == null) return 'var(--ion-color-medium)';
    if (rate >= 80) return '#10b981';
    if (rate >= 40) return '#f59e0b';
    return '#6366f1';
  }

  trackByDate(_: number, bar: ChartBar): string {
    return bar.date;
  }

  trackByUid(_: number, item: EventStatItem): string {
    return item.uid;
  }

  private async loadStats(): Promise<void> {
    if (this.loading) return;
    this.loading = true;
    try {
      const data = await firstValueFrom(this.eventsService.getOrganizerStats());
      this.stats = data;
      this.upcomingEvents = data.events.filter((e) => !e.is_past);
      this.pastEvents = data.events.filter((e) => e.is_past);
      this.chartBars = this.buildChart(data.bookings_by_day);
    } catch {
      const toast = await this.toastCtrl.create({
        message: 'Не вдалося завантажити статистику.',
        duration: 1800,
        position: 'top',
        color: 'danger',
      });
      await toast.present();
    } finally {
      this.loading = false;
    }
  }

  private buildChart(points: BookingsChartPoint[]): ChartBar[] {
    const maxCount = Math.max(...points.map((p) => p.count), 1);
    return points.map((p) => ({
      date: p.date,
      count: p.count,
      height: Math.round((p.count / maxCount) * this.chartHeight),
      label: this.shortDateLabel(p.date),
    }));
  }
}
