'use client';

import { useRouter, usePathname } from 'next/navigation';
import { signOut } from 'next-auth/react';
import { Avatar, Button, ConfigProvider, Dropdown, Layout, Menu, Result, theme } from 'antd';
import {
  BarChartOutlined,
  DashboardOutlined,
  LogoutOutlined,
  SyncOutlined,
  UnorderedListOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

const { Header, Content } = Layout;

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

const adminTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorBgBase: '#121212',
    colorBgContainer: '#211F26',
    colorBgElevated: '#2B2930',
    colorText: '#E6E1E5',
    colorTextSecondary: '#CAC4D0',
    colorPrimary: '#005AC1',
    colorBorder: '#49454F',
    colorBorderSecondary: '#938F99',
  },
};

const menuItems: MenuProps['items'] = [
  {
    key: '/admin',
    icon: <DashboardOutlined />,
    label: 'Dashboard',
  },
  {
    key: '/admin/jobs',
    icon: <UnorderedListOutlined />,
    label: 'Jobs',
  },
  {
    key: '/admin/users',
    icon: <UserOutlined />,
    label: 'Users',
  },
  {
    key: '/admin/clicks',
    icon: <BarChartOutlined />,
    label: 'Clicks',
  },
  {
    key: '/admin/pipeline',
    icon: <SyncOutlined />,
    label: 'Pipeline',
  },
];

function getSelectedKey(pathname: string): string {
  if (pathname.startsWith('/admin/jobs')) return '/admin/jobs';
  if (pathname.startsWith('/admin/users')) return '/admin/users';
  if (pathname.startsWith('/admin/clicks')) return '/admin/clicks';
  if (pathname.startsWith('/admin/pipeline')) return '/admin/pipeline';
  return '/admin';
}

export default function AdminLayoutClient({ user, isAdmin, children }: AdminLayoutClientProps) {
  const router = useRouter();
  const pathname = usePathname();
  const selectedKey = getSelectedKey(pathname);

  const handleMenuClick: MenuProps['onClick'] = (event) => {
    router.push(event.key);
  };

  const handleLogout = async () => {
    await signOut({ callbackUrl: '/' });
  };

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      label: user?.email || 'Admin',
      disabled: true,
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      onClick: handleLogout,
    },
  ];

  if (!isAdmin) {
    return (
      <ConfigProvider theme={adminTheme}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '100vh',
            background: '#121212',
          }}
        >
          <Result
            status="403"
            title="Access Denied"
            subTitle="You do not have admin privileges to access this page."
            extra={
              <Button type="primary" onClick={handleLogout}>
                Logout
              </Button>
            }
          />
        </div>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider theme={adminTheme}>
      <Layout style={{ minHeight: '100vh', background: '#121212' }}>
        <div className="admin-shell">
          <aside className="admin-sidebar" aria-label="Admin navigation">
            <div className="admin-brand">InternNexus</div>
            <Menu
              mode="inline"
              selectedKeys={[selectedKey]}
              items={menuItems}
              onClick={handleMenuClick}
              style={{ background: 'transparent', borderInlineEnd: 0 }}
            />
          </aside>

          <Layout className="admin-main" style={{ background: '#121212' }}>
            <Header
              className="admin-header"
              style={{
                background: '#121212',
                borderBottom: '1px solid #49454F',
              }}
            >
              <div className="admin-header-title">InternNexus Admin</div>
              <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                <button type="button" className="admin-user-button">
                  <Avatar
                    src={user?.image}
                    icon={!user?.image && <UserOutlined />}
                    style={{ backgroundColor: '#1890ff' }}
                  />
                  <span className="admin-user-name">{user?.name || user?.email || 'Admin'}</span>
                </button>
              </Dropdown>
            </Header>

            <nav className="admin-mobile-nav" aria-label="Admin navigation">
              <Menu
                mode="horizontal"
                selectedKeys={[selectedKey]}
                items={menuItems}
                onClick={handleMenuClick}
                style={{ background: 'transparent', borderBottom: 0, minWidth: 0 }}
              />
            </nav>

            <Content className="admin-content">{children}</Content>
          </Layout>
        </div>
      </Layout>

      <style jsx global>{`
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

          .admin-mobile-nav .ant-menu {
            min-width: max-content;
          }

          .admin-content {
            min-height: calc(100vh - 116px);
            margin: 12px;
            padding: 16px;
          }
        }
      `}</style>
    </ConfigProvider>
  );
}
