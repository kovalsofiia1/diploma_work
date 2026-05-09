import { CommonModule } from '@angular/common';
import {
  Component,
  OnDestroy,
} from '@angular/core';
import {
  FormArray,
  FormControl,
  FormGroup,
  FormBuilder,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import {
  IonicModule,
  NavController,
  ToastController,
} from '@ionic/angular';
import { firstValueFrom } from 'rxjs';
import {
  EventCreateRequest,
  EventInterface,
  EventMember,
  EventMemberRole,
} from '../../interfaces/events.interface';
import { EventsService } from '../../services/events.service';
import { LoaderComponent } from 'src/app/shared/components/loader/loader.component';
import { SearchableDropdownComponent } from 'src/app/shared/components/searchable-dropdown/searchable-dropdown.component';
import {
  CitySearchService,
  CitySuggestion,
} from 'src/app/core/city-search.service';

type SeatPricingForm = FormGroup<{
  seatType: FormControl<string>;
  quantity: FormControl<number | null>;
  price: FormControl<number | null>;
}>;

type SeatTierItem = {
  seat_type: string;
  quantity: number;
  price: number;
};

type SeatPricingItem = {
  seat_type: string;
  seat_id: string;
  label: string;
  price: number;
};

type AdditionalInfoItem = {
  title: string;
  info: string;
};

@Component({
  selector: 'app-event-settings-page',
  standalone: true,
  imports: [
    CommonModule,
    IonicModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    LoaderComponent,
    SearchableDropdownComponent,
  ],
  templateUrl: './event-settings.page.html',
  styleUrls: ['./event-settings.page.scss'],
})
export class EventSettingsPage implements OnDestroy {
  uid = '';
  event?: EventInterface;
  loading = false;
  saving = false;
  addingMembers = false;
  deletingMemberId: number | null = null;
  membersLoading = false;
  members: EventMember[] = [];
  uploadingImage = false;
  deletingEvent = false;
  coverPreviewUrl: string | null = null;
  selectedCoverFile: File | null = null;
  citySuggestions: CitySuggestion[] = [];
  citySearchLoading = false;
  private citySearchTimer: ReturnType<typeof setTimeout> | null = null;

  memberRole: EventMemberRole = 'scanner';
  memberEmailsText = '';
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
    name: ['', [Validators.required, Validators.minLength(2)]],
    description: [''],
    categories: this.fb.control<string[] | string>([]),
    city: [''],
    location_name: [''],
    startDate: [''],
    endDate: [''],
    price_currency: ['UAH', [Validators.required]],
    seatPricing: this.fb.array<SeatPricingForm>([]),
  });

  constructor(
    private readonly fb: FormBuilder,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly navCtrl: NavController,
    private readonly eventsService: EventsService,
    private readonly toastCtrl: ToastController,
    private readonly citySearchService: CitySearchService,
  ) {}

  ngOnInit(): void {
    const rawUid = this.route.snapshot.paramMap.get('uid') ?? '';
    this.uid = decodeURIComponent(rawUid);
    this.loadEvent();
  }

  ngOnDestroy(): void {
    if (this.citySearchTimer) {
      clearTimeout(this.citySearchTimer);
      this.citySearchTimer = null;
    }
  }

  get canEdit(): boolean {
    return !!this.event?.can_edit;
  }

  get seatPricing(): FormArray<SeatPricingForm> {
    return this.form.controls.seatPricing;
  }

  back(): void {
    this.navCtrl.back();
  }

  onCoverPicked(ev: Event): void {
    if (!this.canEdit) return;
    const input = ev.target as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      void this.presentToast('Оберіть файл зображення.', 'warning');
      return;
    }

    if (this.coverPreviewUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(this.coverPreviewUrl);
    }
    this.selectedCoverFile = file;
    this.coverPreviewUrl = URL.createObjectURL(file);
  }

  async saveImage(): Promise<void> {
    if (!this.canEdit || this.uploadingImage || !this.event?.id || !this.selectedCoverFile) {
      return;
    }

    this.uploadingImage = true;
    try {
      const ok = await this.uploadSelectedImage();
      if (!ok) {
        await this.presentToast('Не вдалося оновити фото.', 'danger');
        return;
      }
      await this.presentToast('Фото події оновлено.', 'success');
    } catch {
      await this.presentToast('Не вдалося оновити фото.', 'danger');
    } finally {
      this.uploadingImage = false;
    }
  }

  async saveChanges(): Promise<void> {
    if (!this.canEdit || this.saving || !this.event?.id) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) return;

    this.saving = true;
    try {
      const raw = this.form.getRawValue();
      const categories = Array.isArray(raw.categories)
        ? raw.categories
        : raw.categories
          ? [raw.categories]
          : [];
      const seatTierItems = this.getNormalizedSeatPricing();
      const hasInvalidSeatPricing = seatTierItems.some(
        (item) => !item.seatType || item.quantity < 1 || item.price < 0,
      );
      if (hasInvalidSeatPricing) {
        await this.presentToast(
          'У місцях потрібно вказати тип, кількість (мінімум 1) і ціну.',
          'warning',
        );
        this.saving = false;
        return;
      }
      const normalizedSeatTiers: SeatTierItem[] = seatTierItems
        .filter((item) => item.seatType && item.quantity > 0)
        .map((item) => ({
          seat_type: item.seatType,
          quantity: item.quantity,
          price: item.price,
        }));
      if (!normalizedSeatTiers.length) {
        await this.presentToast('Додайте хоча б один тип місць.', 'warning');
        this.saving = false;
        return;
      }

      const normalizedSeatPricing: SeatPricingItem[] = [];
      for (const tier of normalizedSeatTiers) {
        for (let index = 0; index < tier.quantity; index += 1) {
          const generatedLabel = `${tier.seat_type} #${index + 1}`;
          normalizedSeatPricing.push({
            seat_type: tier.seat_type,
            seat_id: this.buildSeatId(generatedLabel, normalizedSeatPricing.length),
            label: generatedLabel,
            price: tier.price,
          });
        }
      }
      const minSeatPrice = Math.min(...normalizedSeatTiers.map((item) => item.price));
      const maxSeatPrice = Math.max(...normalizedSeatTiers.map((item) => item.price));
      const totalPlaces = normalizedSeatTiers.reduce(
        (sum, item) => sum + item.quantity,
        0,
      );

      const additionalInfoItems = this.parseAdditionalInfoItems(
        this.event?.additional,
      );
      const payload: EventCreateRequest = {
        name: (raw.name ?? '').trim(),
        description: (raw.description ?? '').trim() || undefined,
        type: categories.join(', ') || undefined,
        city: (raw.city ?? '').trim() || undefined,
        location_name: (raw.location_name ?? '').trim() || undefined,
        startDate: (raw.startDate ?? '').trim() || undefined,
        endDate: (raw.endDate ?? '').trim() || undefined,
        price_low: minSeatPrice.toString(),
        price_high: maxSeatPrice.toString(),
        price_currency:
          (raw.price_currency ?? '').trim() ||
          this.event?.price_currency ||
          'UAH',
        total_places: totalPlaces,
        additional: JSON.stringify({
          items: additionalInfoItems,
          seat_tiers: normalizedSeatTiers,
          seat_pricing: normalizedSeatPricing,
        }),
      };
      const updated = await firstValueFrom(
        this.eventsService.updateEvent(this.event.id, payload),
      );
      this.event = { ...this.event, ...updated, can_edit: this.event.can_edit };
      let imageUpdated = false;
      if (this.selectedCoverFile) {
        imageUpdated = await this.uploadSelectedImage();
      }
      this.patchForm(this.event);
      if (this.selectedCoverFile && !imageUpdated) {
        await this.presentToast(
          'Налаштування збережено, але фото не вдалося оновити.',
          'warning',
        );
      } else if (imageUpdated) {
        await this.presentToast('Налаштування і фото події збережено.', 'success');
      } else {
        await this.presentToast('Налаштування події збережено.', 'success');
      }
    } catch {
      await this.presentToast('Не вдалося зберегти зміни.', 'danger');
    } finally {
      this.saving = false;
    }
  }

  async addMembers(): Promise<void> {
    if (!this.canEdit || this.addingMembers || !this.uid) return;
    const emails = this.parseEmails(this.memberEmailsText);
    if (!emails.length) {
      await this.presentToast('Вкажіть хоча б один email.', 'warning');
      return;
    }

    this.addingMembers = true;
    try {
      const res = await firstValueFrom(
        this.eventsService.addEventMembers(this.uid, {
          emails,
          role: this.memberRole,
        }),
      );
      const addedCount = (res.added?.length ?? 0) + (res.updated?.length ?? 0);
      const missingCount = res.missing?.length ?? 0;
      this.memberEmailsText = '';
      await this.presentToast(
        `Оновлено: ${addedCount}. Не знайдено: ${missingCount}.`,
        missingCount ? 'warning' : 'success',
      );
      await this.loadMembers();
    } catch {
      await this.presentToast('Не вдалося додати учасників.', 'danger');
    } finally {
      this.addingMembers = false;
    }
  }

  async deleteEvent(): Promise<void> {
    if (!this.canEdit || this.deletingEvent || !this.event?.id) return;
    this.deletingEvent = true;
    try {
      await firstValueFrom(this.eventsService.deleteEvent(this.event.id));
      await this.presentToast('Подію скасовано.', 'success');
      await this.router.navigate(['/tabs/events']);
    } catch {
      await this.presentToast('Не вдалося скасувати подію.', 'danger');
    } finally {
      this.deletingEvent = false;
    }
  }

  private async loadEvent(): Promise<void> {
    this.loading = true;
    try {
      const state =
        (this.router.getCurrentNavigation()?.extras?.state as
          | { item?: EventInterface }
          | undefined) ?? {};
      const fromState = (state.item ?? (history.state?.item as EventInterface)) as
        | EventInterface
        | undefined;

      this.event = fromState?.uid === this.uid ? fromState : undefined;
      if (!this.event) {
        this.event = await firstValueFrom(this.eventsService.getEventByUid(this.uid));
      }
      this.patchForm(this.event);
      await this.loadMembers();
    } catch {
      await this.presentToast('Подію не знайдено.', 'danger');
      this.navCtrl.back();
    } finally {
      this.loading = false;
    }
  }

  private patchForm(item?: EventInterface): void {
    if (!item) return;
    const categories = (item.type ?? '')
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean);
    this.form.patchValue({
      name: item.name ?? '',
      description: item.description ?? '',
      categories,
      city: item.city ?? '',
      location_name: item.location_name ?? '',
      startDate: item.startDate ?? '',
      endDate: item.endDate ?? '',
      price_currency: item.price_currency ?? 'UAH',
    });
    if (!this.selectedCoverFile) {
      this.coverPreviewUrl = this.withCacheBust(item.image);
    }
    this.patchSeatPricingFromEvent(item);
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

  getRoleLabel(role: EventMemberRole): string {
    return role === 'organizer' ? 'Організатор' : 'Сканер';
  }

  async deleteMember(member: EventMember): Promise<void> {
    if (!this.canEdit || this.deletingMemberId === member.user_id) return;

    this.deletingMemberId = member.user_id;
    try {
      await firstValueFrom(
        this.eventsService.deleteEventMember(this.uid, member.user_id),
      );
      this.members = this.members.filter((item) => item.user_id !== member.user_id);
      await this.presentToast('Учасника видалено.', 'success');
    } catch {
      await this.presentToast('Не вдалося видалити учасника.', 'danger');
    } finally {
      this.deletingMemberId = null;
    }
  }

  private async loadMembers(): Promise<void> {
    if (!this.uid) return;
    this.membersLoading = true;
    try {
      this.members = await firstValueFrom(this.eventsService.getEventMembers(this.uid));
    } catch {
      this.members = [];
      await this.presentToast('Не вдалося завантажити учасників.', 'warning');
    } finally {
      this.membersLoading = false;
    }
  }

  private parseEmails(raw: string): string[] {
    return Array.from(
      new Set(
        raw
          .split(/[\s,;\n]+/g)
          .map((item) => item.trim().toLowerCase())
          .filter(Boolean),
      ),
    );
  }

  private async presentToast(
    message: string,
    color: 'success' | 'danger' | 'warning',
  ): Promise<void> {
    const toast = await this.toastCtrl.create({
      message,
      duration: 1800,
      position: 'top',
      color,
    });
    await toast.present();
  }

  private toPositiveIntOrUndefined(value: unknown): number | undefined {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return undefined;
    const int = Math.round(parsed);
    return int > 0 ? int : undefined;
  }

  addSeatPricingField(): void {
    this.seatPricing.push(this.createSeatPricingForm());
  }

  removeSeatPricingField(index: number): void {
    this.seatPricing.removeAt(index);
    if (!this.seatPricing.length) {
      this.addSeatPricingField();
    }
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

  private patchSeatPricingFromEvent(item: EventInterface): void {
    this.seatPricing.clear();
    const parsed = this.parseAdditional(item.additional);
    const seatTiers = parsed.seat_tiers;
    if (seatTiers.length) {
      for (const tier of seatTiers) {
        this.seatPricing.push(
          this.fb.group({
            seatType: this.fb.nonNullable.control(tier.seat_type, [
              Validators.maxLength(64),
            ]),
            quantity: this.fb.control<number | null>(tier.quantity, [
              Validators.required,
              Validators.min(1),
            ]),
            price: this.fb.control<number | null>(tier.price, [Validators.min(0)]),
          }),
        );
      }
    } else {
      const grouped = new Map<string, { quantity: number; price: number }>();
      for (const seat of parsed.seat_pricing) {
        const type = seat.seat_type || this.extractSeatType(seat.label);
        const existing = grouped.get(type);
        if (!existing) {
          grouped.set(type, { quantity: 1, price: seat.price });
        } else {
          existing.quantity += 1;
        }
      }
      grouped.forEach((value, key) => {
        this.seatPricing.push(
          this.fb.group({
            seatType: this.fb.nonNullable.control(key, [Validators.maxLength(64)]),
            quantity: this.fb.control<number | null>(value.quantity, [
              Validators.required,
              Validators.min(1),
            ]),
            price: this.fb.control<number | null>(value.price, [Validators.min(0)]),
          }),
        );
      });
    }
    if (!this.seatPricing.length) {
      this.addSeatPricingField();
    }
  }

  private parseAdditionalInfoItems(raw?: string): AdditionalInfoItem[] {
    const parsed = this.parseAdditional(raw);
    return parsed.items;
  }

  private parseAdditional(raw?: string): {
    items: AdditionalInfoItem[];
    seat_tiers: SeatTierItem[];
    seat_pricing: SeatPricingItem[];
  } {
    const value = (raw ?? '').trim();
    if (!value) {
      return { items: [], seat_tiers: [], seat_pricing: [] };
    }
    try {
      const parsed = JSON.parse(value);
      const itemsSource = Array.isArray(parsed)
        ? parsed
        : Array.isArray(parsed?.items)
          ? parsed.items
          : [];
      const seatTiersSource = Array.isArray(parsed?.seat_tiers)
        ? parsed.seat_tiers
        : [];
      const seatPricingSource = Array.isArray(parsed?.seat_pricing)
        ? parsed.seat_pricing
        : [];

      const items: AdditionalInfoItem[] = itemsSource
        .map((item: any) => ({
          title: (item?.title ?? '').toString().trim(),
          info: (item?.info ?? '').toString().trim(),
        }))
        .filter((item: AdditionalInfoItem) => item.title && item.info);

      const seat_tiers: SeatTierItem[] = seatTiersSource
        .map((item: any) => ({
          seat_type: (item?.seat_type ?? '').toString().trim(),
          quantity: Number(item?.quantity ?? 0),
          price: Number(item?.price ?? 0),
        }))
        .filter(
          (item: SeatTierItem) =>
            item.seat_type &&
            Number.isFinite(item.quantity) &&
            item.quantity > 0 &&
            Number.isFinite(item.price) &&
            item.price >= 0,
        );

      const seat_pricing: SeatPricingItem[] = seatPricingSource
        .map((item: any) => ({
          seat_type: (item?.seat_type ?? '').toString().trim(),
          seat_id: (item?.seat_id ?? '').toString().trim(),
          label: (item?.label ?? '').toString().trim(),
          price: Number(item?.price ?? 0),
        }))
        .filter(
          (item: SeatPricingItem) =>
            item.seat_id &&
            item.label &&
            Number.isFinite(item.price) &&
            item.price >= 0,
        );

      return { items, seat_tiers, seat_pricing };
    } catch {
      return { items: [], seat_tiers: [], seat_pricing: [] };
    }
  }

  private extractSeatType(label: string): string {
    const value = (label ?? '').trim();
    if (!value) return 'General';
    const match = value.match(/^(.*)\s+#\d+$/);
    return (match?.[1] ?? value).trim() || 'General';
  }

  private buildSeatId(label: string, index: number): string {
    const latinFallback = `seat-${index + 1}`;
    const normalized = label
      .toLowerCase()
      .replace(/[^a-z0-9а-яіїєґ]+/giu, '-')
      .replace(/^-+|-+$/g, '');
    return normalized || latinFallback;
  }

  private async uploadSelectedImage(): Promise<boolean> {
    if (!this.event?.id || !this.selectedCoverFile) {
      return false;
    }
    try {
      const updated = await firstValueFrom(
        this.eventsService.updateEventImage(this.event.id, this.selectedCoverFile),
      );
      this.event = { ...this.event, ...updated, can_edit: this.event.can_edit };
      this.coverPreviewUrl = this.withCacheBust(this.event.image);
      this.selectedCoverFile = null;
      return true;
    } catch {
      return false;
    }
  }

  private withCacheBust(url?: string): string | null {
    const value = (url ?? '').trim();
    if (!value) return null;
    const separator = value.includes('?') ? '&' : '?';
    return `${value}${separator}v=${Date.now()}`;
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

