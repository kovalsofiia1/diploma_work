import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output, inject } from '@angular/core';
import { IonicModule } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { AdminUi, formatDateTime } from '../admin-ui';
import { AdminUser, USER_ROLE_LABELS } from '../admin.models';
import { AdminService } from '../admin.service';

const PAGE_SIZE = 30;

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [CommonModule, IonicModule],
  templateUrl: './admin-users.component.html',
  styleUrls: ['../admin-shared.scss'],
})
export class AdminUsersComponent implements OnInit {
  @Output() changed = new EventEmitter<void>();

  private api = inject(AdminService);
  private ui = inject(AdminUi);

  readonly roleLabels = USER_ROLE_LABELS;
  readonly formatDateTime = formatDateTime;

  search = '';
  blockedOnly = false;
  items: AdminUser[] = [];
  total = 0;
  loading = false;
  error = false;
  busyId: number | null = null;

  ngOnInit(): void {
    void this.load();
  }

  onSearch(value: string | null | undefined): void {
    this.search = (value ?? '').trim();
    void this.load();
  }

  setBlockedOnly(value: boolean): void {
    if (this.blockedOnly === value) return;
    this.blockedOnly = value;
    void this.load();
  }

  async load(append = false): Promise<void> {
    this.loading = true;
    this.error = false;
    try {
      const page = await firstValueFrom(
        this.api.getUsers({
          search: this.search,
          blocked: this.blockedOnly ? true : null,
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

  async block(user: AdminUser): Promise<void> {
    const reason = await this.ui.askReason(
      `Заблокувати ${user.email}?`,
      'Користувач одразу втратить доступ до акаунта. Якщо це організатор, його події буде приховано.',
      'Заблокувати',
    );
    if (!reason) return;
    await this.run(user, () => this.api.blockUser(user.id, reason), (u) =>
      u.affected_events ? `Користувача заблоковано. Приховано подій: ${u.affected_events}` : 'Користувача заблоковано',
    );
  }

  async unblock(user: AdminUser): Promise<void> {
    const ok = await this.ui.confirm(`Розблокувати ${user.email}?`, 'Користувач знову зможе увійти.', 'Розблокувати');
    if (!ok) return;
    await this.run(user, () => this.api.unblockUser(user.id), (u) =>
      u.affected_events ? `Користувача розблоковано. Повернуто подій: ${u.affected_events}` : 'Користувача розблоковано',
    );
  }

  async grantAdmin(user: AdminUser): Promise<void> {
    const ok = await this.ui.confirm(
      `Зробити ${user.email} адміном?`,
      'Користувач отримає повний доступ до адмін-панелі.',
      'Надати роль',
    );
    if (!ok) return;
    await this.run(user, () => this.api.grantAdmin(user.id), () => 'Роль адміна надано');
  }

  async revokeAdmin(user: AdminUser): Promise<void> {
    const ok = await this.ui.confirm(
      `Зняти роль адміна з ${user.email}?`,
      'Користувач втратить доступ до адмін-панелі.',
      'Зняти роль',
    );
    if (!ok) return;
    await this.run(user, () => this.api.revokeAdmin(user.id), () => 'Роль адміна знято');
  }

  private async run(
    user: AdminUser,
    action: () => ReturnType<AdminService['unblockUser']>,
    successMessage: (updated: AdminUser) => string,
  ): Promise<void> {
    this.busyId = user.id;
    try {
      const updated = await firstValueFrom(action());
      if (this.blockedOnly && updated.is_active) {
        this.items = this.items.filter((u) => u.id !== user.id);
        this.total = Math.max(0, this.total - 1);
      } else {
        this.items = this.items.map((u) => (u.id === user.id ? updated : u));
      }
      await this.ui.toast(successMessage(updated));
      this.changed.emit();
    } catch (err) {
      await this.ui.toast(this.ui.errorMessage(err, 'Не вдалося виконати дію'), 'danger');
      void this.load();
    } finally {
      this.busyId = null;
    }
  }
}
