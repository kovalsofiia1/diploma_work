import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import {
  FormArray,
  FormBuilder,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { IonicModule, NavController, ToastController } from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import { SearchableDropdownComponent } from 'src/app/shared/components/searchable-dropdown/searchable-dropdown.component';
import { EventCreateRequest } from '../../interfaces/events.interface';
import { EventsService } from '../../services/events.service';

type AdditionalFieldForm = FormGroup<{
  title: FormControl<string>;
  info: FormControl<string>;
}>;

type AdditionalFieldItem = {
  title: string;
  info: string;
};

@Component({
  selector: 'app-event-create-page',
  templateUrl: './event-create.page.html',
  styleUrls: ['./event-create.page.scss'],
  standalone: true,
  imports: [
    CommonModule,
    IonicModule,
    ReactiveFormsModule,
    SearchableDropdownComponent,
  ],
})
export class EventCreatePage {
  submitting = false;
  coverPreviewUrl: string | null = null;
  selectedCoverFile: File | null = null;
  categoriesMultiple = true;
  readonly categories: string[] = [
    'Концерт',
    'Фестиваль',
    'Конференція',
    'Воркшоп',
    'Майстер-клас',
    'Виставка',
    'Нетворкінг',
    'Спорт',
    'Освіта',
    'Інше',
  ];

  form = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(3)]],
    description: ['', [Validators.required, Validators.minLength(20)]],
    categories: this.fb.control<string[] | string>([], [Validators.required]),
    startDate: ['', [Validators.required]],
    endDate: [''],
    location_name: ['', [Validators.required, Validators.minLength(2)]],
    city: ['', [Validators.required, Validators.minLength(2)]],
    price_low: ['0', [Validators.required, Validators.min(0)]],
    price_high: ['0', [Validators.required, Validators.min(0)]],
    price_currency: ['UAH', [Validators.required]],
    additionalFields: this.fb.array<AdditionalFieldForm>([]),
  });

  constructor(
    private fb: FormBuilder,
    private toastCtrl: ToastController,
    private router: Router,
    private route: ActivatedRoute,
    private navCtrl: NavController,
    private eventsService: EventsService,
  ) {}

  ngOnInit(): void {
    this.form.controls.categories.setValue(this.categoriesMultiple ? [] : '');
  }

  get coverSrc(): string | null {
    return this.coverPreviewUrl;
  }

  get additionalFields(): FormArray<AdditionalFieldForm> {
    return this.form.controls.additionalFields;
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

    this.selectedCoverFile = file;
    this.coverPreviewUrl = URL.createObjectURL(file);
  }

  addAdditionalField(): void {
    this.additionalFields.push(this.createAdditionalFieldForm());
  }

  removeAdditionalField(index: number): void {
    this.additionalFields.removeAt(index);
  }

  onCategoriesChange(value: string | string[]): void {
    this.form.controls.categories.setValue(value);
    this.form.controls.categories.markAsTouched();
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
    if (!this.selectedCoverFile) {
      const toast = await this.toastCtrl.create({
        message: 'Завантажте обкладинку події.',
        duration: 1600,
        position: 'top',
      });
      await toast.present();
      return;
    }

    this.submitting = true;
    try {
      const raw = this.form.getRawValue();
      const categories = Array.isArray(raw.categories)
        ? raw.categories
        : raw.categories
          ? [raw.categories]
          : [];
      const additionalItems = this.getNormalizedAdditionalFields();
      const hasIncompleteAdditional = additionalItems.some(
        (item) => !item.title || !item.info,
      );
      if (hasIncompleteAdditional) {
        const toast = await this.toastCtrl.create({
          message:
            'У додаткових полях заповніть і заголовок, і інформацію або видаліть незаповнений рядок.',
          duration: 2200,
          position: 'top',
        });
        await toast.present();
        this.submitting = false;
        return;
      }

      const additional = additionalItems
        .filter((item) => item.title && item.info)
        .map((item) => ({
          title: item.title,
          info: item.info,
        }));

      const payload: EventCreateRequest = {
        name: (raw.name ?? '').trim(),
        type: categories.join(', '),
        startDate: raw.startDate || undefined,
        endDate: raw.endDate || undefined,
        location_name: (raw.location_name ?? '').trim(),
        city: (raw.city ?? '').trim(),
        price_low: raw.price_low?.toString(),
        price_high: raw.price_high?.toString(),
        price_currency: (raw.price_currency ?? '').trim(),
        description: (raw.description ?? '').trim(),
        additional: additional.length ? JSON.stringify(additional) : undefined,
      };

      await firstValueFrom(
        this.eventsService.createEvent(payload, this.selectedCoverFile),
      );

      const toast = await this.toastCtrl.create({
        message: 'Подію створено.',
        duration: 1400,
        position: 'top',
        color: 'success',
      });
      await toast.present();
      await this.router.navigate(['/tabs/explore']);
    } catch {
      const toast = await this.toastCtrl.create({
        message: 'Не вдалося створити подію. Спробуйте ще раз.',
        duration: 1800,
        position: 'top',
        color: 'danger',
      });
      await toast.present();
    } finally {
      this.submitting = false;
    }
  }

  private createAdditionalFieldForm(): AdditionalFieldForm {
    return this.fb.group({
      title: this.fb.nonNullable.control('', [Validators.maxLength(120)]),
      info: this.fb.nonNullable.control('', [Validators.maxLength(3000)]),
    });
  }

  private getNormalizedAdditionalFields(): AdditionalFieldItem[] {
    return this.additionalFields.controls.map((item) => ({
      title: item.controls.title.value.trim(),
      info: item.controls.info.value.trim(),
    }));
  }
}
