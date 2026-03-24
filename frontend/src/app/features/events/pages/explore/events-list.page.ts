import { Component, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonContent, IonicModule } from '@ionic/angular';
import { AppHeaderComponent } from 'src/app/shared/components/app-header/app-header.component';
import { EventsListComponent } from 'src/app/shared/components/events-list/events-list.component';
import { EventsFilterComponent } from 'src/app/shared/components/events-filter/events-filter.component';
import {
  loadCities,
  loadEvents,
  loadFavoriteEvents,
} from '../../redux/events.actions';
import { Store } from '@ngrx/store';
import {
  EventInterface,
  EventsParams,
} from '../../interfaces/events.interface';
import { EventsState } from '../../redux/events.reducer';
import {
  selectCities,
  selectEvents,
  selectEventsError,
  selectEventsLoading,
  selectEventsPagination,
} from '../../redux/events.selectors';
import { ActivatedRoute, Router } from '@angular/router';
import { BehaviorSubject, Observable } from 'rxjs';

@Component({
  selector: 'app-events-list-page',
  templateUrl: './events-list.page.html',
  styleUrls: ['./events-list.page.scss'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IonicModule,
    AppHeaderComponent,
    EventsListComponent,
    EventsFilterComponent,
  ],
})
export class EventsListPage {
  @ViewChild(IonContent) content?: IonContent;

  query = '';
  showFilters = false;
  isFavorite$ = new BehaviorSubject<boolean>(false);
  showSavedOnly = false;
  readonly pageSize = 9;

  pagination = { skip: 0, limit: this.pageSize, total: 0 };

  allEvents: EventInterface[] = [];
  cities: string[] = [];
  activeFilters: EventsParams = {};

  events$ = this.store.select(selectEvents);
  cities$ = this.store.select(selectCities);
  loading$ = this.store.select(selectEventsLoading);
  pagination$ = this.store.select(selectEventsPagination);
  error$ = this.store.select(selectEventsError);

  constructor(private store: Store<{ events: EventsState }>, private route: ActivatedRoute, private router: Router) {}

  ngOnInit() {
    this.store.dispatch(loadCities());
    this.route.queryParams.subscribe(params => {
      const isFavorite = params['isFavorite'];
      if (isFavorite) {
        this.isFavorite$.next(true);
        
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: { isFavorite: null },
          queryParamsHandling: 'merge',
          replaceUrl: true
        });
      }
    });
    this.isFavorite$.subscribe(value => {
      console.log('Changed:', value);
      this.loadPage(1, true);
      this.showSavedOnly = value;
    });
    
    this.events$.subscribe((events) => {
      this.allEvents = events;
    });
    this.pagination$.subscribe((pagination) => {
      this.pagination = pagination;
    });
    this.cities$.subscribe((cities) => {
      this.cities = cities;
    });
  }

  //wtf
  get visibleEvents(): EventInterface[] {
    const q = this.query.trim().toLowerCase();
    let items = this.allEvents;

    if (!q) return items;

    return items.filter((i) => {
      const hay = `${i.name} ${i.city} ${i.description}`.toLowerCase();
      return hay.includes(q);
    });
  }

  toggleSavedOnly(): void {
    this.isFavorite$.next(!this.isFavorite$.value);
  }

  toggleFilters(): void {
    this.showFilters = !this.showFilters;
  }

  onFilterParamsChange(params: EventsParams): void {
    this.activeFilters = { ...params };
    this.loadPage(1, true);
  }

  get currentPage(): number {
    return Math.floor(this.pagination.skip / this.pagination.limit) + 1;
  }

  get totalPages(): number {
    if (!this.pagination.total || !this.pagination.limit) return 1;
    return Math.max(
      1,
      Math.ceil(this.pagination.total / this.pagination.limit),
    );
  }

  get canPrevPage(): boolean {
    return this.pagination.skip > 0;
  }

  get canNextPage(): boolean {
    return this.pagination.skip + this.pagination.limit < this.pagination.total;
  }

  get pageTiles(): number[] {
    const total = this.totalPages;
    const current = this.currentPage;
    const radius = 2;
    const start = Math.max(1, current - radius);
    const end = Math.min(total, current + radius);
    const tiles: number[] = [];
    for (let page = start; page <= end; page += 1) {
      tiles.push(page);
    }
    return tiles;
  }

  prevPage(): void {
    if (!this.canPrevPage) return;
    this.goToPage(this.currentPage - 1);
  }

  nextPage(): void {
    if (!this.canNextPage) return;
    this.goToPage(this.currentPage + 1);
  }

  lastPage(): void {
    this.goToPage(this.totalPages);
  }

  goToPage(page: number): void {
    this.loadPage(page);
  }

  private loadPage(page: number, force: boolean = false): void {
    const safePage = Math.min(this.totalPages, Math.max(1, Math.floor(page)));
    const skip = (safePage - 1) * this.pagination.limit;
    if (!force && skip === this.pagination.skip) return;

    const params = {
      params: {
        ...this.activeFilters,
        skip,
        limit: this.pagination.limit,
      },
    };
    this.store.dispatch(
      this.isFavorite$.value ? loadFavoriteEvents(params) : loadEvents(params),
    );
    this.scrollToTop();
  }

  isActivePage(page: number): boolean {
    return page === this.currentPage;
  }

  trackPage(_: number, page: number): number {
    return page;
  }

  private scrollToTop(): void {
    this.content?.scrollToTop(250);
  }
}
