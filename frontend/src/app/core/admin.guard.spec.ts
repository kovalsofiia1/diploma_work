import { TestBed } from '@angular/core/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AdminGuard } from './admin.guard';
import { AuthService, UserMe } from './auth.service';

describe('AdminGuard', () => {
  let me: jasmine.Spy;

  const user = (status: UserMe['status']): UserMe => ({ id: 1, email: 'a@b.c', is_active: true, status });

  beforeEach(() => {
    me = jasmine.createSpy('me');
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: AuthService, useValue: { me } }],
    });
  });

  it('lets an admin in', async () => {
    me.and.returnValue(of(user('admin')));
    expect(await TestBed.inject(AdminGuard).canActivate()).toBeTrue();
  });

  it('sends an organizer back to home', async () => {
    me.and.returnValue(of(user('verified user')));
    const result = await TestBed.inject(AdminGuard).canActivate();
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe('/tabs/home');
  });

  it('sends a signed-out visitor to sign-in', async () => {
    me.and.returnValue(throwError(() => new Error('401')));
    const result = await TestBed.inject(AdminGuard).canActivate();
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe('/auth');
  });
});
