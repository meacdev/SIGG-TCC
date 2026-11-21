import { useEffect, useRef, useState, type InputHTMLAttributes, type ReactNode } from 'react';

export type IconName =
  | 'cap'
  | 'user'
  | 'users'
  | 'book'
  | 'arrow'
  | 'check'
  | 'shield'
  | 'eye'
  | 'close'
  | 'chat'
  | 'clock'
  | 'file'
  | 'cal'
  | 'menu'
  | 'key'
  | 'plus';

export function Icon({ name, size = 22 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, ReactNode> = {
    users: (
      <>
        <circle cx="9" cy="8" r="3.5" />
        <path d="M2 20v-1a7 7 0 0 1 14 0v1" />
        <path d="M16 4.5a3.5 3.5 0 0 1 0 7M22 20v-1a7 7 0 0 0-4-6.3" />
      </>
    ),
    chat: <path d="M4 5h16v11H9l-5 4Z" />,
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    file: (
      <>
        <path d="M14 3H6v18h12V7Z" />
        <path d="M14 3v4h4M9 13h6M9 17h6" />
      </>
    ),
    cal: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M3 10h18M8 3v4M16 3v4" />
      </>
    ),
    menu: <path d="M4 7h16M4 12h16M4 17h16" />,
    key: (
      <>
        <circle cx="8" cy="15" r="4" />
        <path d="m11 12 9-9M17 6l3 3M14 9l2 2" />
      </>
    ),
    plus: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 8v8M8 12h8" />
      </>
    ),
    cap: (
      <>
        <path d="m2 9 10-5 10 5-10 5Z" />
        <path d="M6 11v6c4 3 8 3 12 0v-6M22 9v8" />
      </>
    ),
    user: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21v-2a8 8 0 0 1 16 0v2" />
      </>
    ),
    book: (
      <>
        <path d="M12 5v16M3 3c4 0 7 0 9 2 2-2 5-2 9-2v16c-4 0-7 0-9 2-2-2-5-2-9-2Z" />
      </>
    ),
    arrow: (
      <>
        <path d="M4 12h16m-6-6 6 6-6 6" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    shield: (
      <>
        <path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z" />
        <path d="m8 12 3 3 5-6" />
      </>
    ),
    eye: (
      <>
        <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
    close: <path d="m6 6 12 12M6 18 18 6" />,
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

export function Field({
  name,
  label,
  optional,
  hint,
  errors,
  children,
}: {
  name: string;
  label: string;
  optional?: boolean;
  hint?: string;
  errors: Record<string, string | undefined>;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <label htmlFor={name}>
        {label} {optional && <span className="optional">(opcional)</span>}
      </label>
      {children}
      {hint && <small id={`${name}-hint`}>{hint}</small>}
      {errors[name] && (
        <small className="field-error" id={`${name}-error`}>
          {errors[name]}
        </small>
      )}
    </div>
  );
}

export function inputA11y(name: string, errors: Record<string, string | undefined>, hint = false) {
  return {
    id: name,
    name,
    'aria-invalid': !!errors[name],
    'aria-describedby':
      [hint ? `${name}-hint` : '', errors[name] ? `${name}-error` : ''].filter(Boolean).join(' ') ||
      undefined,
  };
}

export function Password({
  label,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="password-input">
      <input {...props} type={visible ? 'text' : 'password'} />
      <button
        type="button"
        className="eye-button"
        aria-label={`${visible ? 'Ocultar' : 'Mostrar'} ${label.toLowerCase()}`}
        aria-pressed={visible}
        onClick={() => setVisible(!visible)}
        disabled={props.disabled}
      >
        <Icon name="eye" size={19} />
      </button>
    </div>
  );
}

export function Notice({
  message,
  success = false,
  children,
}: {
  message: string;
  success?: boolean;
  children?: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.focus();
  }, [message]);
  return (
    <div
      ref={ref}
      tabIndex={-1}
      className={`notice ${success ? 'success' : 'error'}`}
      role={success ? 'status' : 'alert'}
    >
      <span>{message}</span>
      {children}
    </div>
  );
}
