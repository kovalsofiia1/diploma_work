import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { EventsParams } from 'src/app/features/events/interfaces/events.interface';
import {
  SearchableDropdownComponent,
  SearchableDropdownOption,
} from '../searchable-dropdown/searchable-dropdown.component';

type DatePreset = 'all' | 'today' | 'week' | 'month' | 'year' | 'specific';

@Component({
  selector: 'app-events-filter',
  templateUrl: './events-filter.component.html',
  styleUrls: ['./events-filter.component.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, IonicModule, SearchableDropdownComponent],
})
export class EventsFilterComponent {
  @Input() cities: string[] = [];
  @Output() paramsChange = new EventEmitter<EventsParams>();

  readonly maxPrice = 5000;
  selectedCity = '';
  selectedDate: DatePreset = 'all';
  selectedStartDate = '';
  selectedEndDate = '';
  priceRange = { lower: 0, upper: this.maxPrice };
  readonly dateOptions: SearchableDropdownOption[] = [
    { value: 'all', label: 'Усі дати' },
    { value: 'today', label: 'Сьогодні' },
    { value: 'week', label: 'Цього тижня' },
    { value: 'month', label: 'Цього місяця' },
    { value: 'year', label: 'Цього року' },
    { value: 'specific', label: 'Конкретні дати' },
  ];

  applyFilters(): void {
    const params: EventsParams = {};

    if (this.selectedCity.trim()) {
      params.city = this.selectedCity.trim();
    }

    if (this.priceRange.lower > 0) {
      params.min_price = this.priceRange.lower;
    }
    if (this.priceRange.upper < this.maxPrice) {
      params.max_price = this.priceRange.upper;
    }

    const presetRange = this.resolveDateRange(this.selectedDate);
    let start =
      this.selectedDate === 'specific'
        ? this.selectedStartDate || undefined
        : presetRange.start;
    let end =
      this.selectedDate === 'specific'
        ? this.selectedEndDate || undefined
        : presetRange.end;

    if (start && end && end < start) {
      [start, end] = [end, start];
    }

    if (start) {
      params.start_date = start;
    }
    if (end) {
      params.end_date = end;
    }

    this.paramsChange.emit(params);
  }

  resetFilters(): void {
    this.selectedCity = '';
    this.selectedDate = 'all';
    this.selectedStartDate = '';
    this.selectedEndDate = '';
    this.priceRange = { lower: 0, upper: this.maxPrice };
    this.paramsChange.emit({});
  }

  private resolveDateRange(preset: DatePreset): { start?: string; end?: string } {
    const now = new Date();
    const start = new Date(now);
    const end = new Date(now);

    switch (preset) {
      case 'today': {
        return { start: this.toDate(start), end: this.toDate(end) };
      }
      case 'week': {
        end.setDate(end.getDate() + 7);
        return { start: this.toDate(start), end: this.toDate(end) };
      }
      case 'month': {
        end.setMonth(end.getMonth() + 1);
        return { start: this.toDate(start), end: this.toDate(end) };
      }
      case 'year': {
        end.setFullYear(end.getFullYear() + 1);
        return { start: this.toDate(start), end: this.toDate(end) };
      }
      default:
        return {};
    }
  }

  private toDate(d: Date): string {
    return d.toISOString().slice(0, 10);
  }
}

