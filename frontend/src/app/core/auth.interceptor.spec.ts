import { TestBed } from '@angular/core/testing';
import { HTTP_INTERCEPTORS, HttpClient, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { ToastController } from '@ionic/angular';
import { of } from 'rxjs';

import { AuthInterceptor } from './auth.interceptor';
import { TokenStorageService } from './token-storage.service';

describe('AuthInterceptor', () => {
  let http: HttpClient;
  let backend: HttpTestingController;
  let tokens: jasmine.SpyObj<TokenStorageService>;
  let router: Router;

  beforeEach(() => {
    tokens = jasmine.createSpyObj<TokenStorageService>('TokenStorageService', ['getToken$', 'clear$']);
    tokens.getToken$.and.returnValue(of('token-123'));
    tokens.clear$.and.returnValue(of(void 0));
    const toast = { present: () => Promise.resolve() };

    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
        { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true },
        { provide: TokenStorageService, useValue: tokens },
        { provide: ToastController, useValue: { create: () => Promise.resolve(toast) } },
      ],
    });
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigateByUrl').and.resolveTo(true);
  });

  it('adds the bearer token', () => {
    http.get('/api/auth/me').subscribe();
    const req = backend.expectOne('/api/auth/me');
    expect(req.request.headers.get('Authorization')).toBe('Bearer token-123');
    req.flush({});
  });

  it('signs out a user whose account was blocked', async () => {
    http.get('/api/auth/me').subscribe({ error: () => undefined });
    backend.expectOne('/api/auth/me').flush({ detail: 'Account is blocked' }, { status: 403, statusText: 'Forbidden' });
    await new Promise((resolve) => setTimeout(resolve));

    expect(tokens.clear$).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/auth');
  });

  it('keeps the session on an ordinary 403', async () => {
    http.get('/api/admin/users').subscribe({ error: () => undefined });
    backend.expectOne('/api/admin/users').flush({ detail: 'Admin access required' }, { status: 403, statusText: 'Forbidden' });
    await new Promise((resolve) => setTimeout(resolve));

    expect(tokens.clear$).not.toHaveBeenCalled();
  });
});
