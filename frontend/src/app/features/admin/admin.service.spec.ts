import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { AdminService } from './admin.service';

describe('AdminService', () => {
  let service: AdminService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AdminService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('drops empty filters from the query string', () => {
    service.getUsers({ search: '', blocked: null, skip: 0, limit: 30 }).subscribe();
    const req = http.expectOne((r) => r.url === '/api/admin/users');
    expect(req.request.params.keys().sort()).toEqual(['limit', 'skip']);
    req.flush({ items: [], total: 0 });
  });

  it('sends the reason when blocking a user', () => {
    service.blockUser(7, 'Spam').subscribe();
    const req = http.expectOne('/api/admin/users/7/block');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ reason: 'Spam' });
    req.flush({});
  });

  it('sends the reason when rejecting an application', () => {
    service.rejectApplication(3, 'No experience').subscribe();
    const req = http.expectOne('/api/admin/organizer-applications/3/reject');
    expect(req.request.body).toEqual({ reason: 'No experience' });
    req.flush({});
  });

  it('grants and revokes the admin role', () => {
    service.grantAdmin(4).subscribe();
    http.expectOne('/api/admin/users/4/grant-admin').flush({});
    service.revokeAdmin(4).subscribe();
    http.expectOne('/api/admin/users/4/revoke-admin').flush({});
  });

  it('filters events by visibility', () => {
    service.getEvents({ hidden: true }).subscribe();
    const req = http.expectOne((r) => r.url === '/api/admin/events');
    expect(req.request.params.get('hidden')).toBe('true');
    req.flush({ items: [], total: 0 });
  });
});
