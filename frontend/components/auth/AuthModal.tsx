'use client';

import { getProviders, signIn } from 'next-auth/react';
import { useState, useEffect, useReducer } from 'react';
import { useRouter } from 'next/navigation';
import { Modal } from '@/components/modals';
import { Alert } from '@/components/ui';
import { loginSchema, registrationSchema } from '@/lib/validation';
import { registerUser } from '@/app/actions/auth';
import { ENABLE_CREDENTIAL_AUTH } from '@/lib/config';
import { OAuthButtons, type OAuthProviderName } from './OAuthButtons';
import { LoginForm } from './LoginForm';
import { RegisterForm } from './RegisterForm';

interface AuthModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly defaultMode?: 'login' | 'register';
  readonly onAuthSuccess?: (applyWindow?: Window | null) => void;
  readonly intent?: 'default' | 'apply';
  readonly callbackUrl?: string;
}

type AuthMode = 'login' | 'register';

function getAuthCopy(mode: AuthMode, isApplyIntent: boolean) {
  const subtitle = isApplyIntent
    ? 'We will open the job application in a new tab right after sign in.'
    : 'Sign in to continue your job search';
  const continuation = isApplyIntent ? ' and continue' : '';

  if (!ENABLE_CREDENTIAL_AUTH) {
    return { title: isApplyIntent ? 'Sign in to apply' : 'Welcome to InternNexus', subtitle };
  }
  if (mode === 'login') {
    return {
      title: isApplyIntent ? 'Sign in to apply' : 'Welcome to InternNexus',
      subtitle,
      submitLabel: `Sign in${continuation}`,
    };
  }
  return {
    title: isApplyIntent ? 'Create an account to apply' : 'Create your account',
    subtitle,
    submitLabel: `Create account${continuation}`,
  };
}

async function loadOAuthProviders(): Promise<OAuthProviderName[]> {
  const providers = await getProviders();
  return Object.keys(providers ?? {}).filter(
    (provider): provider is OAuthProviderName => provider === 'github' || provider === 'google'
  );
}

