import { Injectable, inject } from '@angular/core';
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
  date_of_birth?: string | null;
  description?: string | null;
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

export type OrganizerApplicationStatus =
  | 'not_requested'
  | 'pending'
  | 'approved'
  | 'rejected';

export interface OrganizerApplication {
  status: OrganizerApplicationStatus;
  can_create_events: boolean;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
}

export interface OrganizerApplicationSubmitPayload {
  organization_name: string;
  contact_phone: string;
  motivation: string;
  experience?: string;
}

export interface OrganizerProfile {
  organization_name: string;
  contact_phone: string;
  motivation: string;
  experience?: string | null;
}

export interface UserProfileUpdatePayload {
  full_name?: string | null;
  date_of_birth?: string | null;
  description?: string | null;
}

export interface GoogleAuthStartResponse {
  authorization_url: string;
}

export interface ApiMessageResponse {
  message: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private tokens = inject(TokenStorageService);


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

  updateMe(payload: UserProfileUpdatePayload): Observable<UserMe> {
    return this.http.patch<UserMe>(`${environment.apiBaseUrl}/auth/me`, payload);
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

  getOrganizerApplication(): Observable<OrganizerApplication> {
    return this.http.get<OrganizerApplication>(`${environment.apiBaseUrl}/auth/me/organizer-application`);
  }

  submitOrganizerApplication(
    payload: OrganizerApplicationSubmitPayload,
  ): Observable<OrganizerApplication> {
    return this.http.post<OrganizerApplication>(
      `${environment.apiBaseUrl}/auth/me/organizer-application`,
      payload,
    );
  }

  getOrganizerProfile(): Observable<OrganizerProfile> {
    return this.http.get<OrganizerProfile>(`${environment.apiBaseUrl}/auth/me/organizer-profile`);
  }

  updateOrganizerProfile(payload: OrganizerProfile): Observable<OrganizerProfile> {
    return this.http.patch<OrganizerProfile>(`${environment.apiBaseUrl}/auth/me/organizer-profile`, payload);
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

