import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, NavController } from '@ionic/angular';
import { Router } from '@angular/router';
import { AuthService, UserMe } from '../../core/auth.service';
import { ToastController } from '@ionic/angular';

@Component({
  selector: 'app-profile',
  templateUrl: './profile.page.html',
  styleUrls: ['./profile.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule],
})
export class ProfilePage implements OnInit {
  user?: UserMe;

  constructor(
    private auth: AuthService,
    private router: Router,
    private toastCtrl: ToastController,
    private navCtrl: NavController
  ) {}

  async ngOnInit(): Promise<void> {
    await this.loadProfile();
  }

  async loadProfile(): Promise<void> {
    try {
      this.user = await this.auth.me();
    } catch (err) {
      const toast = await this.toastCtrl.create({
        message: 'Будь ласка, увійдіть до облікового запису.',
        duration: 2500,
        color: 'warning',
        position: 'top',
      });
      await toast.present();
      this.router.navigate(['/auth']);
    }
  }

  onAnyClick(event: Event): void {
    console.log('profile content click', event?.target);
  }

  async logout(): Promise<void> {
    console.log('logout button clicked');
    await this.auth.logout();
    await this.navCtrl.navigateRoot('/auth');
  }
}

