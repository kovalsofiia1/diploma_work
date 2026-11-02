import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AdminApplication,
  AdminEvent,
  AdminSummary,
  AdminUser,
  ApplicationStatus,
  AuditLogEntry,
  Page,
} from './admin.models';

type QueryValue = string | number | boolean | null | undefined;

function toParams(query: Record<string, QueryValue>): HttpParams {
  let params = new HttpParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === '') continue;
    params = params.set(key, String(value));
  }
  return params;
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private http = inject(HttpClient);
  private base = `${environment.apiBaseUrl}/admin`;

  getSummary(): Observable<AdminSummary> {
    return this.http.get<AdminSummary>(`${this.base}/summary`);
  }

  getApplications(query: { status?: ApplicationStatus | ''; skip?: number; limit?: number }): Observable<Page<AdminApplication>> {
    return this.http.get<Page<AdminApplication>>(`${this.base}/organizer-applications`, { params: toParams(query) });
  }

  approveApplication(id: number): Observable<AdminApplication> {
    return this.http.post<AdminApplication>(`${this.base}/organizer-applications/${id}/approve`, {});
  }

  rejectApplication(id: number, reason: string): Observable<AdminApplication> {
    return this.http.post<AdminApplication>(`${this.base}/organizer-applications/${id}/reject`, { reason });
  }

  getUsers(query: { search?: string; blocked?: boolean | null; skip?: number; limit?: number }): Observable<Page<AdminUser>> {
    return this.http.get<Page<AdminUser>>(`${this.base}/users`, { params: toParams(query) });
  }

  blockUser(id: number, reason: string): Observable<AdminUser> {
    return this.http.post<AdminUser>(`${this.base}/users/${id}/block`, { reason });
  }

  unblockUser(id: number): Observable<AdminUser> {
    return this.http.post<AdminUser>(`${this.base}/users/${id}/unblock`, {});
  }

  grantAdmin(id: number): Observable<AdminUser> {
    return this.http.post<AdminUser>(`${this.base}/users/${id}/grant-admin`, {});
  }

  revokeAdmin(id: number): Observable<AdminUser> {
    return this.http.post<AdminUser>(`${this.base}/users/${id}/revoke-admin`, {});
  }

  getEvents(query: { search?: string; hidden?: boolean | null; skip?: number; limit?: number }): Observable<Page<AdminEvent>> {
    return this.http.get<Page<AdminEvent>>(`${this.base}/events`, { params: toParams(query) });
  }

  hideEvent(id: number, reason: string): Observable<AdminEvent> {
    return this.http.post<AdminEvent>(`${this.base}/events/${id}/hide`, { reason });
  }

  unhideEvent(id: number): Observable<AdminEvent> {
    return this.http.post<AdminEvent>(`${this.base}/events/${id}/unhide`, {});
  }

  getAuditLog(query: { action?: string; skip?: number; limit?: number }): Observable<Page<AuditLogEntry>> {
    return this.http.get<Page<AuditLogEntry>>(`${this.base}/audit-log`, { params: toParams(query) });
  }
}
