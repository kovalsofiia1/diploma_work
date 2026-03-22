import { inject, Injectable } from '@angular/core';
import { createEffect, ofType, Actions } from '@ngrx/effects';
import { switchMap, map, catchError, of } from 'rxjs';
import {
  loadEvents,
  loadEventsSuccess,
  loadEventsFailure,
  loadCities,
  loadCitiesSuccess,
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
}
