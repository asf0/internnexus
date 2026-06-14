'use client';

interface AdminSwitchProps {
  readonly checked: boolean;
  readonly onChange: (checked: boolean) => void;
  readonly checkedChildren?: React.ReactNode;
  readonly unCheckedChildren?: React.ReactNode;
  readonly disabled?: boolean;
}

export function AdminSwitch({
  checked,
  onChange,
  checkedChildren,
  unCheckedChildren,
  disabled,
}: AdminSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${
        checked ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-600'
      }`}
    >
      <span
        className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
      <span className="sr-only">{checked ? checkedChildren : unCheckedChildren}</span>
    </button>
  );
}
