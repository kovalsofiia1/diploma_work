import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { AuthRoutingModule } from './auth-routing.module';
import { LoginPage } from './login.page';
import { RegisterPage } from './register.page';
import { ResetPasswordPage } from './reset-password.page';

@NgModule({
  imports: [CommonModule, FormsModule, IonicModule, AuthRoutingModule, LoginPage, RegisterPage, ResetPasswordPage, ],
  declarations: [],
})
export class AuthModule {}

