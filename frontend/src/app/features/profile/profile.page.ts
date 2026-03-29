import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, NavController, ToastController, AlertController } from '@ionic/angular';
import { Router } from '@angular/router';
import { AuthService, UserMe } from '../../core/auth.service';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ProfilePreferencesService, UserProfilePreferences } from 'src/app/core/profile-preferences.service';
import { EventsService } from '../events/services/events.service';
import { SearchableDropdownComponent } from 'src/app/shared/components/searchable-dropdown/searchable-dropdown.component';
import { catchError, from, of, Subscription, switchMap, take } from 'rxjs';

type EditableField = 'fullName' | 'about' | 'birthDate';

@Component({
  selector: 'app-profile',
  templateUrl: './profile.page.html',
  styleUrls: ['./profile.page.scss'],
  standalone: true,
  imports: [
    CommonModule,
    IonicModule,
    ReactiveFormsModule,
    SearchableDropdownComponent,
  ],
})
export class ProfilePage implements OnInit, OnDestroy {
  user?: UserMe;
  prefs: UserProfilePreferences = {};

  attendedCount = 12;
  purchasedCount = 18;
  createdCount = 3;

  editing: EditableField | null = null;
  private editingSnapshot: Partial<Record<EditableField, any>> = {};

  availableCities: string[] = [];
  private readonly subs = new Subscription();

  form = this.fb.group({
    fullName: ['', [Validators.minLength(2)]],
    about: [''],
    birthDate: [''],
    subscribedCities: this.fb.control<string[]>([], { nonNullable: true }),
    interests: this.fb.control<string[]>([], { nonNullable: true }),
  });

  constructor(
    private auth: AuthService,
    private router: Router,
    private toastCtrl: ToastController,
    private navCtrl: NavController,
    private fb: FormBuilder,
    private profilePrefs: ProfilePreferencesService,
    private alertCtrl: AlertController,
    private eventsService: EventsService,
  ) { }

  ngOnInit(): void {
    this.loadProfile();
    this.subs.add(
      this.eventsService.getCities().pipe(take(1)).subscribe((cities) => {
        this.availableCities = cities;
      }),
    );
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }

  loadProfile(): void {
    this.subs.add(
      this.auth
        .me()
        .pipe(
          take(1),
          switchMap((user) =>
            from(this.profilePrefs.get(user.id)).pipe(
              switchMap((prefs) =>
                this.auth.getCitiesSubscription().pipe(
                  take(1),
                  catchError(() => of(prefs.subscribedCities ?? [])),
                  switchMap((subscribedCities) =>
                    of({ user, prefs, subscribedCities }),
                  ),
                ),
              ),
            ),
          ),
        )
        .subscribe({
          next: ({ user, prefs, subscribedCities }) => {
            this.user = user;
            this.prefs = prefs;
            this.form.patchValue({
              fullName: prefs.fullName ?? user.full_name ?? '',
              about: prefs.about ?? '',
              birthDate: prefs.birthDate ?? '',
              subscribedCities: subscribedCities ?? [],
              interests:
                prefs.interests ?? [
                  '#мистецтво',
                  '#спорт',
                  '#музика',
                  '#подорожі',
                  '#освіта',
                ],
            });
          },
          error: async () => {
            const toast = await this.toastCtrl.create({
              message: 'Будь ласка, увійдіть до облікового запису.',
              duration: 2500,
              color: 'warning',
              position: 'top',
            });
            await toast.present();
            this.router.navigate(['/auth']);
          },
        }),
    );
  }

  get displayName(): string {
    const fromForm = this.form.controls.fullName.value?.toString().trim();
    if (fromForm) return fromForm;
    const fromUser = this.user?.full_name?.toString().trim();
    if (fromUser) return fromUser;
    return 'Користувач';
  }

  openTickets(): void {
    this.router.navigate(['/tabs/tickets']);
  }

  openFavorites(): void {
    this.router.navigate(['/tabs/events'], {
      queryParams: { isFavorite: true }
    });
  }

