import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { AdminUi } from '../admin-ui';
import { AdminApplication } from '../admin.models';
import { AdminService } from '../admin.service';
import { AdminApplicationsComponent } from './admin-applications.component';

describe('AdminApplicationsComponent', () => {
  let component: AdminApplicationsComponent;
  let api: jasmine.SpyObj<AdminService>;
  let ui: jasmine.SpyObj<AdminUi>;

  const application: AdminApplication = {
    id: 3,
    user_id: 7,
    user_email: 'organizer@example.com',
    organization_name: 'Event Org',
    contact_phone: '+380501234567',
    motivation: 'We organize events.',
    status: 'pending',
    submitted_at: '2026-01-01T10:00:00',
  };

  beforeEach(() => {
    api = jasmine.createSpyObj<AdminService>('AdminService', [
      'getApplications',
      'approveApplication',
      'rejectApplication',
    ]);
    ui = jasmine.createSpyObj<AdminUi>('AdminUi', ['confirm', 'askReason', 'toast', 'errorMessage']);
    ui.toast.and.returnValue(Promise.resolve());
    ui.errorMessage.and.returnValue('Не вдалося виконати дію');

    TestBed.configureTestingModule({
      providers: [
        { provide: AdminService, useValue: api },
        { provide: AdminUi, useValue: ui },
      ],
    });
    component = TestBed.runInInjectionContext(() => new AdminApplicationsComponent());
    component.items = [application];
    component.total = 1;
  });

  it('removes an approved application from the pending list', async () => {
    ui.confirm.and.returnValue(Promise.resolve(true));
    api.approveApplication.and.returnValue(of({ ...application, status: 'approved' }));
    const changed = jasmine.createSpy('changed');
    component.changed.subscribe(changed);

    await component.approve(application);

    expect(api.approveApplication).toHaveBeenCalledOnceWith(application.id);
    expect(component.items).toEqual([]);
    expect(component.total).toBe(0);
    expect(changed).toHaveBeenCalledTimes(1);
  });

  it('sends the rejection reason and removes the rejected application from the pending list', async () => {
    ui.askReason.and.returnValue(Promise.resolve('No experience'));
    api.rejectApplication.and.returnValue(of({ ...application, status: 'rejected' }));

    await component.reject(application);

    expect(api.rejectApplication).toHaveBeenCalledOnceWith(application.id, 'No experience');
    expect(component.items).toEqual([]);
    expect(component.total).toBe(0);
  });
});
