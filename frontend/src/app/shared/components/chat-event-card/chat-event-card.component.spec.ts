import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { IonicModule } from '@ionic/angular';

import { ChatEvent } from 'src/app/features/chat/interfaces/chat.interface';
import { ChatEventCardComponent } from './chat-event-card.component';

const EVENT: ChatEvent = {
  id: 12,
  uid: 'external:12',
  name: 'Стендап 8х8',
  type: 'Стендап, Комедія',
  startDate: '2026-11-03T19:00:00',
  city: 'Київ',
  location_name: 'Клуб Х',
  price_low: '200',
  url: 'https://concert.ua/event/12',
  order_url: 'https://concert.ua/buy/12',
};

describe('ChatEventCardComponent', () => {
  let fixture: ComponentFixture<ChatEventCardComponent>;
  let component: ChatEventCardComponent;

  function render(event: Partial<ChatEvent> = {}): HTMLElement {
    fixture = TestBed.createComponent(ChatEventCardComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('event', { ...EVENT, ...event });
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChatEventCardComponent, IonicModule.forRoot()],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('shows name, place, price and tags as text', () => {
    const el = render();

    expect(el.querySelector('.chat-card__title')?.textContent).toContain('Стендап 8х8');
    expect(el.textContent).toContain('Клуб Х, Київ');
    expect(el.querySelector('.chat-card__price')?.textContent).toContain('₴200');
    expect(Array.from(el.querySelectorAll('.chat-card__tag')).map((t) => t.textContent?.trim())).toEqual(['Стендап', 'Комедія']);
  });

  it('formats the date in Ukrainian and handles a missing one', () => {
    render();
    expect(component.dateLabel).toMatch(/03\.11\.2026/);

    render({ startDate: null });
    expect(component.dateLabel).toBe('Дата уточнюється');
  });

  it('reads free-text prices instead of calling them free', () => {
    render({ price_low: '400 грн' });
    expect(component.priceLabel).toBe('400 грн');

    render({ price_low: 'від 6200 грн' });
    expect(component.priceLabel).toBe('від 6200 грн');

    render({ price_low: 'безкоштовно' });
    expect(component.priceLabel).toBe('Безкоштовно');

    render({ price_low: '0' });
    expect(component.priceLabel).toBe('Безкоштовно');

    render({ price_low: null });
    expect(component.priceLabel).toBeNull();

    render({ price_low: 'x'.repeat(60) });
    expect(component.priceLabel?.length).toBe(25);
  });

  it('offers the ticket link first and the site otherwise', () => {
    const withTickets = render();
    const link = withTickets.querySelector('a.chat-card__link') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('https://concert.ua/buy/12');
    expect(link.textContent).toContain('Квитки');
    expect(link.getAttribute('rel')).toContain('noopener');
    expect(link.getAttribute('target')).toBe('_blank');

    const siteOnly = render({ order_url: null });
    expect(siteOnly.querySelector('a.chat-card__link')?.textContent).toContain('Сайт');
  });

  it('never links to anything but http(s)', () => {
    expect(render({ order_url: 'javascript:alert(1)', url: 'https://ok.example/e' }).querySelector('a')?.getAttribute('href')).toBe('https://ok.example/e');
    expect(render({ order_url: 'javascript:alert(1)', url: 'data:text/html,<script>1</script>' }).querySelector('a')).toBeNull();
    expect(render({ order_url: null, url: 'ftp://files.example/x' }).querySelector('a')).toBeNull();
    expect(render({ order_url: null, url: 'not a url' }).querySelector('a')).toBeNull();
  });

  it('renders event text as text, not markup', () => {
    const el = render({ name: '<img src=x onerror=alert(1)>' });

    expect(el.querySelector('img')).toBeNull();
    expect(el.querySelector('.chat-card__title')?.textContent).toContain('<img src=x onerror=alert(1)>');
  });

  it('opens the event page with an encoded uid and tells the widget', () => {
    const el = render();
    const router = TestBed.inject(Router);
    const navigate = spyOn(router, 'navigate').and.resolveTo(true);
    let opened = 0;
    component.opened.subscribe(() => opened++);

    (el.querySelector('.chat-card__main') as HTMLButtonElement).click();

    expect(navigate).toHaveBeenCalledWith(['/tabs/events', 'external%3A12']);
    expect(opened).toBe(1);
  });
});
