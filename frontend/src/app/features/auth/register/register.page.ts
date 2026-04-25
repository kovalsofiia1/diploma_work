import { Component, OnInit } from '@angular/core';
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
  regForm: FormGroup<any> = new FormGroup({});

  constructor(
    public formBuilder: FormBuilder,
    public loadingCtrl: LoadingController,
    public authService: AuthService,
    public router: Router,
    private toastCtrl: ToastController,
  ) {}

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
    });
  }

  get errorControl() {
    return this.regForm?.controls;
  }

  async signUp() {
    const loading = await this.loadingCtrl.create();
    await loading.present();

    if (this.regForm?.valid) {
      this.authService
        .register(
          this.regForm.value.email,
          this.regForm.value.password,
          this.regForm.value.fullname,
        )
        .pipe(
          take(1),
          finalize(() => {
            loading.dismiss();
          }),
        )
        .subscribe({
          next: () => {
            this.regForm.reset();
            this.router.navigate(['/auth']);
          },
          error: async (err) => {
            console.error(err);
            const message =
              (err as any)?.error?.detail ||
              'Registration failed. Please try again.';
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

