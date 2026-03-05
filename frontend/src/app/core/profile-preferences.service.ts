import { Injectable } from '@angular/core';
import { Preferences } from '@capacitor/preferences';

export interface UserProfilePreferences {
  fullName?: string;
  about?: string;
  birthDate?: string; // YYYY-MM-DD
  interests?: string[];
  subscribedCities?: string[];
}

const KEY_PREFIX = 'profile_ext:';

@Injectable({ providedIn: 'root' })
export class ProfilePreferencesService {
  private key(userId: number): string {
    return `${KEY_PREFIX}${userId}`;
  }

  async get(userId: number): Promise<UserProfilePreferences> {
    const { value } = await Preferences.get({ key: this.key(userId) });
    if (!value) return {};
    try {
      const parsed = JSON.parse(value) as UserProfilePreferences;
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      return {};
    }
  }

  async set(userId: number, prefs: UserProfilePreferences): Promise<void> {
    await Preferences.set({ key: this.key(userId), value: JSON.stringify(prefs ?? {}) });
  }

  async patch(userId: number, patch: Partial<UserProfilePreferences>): Promise<UserProfilePreferences> {
    const current = await this.get(userId);
    const next: UserProfilePreferences = {
      ...current,
      ...patch,
    };
    await this.set(userId, next);
    return next;
  }
}

