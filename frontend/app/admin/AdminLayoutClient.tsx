'use client';

import { usePathname, useRouter } from 'next/navigation';
import { logoutUser } from '@/app/actions/auth';
import { LayoutDashboard, List, User, BarChart3, RefreshCw, LogOut, Bot } from 'lucide-react';
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

const menuItems: AdminMenuItem[] = [
  { key: '/admin', icon: LayoutDashboard, label: 'Dashboard' },
  { key: '/admin/jobs', icon: List, label: 'Jobs' },
  { key: '/admin/users', icon: User, label: 'Users' },
  { key: '/admin/clicks', icon: BarChart3, label: 'Clicks' },
  { key: '/admin/agent-usage', icon: Bot, label: 'MCP usage' },
  { key: '/admin/pipeline', icon: RefreshCw, label: 'Pipeline' },
];

function getSelectedKey(pathname: string): string {
  if (pathname.startsWith('/admin/jobs')) return '/admin/jobs';
  if (pathname.startsWith('/admin/users')) return '/admin/users';
  if (pathname.startsWith('/admin/clicks')) return '/admin/clicks';
  if (pathname.startsWith('/admin/pipeline')) return '/admin/pipeline';
  if (pathname.startsWith('/admin/agent-usage')) return '/admin/agent-usage';
  return '/admin';
}

export default function AdminLayoutClient({ user, isAdmin, children }: AdminLayoutClientProps) {
  const pathname = usePathname();
  const router = useRouter();
  const selectedKey = getSelectedKey(pathname);
  const userLabel = user?.name || user?.email || 'Admin';

  const handleLogout = async () => {
    const result = await logoutUser();
    if (result.success) {
      router.push('/');
      router.refresh();
    }
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
      <div className="bg-canvas flex min-h-screen items-center justify-center p-4">
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
      <div className="bg-canvas grid min-h-screen w-full grid-cols-[232px_minmax(0,1fr)] max-[900px]:block">
        <aside className="border-border bg-surface dark:bg-nav sticky top-0 h-screen overflow-y-auto border-r max-[900px]:hidden">
          <div className="border-border text-foreground flex h-16 items-center border-b px-6 text-lg font-bold whitespace-nowrap">
            InternNexus
          </div>
          <AdminMenu items={menuItems} selectedKey={selectedKey} />
        </aside>

        <div className="bg-canvas min-w-0">
          <header className="border-border bg-surface/95 dark:bg-nav/95 sticky top-0 z-10 flex h-16 w-full min-w-0 items-center justify-between gap-4 border-b px-6 backdrop-blur max-[900px]:px-4">
            <div className="text-foreground min-w-0 truncate text-lg font-semibold max-[900px]:text-base">
              InternNexus Admin
            </div>
            <AdminDropdown
              trigger={
                <button
                  type="button"
                  className="text-foreground inline-flex max-w-80 cursor-pointer items-center gap-2"
                  aria-label={`Open administrator menu for ${userLabel}`}
                >
                  <AdminAvatar src={user?.image} alt={userLabel} />
                  <span className="min-w-0 truncate max-[900px]:hidden">{userLabel}</span>
                </button>
              }
              items={userMenuItems}
            />
          </header>

          <div className="border-border bg-surface dark:bg-nav hidden border-b max-[900px]:block max-[480px]:[&_a]:flex-col max-[480px]:[&_a]:gap-1 max-[480px]:[&_a]:px-1 max-[480px]:[&_a]:text-xs max-[900px]:[&_ul]:grid max-[900px]:[&_ul]:grid-cols-3 max-[900px]:[&_ul]:gap-1 max-[900px]:[&_ul]:p-2">
            <AdminMenu items={menuItems} selectedKey={selectedKey} />
          </div>

          <main className="border-border bg-surface m-6 min-h-[calc(100vh-7rem)] min-w-0 rounded-xl border p-6 shadow-sm max-[900px]:m-3 max-[900px]:min-h-[calc(100vh-10rem)] max-[900px]:p-4">
            {children}
          </main>
        </div>
      </div>
    </AdminToastProvider>
  );
}
