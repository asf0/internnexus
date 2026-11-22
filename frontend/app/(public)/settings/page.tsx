import { auth } from '@/auth';
import { redirect } from 'next/navigation';
import { fetchMCPApiKeys, getUserProfile } from '@/app/actions/user';
import { SettingsForm } from '@/components/settings';
import { getMcpEndpoint } from '@/lib/mcp';

export default async function SettingsPage() {
  const session = await auth();
  if (!session?.user) redirect('/');

  const [profile, mcpKeys] = await Promise.all([getUserProfile(), fetchMCPApiKeys()]);
  if (!profile) {
    return (
      <div className="bg-canvas flex min-h-screen items-center justify-center">
        <p className="text-foreground-secondary">Failed to load profile. Please try again.</p>
      </div>
    );
  }

  return (
    <SettingsForm
      profile={profile}
      mcpKeys={mcpKeys}
      mcpEndpoint={getMcpEndpoint(process.env.MCP_PUBLIC_URL)}
    />
  );
}
