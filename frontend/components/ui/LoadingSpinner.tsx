interface LoadingSpinnerProps {
  readonly className?: string;
  readonly size?: 'sm' | 'md' | 'lg';
}

export function LoadingSpinner({ className = '', size = 'md' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-5 w-5 border-2',
    md: 'h-8 w-8 border-4',
    lg: 'h-12 w-12 border-4',
  };

  return (
    <output
      className={`border-border border-t-accent animate-spin rounded-full ${sizeClasses[size]} ${className}`}
      aria-label="Loading"
    />
  );
}
