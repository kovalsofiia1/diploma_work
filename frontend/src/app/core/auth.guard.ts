import { Injectable, inject } from '@angular/core';
import { CanActivate, Router, UrlTree } from '@angular/router';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  private auth = inject(AuthService);
  private router = inject(Router);


  async canActivate(): Promise<boolean | UrlTree> {
    const ok = await this.auth.isAuthenticated();
    return ok ? true : this.router.parseUrl('/auth');
  }
}

