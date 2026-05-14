import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, NavController, ToastController, AlertController } from '@ionic/angular';
import { Router } from '@angular/router';
import {
  AuthService,
  OrganizerApplication,
  OrganizerProfile,
  OrganizerApplicationStatus,
  UserMe,
} from '../../core/auth.service';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ProfilePreferencesService, UserProfilePreferences } from 'src/app/core/profile-preferences.service';
import { EventsService } from '../events/services/events.service';
import { SearchableDropdownComponent } from 'src/app/shared/components/searchable-dropdown/searchable-dropdown.component';
import { catchError, from, of, Subscription, switchMap, take } from 'rxjs';
import { AppHeaderComponent } from 'src/app/shared/components/app-header/app-header.component';

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
    AppHeaderComponent,
  ],
})
export class ProfilePage implements OnInit, OnDestroy {
  private auth = inject(AuthService);
  private router = inject(Router);
  private toastCtrl = inject(ToastController);
  private navCtrl = inject(NavController);
  private fb = inject(FormBuilder);
  private profilePrefs = inject(ProfilePreferencesService);
  private alertCtrl = inject(AlertController);
  private eventsService = inject(EventsService);

  user?: UserMe;
  prefs: UserProfilePreferences = {};
  organizerApplication: OrganizerApplication = {
    status: 'not_requested',
    can_create_events: false,
  };
  showOrganizerForm = false;
  organizerProfile?: OrganizerProfile;

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

  organizerForm = this.fb.group({
    organization_name: ['', [Validators.required, Validators.minLength(2)]],
    contact_phone: ['', [Validators.required, Validators.minLength(6)]],
    motivation: ['', [Validators.required, Validators.minLength(20)]],
    experience: [''],
  });

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
              fullName: user.full_name ?? '',
              about: user.description ?? '',
              birthDate: user.date_of_birth ?? '',
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
            this.loadStats();
            this.loadOrganizerApplication();
            if (user.status === 'verified user' || user.status === 'admin') {
              this.loadOrganizerProfile();
            }
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

  private loadStats(): void {
    this.subs.add(
      this.auth
        .getMyStats()
        .pipe(take(1))
        .subscribe({
          next: (stats) => {
            this.attendedCount = Number(stats.visited_events) || 0;
            this.purchasedCount = Number(stats.purchased_tickets) || 0;
            this.createdCount = Number(stats.created_events) || 0;
          },
          error: () => {
            this.attendedCount = 0;
            this.purchasedCount = 0;
            this.createdCount = 0;
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

  get organizerStatus(): OrganizerApplicationStatus {
    return this.organizerApplication.status;
  }

  get isOrganizerApproved(): boolean {
    return this.organizerStatus === 'approved';
  }

  get isOrganizerPending(): boolean {
    return this.organizerStatus === 'pending';
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

  openCreateEvent(): void {
    if (!this.isOrganizerApproved) {
      this.showOrganizerForm = true;
      this.toast('Спочатку подайте заявку організатора.', 'warning');
      return;
    }
    this.router.navigate(['/tabs/create']);
  }

  openOrganizerStats(): void {
    this.openMyEvents();
  }

  toggleOrganizerForm(): void {
    this.showOrganizerForm = !this.showOrganizerForm;
  }

  submitOrganizerApplication(): void {
    this.organizerForm.markAllAsTouched();
    if (this.organizerForm.invalid) return;

    const payload = {
      organization_name: (this.organizerForm.value.organization_name ?? '').trim(),
      contact_phone: (this.organizerForm.value.contact_phone ?? '').trim(),
      motivation: (this.organizerForm.value.motivation ?? '').trim(),
      experience: (this.organizerForm.value.experience ?? '').trim() || undefined,
    };

    this.subs.add(
      this.auth
        .submitOrganizerApplication(payload)
        .pipe(take(1))
        .subscribe({
          next: (application) => {
            this.organizerApplication = application;
            this.showOrganizerForm = false;
            this.loadOrganizerProfile();
            this.toast('Заявку відправлено. Статус: Approved.', 'success');
          },
          error: async (err) => {
            const message = err?.error?.detail || 'Не вдалося відправити заявку. Спробуйте ще раз.';
            this.toast(message, 'danger');
          },
        }),
    );
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
    const value = (this.form.get(field)?.value ?? '').toString().trim();
    const payload: {
      full_name?: string | null;
      description?: string | null;
      date_of_birth?: string | null;
    } = {};
    if (field === 'fullName') payload.full_name = value || null;
    if (field === 'about') payload.description = value || null;
    if (field === 'birthDate') payload.date_of_birth = value || null;

    this.auth
      .updateMe(payload)
      .pipe(take(1))
      .subscribe({
        next: (user) => {
          this.user = user;
        },
      });

    const toast = await this.toastCtrl.create({
      message: 'Зміни збережено.',
      duration: 1200,
      position: 'top',
      color: 'success',
    });
    await toast.present();
    this.editing = null;
  }

  savePersonalInfo(): void {
    if (!this.user) return;
    this.form.controls.fullName.markAsTouched();
    if (this.form.controls.fullName.invalid) return;

    const payload = {
      full_name: (this.form.controls.fullName.value ?? '').trim() || null,
      date_of_birth: (this.form.controls.birthDate.value ?? '').trim() || null,
      description: (this.form.controls.about.value ?? '').trim() || null,
    };

    this.subs.add(
      this.auth
        .updateMe(payload)
        .pipe(take(1))
        .subscribe({
          next: (user) => {
            this.user = user;
            this.toast('Профіль оновлено.', 'success');
          },
          error: (err) => {
            const message = err?.error?.detail || 'Не вдалося оновити профіль.';
            this.toast(message, 'danger');
          },
        }),
    );
  }

  saveOrganizerProfile(): void {
    if (!this.organizerProfile) return;
    this.subs.add(
      this.auth
        .updateOrganizerProfile(this.organizerProfile)
        .pipe(take(1))
        .subscribe({
          next: (profile) => {
            this.organizerProfile = profile;
            this.toast('Дані організатора оновлено.', 'success');
          },
          error: (err) => {
            const message = err?.error?.detail || 'Не вдалося оновити дані організатора.';
            this.toast(message, 'danger');
          },
        }),
    );
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

  private loadOrganizerApplication(): void {
    this.subs.add(
      this.auth
        .getOrganizerApplication()
        .pipe(take(1))
        .subscribe({
          next: (application) => {
            this.organizerApplication = application;
            if (application.status === 'approved') {
              this.loadOrganizerProfile();
            }
          },
          error: () => {
            this.organizerApplication = {
              status: 'not_requested',
              can_create_events: false,
            };
          },
        }),
    );
  }

  private loadOrganizerProfile(): void {
    this.subs.add(
      this.auth
        .getOrganizerProfile()
        .pipe(take(1))
        .subscribe({
          next: (profile) => {
            this.organizerProfile = { ...profile };
          },
          error: () => {
            this.organizerProfile = undefined;
          },
        }),
    );
  }

  private async toast(message: string, color: 'success' | 'warning' | 'danger'): Promise<void> {
    const toast = await this.toastCtrl.create({
      message,
      duration: 1800,
      color,
      position: 'top',
    });
    await toast.present();
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

