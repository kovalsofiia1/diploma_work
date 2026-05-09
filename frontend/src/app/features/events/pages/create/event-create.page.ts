import { CommonModule } from '@angular/common';
import {
  Component,
  OnDestroy,
} from '@angular/core';
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
import {
  CitySearchService,
  CitySuggestion,
} from 'src/app/core/city-search.service';
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

type SeatPricingForm = FormGroup<{
  seatType: FormControl<string>;
  quantity: FormControl<number | null>;
  price: FormControl<number | null>;
}>;

type SeatPricingItem = {
  seat_type: string;
  seat_id: string;
  label: string;
  price: number;
};

type SeatTierItem = {
  seat_type: string;
  quantity: number;
  price: number;
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
export class EventCreatePage implements OnDestroy {
  submitting = false;
  coverPreviewUrl: string | null = null;
  selectedCoverFile: File | null = null;
  citySuggestions: CitySuggestion[] = [];
  citySearchLoading = false;
  private citySearchTimer: ReturnType<typeof setTimeout> | null = null;
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
    price_currency: ['UAH', [Validators.required]],
    additionalFields: this.fb.array<AdditionalFieldForm>([]),
    seatPricing: this.fb.array<SeatPricingForm>([]),
  });

  constructor(
    private fb: FormBuilder,
    private toastCtrl: ToastController,
    private router: Router,
    private route: ActivatedRoute,
    private navCtrl: NavController,
    private eventsService: EventsService,
    private citySearchService: CitySearchService,
  ) {}

  ngOnInit(): void {
    this.form.controls.categories.setValue(this.categoriesMultiple ? [] : '');
    if (this.seatPricing.length === 0) {
      this.addSeatPricingField();
    }
  }

  ngOnDestroy(): void {
    if (this.citySearchTimer) {
      clearTimeout(this.citySearchTimer);
      this.citySearchTimer = null;
    }
  }

  get coverSrc(): string | null {
    return this.coverPreviewUrl;
  }

  get additionalFields(): FormArray<AdditionalFieldForm> {
    return this.form.controls.additionalFields;
  }

  get seatPricing(): FormArray<SeatPricingForm> {
    return this.form.controls.seatPricing;
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

  addSeatPricingField(): void {
    this.seatPricing.push(this.createSeatPricingForm());
  }

  removeSeatPricingField(index: number): void {
    this.seatPricing.removeAt(index);
    if (this.seatPricing.length === 0) {
      this.addSeatPricingField();
    }
  }

  onCategoriesChange(value: string | string[]): void {
    this.form.controls.categories.setValue(value);
    this.form.controls.categories.markAsTouched();
  }

  onCityInput(ev: Event): void {
    const value = (
      (ev as any)?.detail?.value ??
      (ev.target as any)?.value ??
      ''
    ).toString();
    void this.searchCitySuggestions(value);
  }

  chooseCitySuggestion(item: CitySuggestion): void {
    this.form.controls.city.setValue(item.city);
    this.form.controls.city.markAsDirty();
    this.form.controls.city.markAsTouched();
    this.citySuggestions = [];
  }

  onCityBlur(): void {
    setTimeout(() => {
      this.citySuggestions = [];
    }, 120);
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
      const seatPricingItems = this.getNormalizedSeatPricing();
      const hasInvalidSeatPricing = seatPricingItems.some(
        (item) => !item.seatType || item.quantity < 1 || item.price < 0,
      );
      if (hasInvalidSeatPricing) {
        const toast = await this.toastCtrl.create({
          message:
            'У місцях потрібно вказати тип, кількість (мінімум 1) і ціну.',
          duration: 2200,
          position: 'top',
        });
        await toast.present();
        this.submitting = false;
        return;
      }
      const normalizedSeatTiers: SeatTierItem[] = seatPricingItems
        .filter((item) => item.seatType && item.quantity > 0)
        .map((item) => ({
          seat_type: item.seatType,
          quantity: item.quantity,
          price: item.price,
        }));
      if (!normalizedSeatTiers.length) {
        const toast = await this.toastCtrl.create({
          message: 'Додайте хоча б один тип місць.',
          duration: 1800,
          position: 'top',
        });
        await toast.present();
        this.submitting = false;
        return;
      }
      const normalizedSeatPricing: SeatPricingItem[] = [];
      for (const tier of normalizedSeatTiers) {
        const safeQty = tier.quantity;
        for (let index = 0; index < safeQty; index += 1) {
          const generatedLabel = `${tier.seat_type} #${index + 1}`;
          normalizedSeatPricing.push({
            seat_type: tier.seat_type,
            seat_id: this.buildSeatId(generatedLabel, normalizedSeatPricing.length),
            label: generatedLabel,
            price: tier.price,
          });
        }
      }
      const hasDuplicateSeatIds = new Set(
        normalizedSeatPricing.map((item) => item.seat_id),
      ).size !== normalizedSeatPricing.length;
      if (hasDuplicateSeatIds) {
        const toast = await this.toastCtrl.create({
          message: 'Назви місць мають бути унікальними.',
          duration: 1800,
          position: 'top',
        });
        await toast.present();
        this.submitting = false;
        return;
      }
      const minSeatPrice = Math.min(...normalizedSeatTiers.map((item) => item.price));
      const maxSeatPrice = Math.max(...normalizedSeatTiers.map((item) => item.price));
      const totalPlaces = normalizedSeatTiers.reduce(
        (sum, item) => sum + item.quantity,
        0,
      );

      const payload: EventCreateRequest = {
        name: (raw.name ?? '').trim(),
        type: categories.join(', '),
        startDate: raw.startDate || undefined,
        endDate: raw.endDate || undefined,
        location_name: (raw.location_name ?? '').trim(),
        city: (raw.city ?? '').trim(),
        price_low: minSeatPrice.toString(),
        price_high: maxSeatPrice.toString(),
        price_currency: (raw.price_currency ?? '').trim(),
        total_places: totalPlaces,
        description: (raw.description ?? '').trim(),
        additional:
          additional.length || normalizedSeatPricing.length
            ? JSON.stringify({
                items: additional,
                seat_tiers: normalizedSeatTiers,
                seat_pricing: normalizedSeatPricing,
              })
            : undefined,
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

  private createSeatPricingForm(): SeatPricingForm {
    return this.fb.group({
      seatType: this.fb.nonNullable.control('', [Validators.maxLength(64)]),
      quantity: this.fb.control<number | null>(1, [
        Validators.required,
        Validators.min(1),
      ]),
      price: this.fb.control<number | null>(0, [Validators.min(0)]),
    });
  }

  private getNormalizedAdditionalFields(): AdditionalFieldItem[] {
    return this.additionalFields.controls.map((item) => ({
      title: item.controls.title.value.trim(),
      info: item.controls.info.value.trim(),
    }));
  }

  private getNormalizedSeatPricing(): Array<{
    seatType: string;
    quantity: number;
    price: number;
  }> {
    return this.seatPricing.controls.map((item) => ({
      seatType: item.controls.seatType.value.trim(),
      quantity: Number(item.controls.quantity.value ?? 1),
      price: Number(item.controls.price.value ?? 0),
    }));
  }

  private buildSeatId(label: string, index: number): string {
    const latinFallback = `seat-${index + 1}`;
    const normalized = label
      .toLowerCase()
      .replace(/[^a-z0-9а-яіїєґ]+/giu, '-')
      .replace(/^-+|-+$/g, '');
    return normalized || latinFallback;
  }

  private async searchCitySuggestions(rawValue: string): Promise<void> {
    const value = rawValue.trim();
    if (this.citySearchTimer) {
      clearTimeout(this.citySearchTimer);
      this.citySearchTimer = null;
    }
    if (value.length < 2) {
      this.citySuggestions = [];
      this.citySearchLoading = false;
      return;
    }

    this.citySearchLoading = true;
    await new Promise<void>((resolve) => {
      this.citySearchTimer = setTimeout(() => {
        this.citySearchTimer = null;
        resolve();
      }, 260);
    });

    const activeValue = (this.form.controls.city.value ?? '').toString().trim();
    if (activeValue !== value) {
      this.citySearchLoading = false;
      return;
    }

    const suggestions = await this.citySearchService.searchCities(value, 8);
    const latestValue = (this.form.controls.city.value ?? '').toString().trim();
    if (latestValue !== value) {
      this.citySearchLoading = false;
      return;
    }
    this.citySuggestions = suggestions;
    this.citySearchLoading = false;
  }
}
