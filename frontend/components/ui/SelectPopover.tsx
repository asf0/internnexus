'use client';

import {
  forwardRef,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type RefObject,
  useEffect,
  useRef,
} from 'react';

interface UseSelectPopoverOptions {
  readonly isOpen: boolean;
  readonly onOpenChange: (isOpen: boolean) => void;
  readonly initialFocusRef?: RefObject<HTMLElement | null>;
  readonly triggerRef?: RefObject<HTMLButtonElement | null>;
}

export function useSelectPopover({
  isOpen,
  onOpenChange,
  initialFocusRef,
  triggerRef,
}: UseSelectPopoverOptions) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        onOpenChange(false);
      }
    };

    document.addEventListener('mousedown', closeOnOutsideClick);
    return () => document.removeEventListener('mousedown', closeOnOutsideClick);
  }, [onOpenChange]);

  useEffect(() => {
    if (!isOpen) return;

    initialFocusRef?.current?.focus();

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      onOpenChange(false);
      triggerRef?.current?.focus();
    };

    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [initialFocusRef, isOpen, onOpenChange, triggerRef]);

  return rootRef;
}

export const SelectTrigger = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement>>(
  function SelectTrigger({ className = '', children, ...props }, ref) {
    return (
      <button
        ref={ref}
        type="button"
        className={`border-border bg-surface text-foreground focus-visible:ring-focus-ring flex min-h-11 w-full items-center rounded-lg border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  }
);

export function SelectPopoverPanel({
  className = '',
  children,
  ...props
}: Readonly<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      className={`border-border bg-surface absolute z-40 mt-1 w-full overflow-hidden rounded-lg border shadow-lg ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export const SelectSearchInput = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>(function SelectSearchInput({ className = '', ...props }, ref) {
  return (
    <input
      ref={ref}
      type="search"
      className={`border-border bg-surface text-foreground placeholder:text-foreground-muted focus:border-accent focus:ring-focus-ring w-full rounded-lg border px-3 py-2 text-sm focus:ring-2 focus:outline-none ${className}`}
      {...props}
    />
  );
});

export function SelectList({
  className = '',
  children,
  ...props
}: Readonly<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div className={`max-h-60 overflow-y-auto ${className}`} {...props}>
      {children}
    </div>
  );
}

interface SelectOptionProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  readonly selected: boolean;
  readonly selectionMode?: 'single' | 'multiple';
}

export const SelectOption = forwardRef<HTMLButtonElement, SelectOptionProps>(function SelectOption(
  { selected, selectionMode = 'single', className = '', children, ...props },
  ref
) {
  return (
    <button
      ref={ref}
      type="button"
      role={selectionMode === 'multiple' ? 'menuitemcheckbox' : 'menuitemradio'}
      aria-checked={selected}
      className={`text-foreground hover:bg-surface-subtle focus-visible:bg-surface-subtle flex w-full cursor-pointer items-center justify-between px-3 py-2 text-left text-sm focus-visible:outline-none ${className}`}
      {...props}
    >
      {children}
    </button>
  );
});

export function SelectOptionRow({
  className = '',
  children,
  ...props
}: Readonly<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      className={`hover:bg-surface-subtle flex items-center justify-between px-3 py-2 text-sm ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function SelectEmpty({ children }: { readonly children: React.ReactNode }) {
  return <div className="text-foreground-muted px-3 py-2 text-sm">{children}</div>;
}

export function SelectFooter({ children }: { readonly children: React.ReactNode }) {
  return (
    <div className="border-border bg-surface flex items-center justify-between border-t p-2">
      {children}
    </div>
  );
}

export const selectClearButtonClass =
  'text-foreground-secondary hover:bg-surface-subtle rounded px-2 py-1 text-xs font-medium disabled:cursor-not-allowed disabled:opacity-50';

export const selectDoneButtonClass =
  'bg-accent text-on-accent hover:bg-accent-hover rounded px-2 py-1 text-xs font-medium';
