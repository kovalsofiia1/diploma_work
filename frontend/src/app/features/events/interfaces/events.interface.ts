import { Optional } from "@angular/core"

export enum EventKind {
    internal = "internal",
    external = "external",
}

export interface EventInterface {
    name?: string,
    type?: string,
    url?: string,
    order_url?: string,
    startDate?: string,
    endDate?: string,
    location_name?: string,
    city?: string,
    price_low?: string,
    price_high?: string,
    price_currency?: string,
    image?: string,
    source?: string,
    verified?: boolean,
    description?: string,
    id?: number,
    uid?: string,
    kind?: EventKind,
}

export interface EventsApiResponse {
    items: EventInterface[];
    total: number;
}

export interface EventCreateRequest {
    name: string,
    type?: string,
    url?: string,
    order_url?: string,
    startDate?: string,
    endDate?: string,
    location_name?: string,
    city?: string,
    price_low?: string,
    price_high?: string,
    price_currency?: string,
    description?: string,
    image?: File,
    verified?: boolean,
}

export interface Cities {
    cities: string[];
}

export interface EventsParams {
    skip?: number,
    limit?: number,
    city?: string,
    start_date?: string,
    end_date?: string,
    min_price?: number,
    max_price?: number,
    event_type?: string,
}