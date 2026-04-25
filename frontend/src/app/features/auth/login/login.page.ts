import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, LoadingController, ToastController } from '@ionic/angular';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormGroup, FormBuilder, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { AuthService } from 'src/app/core/auth.service';
import { finalize, take } from 'rxjs';

@Component({
  selector: 'app-login',
  templateUrl: './login.page.html',
  styleUrls: ['./login.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule, RouterModule, FormsModule,  ReactiveFormsModule,],
})
export class LoginPage implements OnInit{
  loginForm: FormGroup<any> = new FormGroup({});

  constructor(
    public formBuilder: FormBuilder,
    public loadingCtrl: LoadingController,
    public authService: AuthService,
    public router: Router,
    private route: ActivatedRoute,
    private toastCtrl: ToastController,
  ) {}

  ngOnInit() {
    this.loginForm = this.formBuilder.group({
      email: [
        '',
        [
          Validators.required,
          Validators.email,
          Validators.pattern('^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$'),
        ],
      ],
      password: [
        '',
        [
          Validators.required,
          Validators.pattern('(?=.*\d)(?=.*[a-z])(?=.*[0-9])(?=.*[A-Z]).{8,}'),
        ],
      ],
    });
    this.tryCompleteGoogleLogin();
  }

  get errorControl() {
    return this.loginForm?.controls;
  }

  async signIn() {
    const loading = await this.loadingCtrl.create();
    await loading.present();

    if (this.loginForm?.valid) {
      this.authService
        .login(this.loginForm.value.email, this.loginForm.value.password)
        .pipe(
          take(1),
          finalize(() => {
            loading.dismiss();
          }),
        )
        .subscribe({
          next: () => {
            this.loginForm.reset();
            this.router.navigate(['/events']);
          },
          error: async (err) => {
            console.error(err);
            const message =
              (err as any)?.error?.detail ||
              'Login failed. Please check your credentials.';
            const toast = await this.toastCtrl.create({
              message,
              duration: 2500,
              color: 'danger',
              position: 'top',
            });
            await toast.present();
          },
        });
    }
  }

  async signInWithGoogle(): Promise<void> {
    const loading = await this.loadingCtrl.create();
    await loading.present();
    this.authService
      .getGoogleAuthorizationUrl()
      .pipe(
        take(1),
        finalize(() => {
          loading.dismiss();
        }),
      )
      .subscribe({
        next: (url) => {
          if (!url) {
            this.presentToast('Google OAuth URL is empty.', 'danger');
            return;
          }
          window.location.href = url;
        },
        error: () => {
          this.presentToast('Google login is not configured on backend.', 'danger');
        },
      });
  }

  private tryCompleteGoogleLogin(): void {
    this.route.queryParamMap.pipe(take(1)).subscribe((params) => {
      const code = params.get('code');
      if (!code) return;

      this.authService
        .loginWithGoogleCode(code)
        .pipe(take(1))
        .subscribe({
          next: () => {
            this.router.navigate(['/events']);
          },
          error: async (err) => {
            const message =
              (err as any)?.error?.detail || 'Google login failed. Please try again.';
            await this.presentToast(message, 'danger');
          },
        });
    });
  }

  private async presentToast(message: string, color: 'danger' | 'success'): Promise<void> {
    const toast = await this.toastCtrl.create({
      message,
      duration: 2500,
      color,
      position: 'top',
    });
    await toast.present();
  }
}

