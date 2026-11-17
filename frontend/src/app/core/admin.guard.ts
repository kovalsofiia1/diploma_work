import { Injectable, inject } from '@angular/core';
import { CanActivate, Router, UrlTree } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';

/** UI-level gate only; every /admin API route is also checked on the server. */
@Injectable({ providedIn: 'root' })
export class AdminGuard implements CanActivate {
  private auth = inject(AuthService);
  private router = inject(Router);

  async canActivate(): Promise<boolean | UrlTree> {
    try {
      const user = await firstValueFrom(this.auth.me());
      return user.status === 'admin' ? true : this.router.parseUrl('/tabs/home');
    } catch {
      return this.router.parseUrl('/auth');
    }
  }
}
