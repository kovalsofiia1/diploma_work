import {
  AfterViewInit,
  Component,
  ElementRef,
  HostListener,
  ViewChild,
} from '@angular/core';
import { EventInterface } from '../events/interfaces/events.interface';
import { EventsService } from '../events/services/events.service';

@Component({
  selector: 'app-home',
  templateUrl: 'home.page.html',
  styleUrls: ['home.page.scss'],
  standalone: false,

})
export class HomePage implements AfterViewInit {
  @ViewChild('popularRail') popularRail?: ElementRef<HTMLDivElement>;

  organizedEventsCount = 15000;
  isPopularLoading = false;
  hasPopularError = false;
  currentPopularSlide = 0;
  popularSlideCount = 1;
  canScrollPopularLeft = false;
  canScrollPopularRight = false;

  popularEvents: EventInterface[] = [
  ];

  constructor(private eventsService: EventsService) {}

  ngOnInit(): void {
    this.loadPopularEvents();
  }

  ngAfterViewInit(): void {
    this.syncPopularSliderState();
  }

  @HostListener('window:resize')
  onWindowResize(): void {
    this.syncPopularSliderState();
  }

  scrollPopular(direction: 'left' | 'right'): void {
    const rail = this.popularRail?.nativeElement;
    if (!rail) {
      return;
    }
    const offset = this.getPopularScrollOffset(rail);
    rail.scrollBy({
      left: direction === 'right' ? offset : -offset,
      behavior: 'smooth',
    });
  }

  onPopularScroll(): void {
    this.syncPopularSliderState();
  }

  goToPopularSlide(index: number): void {
    const rail = this.popularRail?.nativeElement;
    if (!rail) {
      return;
    }
    const safeIndex = Math.min(
      Math.max(0, index),
      Math.max(0, this.popularSlideCount - 1),
    );
    const maxScrollLeft = Math.max(0, rail.scrollWidth - rail.clientWidth);
    const targetLeft =
      this.popularSlideCount <= 1
        ? 0
        : (safeIndex / (this.popularSlideCount - 1)) * maxScrollLeft;
    rail.scrollTo({ left: targetLeft, behavior: 'smooth' });
  }

  trackByPopularUid(index: number, event: EventInterface): string {
    return event.uid ?? `popular-${index}`;
  }

  trackBySlideIndex(index: number): number {
    return index;
  }

  get popularSlideIndicators(): number[] {
    return Array.from({ length: this.popularSlideCount }, (_, index) => index);
  }

  isPopularSlideActive(index: number): boolean {
    return index === this.currentPopularSlide;
  }

  private loadPopularEvents(): void {
    this.isPopularLoading = true;
    this.hasPopularError = false;
    this.eventsService.getPopularEvents(12).subscribe({
      next: (response) => {
        this.popularEvents = response.items ?? [];
        setTimeout(() => this.syncPopularSliderState(), 0);
      },
      error: () => {
        this.hasPopularError = true;
        this.isPopularLoading = false;
        this.popularEvents = [];
        this.currentPopularSlide = 0;
        this.popularSlideCount = 1;
        this.canScrollPopularLeft = false;
        this.canScrollPopularRight = false;
      },
      complete: () => {
        this.isPopularLoading = false;
      },
    });
  }

  private syncPopularSliderState(): void {
    const rail = this.popularRail?.nativeElement;
    if (!rail) {
      this.currentPopularSlide = 0;
      this.popularSlideCount = 1;
      this.canScrollPopularLeft = false;
      this.canScrollPopularRight = false;
      return;
    }

    const maxScrollLeft = Math.max(0, rail.scrollWidth - rail.clientWidth);
    const pageWidth = this.getPopularScrollOffset(rail);
    const computedSlides = Math.max(1, Math.ceil(maxScrollLeft / pageWidth) + 1);
    const computedIndex =
      computedSlides <= 1 || maxScrollLeft <= 0
        ? 0
        : Math.round((rail.scrollLeft / maxScrollLeft) * (computedSlides - 1));

    this.popularSlideCount = computedSlides;
    this.currentPopularSlide = Math.min(
      Math.max(0, computedIndex),
      this.popularSlideCount - 1,
    );
    this.canScrollPopularLeft = rail.scrollLeft > 8;
    this.canScrollPopularRight = rail.scrollLeft < maxScrollLeft - 8;
  }

  private getPopularScrollOffset(rail: HTMLDivElement): number {
    return Math.max(220, Math.floor(rail.clientWidth * 0.84));
  }
}
