'use client';

import { usePathname } from 'next/navigation';
import { signOut } from 'next-auth/react';
import { LayoutDashboard, List, User, BarChart3, RefreshCw, LogOut } from 'lucide-react';
import { Button } from '@/components/ui';
import {
  AdminAvatar,
  AdminDropdown,
  AdminMenu,
  AdminResult,
  AdminToastProvider,
  type AdminMenuItem,
} from '@/components/admin/ui';

interface AdminLayoutClientProps {
  readonly user: {
    readonly id?: string;
    readonly name?: string | null;
    readonly email?: string | null;
    readonly image?: string | null;
  } | null;
  readonly isAdmin: boolean;
  readonly children: React.ReactNode;
}

const layoutStyles = `
  .admin-shell {
    display: grid;
    grid-template-columns: 232px minmax(0, 1fr);
    min-height: 100vh;
    width: 100%;
    background: #121212;
  }

  .admin-sidebar {
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
    border-right: 1px solid #49454f;
    background: #121212;
  }

  .admin-brand {
    height: 64px;
    display: flex;
    align-items: center;
    padding: 0 24px;
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    white-space: nowrap;
  }

  .admin-main {
    min-width: 0;
  }

  .admin-header {
    position: sticky;
    top: 0;
    z-index: 10;
    min-width: 0;
    width: 100%;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 0 24px;
  }

  .admin-header-title {
    min-width: 0;
    overflow: hidden;
    color: #e6e1e5;
    font-size: 18px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .admin-user-button {
    display: inline-flex;
    align-items: center;
    max-width: 320px;
    gap: 8px;
    padding: 0;
    border: 0;
    background: transparent;
    color: #e6e1e5;
    cursor: pointer;
  }

  .admin-user-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .admin-mobile-nav {
    display: none;
    overflow-x: auto;
    border-bottom: 1px solid #49454f;
    background: #121212;
  }

  .admin-mobile-nav nav {
    min-width: max-content;
  }

  .admin-content {
    min-width: 0;
    min-height: calc(100vh - 112px);
    margin: 24px;
    padding: 24px;
    border-radius: 8px;
    background: #121212;
  }

  @media (max-width: 900px) {
    .admin-shell {
      display: block;
    }

    .admin-sidebar {
      display: none;
    }

    .admin-header {
      padding: 0 16px;
    }

    .admin-header-title {
      font-size: 16px;
    }

    .admin-user-name {
      display: none;
    }

    .admin-mobile-nav {
      display: block;
    }

    .admin-content {
      min-height: calc(100vh - 116px);
      margin: 12px;
      padding: 16px;
    }
  }
`;

const menuItems: AdminMenuItem[] = [
  { key: '/admin', icon: LayoutDashboard, label: 'Dashboard' },
  { key: '/admin/jobs', icon: List, label: 'Jobs' },
  { key: '/admin/users', icon: User, label: 'Users' },
  { key: '/admin/clicks', icon: BarChart3, label: 'Clicks' },
  { key: '/admin/pipeline', icon: RefreshCw, label: 'Pipeline' },
];

function getSelectedKey(pathname: string): string {
  if (pathname.startsWith('/admin/jobs')) return '/admin/jobs';
  if (pathname.startsWith('/admin/users')) return '/admin/users';
  if (pathname.startsWith('/admin/clicks')) return '/admin/clicks';
  if (pathname.startsWith('/admin/pipeline')) return '/admin/pipeline';
  return '/admin';
}

export default function AdminLayoutClient({ user, isAdmin, children }: AdminLayoutClientProps) {
  const pathname = usePathname();
  const selectedKey = getSelectedKey(pathname);

  const handleLogout = async () => {
    await signOut({ callbackUrl: '/' });
  };

  const userMenuItems = [
    { key: 'profile', label: user?.email || 'Admin', disabled: true },
    { key: 'divider', label: '', disabled: true },
    {
      key: 'logout',
      icon: LogOut,
      label: 'Logout',
      onClick: handleLogout,
    },
  ];

  if (!isAdmin) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
          background: '#121212',
        }}
      >
        <AdminResult
          status="403"
          title="Access Denied"
          subTitle="You do not have admin privileges to access this page."
          extra={<Button onClick={handleLogout}>Logout</Button>}
        />
      </div>
    );
  }

  return (
    <AdminToastProvider>
      <div className="admin-shell">
        <aside className="admin-sidebar">
          <div className="admin-brand">InternNexus</div>
          <AdminMenu items={menuItems} selectedKey={selectedKey} />
        </aside>

        <div className="admin-main" style={{ background: '#121212' }}>
          <header
            className="admin-header"
            style={{
              background: '#121212',
              borderBottom: '1px solid #49454F',
            }}
          >
            <div className="admin-header-title">InternNexus Admin</div>
            <AdminDropdown
              trigger={
                <button type="button" className="admin-user-button">
                  <AdminAvatar src={user?.image} alt={user?.name || user?.email || 'Admin'} />
                  <span className="admin-user-name">{user?.name || user?.email || 'Admin'}</span>
                </button>
              }
              items={userMenuItems}
            />
          </header>

          <nav className="admin-mobile-nav">
            <AdminMenu items={menuItems} selectedKey={selectedKey} />
          </nav>

          <main className="admin-content">{children}</main>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{ __html: layoutStyles }} />
    </AdminToastProvider>
  );
}
