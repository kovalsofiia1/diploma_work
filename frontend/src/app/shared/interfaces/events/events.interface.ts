export interface PopularEventItem {
    title: string;
    city: string;
    date: string;
    uid: string;
    description: string;
    theme: 'art' | 'games' | 'cinema';
    price?: number;
    availableSeats?: number;
    tag?: string;
    featured?: boolean;
    imageUrl?: string;
    isFavorite?: boolean;
  }