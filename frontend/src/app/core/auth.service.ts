import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { catchError, concatMap, firstValueFrom, map, Observable, of } from 'rxjs';
import { TokenStorageService } from './token-storage.service';

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserMe {
  id: number;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  status: 'admin' | 'verified user' | 'user';
}

export interface UserCitiesResponse {
  cities: string[];
}

export interface UserProfileStats {
  created_events: number;
  visited_events: number;
  purchased_tickets: number;
}

export interface GoogleAuthStartResponse {
  authorization_url: string;
}

export interface ApiMessageResponse {
  message: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  constructor(private http: HttpClient, private tokens: TokenStorageService) { }

  async isAuthenticated(): Promise<boolean> {
    return firstValueFrom(this.isAuthenticated$());
  }

  isAuthenticated$(): Observable<boolean> {
    return this.tokens.getToken$().pipe(map((token: string | null) => !!token));
  }

  sendRegistrationCode(email: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${environment.apiBaseUrl}/auth/register/send-code`, {
      email,
    });
  }

  register(
    email: string,
    password: string,
    verificationCode: string,
    fullName?: string,
  ): Observable<TokenResponse> {
    const body = {
      email,
      password,
      full_name: fullName ?? null,
      verification_code: verificationCode,
    };
    return this.http.post<TokenResponse>(`${environment.apiBaseUrl}/auth/register`, body);
  }

  login(email: string, password: string): Observable<TokenResponse> {
    const form = new URLSearchParams();
    form.set('username', email);
    form.set('password', password);
    return this.http
      .post<TokenResponse>(`${environment.apiBaseUrl}/auth/login`, form.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      .pipe(
        concatMap((res) =>
          this.tokens.setToken$(res?.access_token || null).pipe(map(() => res)),
        ),
      );
  }

  getGoogleAuthorizationUrl(): Observable<string> {
    return this.http
      .get<GoogleAuthStartResponse>(`${environment.apiBaseUrl}/auth/google/start`)
      .pipe(map((res) => res?.authorization_url || ''));
  }

  loginWithGoogleCode(code: string): Observable<TokenResponse> {
    return this.http
      .get<TokenResponse>(`${environment.apiBaseUrl}/auth/google/callback`, {
        params: { code },
      })
      .pipe(
        concatMap((res) =>
          this.tokens.setToken$(res?.access_token || null).pipe(map(() => res)),
        ),
      );
  }

  me(): Observable<UserMe> {
    return this.http.get<UserMe>(`${environment.apiBaseUrl}/auth/me`);
  }

  logout(): Observable<void> {
    // Clear token first for instant UI effect
    return this.tokens.clear$().pipe(
      concatMap(() =>
        this.http.post<void>(`${environment.apiBaseUrl}/auth/logout`, {}).pipe(
          catchError(() => of(void 0)),
        ),
      ),
      catchError(() => of(void 0)),
    );
  }

  setCitiesSubscription(cities: string[]): Observable<string[]> {
    return this.http
      .post<UserCitiesResponse>(`${environment.apiBaseUrl}/auth/me/cities`, {
        cities,
      })
      .pipe(map((res) => res?.cities ?? []));
  }

  getCitiesSubscription(): Observable<string[]> {
    return this.http
      .get<UserCitiesResponse>(`${environment.apiBaseUrl}/auth/me/cities`)
      .pipe(map((res) => res?.cities ?? []));
  }

  getMyStats(): Observable<UserProfileStats> {
    return this.http.get<UserProfileStats>(`${environment.apiBaseUrl}/auth/me/stats`);
  }

  sendPasswordResetCode(email: string): Observable<ApiMessageResponse> {
    return this.http.post<ApiMessageResponse>(`${environment.apiBaseUrl}/auth/password/send-code`, {
      email,
    });
  }

  resetPasswordWithCode(email: string, code: string, newPassword: string): Observable<ApiMessageResponse> {
    return this.http.post<ApiMessageResponse>(`${environment.apiBaseUrl}/auth/password/reset`, {
      email,
      code,
      new_password: newPassword,
    });
  }
}

