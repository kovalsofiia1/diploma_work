import { CommonModule } from '@angular/common';
import { Component, ElementRef, EventEmitter, HostListener, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';

export interface SearchableDropdownOption {
  value: string;
  label: string;
}

@Component({
  selector: 'app-searchable-dropdown',
  templateUrl: './searchable-dropdown.component.html',
  styleUrls: ['./searchable-dropdown.component.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, IonicModule],
})
export class SearchableDropdownComponent {
  @Input() label = '';
  @Input() placeholder = '';
  @Input() searchPlaceholder = 'Пошук...';
  @Input() emptyLabel = 'Усі';
  @Input() searchable = true;
  @Input() value = '';
  @Input() options: Array<string | SearchableDropdownOption> = [];
  @Input() showEmptyOption = true;

  @Output() valueChange = new EventEmitter<string>();

  isOpen = false;
  searchTerm = '';

  constructor(private elementRef: ElementRef<HTMLElement>) {}

  get normalizedOptions(): SearchableDropdownOption[] {
    return this.options.map((opt) =>
      typeof opt === 'string' ? { value: opt, label: opt } : opt
    );
  }

  get filteredOptions(): SearchableDropdownOption[] {
    if (!this.searchable) return this.normalizedOptions;
    const q = this.searchTerm.trim().toLowerCase();
    if (!q) return this.normalizedOptions;
    return this.normalizedOptions.filter((opt) => opt.label.toLowerCase().includes(q));
  }

  get displayValue(): string {
    if (this.isOpen) {
      return this.searchTerm;
    }
    const selected = this.normalizedOptions.find((opt) => opt.value === this.value);
    return selected?.label ?? this.value ?? '';
  }

  onFocusInput(): void {
    this.isOpen = true;
    this.searchTerm = this.searchable ? (this.value || '') : '';
  }

  onInputChange(value: string): void {
    if (!this.searchable) return;
    this.searchTerm = value ?? '';
    if (!this.isOpen) {
      this.isOpen = true;
    }
  }

  selectOption(option: SearchableDropdownOption): void {
    this.valueChange.emit(option.value);
    this.searchTerm = option.label;
    this.isOpen = false;
  }

  clearSelection(): void {
    this.valueChange.emit('');
    this.searchTerm = '';
    this.isOpen = false;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as Node | null;
    if (!target) return;
    if (this.elementRef.nativeElement.contains(target)) return;
    this.isOpen = false;
    this.searchTerm = '';
  }
}

