import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { AdminUi } from '../admin-ui';
import { AdminUser } from '../admin.models';
import { AdminService } from '../admin.service';
import { AdminUsersComponent } from './admin-users.component';

describe('AdminUsersComponent', () => {
  let component: AdminUsersComponent;
  let api: jasmine.SpyObj<AdminService>;
  let ui: jasmine.SpyObj<AdminUi>;

  const blockedUser: AdminUser = {
    id: 9,
    email: 'blocked@example.com',
    status: 'user',
    provider: 'local',
    is_active: false,
    blocked_reason: 'Spam',
    created_at: '2026-01-01T10:00:00',
  };

  beforeEach(() => {
    api = jasmine.createSpyObj<AdminService>('AdminService', ['getUsers', 'unblockUser']);
    ui = jasmine.createSpyObj<AdminUi>('AdminUi', ['confirm', 'toast', 'errorMessage']);
    ui.toast.and.returnValue(Promise.resolve());
    ui.errorMessage.and.returnValue('Не вдалося виконати дію');

    TestBed.configureTestingModule({
      providers: [
        { provide: AdminService, useValue: api },
        { provide: AdminUi, useValue: ui },
      ],
    });
    component = TestBed.runInInjectionContext(() => new AdminUsersComponent());
    component.blockedOnly = true;
    component.items = [blockedUser];
    component.total = 1;
  });

  it('removes an unblocked user from the blocked-only list', async () => {
    ui.confirm.and.returnValue(Promise.resolve(true));
    api.unblockUser.and.returnValue(of({ ...blockedUser, is_active: true }));
    const changed = jasmine.createSpy('changed');
    component.changed.subscribe(changed);

    await component.unblock(blockedUser);

    expect(api.unblockUser).toHaveBeenCalledOnceWith(blockedUser.id);
    expect(component.items).toEqual([]);
    expect(component.total).toBe(0);
    expect(changed).toHaveBeenCalledTimes(1);
  });
});
