import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Button } from './Button';

interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'aria-label'> {
  readonly label: string;
  readonly children: ReactNode;
  readonly variant?: 'secondary' | 'outline' | 'ghost';
}

export function IconButton({
  label,
  children,
  variant = 'outline',
  className = '',
  ...props
}: Readonly<IconButtonProps>) {
  return (
    <Button
      variant={variant}
      size="sm"
      aria-label={label}
      title={props.title ?? label}
      className={`min-w-10 px-2 ${className}`}
      {...props}
    >
      {children}
    </Button>
  );
}
