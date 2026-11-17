import { ComponentFixture, TestBed, fakeAsync, flush, tick } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { Observable, Subject, of, throwError } from 'rxjs';

import { ChatError, ChatEvent, ChatReply } from 'src/app/features/chat/interfaces/chat.interface';
import { ChatService } from 'src/app/features/chat/services/chat.service';
import { CHAT_EXAMPLE_PROMPTS, CHAT_SLOW_AFTER_MS, CHAT_STORAGE_KEY, ChatWidgetComponent } from './chat-widget.component';

const EVENT: ChatEvent = { id: 1, uid: 'external:1', name: 'Концерт у Львові', city: 'Львів', price_low: '300', startDate: '2026-11-08T19:00:00' };

function reply(text = 'Ось добірка.', events: ChatEvent[] = [], remaining: number | null = 19): ChatReply {
  return { response: { status: 'found', reply: text, events, suggestions: [], degraded: false }, limit: 20, remaining };
}

describe('ChatWidgetComponent', () => {
  let fixture: ComponentFixture<ChatWidgetComponent>;
  let el: HTMLElement;
  let send: jasmine.Spy<(message: string) => Observable<ChatReply>>;
  let warmUp: jasmine.Spy;

  function create(): void {
    fixture = TestBed.createComponent(ChatWidgetComponent);
    el = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
  }

  const q = <T extends Element = HTMLElement>(selector: string): T | null => el.querySelector<T>(selector);
  const all = (selector: string): HTMLElement[] => Array.from(el.querySelectorAll<HTMLElement>(selector));

  function openPanel(): void {
    q('.chat__fab')!.click();
    fixture.detectChanges();
  }

  function type(text: string): void {
    const textarea = q<HTMLTextAreaElement>('textarea')!;
    textarea.value = text;
    textarea.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  function submit(): void {
    q<HTMLFormElement>('form')!.dispatchEvent(new Event('submit', { cancelable: true }));
    fixture.detectChanges();
  }

  const bubbles = (): string[] => all('.chat__bubble').map((b) => b.textContent!.trim());

  beforeEach(async () => {
    sessionStorage.clear();
    send = jasmine.createSpy('send').and.callFake(() => of(reply()));
    warmUp = jasmine.createSpy('warmUp');

    await TestBed.configureTestingModule({
      imports: [ChatWidgetComponent, IonicModule.forRoot()],
      providers: [provideRouter([]), { provide: ChatService, useValue: { send, warmUp } }],
    }).compileComponents();
  });

  afterEach(() => sessionStorage.clear());

  it('starts closed with only the floating button', () => {
    create();

    expect(q('.chat__panel')).toBeNull();
    expect(q('.chat__fab')?.getAttribute('aria-label')).toBe('Відкрити чат-помічника');
    expect(q('.chat__fab')?.getAttribute('aria-expanded')).toBe('false');
  });

  it('opens and closes from the button, the close icon and Escape', () => {
    create();

    openPanel();
    expect(q('.chat__panel')).not.toBeNull();
    expect(q('.chat__fab')?.getAttribute('aria-expanded')).toBe('true');

    q('.chat__fab')!.click();
    fixture.detectChanges();
    expect(q('.chat__panel')).toBeNull();

    openPanel();
    q('[aria-label="Закрити чат"]')!.click();
    fixture.detectChanges();
    expect(q('.chat__panel')).toBeNull();

    openPanel();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    fixture.detectChanges();
    expect(q('.chat__panel')).toBeNull();
  });

  it('wakes the backend once, on the first open', () => {
    create();

    openPanel();
    q('.chat__fab')!.click();
    openPanel();

    expect(warmUp).toHaveBeenCalledTimes(1);
  });

  it('offers example questions and sends one when clicked', () => {
    create();
    openPanel();

    expect(all('.chat__chip').map((c) => c.textContent!.trim())).toEqual(CHAT_EXAMPLE_PROMPTS);

    all('.chat__chip')[1].click();
    fixture.detectChanges();

    expect(send).toHaveBeenCalledOnceWith(CHAT_EXAMPLE_PROMPTS[1]);
    expect(bubbles()).toEqual([CHAT_EXAMPLE_PROMPTS[1], 'Ось добірка.']);
    expect(q('.chat__chip')).toBeNull();
  });

  it('sends the typed question, shows the answer with event cards and clears the input', () => {
    send.and.returnValue(of(reply('Ось що є у Львові.', [EVENT, { ...EVENT, id: 2, uid: 'external:2', name: 'Другий концерт' }])));
    create();
    openPanel();

    type('  концерти у Львові  ');
    submit();

    expect(send).toHaveBeenCalledOnceWith('концерти у Львові');
    expect(bubbles()).toEqual(['концерти у Львові', 'Ось що є у Львові.']);
    expect(all('app-chat-event-card').length).toBe(2);
    expect(q<HTMLTextAreaElement>('textarea')!.value).toBe('');
  });

  it('does not send empty or whitespace-only input', () => {
    create();
    openPanel();

    type('   ');
    submit();

    expect(send).not.toHaveBeenCalled();
    expect(q<HTMLButtonElement>('.chat__send')!.disabled).toBeTrue();
  });

  it('does not send a question longer than the message limit', () => {
    create();
    openPanel();

    type('x'.repeat(501));
    submit();

    expect(send).not.toHaveBeenCalled();
    expect(bubbles()).toEqual([]);
  });

  it('sends on Enter but keeps a new line on Shift+Enter', () => {
    create();
    openPanel();
    type('концерти');

    q('textarea')!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, cancelable: true }));
    expect(send).not.toHaveBeenCalled();

    q('textarea')!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', cancelable: true }));
    expect(send).toHaveBeenCalledOnceWith('концерти');
  });

  it('shows a typing indicator, locks the input while waiting, then the wake-up hint after a while', fakeAsync(() => {
    const pending = new Subject<ChatReply>();
    send.and.returnValue(pending);
    create();
    openPanel();
    tick();

    type('концерти');
    submit();

    expect(q('.chat__typing')).not.toBeNull();
    expect(q<HTMLTextAreaElement>('textarea')!.disabled).toBeTrue();
    expect(q('.chat__slow')).toBeNull();

    tick(CHAT_SLOW_AFTER_MS);
    fixture.detectChanges();
    expect(q('.chat__slow')?.textContent).toContain('Сервер прокидається');

    pending.next(reply());
    pending.complete();
    fixture.detectChanges();
    flush();

    expect(q('.chat__typing')).toBeNull();
    expect(q('.chat__slow')).toBeNull();
    expect(q<HTMLTextAreaElement>('textarea')!.disabled).toBeFalse();
  }));

  it('ignores a second question while one is running', () => {
    send.and.returnValue(new Subject<ChatReply>());
    create();
    openPanel();

    type('перше');
    submit();
    type('друге');
    submit();

    expect(send).toHaveBeenCalledTimes(1);
  });

  describe('errors', () => {
    function failWith(error: ChatError): void {
      send.and.returnValue(throwError(() => error));
      create();
      openPanel();
      type('концерти');
      submit();
    }

    it('tells how long to wait when rate limited and links to the regular search', () => {
      failWith({ kind: 'rate_limited', message: 'x', retryAfterSeconds: 120 });

      const error = q('.chat__bubble--error')!;
      expect(error.textContent).toContain('Спробуйте через 2 хв.');
      expect(q('.chat__footer')?.textContent).toContain('Залишилось запитів: 0');

      const router = TestBed.inject(Router);
      const navigate = spyOn(router, 'navigate').and.resolveTo(true);
      q('.chat__action')!.click();
      expect(navigate).toHaveBeenCalledWith(['/tabs/events']);
    });

    it('rounds the wait up to at least a minute', () => {
      failWith({ kind: 'rate_limited', message: 'x', retryAfterSeconds: 5 });

      expect(q('.chat__bubble--error')!.textContent).toContain('через 1 хв.');
    });

    it('points to the regular filters when the bot is unavailable', () => {
      failWith({ kind: 'unavailable', message: 'x' });

      expect(q('.chat__bubble--error')!.textContent).toContain('тимчасово недоступний');
      expect(q('.chat__action')!.textContent).toContain('огляд подій');
    });

    it('offers a retry on network errors and asks the same question again', () => {
      failWith({ kind: 'network', message: 'Не вдалося зв’язатися із сервером.' });
      expect(q('.chat__action')!.textContent).toContain('Спробувати ще раз');

      send.and.returnValue(of(reply('Тепер вийшло.')));
      q('.chat__action')!.click();
      fixture.detectChanges();

      expect(send.calls.allArgs()).toEqual([['концерти'], ['концерти']]);
      expect(bubbles()).toContain('Тепер вийшло.');
      expect(all('.chat__bubble').filter((b) => b.textContent!.includes('концерти')).length).toBe(1); // not echoed twice
    });
  });

  it('shows how many requests are left only when few remain', () => {
    send.and.returnValue(of(reply('Ок.', [], 4)));
    create();
    openPanel();

    type('концерти');
    submit();

    expect(q('.chat__footer')?.textContent).toContain('Залишилось запитів: 4');
  });

  it('counts characters near the limit', () => {
    create();
    openPanel();

    type('x'.repeat(420));

    expect(q('.chat__footer')?.textContent).toContain('420/500');
    expect(q<HTMLTextAreaElement>('textarea')!.getAttribute('maxlength')).toBe('500');
  });

  it('renders the bot reply as text, never as HTML', () => {
    send.and.returnValue(of(reply('<img src=x onerror=alert(1)> <b>жирний</b>')));
    create();
    openPanel();

    type('концерти');
    submit();

    expect(q('.chat__messages img')).toBeNull();
    expect(q('.chat__messages b')).toBeNull();
    expect(bubbles()[1]).toBe('<img src=x onerror=alert(1)> <b>жирний</b>');
  });

  describe('remembering the conversation', () => {
    it('keeps it in sessionStorage and restores it for a new widget', () => {
      create();
      openPanel();
      type('концерти');
      submit();
      fixture.detectChanges();

      const stored = JSON.parse(sessionStorage.getItem(CHAT_STORAGE_KEY) ?? '[]');
      expect(stored.map((m: { text: string }) => m.text)).toEqual(['концерти', 'Ось добірка.']);

      fixture.destroy();
      create();
      openPanel();

      expect(bubbles()).toEqual(['концерти', 'Ось добірка.']);
    });

    it('ignores broken stored data', () => {
      sessionStorage.setItem(CHAT_STORAGE_KEY, '{not json');
      create();
      openPanel();

      expect(all('.chat__bubble').length).toBe(0);

      fixture.destroy();
      sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify([{ id: 1, role: 'hacker', text: 'x' }, { id: 2, role: 'bot', text: 'ok' }, 'junk']));
      create();
      openPanel();

      expect(bubbles()).toEqual(['ok']);
    });

    it('starts over with "Нова розмова"', () => {
      create();
      openPanel();
      type('концерти');
      submit();
      expect(bubbles().length).toBe(2);

      q('[aria-label="Нова розмова"]')!.click();
      fixture.detectChanges();

      expect(all('.chat__bubble').length).toBe(0);
      expect(all('.chat__chip').length).toBe(CHAT_EXAMPLE_PROMPTS.length);
    });
  });
});
