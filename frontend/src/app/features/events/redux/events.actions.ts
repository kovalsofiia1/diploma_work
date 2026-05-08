import { createAction, props } from '@ngrx/store';
import { EventInterface, EventsParams } from '../interfaces/events.interface';

export const loadEvents = createAction(
  '[Events] Load Events',
  props<{ params: EventsParams }>(),
);

export const loadFavoriteEvents = createAction(
  '[Events] Load Favorite Events',
  props<{ params: EventsParams }>(),
);

export const loadEventsSuccess = createAction(
  '[Events] Load Events Success',
  props<{ events: EventInterface[]; total: number; done?: boolean }>(),
);

export const loadEventsFailure = createAction(
  '[Events] Load Events Failure',
  props<{ error: string }>(),
);

export const loadEventsFinalize = createAction('[Events] Load Events Finalize');

export const loadCities = createAction('[Events] Get Cities');

export const loadCitiesSuccess = createAction(
  '[Events] Get Cities Success',
  props<{ cities: string[] }>(),
);

export const addFavoriteEvent = createAction(
  '[Events] Add to Favorite',
  props<{ id: string }>(),
);

export const deleteFavoriteEvent = createAction(
  '[Events] Delete from Favorite',
  props<{ id: string }>(),
);

export const addFavoriteEventSuccess = createAction(
  '[Event] Add Favorite Event Success',
);

export const addFavoriteEventFailure = createAction(
  '[Event] Add Favorite Event Failure',
);

export const deleteFavoriteEventSuccess = createAction(
  '[Event] Delete Favorite Event Success',
);

export const deleteFavoriteEventFailure = createAction(
  '[Event] Delete Favorite Event Failure',
);
