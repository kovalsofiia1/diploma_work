import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { IonicModule } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { AppHeaderComponent } from 'src/app/shared/components/app-header/app-header.component';
import { AdminSummary } from './admin.models';
import { AdminService } from './admin.service';
import { AdminApplicationsComponent } from './tabs/admin-applications.component';
import { AdminAuditLogComponent } from './tabs/admin-audit-log.component';
import { AdminEventsComponent } from './tabs/admin-events.component';
import { AdminUsersComponent } from './tabs/admin-users.component';

export type AdminTab = 'applications' | 'users' | 'events' | 'audit';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [
    CommonModule,
    IonicModule,
    AppHeaderComponent,
    AdminApplicationsComponent,
    AdminUsersComponent,
    AdminEventsComponent,
    AdminAuditLogComponent,
  ],
  templateUrl: './admin.page.html',
  styleUrls: ['./admin.page.scss'],
})
export class AdminPage implements OnInit {
  private api = inject(AdminService);

  tab: AdminTab = 'applications';
  summary: AdminSummary | null = null;

  readonly tabs: { value: AdminTab; label: string; icon: string }[] = [
    { value: 'applications', label: 'Заявки', icon: 'document-text-outline' },
    { value: 'users', label: 'Користувачі', icon: 'people-outline' },
    { value: 'events', label: 'Події', icon: 'calendar-outline' },
    { value: 'audit', label: 'Журнал', icon: 'time-outline' },
  ];

  ngOnInit(): void {
    void this.refreshSummary();
  }

  selectTab(value: unknown): void {
    if (value === 'applications' || value === 'users' || value === 'events' || value === 'audit') {
      this.tab = value;
    }
  }

  async refreshSummary(): Promise<void> {
    try {
      this.summary = await firstValueFrom(this.api.getSummary());
    } catch {
      this.summary = null;
    }
  }
}
