import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { IonicModule } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { formatDateTime } from '../admin-ui';
import { AUDIT_ACTION_LABELS, AuditLogEntry } from '../admin.models';
import { AdminService } from '../admin.service';

const PAGE_SIZE = 50;

const TARGET_LABELS: Record<string, string> = {
  organizer_application: 'Заявка',
  user: 'Користувач',
  event: 'Подія',
};

@Component({
  selector: 'app-admin-audit-log',
  standalone: true,
  imports: [CommonModule, IonicModule],
  templateUrl: './admin-audit-log.component.html',
  styleUrls: ['../admin-shared.scss'],
})
export class AdminAuditLogComponent implements OnInit {
  private api = inject(AdminService);

  readonly formatDateTime = formatDateTime;
  readonly actionFilters = [
    { value: '', label: 'Усі дії' },
    ...Object.entries(AUDIT_ACTION_LABELS).map(([value, label]) => ({ value, label })),
  ];

  action = '';
  items: AuditLogEntry[] = [];
  total = 0;
  loading = false;
  error = false;

  ngOnInit(): void {
    void this.load();
  }

  setAction(value: string): void {
    if (this.action === value) return;
    this.action = value;
    void this.load();
  }

  async load(append = false): Promise<void> {
    this.loading = true;
    this.error = false;
    try {
      const page = await firstValueFrom(
        this.api.getAuditLog({ action: this.action, skip: append ? this.items.length : 0, limit: PAGE_SIZE }),
      );
      this.items = append ? [...this.items, ...page.items] : page.items;
      this.total = page.total;
    } catch {
      this.error = true;
    } finally {
      this.loading = false;
    }
  }

  actionLabel(entry: AuditLogEntry): string {
    return AUDIT_ACTION_LABELS[entry.action] ?? entry.action;
  }

  isNegative(entry: AuditLogEntry): boolean {
    return ['organizer_application.rejected', 'user.blocked', 'event.hidden'].includes(entry.action);
  }

  targetLabel(entry: AuditLogEntry): string {
    const d = entry.details ?? {};
    const name = (d['event_name'] ?? d['user_email']) as string | undefined;
    const kind = TARGET_LABELS[entry.target_type] ?? entry.target_type;
    return name ? `${kind} #${entry.target_id} · ${name}` : `${kind} #${entry.target_id}`;
  }

  reason(entry: AuditLogEntry): string | null {
    const d = entry.details ?? {};
    if (d['reason']) return `Причина: ${d['reason']}`;
    if (d['previous_reason']) return `Попередня причина: ${d['previous_reason']}`;
    return null;
  }
}
