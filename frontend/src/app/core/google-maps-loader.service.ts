import { Injectable } from '@angular/core';
import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root',
})
export class GoogleMapsLoaderService {
  private loadPromise: Promise<boolean> | null = null;

  async loadPlacesLibrary(): Promise<boolean> {
    const apiKey = (environment.googleMapsApiKey ?? '').trim();
    if (!apiKey) {
      return false;
    }

    const globalGoogle = (window as any).google;
    if (globalGoogle?.maps?.places) {
      return true;
    }
    if (this.loadPromise) {
      return this.loadPromise;
    }

    this.loadPromise = new Promise<boolean>((resolve) => {
      const callbackName = `__googleMapsInit_${Date.now()}`;
      (window as any)[callbackName] = () => {
        resolve(true);
        delete (window as any)[callbackName];
      };

      const script = document.createElement('script');
      script.src =
        `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}` +
        `&libraries=places&callback=${encodeURIComponent(callbackName)}`;
      script.async = true;
      script.defer = true;
      script.onerror = () => {
        resolve(false);
        delete (window as any)[callbackName];
      };
      document.head.appendChild(script);
    });

    return this.loadPromise;
  }
}
