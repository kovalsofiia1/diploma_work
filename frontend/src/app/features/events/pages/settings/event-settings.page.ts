import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import {
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
export class EventSettingsPage {
  uid = '';
  event?: EventInterface;
  loading = false;
  saving = false;
  addingMembers = false;
  deletingMemberId: number | null = null;
  membersLoading = false;
  members: EventMember[] = [];

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
  });

  constructor(
    private readonly fb: FormBuilder,
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly navCtrl: NavController,
    private readonly eventsService: EventsService,
    private readonly toastCtrl: ToastController,
  ) {}

  ngOnInit(): void {
    const rawUid = this.route.snapshot.paramMap.get('uid') ?? '';
    this.uid = decodeURIComponent(rawUid);
    this.loadEvent();
  }

  get canEdit(): boolean {
    return !!this.event?.can_edit;
  }

  back(): void {
    this.navCtrl.back();
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
      const payload: EventCreateRequest = {
        name: (raw.name ?? '').trim(),
        description: (raw.description ?? '').trim() || undefined,
        type: categories.join(', ') || undefined,
        city: (raw.city ?? '').trim() || undefined,
        location_name: (raw.location_name ?? '').trim() || undefined,
        startDate: (raw.startDate ?? '').trim() || undefined,
        endDate: (raw.endDate ?? '').trim() || undefined,
      };
      const updated = await firstValueFrom(
        this.eventsService.updateEvent(this.event.id, payload),
      );
      this.event = { ...this.event, ...updated, can_edit: this.event.can_edit };
      this.patchForm(this.event);
      await this.presentToast('Налаштування події збережено.', 'success');
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
    });
  }

  onCategoriesChange(value: string | string[]): void {
    this.form.controls.categories.setValue(value);
    this.form.controls.categories.markAsTouched();
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
}

