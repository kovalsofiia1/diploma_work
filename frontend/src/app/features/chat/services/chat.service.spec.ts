import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ChatError, ChatResponse } from '../interfaces/chat.interface';
import { ChatService } from './chat.service';

const ANSWER: ChatResponse = {
  status: 'found',
  reply: 'Ось добірка.',
  events: [],
  suggestions: [],
  degraded: false,
};

describe('ChatService', () => {
  let service: ChatService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ChatService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('posts the question and reads the rate-limit headers', (done) => {
    service.send('концерти у Львові').subscribe((reply) => {
      expect(reply.response.status).toBe('found');
      expect(reply.limit).toBe(20);
      expect(reply.remaining).toBe(19);
      done();
    });

    const req = http.expectOne('/api/chat/messages');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ message: 'концерти у Львові' });
    req.flush(ANSWER, { headers: { 'X-RateLimit-Limit': '20', 'X-RateLimit-Remaining': '19' } });
  });

  it('gives null limits when the headers are missing', (done) => {
    service.send('hi').subscribe((reply) => {
      expect(reply.limit).toBeNull();
      expect(reply.remaining).toBeNull();
      done();
    });

    http.expectOne('/api/chat/messages').flush(ANSWER);
  });

  function failWith(status: number, body: object | string, headers: Record<string, string> = {}): Promise<ChatError> {
    return new Promise((resolve) => {
      service.send('hi').subscribe({ error: (e: ChatError) => resolve(e) });
      http.expectOne('/api/chat/messages').flush(body, { status, statusText: 'error', headers });
    });
  }

  it('maps 429 to rate_limited with the wait time from the body', async () => {
    const error = await failWith(429, { detail: { code: 'rate_limited', message: 'Забагато', retry_after_seconds: 120 } });

    expect(error.kind).toBe('rate_limited');
    expect(error.retryAfterSeconds).toBe(120);
  });

  it('falls back to the Retry-After header for 429', async () => {
    const error = await failWith(429, {}, { 'Retry-After': '300' });

    expect(error.kind).toBe('rate_limited');
    expect(error.retryAfterSeconds).toBe(300);
  });

  it('maps 503 to unavailable', async () => {
    const error = await failWith(503, { detail: { code: 'llm_unavailable', message: 'Недоступний' } });

    expect(error.kind).toBe('unavailable');
    expect(error.message).toBe('Недоступний');
  });

  it('maps 422 to invalid', async () => {
    expect((await failWith(422, { detail: [] })).kind).toBe('invalid');
  });

  it('maps everything else (including no connection) to network', async () => {
    expect((await failWith(500, 'oops')).kind).toBe('network');

    const network = new Promise<ChatError>((resolve) => {
      service.send('hi').subscribe({ error: (e: ChatError) => resolve(e) });
      http.expectOne('/api/chat/messages').error(new ProgressEvent('error'));
    });
    expect((await network).kind).toBe('network');
  });

  it('warm-up pings /health and ignores failures', () => {
    service.warmUp();

    const req = http.expectOne('/api/health');
    expect(req.request.method).toBe('GET');
    req.flush('boom', { status: 502, statusText: 'Bad Gateway' });
  });
});
