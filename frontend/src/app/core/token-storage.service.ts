import { Injectable } from '@angular/core';
import { Preferences } from '@capacitor/preferences';
import { BehaviorSubject, Observable, defer, from, map, of, tap } from 'rxjs';

const TOKEN_KEY = 'access_token';

@Injectable({ providedIn: 'root' })
export class TokenStorageService {
  private readonly tokenSubject = new BehaviorSubject<string | null>(null);
  readonly token$ = this.tokenSubject.asObservable();
  private hydrated = false;

  constructor() {
    this.hydrateToken$().subscribe();
  }

  getToken$(): Observable<string | null> {
    if (this.hydrated) {
      return of(this.tokenSubject.value);
    }
    return this.hydrateToken$();
  }

  setToken$(token: string | null): Observable<void> {
    const operation$ = token
      ? defer(() => from(Preferences.set({ key: TOKEN_KEY, value: token })))
      : defer(() => from(Preferences.remove({ key: TOKEN_KEY })));

    return operation$.pipe(
      tap(() => {
        this.hydrated = true;
        this.tokenSubject.next(token ?? null);
      }),
      map(() => void 0),
    );
  }

  clear$(): Observable<void> {
    return this.setToken$(null);
  }

  getTokenSnapshot(): string | null {
    return this.tokenSubject.value;
  }

  private hydrateToken$(): Observable<string | null> {
    return defer(() => from(Preferences.get({ key: TOKEN_KEY }))).pipe(
      map(({ value }) => value ?? null),
      tap((token) => {
        this.hydrated = true;
        this.tokenSubject.next(token);
      }),
    );
  }
}