export default function AuthModal({
  isOpen,
  onClose,
  defaultMode = 'login',
  onAuthSuccess,
  intent = 'default',
  callbackUrl,
}: AuthModalProps) {
  const [mode, setMode] = useState<AuthMode>(defaultMode);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [oauthProviders, setOAuthProviders] = useReducer(
    (_current: OAuthProviderName[], next: OAuthProviderName[]) => next,
    []
  );
  const router = useRouter();

  useEffect(() => {
    if (isOpen) {
      setMode(defaultMode);
      setError(null);
      setIsLoading(false);
      setPassword('');
      setConfirmPassword('');
    }
  }, [isOpen, defaultMode]);

  useEffect(() => {
    if (!isOpen) return;
    let active = true;

    loadOAuthProviders()
      .then((enabled) => {
        if (!active) return;
        setOAuthProviders(enabled);
      })
      .catch(() => {
        if (active) setOAuthProviders([]);
      });

    return () => {
      active = false;
    };
  }, [isOpen]);

  const handleOAuthSignIn = async (provider: 'github' | 'google') => {
    setIsLoading(true);
    setError(null);
    try {
      await signIn(provider, callbackUrl ? { callbackUrl } : undefined);
    } catch {
      setError('Failed to sign in. Please try again.');
      setIsLoading(false);
    }
  };

  const handleLoginSubmit = async (e: React.SyntheticEvent<HTMLFormElement, SubmitEvent>) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    const continuationWindow =
      intent === 'apply' ? window.open('', '_blank', 'noopener,noreferrer') : null;

    const formData = new FormData(e.currentTarget);
    const data = {
      email: formData.get('email') as string,
      password: formData.get('password') as string,
    };

    const result = loginSchema.safeParse(data);
    if (!result.success) {
      continuationWindow?.close();
      setError(result.error.issues[0].message);
      setIsLoading(false);
      return;
    }

    try {
      const authResult = await signIn('credentials', {
        email: result.data.email,
        password: result.data.password,
        redirect: false,
      });

      if (authResult?.error) {
        continuationWindow?.close();
        setError('Invalid email or password');
        setIsLoading(false);
        return;
      }

      onAuthSuccess?.(continuationWindow);
      router.refresh();
      onClose();
    } catch {
      continuationWindow?.close();
      setError('An unexpected error occurred. Please try again.');
      setIsLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.SyntheticEvent<HTMLFormElement, SubmitEvent>) => {
    e.preventDefault();
    setError(null);
    const continuationWindow =
      intent === 'apply' ? window.open('', '_blank', 'noopener,noreferrer') : null;

    const formData = new FormData(e.currentTarget);
    const data = {
      name: formData.get('name') as string,
      email: formData.get('email') as string,
      password: password,
      confirm_password: confirmPassword,
    };

    const validationResult = registrationSchema.safeParse(data);
    if (!validationResult.success) {
      continuationWindow?.close();
      setError(validationResult.error.issues[0].message);
      return;
    }

    setIsLoading(true);

    try {
      const registerResult = await registerUser({
        email: validationResult.data.email,
        password: validationResult.data.password,
        name: validationResult.data.name,
      });

      if (!registerResult.success) {
        continuationWindow?.close();
        if (registerResult.errorType === 'EMAIL_REGISTERED_WITH_OAUTH') {
          setError(
            `${registerResult.error} Please sign in with your OAuth provider or go to Settings to set a password.`
          );
        } else {
          setError(registerResult.error || 'Registration failed. Please try again.');
        }
        setIsLoading(false);
        return;
      }

      const authResult = await signIn('credentials', {
        email: validationResult.data.email,
        password: validationResult.data.password,
        redirect: false,
      });

      if (authResult?.error) {
        continuationWindow?.close();
        setError('Account created but sign in failed. Please try signing in.');
        setIsLoading(false);
        return;
      }

      onAuthSuccess?.(continuationWindow);
      router.refresh();
      onClose();
    } catch {
      continuationWindow?.close();
      setError('An unexpected error occurred. Please try again.');
      setIsLoading(false);
    }
  };

  const toggleMode = () => {
    if (isLoading) return;
    setMode(mode === 'login' ? 'register' : 'login');
    setError(null);
  };

  const isApplyIntent = intent === 'apply';
  const authCopy = getAuthCopy(mode, isApplyIntent);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <>
          {authCopy.title}
          <p className="text-foreground-muted mt-1 text-sm font-normal">{authCopy.subtitle}</p>
        </>
      }
      size="md"
    >
      {error && (
        <Alert type="error" className="mb-4">
          {error}
        </Alert>
      )}

      {oauthProviders.length > 0 && (
        <OAuthButtons
          isLoading={isLoading}
          providers={oauthProviders}
          onSignIn={handleOAuthSignIn}
        />
      )}

      {!ENABLE_CREDENTIAL_AUTH && (
        <p className="text-foreground-muted mt-4 text-center text-xs">
          {oauthProviders.length > 0
            ? 'Email sign-in is temporarily disabled. Please use one of the providers above.'
            : 'No sign-in providers are currently configured.'}
        </p>
      )}

      {ENABLE_CREDENTIAL_AUTH && (
        <>
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="border-border w-full border-t" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="bg-surface text-foreground-muted px-2">Or continue with email</span>
            </div>
          </div>

          {mode === 'login' ? (
            <LoginForm
              isLoading={isLoading}
              onSubmit={handleLoginSubmit}
              submitLabel={authCopy.submitLabel ?? 'Sign in'}
            />
          ) : (
            <RegisterForm
              isLoading={isLoading}
              password={password}
              confirmPassword={confirmPassword}
              onPasswordChange={setPassword}
              onConfirmPasswordChange={setConfirmPassword}
              onSubmit={handleRegisterSubmit}
              submitLabel={authCopy.submitLabel ?? 'Create account'}
            />
          )}

          <div className="mt-6 text-center">
            <p className="text-foreground-secondary text-sm">
              {mode === 'login' ? (
                <>
                  Don&apos;t have an account?{' '}
                  <button
                    onClick={toggleMode}
                    disabled={isLoading}
                    className="text-accent hover:text-accent-hover font-medium transition-colors"
                  >
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{' '}
                  <button
                    onClick={toggleMode}
                    disabled={isLoading}
                    className="text-accent hover:text-accent-hover font-medium transition-colors"
                  >
                    Sign in
                  </button>
                </>
              )}
            </p>
          </div>
        </>
      )}
    </Modal>
  );
}
