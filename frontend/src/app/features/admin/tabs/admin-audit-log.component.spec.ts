import { TestBed } from '@angular/core/testing';
import { AdminService } from '../admin.service';
import { AdminAuditLogComponent } from './admin-audit-log.component';

describe('AdminAuditLogComponent', () => {
  let component: AdminAuditLogComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [{ provide: AdminService, useValue: {} }],
    });
    component = TestBed.runInInjectionContext(() => new AdminAuditLogComponent());
  });

  it('formats audit targets and moderation reasons', () => {
    const entry = {
      id: 1,
      action: 'user.blocked',
      target_type: 'user',
      target_id: 9,
      details: { user_email: 'blocked@example.com', reason: 'Spam' },
      created_at: '2026-01-01T10:00:00',
    };

    expect(component.actionLabel(entry)).toBe('Заблоковано користувача');
    expect(component.targetLabel(entry)).toBe('Користувач #9 · blocked@example.com');
    expect(component.reason(entry)).toBe('Причина: Spam');
  });

  it('falls back to target type and returns no reason when audit details are absent', () => {
    const entry = {
      id: 2,
      action: 'custom.action',
      target_type: 'custom_target',
      target_id: 14,
      created_at: '2026-01-01T10:00:00',
    };

    expect(component.actionLabel(entry)).toBe('custom.action');
    expect(component.targetLabel(entry)).toBe('custom_target #14');
    expect(component.reason(entry)).toBeNull();
  });
});
