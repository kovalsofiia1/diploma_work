import { CommonModule } from '@angular/common';
import { Component, ElementRef, EventEmitter, HostListener, Input, Output, inject } from '@angular/core';
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
  private elementRef = inject<ElementRef<HTMLElement>>(ElementRef);

  @Input() label = '';
  @Input() placeholder = '';
  @Input() searchPlaceholder = 'Пошук...';
  @Input() emptyLabel = 'Усі';
  @Input() searchable = true;
  @Input() value: string | string[] = '';
  @Input() options: Array<string | SearchableDropdownOption> = [];
  @Input() showEmptyOption = true;
  @Input() multiple = false;

  @Output() valueChange = new EventEmitter<string | string[]>();

  isOpen = false;
  searchTerm = '';

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
    if (this.multiple) {
      const selectedValues = this.selectedValues;
      if (!selectedValues.length) return '';
      const labels = this.normalizedOptions
        .filter((opt) => selectedValues.includes(opt.value))
        .map((opt) => opt.label);
      return labels.join(', ');
    }
    const selected = this.normalizedOptions.find(
      (opt) => opt.value === this.value,
    );
    return selected?.label ?? (this.value as string) ?? '';
  }

  get selectedValues(): string[] {
    if (!this.multiple) {
      return typeof this.value === 'string' && this.value ? [this.value] : [];
    }
    return Array.isArray(this.value) ? this.value : [];
  }

  onFocusInput(): void {
    this.isOpen = true;
    this.searchTerm = this.searchable ? this.getInitialSearchTerm() : '';
  }

  onInputChange(value: string): void {
    if (!this.searchable) return;
    this.searchTerm = value ?? '';
    if (!this.isOpen) {
      this.isOpen = true;
    }
  }

  selectOption(option: SearchableDropdownOption): void {
    if (this.multiple) {
      this.toggleMultipleOption(option.value);
      return;
    }
    this.valueChange.emit(option.value);
    this.searchTerm = option.label;
    this.isOpen = false;
  }

  clearSelection(): void {
    this.valueChange.emit(this.multiple ? [] : '');
    this.searchTerm = '';
    if (!this.multiple) {
      this.isOpen = false;
    }
  }

  isSelected(optionValue: string): boolean {
    return this.multiple
      ? this.selectedValues.includes(optionValue)
      : this.value === optionValue;
  }

  private toggleMultipleOption(optionValue: string): void {
    const current = new Set(this.selectedValues);
    if (current.has(optionValue)) {
      current.delete(optionValue);
    } else {
      current.add(optionValue);
    }
    this.valueChange.emit(Array.from(current));
  }

  private getInitialSearchTerm(): string {
    if (this.multiple) return '';
    return typeof this.value === 'string' ? this.value : '';
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

