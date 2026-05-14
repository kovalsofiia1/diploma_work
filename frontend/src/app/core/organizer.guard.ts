import { Injectable, inject } from '@angular/core';
import { CanActivate, Router, UrlTree } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class OrganizerGuard implements CanActivate {
  private auth = inject(AuthService);
  private router = inject(Router);


  async canActivate(): Promise<boolean | UrlTree> {
    try {
      const user = await firstValueFrom(this.auth.me());
      const approved = user.status === 'verified user' || user.status === 'admin';
      return approved ? true : this.router.parseUrl('/tabs/profile');
    } catch {
      return this.router.parseUrl('/auth');
    }
  }
}
