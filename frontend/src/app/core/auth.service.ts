import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { firstValueFrom } from 'rxjs';
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

@Injectable({ providedIn: 'root' })
export class AuthService {
  constructor(private http: HttpClient, private tokens: TokenStorageService) {}

  async isAuthenticated(): Promise<boolean> {
    return !!(await this.tokens.getToken());
  }

  async register(email: string, password: string, fullName?: string): Promise<TokenResponse> {
    const body = { email, password, full_name: fullName ?? null };
    const res = await firstValueFrom(this.http.post<TokenResponse>(`${environment.apiBaseUrl}/auth/register`, body));
    // no auto-login on register; redirect to login
    return res;
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    const form = new URLSearchParams();
    form.set('username', email);
    form.set('password', password);
    const res = await firstValueFrom(
      this.http.post<TokenResponse>(`${environment.apiBaseUrl}/auth/login`, form.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
    );
    await this.tokens.setToken(res?.access_token || null);
    return res;
  }

  async me(): Promise<UserMe> {
    return await firstValueFrom(this.http.get<UserMe>(`${environment.apiBaseUrl}/auth/me`));
  }

  logout(): void {
    void this.tokens.clear();
  }
}

