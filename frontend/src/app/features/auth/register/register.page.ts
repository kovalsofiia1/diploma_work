import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { IonicModule, LoadingController, ToastController } from '@ionic/angular';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from 'src/app/core/auth.service';
import { finalize, take } from 'rxjs';

@Component({
  selector: 'app-register',
  templateUrl: './register.page.html',
  styleUrls: ['./register.page.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, IonicModule, ReactiveFormsModule, RouterModule],
})
export class RegisterPage implements OnInit {
  formBuilder = inject(FormBuilder);
  loadingCtrl = inject(LoadingController);
  authService = inject(AuthService);
  router = inject(Router);
  private toastCtrl = inject(ToastController);

  regForm: FormGroup<any> = new FormGroup({});
  verificationStep = false;
  showPassword = false;

  ngOnInit() {
    this.regForm = this.formBuilder.group({
      fullname: ['', [Validators.required]],
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
      verificationCode: ['', [Validators.required, Validators.pattern('^[0-9]{4,12}$')]],
    });
  }

  get errorControl() {
    return this.regForm?.controls;
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  async signUp() {
    const loading = await this.loadingCtrl.create();
    await loading.present();

    if (this.canSubmitRegister) {
      if (!this.verificationStep) {
        this.authService
          .sendRegistrationCode(this.regForm.value.email)
          .pipe(
            take(1),
            finalize(() => {
              loading.dismiss();
            }),
          )
          .subscribe({
            next: async () => {
              this.verificationStep = true;
              await this.presentToast('Verification code sent to your email.', 'success');
            },
            error: async (err) => {
              console.error(err);
              const message =
                (err as any)?.error?.detail ||
                'Failed to send verification code.';
              await this.presentToast(message, 'danger');
            },
          });
        return;
      }

      this.authService
        .register(
          this.regForm.value.email,
          this.regForm.value.password,
          this.regForm.value.verificationCode,
          this.regForm.value.fullname,
        )
        .pipe(
          take(1),
          finalize(() => {
            loading.dismiss();
          }),
        )
        .subscribe({
          next: async () => {
            this.regForm.reset();
            this.verificationStep = false;
            await this.presentToast('Registration completed. Please sign in.', 'success');
            this.router.navigate(['/auth']);
          },
          error: async (err) => {
            console.error(err);
            const message =
              (err as any)?.error?.detail ||
              'Registration failed. Please try again.';
            await this.presentToast(message, 'danger');
          },
        });
    } else {
      await loading.dismiss();
    }
  }

  get canSubmitRegister(): boolean {
    const baseValid =
      !!this.regForm.value.fullname &&
      this.regForm.controls['email'].valid &&
      this.regForm.controls['password'].valid;
    if (!this.verificationStep) return baseValid;
    return baseValid && this.regForm.controls['verificationCode'].valid;
  }

  async signUpWithGoogle(): Promise<void> {
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

