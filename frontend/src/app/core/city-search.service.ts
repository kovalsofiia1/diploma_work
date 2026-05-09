import { Injectable } from '@angular/core';

export type CitySuggestion = {
  city: string;
  displayName: string;
};

@Injectable({
  providedIn: 'root',
})
export class CitySearchService {
  async searchCities(query: string, limit = 8): Promise<CitySuggestion[]> {
    const q = query.trim();
    if (q.length < 2) {
      return [];
    }

    const url =
      'https://nominatim.openstreetmap.org/search?' +
      `format=jsonv2&addressdetails=1&countrycodes=ua&limit=${Math.max(1, Math.min(20, limit))}` +
      `&q=${encodeURIComponent(q)}`;

    try {
      const response = await fetch(url, {
        headers: {
          Accept: 'application/json',
          'Accept-Language': 'uk,en;q=0.8',
        },
      });
      if (!response.ok) {
        return [];
      }

      const payload = (await response.json()) as any[];
      if (!Array.isArray(payload)) {
        return [];
      }

      const dedup = new Set<string>();
      const items: CitySuggestion[] = [];
      for (const entry of payload) {
        const city = this.extractCityName(entry).trim();
        if (!city) {
          continue;
        }
        const key = city.toLowerCase();
        if (dedup.has(key)) {
          continue;
        }
        dedup.add(key);
        items.push({
          city,
          displayName: (entry?.display_name ?? city).toString(),
        });
      }
      return items;
    } catch {
      return [];
    }
  }

  private extractCityName(entry: any): string {
    const address = entry?.address ?? {};
    return (
      address?.city ??
      address?.town ??
      address?.village ??
      address?.municipality ??
      address?.county ??
      address?.state ??
      entry?.name ??
      ''
    )
      .toString()
      .trim();
  }
}
