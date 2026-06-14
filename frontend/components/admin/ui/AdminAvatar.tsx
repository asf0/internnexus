'use client';

import { User } from 'lucide-react';

interface AdminAvatarProps {
  readonly src?: string | null;
  readonly alt?: string;
  readonly fallback?: string;
  readonly size?: 'sm' | 'md' | 'lg';
}

export function AdminAvatar({ src, alt = '', fallback, size = 'md' }: AdminAvatarProps) {
  const sizeClasses = {
    sm: 'h-8 w-8 text-xs',
    md: 'h-10 w-10 text-sm',
    lg: 'h-12 w-12 text-base',
  };

  if (src) {
    return (
      <img
        src={src}
        alt={alt}
        className={`inline-flex items-center justify-center rounded-full object-cover ${sizeClasses[size]}`}
      />
    );
  }

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full bg-blue-600 font-medium text-white ${sizeClasses[size]}`}
      aria-label={alt || fallback || 'User avatar'}
    >
      {fallback ? fallback.charAt(0).toUpperCase() : <User className="h-1/2 w-1/2" />}
    </span>
  );
}
