import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { AdminUi } from '../admin-ui';
import { AdminEvent } from '../admin.models';
import { AdminService } from '../admin.service';
import { AdminEventsComponent } from './admin-events.component';

describe('AdminEventsComponent', () => {
  let component: AdminEventsComponent;
  let api: jasmine.SpyObj<AdminService>;
  let ui: jasmine.SpyObj<AdminUi>;

  const visibleEvent: AdminEvent = {
    id: 11,
    uid: 'event-11',
    name: 'Concert',
    city: 'Kyiv',
    source_type: 'INTERNAL',
    status: 'ACTIVE',
    is_hidden: false,
  };

  beforeEach(() => {
    api = jasmine.createSpyObj<AdminService>('AdminService', ['getEvents', 'hideEvent']);
    ui = jasmine.createSpyObj<AdminUi>('AdminUi', ['askReason', 'toast', 'errorMessage']);
    ui.toast.and.returnValue(Promise.resolve());
    ui.errorMessage.and.returnValue('Не вдалося виконати дію');

    TestBed.configureTestingModule({
      providers: [
        { provide: AdminService, useValue: api },
        { provide: AdminUi, useValue: ui },
      ],
    });
    component = TestBed.runInInjectionContext(() => new AdminEventsComponent());
    component.visibility = 'visible';
    component.items = [visibleEvent];
    component.total = 1;
  });

  it('removes a hidden event from the visible-only list', async () => {
    ui.askReason.and.returnValue(Promise.resolve('Incorrect event details'));
    api.hideEvent.and.returnValue(
      of({ ...visibleEvent, is_hidden: true, hidden_reason: 'Incorrect event details' }),
    );
    const changed = jasmine.createSpy('changed');
    component.changed.subscribe(changed);

    await component.hide(visibleEvent);

    expect(api.hideEvent).toHaveBeenCalledOnceWith(visibleEvent.id, 'Incorrect event details');
    expect(component.items).toEqual([]);
    expect(component.total).toBe(0);
    expect(changed).toHaveBeenCalledTimes(1);
  });
});