  openMyEvents(): void {
    this.router.navigate(['/tabs/events/organizer-cabinet']);
  }

  async openNotifications(): Promise<void> {
    const toast = await this.toastCtrl.create({
      message: 'Налаштування сповіщень буде додано незабаром.',
      duration: 1400,
      position: 'top',
    });
    await toast.present();
  }

  async openAppSettings(): Promise<void> {
    const toast = await this.toastCtrl.create({
      message: 'Налаштування застосунку буде додано незабаром.',
      duration: 1400,
      position: 'top',
    });
    await toast.present();
  }

  async openHelp(): Promise<void> {
    const toast = await this.toastCtrl.create({
      message: 'Підтримка буде додана незабаром.',
      duration: 1400,
      position: 'top',
    });
    await toast.present();
  }

  isEditing(field: EditableField): boolean {
    return this.editing === field;
  }

  startEdit(field: EditableField): void {
    if (this.editing && this.editing !== field) {
      this.cancelEdit();
    }
    this.editing = field;
    this.editingSnapshot[field] = this.form.get(field)?.value;
  }

  cancelEdit(): void {
    if (!this.editing) return;
    const field = this.editing;
    const snap = this.editingSnapshot[field];
    if (snap !== undefined) {
      this.form.get(field)?.setValue(snap);
    }
    this.editing = null;
  }

  async saveEdit(field: EditableField): Promise<void> {
    if (!this.user) return;
    this.form.get(field)?.markAsTouched();
    if (this.form.get(field)?.invalid) return;

    const patch: Partial<UserProfilePreferences> = {};
    const value = (this.form.get(field)?.value ?? '').toString().trim();
    if (field === 'fullName') patch.fullName = value;
    if (field === 'about') patch.about = value;
    if (field === 'birthDate') patch.birthDate = value;

    this.prefs = await this.profilePrefs.patch(this.user.id, patch);

    const toast = await this.toastCtrl.create({
      message: 'Зміни збережено.',
      duration: 1200,
      position: 'top',
      color: 'success',
    });
    await toast.present();
    this.editing = null;
  }

 onCitiesChanged(): void {
    if (!this.user) return;
    const cities = this.form.controls.subscribedCities.value ?? [];

    this.auth.setCitiesSubscription(cities).subscribe(() => {});
  }

  onCitiesSelectionChange(value: string | string[]): void {
    const cities = Array.isArray(value) ? value : value ? [value] : [];
    this.form.controls.subscribedCities.setValue(cities);
    this.onCitiesChanged();
  }

  async addInterest(): Promise<void> {
    const alert = await this.alertCtrl.create({
      header: 'Додати інтерес',
      inputs: [
        {
          name: 'interest',
          type: 'text',
          placeholder: 'Напр. #кіно або кіно',
        },
      ],
      buttons: [
        { text: 'Скасувати', role: 'cancel' },
        {
          text: 'Додати',
          role: 'confirm',
        },
      ],
    });
    await alert.present();
    const res = await alert.onDidDismiss();
    if (res.role !== 'confirm' || !this.user) return;

    const raw = (res.data?.values?.interest ?? '').toString().trim();
    if (!raw) return;

    const normalized = raw.startsWith('#') ? raw : `#${raw}`;
    const current = this.form.controls.interests.value ?? [];
    const next = Array.from(new Set([...current, normalized]));
    this.form.controls.interests.setValue(next);
    this.prefs = await this.profilePrefs.patch(this.user.id, { interests: next });
  }

  async removeInterest(tag: string): Promise<void> {
    if (!this.user) return;
    const current = this.form.controls.interests.value ?? [];
    const next = current.filter((t) => t !== tag);
    this.form.controls.interests.setValue(next);
    this.prefs = await this.profilePrefs.patch(this.user.id, { interests: next });
  }

  logout(): void {
    this.subs.add(
      this.auth
        .logout()
        .pipe(take(1))
        .subscribe(() => {
          this.navCtrl.navigateRoot('/auth');
        }),
    );
  }
}

