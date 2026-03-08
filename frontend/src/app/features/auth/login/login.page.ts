import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, LoadingController, ToastController } from '@ionic/angular';
import { Router, RouterModule } from '@angular/router';
import { FormGroup, FormBuilder, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { AuthService } from 'src/app/core/auth.service';

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
  }

  get errorControl() {
    return this.loginForm?.controls;
  }

  async signIn() {
    const loading = await this.loadingCtrl.create();
    await loading.present();

    if (this.loginForm?.valid) {
      try {
        await this.authService.login(this.loginForm.value.email, this.loginForm.value.password);
        await loading.dismiss();
        this.loginForm.reset();
        this.router.navigate(['/events']);
      } catch (err) {
        console.error(err);
        await loading.dismiss();
        const message = (err as any)?.error?.detail || 'Login failed. Please check your credentials.';
        const toast = await this.toastCtrl.create({ message, duration: 2500, color: 'danger', position: 'top' });
        await toast.present();
      }
    }
  }
}

