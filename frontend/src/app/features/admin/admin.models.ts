export interface Page<T> {
  items: T[];
  total: number;
}

export interface AdminSummary {
  pending_applications: number;
  blocked_users: number;
  hidden_events: number;
}

export type ApplicationStatus = 'pending' | 'approved' | 'rejected';

export interface AdminApplication {
  id: number;
  user_id: number;
  user_email: string;
  user_full_name?: string | null;
  organization_name: string;
  contact_phone: string;
  motivation: string;
  experience?: string | null;
  status: ApplicationStatus;
  submitted_at: string;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
}

export type UserRole = 'admin' | 'verified user' | 'user';

export interface AdminUser {
  id: number;
  email: string;
  full_name?: string | null;
  status: UserRole;
  provider: string;
  is_active: boolean;
  blocked_reason?: string | null;
  blocked_at?: string | null;
  created_at: string;
  /** Events hidden on block or restored on unblock by the last action. */
  affected_events?: number;
}

export interface AdminEvent {
  id: number;
  uid?: string | null;
  name: string;
  city?: string | null;
  start_date?: string | null;
  source_type: 'INTERNAL' | 'EXTERNAL';
  source_name?: string | null;
  source_url?: string | null;
  status: string;
  is_hidden: boolean;
  hidden_reason?: string | null;
  hidden_at?: string | null;
  created_by_user_id?: number | null;
  created_by_email?: string | null;
}

export interface AuditLogEntry {
  id: number;
  admin_user_id?: number | null;
  admin_email?: string | null;
  action: string;
  target_type: string;
  target_id: number;
  details?: Record<string, unknown> | null;
  created_at: string;
}

export const AUDIT_ACTION_LABELS: Record<string, string> = {
  'organizer_application.approved': 'Схвалено заявку організатора',
  'organizer_application.rejected': 'Відхилено заявку організатора',
  'user.blocked': 'Заблоковано користувача',
  'user.unblocked': 'Розблоковано користувача',
  'user.admin_granted': 'Надано роль адміна',
  'user.admin_revoked': 'Знято роль адміна',
  'event.hidden': 'Приховано подію',
  'event.unhidden': 'Повернуто подію',
};

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Адмін',
  'verified user': 'Організатор',
  user: 'Користувач',
};
