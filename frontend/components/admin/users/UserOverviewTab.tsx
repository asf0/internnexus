import { Mail, User, Shield, Key, Calendar, CheckCircle } from 'lucide-react';
import { Badge } from '@/components/ui';
import { AdminCard, AdminTag } from '@/components/admin/ui';
import { type AdminUser } from '@/app/actions/admin';
import { formatDate, getAdminRoleBadgeVariant } from './types';

interface UserOverviewTabProps {
  readonly user: AdminUser;
}

export function UserOverviewTab({ user }: UserOverviewTabProps) {
  return (
    <AdminCard className="shadow-sm">
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
          <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
            <Mail className="h-4 w-4" />
            Email
          </dt>
          <dd className="dark:text-md-on-surface text-slate-900">{user.email}</dd>
        </div>
        <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
          <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
            <User className="h-4 w-4" />
            Name
          </dt>
          <dd className="dark:text-md-on-surface text-slate-900">
            {user.name || <span className="text-slate-400">Not set</span>}
          </dd>
        </div>
        <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
          <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
            <Shield className="h-4 w-4" />
            Admin Role
          </dt>
          <dd className="dark:text-md-on-surface text-slate-900">
            {user.admin_role ? (
              <Badge variant={getAdminRoleBadgeVariant(user.admin_role)}>
                {user.admin_role === 'super_admin' ? 'Super Admin' : 'Admin'}
              </Badge>
            ) : (
              <span className="text-slate-400">Not an admin</span>
            )}
          </dd>
        </div>
        <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
          <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
            <Key className="h-4 w-4" />
            Provider
          </dt>
          <dd className="dark:text-md-on-surface text-slate-900 capitalize">
            {user.provider || 'credentials'}
          </dd>
        </div>
        <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
          <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
            <CheckCircle className="h-4 w-4" />
            Active Status
          </dt>
          <dd className="dark:text-md-on-surface text-slate-900">
            {user.is_active ? (
              <Badge variant="success">Active</Badge>
            ) : (
              <Badge variant="danger">Deactivated</Badge>
            )}
          </dd>
        </div>
        <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
          <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
            <Key className="h-4 w-4" />
            Has Password
          </dt>
          <dd className="dark:text-md-on-surface text-slate-900">
            {user.has_password ? (
              <AdminTag color="green">Yes</AdminTag>
            ) : (
              <AdminTag color="default">No</AdminTag>
            )}
          </dd>
        </div>
        <div className="dark:bg-md-surface-container-high rounded-lg bg-slate-50 p-3">
          <dt className="dark:text-md-on-surface-variant mb-1 flex items-center gap-2 text-sm text-slate-500">
            <Calendar className="h-4 w-4" />
            Created At
          </dt>
          <dd className="dark:text-md-on-surface text-slate-900">
            {user.created_at && formatDate(user.created_at)}
          </dd>
        </div>
      </dl>
    </AdminCard>
  );
}
