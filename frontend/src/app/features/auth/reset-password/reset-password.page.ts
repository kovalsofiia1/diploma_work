import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { IonicModule, LoadingController, ToastController } from '@ionic/angular';
import { Router } from '@angular/router';
import { AuthService } from 'src/app/core/auth.service';
import { finalize, take } from 'rxjs';

@Component({
  selector: 'app-reset-password',
  templateUrl: './reset-password.page.html',
  styleUrls: ['./reset-password.page.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, IonicModule, ReactiveFormsModule],
})
export class ResetPasswordPage implements OnInit {
  resetForm: FormGroup<any> = new FormGroup({});
  verificationStep = false;

  constructor(
    public formBuilder: FormBuilder,
    public loadingCtrl: LoadingController,
    public authService: AuthService,
    public router: Router,
    private toastCtrl: ToastController,
  ) {}

  ngOnInit() {
    this.resetForm = this.formBuilder.group({
      email: [
        '',
        [
          Validators.required,
          Validators.email,
          Validators.pattern('^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$'),
        ],
      ],
      code: ['', [Validators.required, Validators.pattern('^[0-9]{4,12}$')]],
      newPassword: [
        '',
        [
          Validators.required,
          Validators.pattern('(?=.*\\d)(?=.*[a-z])(?=.*[0-9])(?=.*[A-Z]).{8,}'),
        ],
      ],
    });
  }

  get errorControl() {
    return this.resetForm?.controls;
  }

  async resetPassword() {
    const loading = await this.loadingCtrl.create();
    await loading.present();

    if (!this.canSubmit) {
      await loading.dismiss();
      return;
    }

    if (!this.verificationStep) {
      this.authService
        .sendPasswordResetCode(this.resetForm.value.email)
        .pipe(
          take(1),
          finalize(() => {
            loading.dismiss();
          }),
        )
        .subscribe({
          next: async (res) => {
            this.verificationStep = true;
            await this.presentToast(res?.message || 'Reset code sent.', 'success');
          },
          error: async (err) => {
            const message = (err as any)?.error?.detail || 'Failed to send reset code.';
            await this.presentToast(message, 'danger');
          },
        });
      return;
    }

    this.authService
      .resetPasswordWithCode(
        this.resetForm.value.email,
        this.resetForm.value.code,
        this.resetForm.value.newPassword,
      )
      .pipe(
        take(1),
        finalize(() => {
          loading.dismiss();
        }),
      )
      .subscribe({
        next: async (res) => {
          await this.presentToast(res?.message || 'Password updated.', 'success');
          this.resetForm.reset();
          this.verificationStep = false;
          this.router.navigate(['/auth']);
        },
        error: async (err) => {
          const message = (err as any)?.error?.detail || 'Failed to reset password.';
          await this.presentToast(message, 'danger');
        },
      });
  }

  get canSubmit(): boolean {
    const emailValid = this.resetForm.controls['email'].valid;
    if (!this.verificationStep) return emailValid;
    return emailValid && this.resetForm.controls['code'].valid && this.resetForm.controls['newPassword'].valid;
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