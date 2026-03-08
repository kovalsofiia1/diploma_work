import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { IonicModule, LoadingController } from '@ionic/angular';
import { Router } from '@angular/router';
import { AuthService } from 'src/app/core/auth.service';

@Component({
  selector: 'app-reset-password',
  templateUrl: './reset-password.page.html',
  styleUrls: ['./reset-password.page.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, IonicModule, ReactiveFormsModule],
})
export class ResetPasswordPage implements OnInit {
  regForm: FormGroup<any> = new FormGroup({});

  constructor(
    public formBuilder: FormBuilder,
    public loadingCtrl: LoadingController,
    public authService: AuthService,
    public router: Router,
  ) {}

  ngOnInit() {
    this.regForm = this.formBuilder.group({
      email: [
        '',
        [
          Validators.required,
          Validators.email,
          Validators.pattern('^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$'),
        ],
      ],
    });
  }

  get errorControl() {
    return this.regForm?.controls;
  }

  async resetPassword() {
    if (this.regForm?.valid) {
      this.router.navigate(['/auth']);
      // await this.authService
      //   .resetPassword(this.regForm.value.email)
      //   .then(() => {
      //     this.router.navigate(['/login']);
      //   })
      //   .catch((err) => console.log(err));
    }
  
  }
}