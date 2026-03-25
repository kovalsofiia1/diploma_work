import { EventsState } from './events.reducer';
import { createFeatureSelector, createSelector } from '@ngrx/store';

export const selectEventsState = createFeatureSelector<EventsState>('events');

export const selectEvents = createSelector(
  selectEventsState,
  (state) => state.events,
);

export const selectEventsLoading = createSelector(
  selectEventsState,
  (state) => state.loading,
);

export const selectEventsPagination = createSelector(
  selectEventsState,
  (state) => state.pagination,
);

export const selectEventsError = createSelector(
  selectEventsState,
  (state) => state.error,
);

export const selectCities = createSelector(
  selectEventsState,
  (state) => state?.cities ?? [],
);
