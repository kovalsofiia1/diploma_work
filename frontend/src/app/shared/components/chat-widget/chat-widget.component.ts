import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, OnDestroy, ViewChild, computed, effect, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { IonicModule } from '@ionic/angular';

import { ChatError, ChatMessage, ChatReply } from 'src/app/features/chat/interfaces/chat.interface';
import { CHAT_MESSAGE_MAX_LENGTH, ChatService } from 'src/app/features/chat/services/chat.service';
import { ChatEventCardComponent } from '../chat-event-card/chat-event-card.component';

export const CHAT_STORAGE_KEY = 'chat.widget.v1';
export const CHAT_SLOW_AFTER_MS = 6000;
const MAX_STORED_MESSAGES = 30;
const SMALL_SCREEN_PX = 576;

export const CHAT_EXAMPLE_PROMPTS = [
  'Що цікавого у Львові на вихідних?',
  'Стендап у Києві до 500 грн',
  'Концерти в Одесі цього тижня',
];

/**
 * Floating chat on every page. The backend is stateless (one question, one answer), so the conversation
 * only lives here and in sessionStorage. Replies are rendered as plain text, never as HTML.
 */
@Component({
  selector: 'app-chat-widget',
  templateUrl: './chat-widget.component.html',
  styleUrls: ['./chat-widget.component.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule, ChatEventCardComponent],
})
export class ChatWidgetComponent implements OnDestroy {
  private chat = inject(ChatService);
  private router = inject(Router);

  @ViewChild('list') private list?: ElementRef<HTMLElement>;
  @ViewChild('input') private input?: ElementRef<HTMLTextAreaElement>;

  readonly maxLength = CHAT_MESSAGE_MAX_LENGTH;
  readonly examples = CHAT_EXAMPLE_PROMPTS;

  readonly open = signal(false);
  readonly messages = signal<ChatMessage[]>(this.restore());
  readonly draft = signal('');
  readonly loading = signal(false);
  /** True when the answer takes long, typically a sleeping backend on free hosting. */
  readonly slow = signal(false);
  readonly remaining = signal<number | null>(null);

  readonly canSend = computed(() => !this.loading() && this.draft().trim().length > 0 && this.draft().length <= this.maxLength);
  readonly showCounter = computed(() => this.draft().length >= this.maxLength - 100);
  readonly showRemaining = computed(() => this.remaining() !== null && (this.remaining() as number) <= 5);

  private nextId = this.messages().reduce((max, m) => Math.max(max, m.id), 0) + 1;
  private lastQuestion = '';
  private warmedUp = false;
  private slowTimer?: ReturnType<typeof setTimeout>;

  constructor() {
    effect(() => this.persist(this.messages()));
    effect(() => {
      this.messages();
      this.loading();
      setTimeout(() => this.scrollToEnd());
    });
  }

  ngOnDestroy(): void {
    this.clearSlowTimer();
  }

  toggle(): void {
    if (this.open()) {
      this.close();
      return;
    }
    this.open.set(true);
    if (!this.warmedUp) {
      this.warmedUp = true;
      this.chat.warmUp();
    }
    setTimeout(() => this.input?.nativeElement.focus());
  }

  close(): void {
    this.open.set(false);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open()) this.close();
  }

  reset(): void {
    this.messages.set([]);
    this.remaining.set(null);
    this.lastQuestion = '';
  }

  onInput(event: Event): void {
    this.draft.set((event.target as HTMLTextAreaElement).value);
  }

  onEnter(event: Event): void {
    const key = event as KeyboardEvent;
    if (key.shiftKey) return; // Shift+Enter keeps a new line
    key.preventDefault();
    this.send();
  }

  onSubmit(event: Event): void {
    event.preventDefault();
    this.send();
  }

  /** Send the draft, or `text` (an example chip). */
  send(text?: string): void {
    const value = (text ?? this.draft()).trim();
    if (!value || this.loading() || value.length > this.maxLength) return;

    this.push({ role: 'user', text: value });
    this.draft.set('');
    this.ask(value);
  }

  retry(): void {
    if (this.lastQuestion && !this.loading()) this.ask(this.lastQuestion);
  }

  goToEvents(): void {
    this.router.navigate(['/tabs/events']);
    this.closeOnSmallScreen();
  }

  onCardOpened(): void {
    this.closeOnSmallScreen();
  }

  private ask(question: string): void {
    this.lastQuestion = question;
    this.loading.set(true);
    this.slow.set(false);
    this.clearSlowTimer();
    this.slowTimer = setTimeout(() => this.slow.set(true), CHAT_SLOW_AFTER_MS);

    this.chat.send(question).subscribe({
      next: (reply) => this.onReply(reply),
      error: (error: ChatError) => this.onError(error),
    });
  }

  private onReply(reply: ChatReply): void {
    this.finish();
    if (reply.remaining !== null) this.remaining.set(reply.remaining);

    const { response } = reply;
    this.push({
      role: 'bot',
      text: response.reply,
      events: response.events ?? [],
      hints: response.suggestions ?? [],
    });
  }

  private onError(error: ChatError): void {
    this.finish();

    switch (error.kind) {
      case 'rate_limited': {
        const minutes = error.retryAfterSeconds ? Math.max(1, Math.ceil(error.retryAfterSeconds / 60)) : null;
        const when = minutes ? `Спробуйте через ${minutes} хв.` : 'Спробуйте пізніше.';
        this.remaining.set(0);
        this.push({ role: 'bot', tone: 'error', text: `Ліміт запитів до чат-бота на годину вичерпано. ${when}`, action: 'events' });
        break;
      }
      case 'unavailable':
        this.push({
          role: 'bot',
          tone: 'error',
          text: 'Чат-бот тимчасово недоступний. Скористайтеся фільтрами на сторінці подій.',
          action: 'events',
        });
        break;
      case 'invalid':
        this.push({ role: 'bot', tone: 'error', text: error.message });
        break;
      default:
        this.push({ role: 'bot', tone: 'error', text: `${error.message} Перевірте з’єднання та спробуйте ще раз.`, action: 'retry' });
    }
  }

  private finish(): void {
    this.loading.set(false);
    this.slow.set(false);
    this.clearSlowTimer();
    setTimeout(() => this.input?.nativeElement.focus());
  }

  private push(message: Omit<ChatMessage, 'id'>): void {
    this.messages.update((list) => [...list, { ...message, id: this.nextId++ }]);
  }

  private clearSlowTimer(): void {
    if (this.slowTimer !== undefined) {
      clearTimeout(this.slowTimer);
      this.slowTimer = undefined;
    }
  }

  private closeOnSmallScreen(): void {
    if (window.innerWidth < SMALL_SCREEN_PX) this.close();
  }

  private scrollToEnd(): void {
    const el = this.list?.nativeElement;
    if (el) el.scrollTop = el.scrollHeight;
  }

  private persist(messages: ChatMessage[]): void {
    try {
      sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages.slice(-MAX_STORED_MESSAGES)));
    } catch {
      // storage unavailable (private mode, quota): the chat still works, it just is not remembered
    }
  }

  private restore(): ChatMessage[] {
    try {
      const parsed: unknown = JSON.parse(sessionStorage.getItem(CHAT_STORAGE_KEY) ?? '[]');
      if (!Array.isArray(parsed)) return [];
      return parsed.filter(
        (m): m is ChatMessage =>
          !!m && typeof m.id === 'number' && (m.role === 'user' || m.role === 'bot') && typeof m.text === 'string',
      );
    } catch {
      return [];
    }
  }
}
