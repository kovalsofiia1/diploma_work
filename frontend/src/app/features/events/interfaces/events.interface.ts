export enum EventKind {
  internal = 'internal',
  external = 'external',
}

export interface EventInterface {
  name?: string;
  type?: string;
  url?: string;
  order_url?: string;
  startDate?: string;
  endDate?: string;
  location_name?: string;
  city?: string;
  price_low?: string;
  price_high?: string;
  price_currency?: string;
  image?: string;
  source?: string;
  verified?: boolean;
  description?: string;
  additional?: string;
  total_places?: number;
  booked_places?: number;
  available_places?: number;
  id?: number;
  uid?: string;
  kind?: EventKind;
  isSaved?: boolean;
  can_edit?: boolean;
  organizer_name?: string;
  organizer_email?: string;
  organizer_phone?: string;
  organizer_description?: string;
  organizer_organization_name?: string;
}

export interface EventsApiResponse {
  items: EventInterface[];
  total: number;
  done?: boolean;
}

export interface EventCreateRequest {
  name: string;
  type?: string;
  url?: string;
  order_url?: string;
  startDate?: string;
  endDate?: string;
  location_name?: string;
  city?: string;
  price_low?: string;
  price_high?: string;
  price_currency?: string;
  description?: string;
  additional?: string;
  image?: string | File;
  verified?: boolean;
  source?: string;
  total_places?: number;
}

export interface Cities {
  cities: string[];
}

export interface EventsParams {
  skip?: number;
  limit?: number;
  search?: string;
  city?: string;
  start_date?: string;
  end_date?: string;
  min_price?: number;
  max_price?: number;
  event_type?: string;
}

export type EventMemberRole = 'organizer' | 'scanner';

export interface EventMembersUpsertRequest {
  emails: string[];
  role: EventMemberRole;
}

export interface EventMembersUpsertResponse {
  role: EventMemberRole;
  added: string[];
  updated: string[];
  missing: string[];
}

export interface EventMember {
  user_id: number;
  email: string;
  full_name?: string;
  role: EventMemberRole;
}

export interface EventStatItem {
  event_id: number;
  uid: string;
  name: string;
  start_date?: string;
  status: string;
  total_places?: number;
  booked_places: number;
  available_places?: number;
  fill_rate?: number;
  is_past: boolean;
}

export interface BookingsChartPoint {
  date: string;
  count: number;
}

export interface OrganizerStatsResponse {
  total_events: number;
  upcoming_events: number;
  past_events: number;
  total_tickets_sold: number;
  events: EventStatItem[];
  bookings_by_day: BookingsChartPoint[];
}
