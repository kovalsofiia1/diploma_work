import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output, inject } from '@angular/core';
import { IonicModule } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { AdminUi, formatDateTime } from '../admin-ui';
import { AdminApplication, ApplicationStatus } from '../admin.models';
import { AdminService } from '../admin.service';

const PAGE_SIZE = 20;

@Component({
  selector: 'app-admin-applications',
  standalone: true,
  imports: [CommonModule, IonicModule],
  templateUrl: './admin-applications.component.html',
  styleUrls: ['../admin-shared.scss'],
})
export class AdminApplicationsComponent implements OnInit {
  @Output() changed = new EventEmitter<void>();

  private api = inject(AdminService);
  private ui = inject(AdminUi);

  readonly filters: { value: ApplicationStatus | ''; label: string }[] = [
    { value: 'pending', label: 'Очікують' },
    { value: 'approved', label: 'Схвалені' },
    { value: 'rejected', label: 'Відхилені' },
    { value: '', label: 'Усі' },
  ];
  readonly statusLabels: Record<ApplicationStatus, string> = {
    pending: 'Очікує',
    approved: 'Схвалено',
    rejected: 'Відхилено',
  };
  readonly formatDateTime = formatDateTime;

  status: ApplicationStatus | '' = 'pending';
  items: AdminApplication[] = [];
  total = 0;
  loading = false;
  error = false;
  busyId: number | null = null;

  ngOnInit(): void {
    void this.load();
  }

  setStatus(status: ApplicationStatus | ''): void {
    if (this.status === status) return;
    this.status = status;
    void this.load();
  }

  async load(append = false): Promise<void> {
    this.loading = true;
    this.error = false;
    try {
      const page = await firstValueFrom(
        this.api.getApplications({ status: this.status, skip: append ? this.items.length : 0, limit: PAGE_SIZE }),
      );
      this.items = append ? [...this.items, ...page.items] : page.items;
      this.total = page.total;
    } catch {
      this.error = true;
    } finally {
      this.loading = false;
    }
  }

  async approve(app: AdminApplication): Promise<void> {
    const ok = await this.ui.confirm(
      'Схвалити заявку?',
      `${app.user_email} отримає роль організатора і зможе створювати події.`,
      'Схвалити',
    );
    if (!ok) return;
    await this.run(app, () => this.api.approveApplication(app.id), 'Заявку схвалено');
  }

  async reject(app: AdminApplication): Promise<void> {
    const reason = await this.ui.askReason(
      'Відхилити заявку',
      'Причину побачить користувач у своєму профілі.',
      'Відхилити',
    );
    if (!reason) return;
    await this.run(app, () => this.api.rejectApplication(app.id, reason), 'Заявку відхилено');
  }

  private async run(
    app: AdminApplication,
    action: () => ReturnType<AdminService['approveApplication']>,
    successMessage: string,
  ): Promise<void> {
    this.busyId = app.id;
    try {
      const updated = await firstValueFrom(action());
      // Leave the filtered view once the application no longer matches it
      this.items = this.status && updated.status !== this.status
        ? this.items.filter((i) => i.id !== app.id)
        : this.items.map((i) => (i.id === app.id ? updated : i));
      if (this.status && updated.status !== this.status) this.total = Math.max(0, this.total - 1);
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
