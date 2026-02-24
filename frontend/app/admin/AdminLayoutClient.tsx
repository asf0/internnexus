"use client";

import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import { Layout, Menu, Button, Avatar, Dropdown, Result, ConfigProvider, theme } from "antd";
import {
  DashboardOutlined,
  UnorderedListOutlined,
  UserOutlined,
  BarChartOutlined,
  SyncOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from "@ant-design/icons";
import type { MenuProps } from "antd";

const { Sider, Header, Content } = Layout;

interface AdminLayoutClientProps {
  user: {
    id?: string;
    name?: string | null;
    email?: string | null;
    image?: string | null;
  } | null;
  isAdmin: boolean;
  children: React.ReactNode;
}

const menuItems: MenuProps["items"] = [
  {
    key: "/admin",
    icon: <DashboardOutlined />,
    label: "Dashboard",
  },
  {
    key: "/admin/jobs",
    icon: <UnorderedListOutlined />,
    label: "Jobs",
  },
  {
    key: "/admin/users",
    icon: <UserOutlined />,
    label: "Users",
  },
  {
    key: "/admin/clicks",
    icon: <BarChartOutlined />,
    label: "Clicks",
  },
  {
    key: "/admin/pipeline",
    icon: <SyncOutlined />,
    label: "Pipeline",
  },
];

export default function AdminLayoutClient({
  user,
  isAdmin,
  children,
}: AdminLayoutClientProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const handleMenuClick: MenuProps["onClick"] = (e) => {
    router.push(e.key);
  };

  const handleLogout = async () => {
    await signOut({ callbackUrl: "/" });
  };

  const userMenuItems: MenuProps["items"] = [
    {
      key: "profile",
      label: user?.email || "Admin",
      disabled: true,
    },
    {
      type: "divider",
    },
    {
      key: "logout",
      icon: <LogoutOutlined />,
      label: "Logout",
      onClick: handleLogout,
    },
  ];

  // Not admin
  if (!isAdmin) {
    return (
      <ConfigProvider
        theme={{
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
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            height: "100vh",
            background: "#121212",
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
    <ConfigProvider
      theme={{
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
      }}
    >
      <Layout style={{ minHeight: "100vh", background: "#121212" }}>
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          trigger={null}
          style={{
            overflow: "auto",
            height: "100vh",
            position: "fixed",
            left: 0,
            top: 0,
            bottom: 0,
            background: "#121212",
          }}
        >
          <div
            style={{
              height: 64,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontSize: collapsed ? 16 : 18,
              fontWeight: "bold",
              borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
            }}
          >
            {collapsed ? "IN" : "InternNexus"}
          </div>
          <Menu
            mode="inline"
            selectedKeys={[pathname]}
            items={menuItems}
            onClick={handleMenuClick}
            style={{
              background: "transparent",
              color: "#E6E1E5",
            }}
          />
        </Sider>
        <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: "margin-left 0.2s" }}>
          <Header
            style={{
              position: "sticky",
              top: 0,
              zIndex: 1,
              width: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0 24px",
              background: "#121212",
              borderBottom: "1px solid #49454F",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <Button
                type="text"
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed(!collapsed)}
                style={{ fontSize: 16 }}
              />
              <span style={{ fontSize: 18, fontWeight: 600 }}>
                InternNexus Admin
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                <div style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
                  <Avatar
                    src={user?.image}
                    icon={!user?.image && <UserOutlined />}
                    style={{ backgroundColor: "#1890ff" }}
                  />
                  <span style={{ color: "#E6E1E5" }}>
                    {user?.name || user?.email || "Admin"}
                  </span>
                </div>
              </Dropdown>
            </div>
          </Header>
          <Content
            style={{
              margin: 24,
              padding: 24,
              background: "#121212",
              borderRadius: 8,
              minHeight: "calc(100vh - 112px)",
            }}
          >
            {children}
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}
