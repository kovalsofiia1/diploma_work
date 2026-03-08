import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, NavController, ToastController } from '@ionic/angular';

type VerifyStatus = 'idle' | 'success' | 'error';

@Component({
  selector: 'app-verify-ticket',
  templateUrl: './verify-ticket.page.html',
  styleUrls: ['./verify-ticket.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule],
})
export class VerifyTicketPage {
  code = '';
  status: VerifyStatus = 'idle';
  message = '';

  constructor(private navCtrl: NavController, private toastCtrl: ToastController) {}

  back(): void {
    this.navCtrl.back();
  }

  setCodeFromInput(ev: any): void {
    this.code = (ev?.detail?.value ?? '').toString();
    if (this.status !== 'idle') {
      this.status = 'idle';
      this.message = '';
    }
  }

  async simulateScan(): Promise<void> {
    this.code = 'QR-EVENT-2026-001-ABC123';
    await this.verify();
  }

  async verify(): Promise<void> {
    const raw = (this.code ?? '').toString().trim();
    if (!raw) {
      this.status = 'error';
      this.message = 'Введіть або відскануйте QR-код.';
      return;
    }

    const ok = raw.startsWith('QR-') || raw.startsWith('TKT-') || raw.includes('EVENT');
    if (ok) {
      this.status = 'success';
      this.message = 'Квиток дійсний. Перевірку успішно пройдено.';
      const toast = await this.toastCtrl.create({
        message: 'Квиток підтверджено.',
        duration: 1200,
        position: 'top',
        color: 'success',
      });
      await toast.present();
      return;
    }

    this.status = 'error';
    this.message = 'Не вдалося підтвердити квиток. Перевірте код і спробуйте ще раз.';
  }
}

