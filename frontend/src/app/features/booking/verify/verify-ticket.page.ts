import { Component, ElementRef, inject, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { IonicModule, NavController, ToastController } from '@ionic/angular';
import QrScanner from 'qr-scanner';
import { firstValueFrom } from 'rxjs';
import { BookingService } from '../services/booking.service';

type VerifyStatus = 'idle' | 'success' | 'error';

type BarcodeDetectorResult = { rawValue?: string };
type BarcodeDetectorCtor = new (options?: { formats?: string[] }) => {
  detect: (source: ImageBitmapSource) => Promise<BarcodeDetectorResult[]>;
};

@Component({
  selector: 'app-verify-ticket',
  templateUrl: './verify-ticket.page.html',
  styleUrls: ['./verify-ticket.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule],
})
export class VerifyTicketPage implements OnDestroy {
  private navCtrl = inject(NavController);
  private toastCtrl = inject(ToastController);
  private bookingService = inject(BookingService);

  @ViewChild('cameraVideo') cameraVideo?: ElementRef<HTMLVideoElement>;

  code = '';
  status: VerifyStatus = 'idle';
  message = '';
  scanError = '';
  scanning = false;

  private stream: MediaStream | null = null;
  private scanRafId: number | null = null;
  private detector: InstanceType<BarcodeDetectorCtor> | null = null;
  private qrScanner: QrScanner | null = null;
  private lastScannedRaw = '';
  private lastScannedAtMs = 0;

  ngOnDestroy(): void {
    this.stopCamera();
  }

  get cameraSupported(): boolean {
    return !!navigator.mediaDevices?.getUserMedia;
  }

  get barcodeSupported(): boolean {
    return typeof (window as any).BarcodeDetector !== 'undefined';
  }

  back(): void {
    this.stopCamera();
    this.navCtrl.back();
  }

  async onCameraFrameTap(): Promise<void> {
    this.status = 'idle';
    this.message = '';
    this.scanError = '';
    this.lastScannedRaw = '';
    if (!this.scanning) {
      await this.startCameraScan();
    }
  }

  setCodeFromInput(ev: any): void {
    this.code = (ev?.detail?.value ?? '').toString();
    if (this.status !== 'idle') {
      this.status = 'idle';
      this.message = '';
    }
  }

  async startCameraScan(): Promise<void> {
    this.scanError = '';
    if (!this.cameraSupported) {
      this.scanError = 'Камера недоступна у цьому браузері.';
      return;
    }

    try {
      this.stopCamera();
      const video = this.cameraVideo?.nativeElement;
      if (!video) {
        this.scanError = 'Не вдалося ініціалізувати превʼю камери.';
        this.stopCamera();
        return;
      }

      if (this.barcodeSupported) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'environment' },
          },
          audio: false,
        });
        this.stream = stream;
        video.srcObject = stream;
        await video.play();
        this.scanning = true;
        this.ensureDetector();
        this.scanLoop();
        return;
      }

      this.qrScanner = new QrScanner(
        video,
        async (result) => {
          const raw = this.normalizeScannedValue(result);
          if (!raw) return;
          if (!this.shouldProcessScan(raw)) return;
          this.code = raw;
          await this.verify(true);
        },
        {
          preferredCamera: 'environment',
        },
      );
      await this.qrScanner.start();
      this.scanning = true;
    } catch {
      this.scanError =
        'Не вдалося відкрити камеру. Перевірте дозволи браузера та використовуйте HTTPS.';
      this.stopCamera();
    }
  }

  stopCamera(): void {
    this.scanning = false;
    if (this.scanRafId !== null) {
      cancelAnimationFrame(this.scanRafId);
      this.scanRafId = null;
    }
    if (this.qrScanner) {
      this.qrScanner.stop();
      this.qrScanner.destroy();
      this.qrScanner = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    const video = this.cameraVideo?.nativeElement;
    if (video) {
      video.pause();
      video.srcObject = null;
    }
  }

  async onQrFilePicked(ev: Event): Promise<void> {
    this.scanError = '';

    const input = ev.target as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file) return;
    try {
      let raw = '';
      if (this.barcodeSupported) {
        this.ensureDetector();
        const bitmap = await createImageBitmap(file);
        raw = await this.detectRawValue(bitmap);
      } else {
        const scanned = await QrScanner.scanImage(file, {
          returnDetailedScanResult: true,
        } as any);
        raw = this.normalizeScannedValue(scanned);
      }
      if (!raw) {
        this.scanError = 'QR-код на зображенні не знайдено.';
        return;
      }
      this.code = raw;
      await this.verify(true);
    } catch {
      this.scanError = 'Не вдалося зчитати QR-код із файлу.';
    } finally {
      if (input) {
        input.value = '';
      }
    }
  }

  async verify(silent = false): Promise<void> {
    const raw = (this.code ?? '').toString().trim();
    if (!raw) {
      this.status = 'error';
      this.message = 'Введіть або відскануйте QR-код.';
      return;
    }

    const qrToken = this.extractQrToken(raw);
    if (!qrToken) {
      this.status = 'error';
      this.message =
        'QR не містить валідний токен. Згенеруйте QR заново в "Мої квитки".';
      return;
    }

    try {
      const response = await firstValueFrom(this.bookingService.verifyTicket(qrToken));
      const valid = (response?.status ?? '').toUpperCase() === 'VALID';
      if (!valid) {
        this.status = 'error';
        this.message = response?.reason?.trim() || 'Квиток недійсний.';
        return;
      }

      await firstValueFrom(this.bookingService.checkinTicket(qrToken));
      this.status = 'success';
      this.message = 'Квиток дійсний. Вхід підтверджено.';
      if (!silent) {
        const toast = await this.toastCtrl.create({
          message: 'Чекін виконано.',
          duration: 1200,
          position: 'top',
          color: 'success',
        });
        await toast.present();
      }
    } catch (error) {
      const backendReason = this.extractBackendError(error);
      this.status = 'error';
      this.message = backendReason || 'Помилка перевірки. Переконайтесь, що бекенд доступний.';
    }
  }

  private ensureDetector(): void {
    if (this.detector) return;
    const Detector = (window as any).BarcodeDetector as BarcodeDetectorCtor;
    this.detector = new Detector({ formats: ['qr_code'] });
  }

  private async detectRawValue(source: ImageBitmapSource): Promise<string> {
    if (!this.detector) return '';
    const results = await this.detector.detect(source);
    const first = results.find((r) => (r.rawValue ?? '').trim());
    return (first?.rawValue ?? '').trim();
  }

  private scanLoop(): void {
    if (!this.scanning) return;
    const video = this.cameraVideo?.nativeElement;
    if (!video || video.readyState < 2) {
      this.scanRafId = requestAnimationFrame(() => this.scanLoop());
      return;
    }

    this.detectRawValue(video)
      .then(async (raw) => {
        if (raw) {
          if (!this.shouldProcessScan(raw)) {
            this.scanRafId = requestAnimationFrame(() => this.scanLoop());
            return;
          }
          this.code = raw;
          await this.verify(true);
        }
        this.scanRafId = requestAnimationFrame(() => this.scanLoop());
      })
      .catch(() => {
        this.scanRafId = requestAnimationFrame(() => this.scanLoop());
      });
  }

  private normalizeScannedValue(result: unknown): string {
    if (typeof result === 'string') return result.trim();
    if (result && typeof result === 'object' && 'data' in (result as any)) {
      return String((result as any).data ?? '').trim();
    }
    if (result && typeof result === 'object' && 'rawValue' in (result as any)) {
      return String((result as any).rawValue ?? '').trim();
    }
    return '';
  }

  private parsePayload(raw: string): { qrToken: string } {
    const value = (raw ?? '').trim();
    if (!value) return { qrToken: '' };
    try {
      const parsed = JSON.parse(value) as { qr_token?: unknown };
      return {
        qrToken: typeof parsed.qr_token === 'string' ? parsed.qr_token.trim() : '',
      };
    } catch {
      return { qrToken: '' };
    }
  }

  private extractQrToken(raw: string): string {
    const value = (raw ?? '').trim();
    if (!value) return '';
    const fromJson = this.parsePayload(value).qrToken;
    if (fromJson) return fromJson;
    // JWT-like token: header.payload.signature
    if (/^[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+$/.test(value)) return value;
    return '';
  }

  private extractBackendError(error: unknown): string {
    if (!(error instanceof HttpErrorResponse)) return '';
    const detail = (error.error as { detail?: unknown } | null)?.detail;
    if (typeof detail === 'string') return detail.trim();
    return '';
  }

  private shouldProcessScan(raw: string): boolean {
    const value = raw.trim();
    if (!value) return false;
    const now = Date.now();
    const isSameCode = value === this.lastScannedRaw;
    const withinCooldown = now - this.lastScannedAtMs < 1200;
    if (isSameCode && withinCooldown) return false;
    this.lastScannedRaw = value;
    this.lastScannedAtMs = now;
    return true;
  }
}

