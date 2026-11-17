import { Injectable, inject } from '@angular/core';
import { HttpErrorResponse, HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Router } from '@angular/router';
import { ToastController } from '@ionic/angular';
import { Observable, catchError, firstValueFrom, switchMap, throwError } from 'rxjs';
import { TokenStorageService } from './token-storage.service';
import { BLOCKED_ACCOUNT_DETAIL, BLOCKED_ACCOUNT_MESSAGE } from './auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private tokens = inject(TokenStorageService);
  private router = inject(Router);
  private toastCtrl = inject(ToastController);
  private signingOut = false;


  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return this.tokens.getToken$().pipe(
      switchMap((token) => {
        if (token) {
          const authReq = req.clone({
            setHeaders: {
              Authorization: `Bearer ${token}`,
            },
          });
          return next.handle(authReq).pipe(
            catchError((err: unknown) => {
              if (err instanceof HttpErrorResponse && err.status === 403 && err.error?.detail === BLOCKED_ACCOUNT_DETAIL) {
                void this.signOutBlockedUser();
              }
              return throwError(() => err);
            }),
          );
        }
        return next.handle(req);
      })
    );
  }

  /** The account was blocked mid-session: drop the token and send the user to sign-in. */
  private async signOutBlockedUser(): Promise<void> {
    if (this.signingOut) return;
    this.signingOut = true;
    try {
      await firstValueFrom(this.tokens.clear$());
      const toast = await this.toastCtrl.create({
        message: BLOCKED_ACCOUNT_MESSAGE,
        color: 'danger',
        duration: 4000,
        position: 'top',
      });
      await toast.present();
      await this.router.navigateByUrl('/auth');
    } finally {
      this.signingOut = false;
    }
  }
}
