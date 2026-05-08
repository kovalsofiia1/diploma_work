import { inject, Injectable } from '@angular/core';
import { createEffect, ofType, Actions } from '@ngrx/effects';
import { switchMap, map, catchError, of, endWith } from 'rxjs';
import {
  loadEvents,
  loadEventsSuccess,
  loadEventsFailure,
  loadCities,
  loadCitiesSuccess,
  loadFavoriteEvents,
  loadEventsFinalize,
  addFavoriteEvent,
  addFavoriteEventFailure,
  addFavoriteEventSuccess,
  deleteFavoriteEventFailure,
  deleteFavoriteEventSuccess,
  deleteFavoriteEvent,
} from './events.actions';
import { EventsService } from '../services/events.service';

@Injectable()
export class EventsEffects {
  private actions$ = inject(Actions);
  private eventsService = inject(EventsService);

  loadEvents$ = createEffect(() =>
    this.actions$.pipe(
      ofType(loadEvents),
      switchMap((action) =>
        this.eventsService.getEvents(action.params).pipe(
          map((response) =>
            loadEventsSuccess({
              events: response.items,
              total: response.total,
              done: response.done ?? true,
            }),
          ),
          catchError((error) => of(loadEventsFailure({ error }))),
          endWith(loadEventsFinalize()),
        ),
      ),
    ),
  );

  loadFavoriteEvents$ = createEffect(() =>
    this.actions$.pipe(
      ofType(loadFavoriteEvents),
      switchMap((action) =>
        this.eventsService.getFavoriteEvents(action.params).pipe(
          map((response) =>
            loadEventsSuccess({
              events: response.items,
              total: response.total,
              done: true,
            }),
          ),
          catchError((error) => of(loadEventsFailure({ error }))),
        ),
      ),
    ),
  );

  loadCities$ = createEffect(() =>
    this.actions$.pipe(
      ofType(loadCities),
      switchMap((action) =>
        this.eventsService
          .getCities()
          .pipe(map((response) => loadCitiesSuccess({ cities: response }))),
      ),
    ),
  );

  addFavoriteEvent$ = createEffect(() =>
    this.actions$.pipe(
      ofType(addFavoriteEvent),
      switchMap((action) =>
        this.eventsService.addFavoriteEvent(action.id).pipe(
          map((event) => addFavoriteEventSuccess()),
          catchError((error) => of(addFavoriteEventFailure())),
        ),
      ),
    ),
  );

  deleteFavoriteEvent$ = createEffect(() =>
    this.actions$.pipe(
      ofType(deleteFavoriteEvent),
      switchMap((action) =>
        this.eventsService.deleteFavoriteEvent(action.id).pipe(
          map((event) => deleteFavoriteEventSuccess()),
          catchError((error) => of(deleteFavoriteEventFailure())),
        ),
      ),
    ),
  );
}
