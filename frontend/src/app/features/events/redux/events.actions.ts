import { createAction, props } from '@ngrx/store';
import { EventInterface, EventsParams } from '../interfaces/events.interface';

export const loadEvents = createAction(
  '[Events] Load Events',
  props<{ params: EventsParams }>(),
);

export const loadEventsSuccess = createAction(
  '[Events] Load Events Success',
  props<{ events: EventInterface[]; total: number }>(),
);

export const loadEventsFailure = createAction(
  '[Events] Load Events Failure',
  props<{ error: string }>(),
);

export const loadCities = createAction('[Events] Get Cities');

export const loadCitiesSuccess = createAction(
  '[Events] Get Cities Success',
  props<{ cities: string[] }>(),
);
