import {
  ReactNode,
  ButtonHTMLAttributes,
  cloneElement,
  isValidElement,
  type ReactElement,
} from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  readonly variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  readonly size?: 'sm' | 'md' | 'lg';
  readonly children: ReactNode;
  readonly asChild?: boolean;
}

export function Button({
  variant = 'primary',
  size = 'md',
  children,
  className = '',
  asChild = false,
  type = 'button',
  ...props
}: Readonly<ButtonProps>) {
  const baseStyles =
    'inline-flex min-h-10 items-center justify-center gap-2 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-50';

  const variants = {
    primary: 'border border-transparent bg-accent text-on-accent hover:bg-accent-hover',
    secondary:
      'border border-border bg-surface text-foreground-secondary hover:bg-surface-subtle hover:text-foreground',
    outline:
      'border border-border bg-transparent text-foreground-secondary hover:bg-surface-subtle hover:text-foreground',
    ghost:
      'border border-transparent bg-transparent text-foreground-secondary hover:bg-surface-subtle hover:text-foreground',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  };
  const combinedClassName = `${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`;

  if (asChild && isValidElement(children)) {
    const child = children as ReactElement<{ className?: string }>;
    const childClassName = child.props.className || '';
    return cloneElement(child, {
      className: `${combinedClassName} ${childClassName}`.trim(),
    });
  }

  return (
    <button type={type} className={combinedClassName} {...props}>
      {children}
    </button>
  );
}
