import { createReducer, on } from '@ngrx/store';
import {
  loadEvents,
  loadEventsSuccess,
  loadEventsFailure,
  loadCities,
  loadCitiesSuccess,
  loadFavoriteEvents,
  loadEventsFinalize,
} from './events.actions';
import { EventInterface } from '../interfaces/events.interface';

export interface EventsState {
  events: EventInterface[];
  cities: string[];
  loading: boolean;
  syncing: boolean;
  pagination: {
    skip: number;
    limit: number;
    total: number;
  };
  error: string | null;
}

export const initialState: EventsState = {
  events: [],
  loading: false,
  syncing: false,
  cities: [],
  pagination: {
    skip: 0,
    limit: 20,
    total: 0,
  },
  error: null,
};

export const eventsReducer = createReducer(
  initialState,
  on(loadEvents, (state, { params }) => ({
    ...state,
    loading: true,
    syncing: false,
    pagination: {
      skip: Number.isFinite(params.skip)
        ? Number(params.skip)
        : state.pagination.skip,
      limit: Number.isFinite(params.limit)
        ? Number(params.limit)
        : state.pagination.limit,
      total: state.pagination.total,
    },
  })),
  on(loadFavoriteEvents, (state, { params }) => ({
    ...state,
    loading: true,
    syncing: false,
    pagination: {
      skip: Number.isFinite(params.skip)
        ? Number(params.skip)
        : state.pagination.skip,
      limit: Number.isFinite(params.limit)
        ? Number(params.limit)
        : state.pagination.limit,
      total: state.pagination.total,
    },
  })),
  on(loadEventsSuccess, (state, { events, total, done }) => ({
    ...state,
    events,
    pagination: {
      skip: state.pagination.skip,
      limit: state.pagination.limit,
      total: total,
    },
    loading: false,
    syncing: done === false,
    error: null,
  })),
  on(loadEventsFailure, (state, { error }) => ({
    ...state,
    loading: false,
    syncing: false,
    error,
  })),
  on(loadEventsFinalize, (state) => ({
    ...state,
    loading: false,
    syncing: false,
  })),
  on(loadCitiesSuccess, (state, { cities }) => ({
    ...state,
    cities,
  })),
);
