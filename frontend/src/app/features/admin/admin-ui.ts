import { Injectable, inject } from '@angular/core';
import { AlertController, ToastController } from '@ionic/angular';

const MIN_REASON_LENGTH = 4;

/** Dialogs and toasts shared by the admin tabs. */
@Injectable({ providedIn: 'root' })
export class AdminUi {
  private alertCtrl = inject(AlertController);
  private toastCtrl = inject(ToastController);

  /** Ask for a moderation reason; resolves to null when the admin cancels. */
  async askReason(header: string, message: string, confirmText: string): Promise<string | null> {
    const alert = await this.alertCtrl.create({
      header,
      message,
      inputs: [
        {
          name: 'reason',
          type: 'textarea',
          placeholder: `Причина (мінімум ${MIN_REASON_LENGTH} символи)`,
          attributes: { maxlength: 500 },
        },
      ],
      buttons: [
        { text: 'Скасувати', role: 'cancel' },
        {
          text: confirmText,
          role: 'confirm',
          handler: (data: { reason?: string }) => (data?.reason ?? '').trim().length >= MIN_REASON_LENGTH,
        },
      ],
    });
    await alert.present();
    const { role, data } = await alert.onDidDismiss();
    if (role !== 'confirm') return null;
    return (data?.values?.reason ?? '').trim();
  }

  async confirm(header: string, message: string, confirmText: string): Promise<boolean> {
    const alert = await this.alertCtrl.create({
      header,
      message,
      buttons: [
        { text: 'Скасувати', role: 'cancel' },
        { text: confirmText, role: 'confirm' },
      ],
    });
    await alert.present();
    const { role } = await alert.onDidDismiss();
    return role === 'confirm';
  }

  async toast(message: string, color: 'success' | 'danger' = 'success'): Promise<void> {
    const toast = await this.toastCtrl.create({ message, color, duration: 2500, position: 'top' });
    await toast.present();
  }

  errorMessage(err: unknown, fallback: string): string {
    const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
    return typeof detail === 'string' && detail ? detail : fallback;
  }
}

/**
 * Server timestamps (created_at, blocked_at, ...) are naive UTC, so they are read as UTC.
 * Event start dates are naive local times; pass `assumeUtc = false` for those.
 */
export function formatDateTime(raw?: string | null, assumeUtc = true): string {
  if (!raw) return '—';
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(raw);
  const parsed = new Date(assumeUtc && !hasZone ? `${raw}Z` : raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return new Intl.DateTimeFormat('uk-UA', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed);
}
