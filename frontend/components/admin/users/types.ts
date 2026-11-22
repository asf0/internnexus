export interface CurrentAdminInfo {
  id: string;
  role: 'admin' | 'super_admin';
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getAdminRoleBadgeVariant(role: string): 'purple' | 'danger' {
  return role === 'super_admin' ? 'danger' : 'purple';
}
