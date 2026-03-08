import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { IonicModule, NavController, ToastController } from '@ionic/angular';
import { PopularEventItem } from 'src/app/shared/interfaces/events/events.interface';

type Theme = PopularEventItem['theme'];

@Component({
  selector: 'app-event-create-page',
  templateUrl: './event-create.page.html',
  styleUrls: ['./event-create.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule, ReactiveFormsModule],
})
export class EventCreatePage {
  submitting = false;
  coverPreviewUrl: string | null = null;

  themes: Array<{ value: Theme; label: string }> = [
    { value: 'art', label: 'Майстер-клас / Арт' },
    { value: 'games', label: 'Ігри / Активності' },
    { value: 'cinema', label: 'Кіно / Перегляд' },
  ];

  form = this.fb.group({
    title: ['', [Validators.required, Validators.minLength(3)]],
    description: ['', [Validators.required, Validators.minLength(20)]],
    city: ['', [Validators.required, Validators.minLength(2)]],
    address: [''],
    date: ['', [Validators.required]],
    time: ['', [Validators.required]],
    capacity: [50, [Validators.required, Validators.min(1), Validators.max(5000)]],
    price: [0, [Validators.required, Validators.min(0), Validators.max(1000000)]],
    theme: ['art' as Theme, [Validators.required]],
    imageUrl: [''],
    organizer: [''],
  });

  constructor(
    private fb: FormBuilder,
    private toastCtrl: ToastController,
    private router: Router,
    private navCtrl: NavController
  ) {}

  get imageUrl(): string {
    const url = this.form.controls.imageUrl.value?.trim();
    return url ? url : '';
  }

  get coverSrc(): string | null {
    return this.coverPreviewUrl || this.imageUrl || null;
  }

  back(): void {
    this.navCtrl.back();
  }

  onCoverPicked(ev: Event): void {
    const input = ev.target as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file) return;

    if (this.coverPreviewUrl) {
      URL.revokeObjectURL(this.coverPreviewUrl);
    }

    this.coverPreviewUrl = URL.createObjectURL(file);
  }

  async submit(): Promise<void> {
    if (this.submitting) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) {
      const toast = await this.toastCtrl.create({
        message: 'Перевірте поля форми — деякі з них заповнені некоректно.',
        duration: 1600,
        position: 'top',
      });
      await toast.present();
      return;
    }

    this.submitting = true;
    try {
      // Demo-only: тут можна підключити бекенд/контракт.
      const toast = await this.toastCtrl.create({
        message: 'Подію створено (демо).',
        duration: 1400,
        position: 'top',
        color: 'success',
      });
      await toast.present();
      await this.router.navigate(['/tabs/explore']);
    } finally {
      this.submitting = false;
    }
  }
}

