import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { IonicModule, ToastController } from '@ionic/angular';
import { AppHeaderComponent } from 'src/app/shared/components/app-header/app-header.component';
import { PopularEventItem } from 'src/app/shared/interfaces/events/events.interface';

type Theme = PopularEventItem['theme'];

@Component({
  selector: 'app-event-create-page',
  templateUrl: './event-create.page.html',
  styleUrls: ['./event-create.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule, RouterModule, ReactiveFormsModule, AppHeaderComponent],
})
export class EventCreatePage {
  submitting = false;

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
    imageUrl: ['assets/shapes.svg'],
    organizer: [''],
  });

  constructor(
    private fb: FormBuilder,
    private toastCtrl: ToastController,
    private router: Router
  ) {}

  get preview(): PopularEventItem {
    const v = this.form.getRawValue();
    return {
      title: (v.title ?? 'Нова подія').toString(),
      description: (v.description ?? 'Опис події з’явиться тут.').toString(),
      city: (v.city ?? 'Місто').toString(),
      date: `${v.date || '—'} ${v.time || ''}`.trim(),
      uid: 'draft:new',
      theme: (v.theme ?? 'art') as Theme,
    };
  }

  get imageUrl(): string {
    const url = this.form.controls.imageUrl.value?.trim();
    return url ? url : 'assets/shapes.svg';
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
      await this.router.navigate(['/tabs/events']);
    } finally {
      this.submitting = false;
    }
  }
}

