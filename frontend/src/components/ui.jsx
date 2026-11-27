import React, { useEffect, useRef } from 'react';
import { X, AlertTriangle, Check } from 'lucide-react';

export const cx = (...parts) => parts.filter(Boolean).join(' ');

/* ---------------------------------------------------------------------------
 * Tombol. Hijau (primary) hanya untuk aksi utama halaman; sisanya secondary/ghost.
 * ------------------------------------------------------------------------- */
const BTN_VARIANTS = {
  primary: 'bg-go text-on-go hover:bg-go/90 active:bg-go/80',
  brand: 'bg-brand text-on-brand hover:bg-brand/90 active:bg-brand/80',
  secondary: 'bg-surface text-ink border border-line hover:border-ink/40 hover:bg-sunken/60 active:bg-sunken',
  ghost: 'text-muted hover:text-ink hover:bg-sunken active:bg-sunken',
  danger: 'text-stop-text hover:bg-stop/10 active:bg-stop/15',
  'danger-solid': 'bg-stop text-on-stop hover:bg-stop/90 active:bg-stop/80',
  record: 'bg-stop text-on-stop hover:bg-stop/90 active:bg-stop/80'
};
const BTN_SIZES = {
  sm: 'h-8 px-3 text-[13px] gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-base gap-2'
};

export function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  icon: Icon,
  iconEnd: IconEnd,
  as: Tag = 'button',
  className,
  children,
  disabled,
  ...rest
}) {
  const isButton = Tag === 'button';
  const iconCls = size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4';
  return (
    <Tag
      {...(isButton ? { type: rest.type || 'button', disabled: disabled || loading } : {})}
      {...rest}
      className={cx(
        'inline-flex items-center justify-center rounded-md font-semibold whitespace-nowrap select-none',
        'transition-colors duration-150 disabled:opacity-45 disabled:pointer-events-none',
        BTN_VARIANTS[variant],
        BTN_SIZES[size],
        className
      )}
    >
      {loading ? <Spinner /> : Icon ? <Icon className={iconCls} aria-hidden="true" /> : null}
      {children}
      {IconEnd && !loading && <IconEnd className={iconCls} aria-hidden="true" />}
    </Tag>
  );
}

export function IconButton({ label, icon: Icon, className, ...rest }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      {...rest}
      className={cx(
        'inline-flex items-center justify-center w-9 h-9 rounded-md text-muted hover:text-ink hover:bg-sunken transition-colors disabled:opacity-35 disabled:pointer-events-none',
        className
      )}
    >
      <Icon className="w-4 h-4" aria-hidden="true" />
    </button>
  );
}

export const Spinner = ({ className }) => (
  <span
    aria-hidden="true"
    className={cx('inline-block w-4 h-4 rounded-full border-2 border-current border-t-transparent animate-spin', className)}
  />
);

/* ---------------------------------------------------------------------------
 * Judul halaman: besar, rapat, rata kiri. Tindakan di kanan.
 * ------------------------------------------------------------------------- */
export function PageHeader({ title, description, actions, children }) {
  return (
    <header className="mb-8 lg:mb-10">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0 max-w-2xl">
          <h1 className="font-display font-extrabold text-[2.5rem] sm:text-5xl leading-[0.95] tracking-[-0.01em] text-ink">
            {title}
          </h1>
          {description && <p className="mt-3 text-muted max-w-[62ch]">{description}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
      </div>
      {children}
    </header>
  );
}

/* ---------------------------------------------------------------------------
 * Bagian formulir: dipisah garis tipis, bukan kartu. Desktop: label kiri, isian kanan.
 * ------------------------------------------------------------------------- */
export function Section({ title, description, aside, children, className, id, layout = 'split' }) {
  const headingId = id ? `${id}-title` : undefined;
  if (layout === 'stack') {
    return (
      <section aria-labelledby={headingId} className={cx('border-t border-line pt-6 pb-8', className)}>
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="min-w-0">
            <h2 id={headingId} className="font-display font-bold text-2xl leading-tight text-ink">
              {title}
            </h2>
            {description && <p className="mt-1 text-sm text-muted max-w-[62ch]">{description}</p>}
          </div>
          {aside && <div className="shrink-0">{aside}</div>}
        </div>
        {children}
      </section>
    );
  }
  return (
    <section
      aria-labelledby={headingId}
      className={cx('border-t border-line pt-6 pb-8 grid grid-cols-1 gap-4 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-10', className)}
    >
      <div className="min-w-0">
        <h2 id={headingId} className="font-display font-bold text-xl leading-tight text-ink">
          {title}
        </h2>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
        {aside && <div className="mt-3">{aside}</div>}
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

/* ---------------------------------------------------------------------------
 * Label + isian + petunjuk/error
 * ------------------------------------------------------------------------- */
export function Field({ label, htmlFor, optional, hint, error, aside, children, className }) {
  return (
    <div className={cx('min-w-0', className)}>
      {(label || aside) && (
        <div className="flex items-baseline justify-between gap-3 mb-1.5">
          {label && (
            <label htmlFor={htmlFor} className="text-sm font-semibold text-ink">
              {label}
              {optional && <span className="font-normal text-muted"> (opsional)</span>}
            </label>
          )}
          {aside}
        </div>
      )}
      {children}
      {error ? (
        <p className="mt-1.5 text-[13px] font-medium text-stop-text" role="alert">
          {error}
        </p>
      ) : (
        hint && <p className="mt-1.5 text-[13px] text-muted">{hint}</p>
      )}
    </div>
  );
}

/** Penghitung kata/huruf hook. Merah bila melewati batas. */
export function HookCounter({ stats, id }) {
  return (
    <span id={id} className={cx('text-[13px] num', stats.over ? 'text-stop-text font-semibold' : 'text-muted')}>
      {`${stats.words}/${stats.maxWords} kata, ${stats.chars}/${stats.maxChars} huruf`}
    </span>
  );
}

/* ---------------------------------------------------------------------------
 * Kontrol segmen (pilih satu dari beberapa)
 * ------------------------------------------------------------------------- */
export function Segmented({ options, value, onChange, label, size = 'md', className }) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cx('inline-flex flex-wrap max-w-full rounded-md bg-sunken p-1 gap-1', className)}
    >
      {options.map((o) => {
        const active = value === o.id;
        return (
          <button
            key={o.id}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(o.id)}
            className={cx(
              'shrink-0 rounded-[5px] font-semibold whitespace-nowrap transition-colors',
              size === 'sm' ? 'px-2.5 h-7 text-[13px]' : 'px-3.5 h-8 text-sm',
              active ? 'bg-surface text-ink shadow-[0_1px_2px_rgb(var(--ink)/0.12)]' : 'text-muted hover:text-ink'
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

/** Ubin yang bisa dipilih (pilar, style, voice over). Pilihan aktif: garis ungu tebal. */
export function ChoiceTile({ selected, onClick, children, className, ...rest }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onClick}
      {...rest}
      className={cx(
        'relative text-left rounded-lg border bg-surface p-4 transition-colors min-w-0',
        selected ? 'border-brand ring-1 ring-brand bg-brand-soft/60' : 'border-line hover:border-ink/35',
        className
      )}
    >
      {children}
    </button>
  );
}

/* ---------------------------------------------------------------------------
 * Status job
 * ------------------------------------------------------------------------- */
export function StatusMark({ status, className }) {
  const ok = status === 'siap_unggah';
  return (
    <span className={cx('inline-flex items-center gap-1.5 text-[13px] font-semibold', ok ? 'text-go-text' : 'text-stop-text', className)}>
      <span className={cx('w-2 h-2 rounded-full', ok ? 'bg-go' : 'bg-stop')} aria-hidden="true" />
      {ok ? 'Siap unggah' : 'Perlu tinjau'}
    </span>
  );
}

/* ---------------------------------------------------------------------------
 * Keadaan kosong: arahkan ke tindakan
 * ------------------------------------------------------------------------- */
export function Empty({ title, children, action, className }) {
  return (
    <div className={cx('rounded-lg border border-dashed border-line px-6 py-10 text-center', className)}>
      <p className="font-display font-bold text-xl text-ink">{title}</p>
      {children && <p className="mt-1 text-sm text-muted max-w-[46ch] mx-auto">{children}</p>}
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Dialog modal (Esc / klik latar menutup; fokus ke tombol pertama)
 * ------------------------------------------------------------------------- */
export function Dialog({ open, onClose, title, children, actions, size = 'md', labelledBy = 'dialog-title' }) {
  const panelRef = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const prev = document.activeElement;
    const onKey = (e) => e.key === 'Escape' && onClose?.();
    document.addEventListener('keydown', onKey);
    const first = panelRef.current?.querySelector('[data-autofocus], button, [href], input, textarea, select');
    first?.focus();
    const { overflow } = document.body.style;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
      prev?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4">
      <div className="absolute inset-0 bg-[rgb(12_8_26/0.55)]" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        className={cx(
          'relative w-full bg-surface text-ink border border-line shadow-[0_24px_60px_rgb(12_8_26/0.35)]',
          'rounded-t-xl sm:rounded-xl flex flex-col max-h-[88vh] overscroll-contain',
          size === 'lg' ? 'sm:max-w-2xl' : 'sm:max-w-md'
        )}
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div className="flex items-start justify-between gap-4 px-6 pt-5 pb-3">
          <h2 id={labelledBy} className="font-display font-bold text-2xl leading-tight">
            {title}
          </h2>
          <IconButton label="Tutup" icon={X} onClick={onClose} className="-mr-2 -mt-1" />
        </div>
        <div className="px-6 pb-2 overflow-y-auto scroll-thin">{children}</div>
        {actions && <div className="px-6 py-4 flex flex-wrap justify-end gap-2">{actions}</div>}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Toast (diumumkan ke pembaca layar)
 * ------------------------------------------------------------------------- */
export function Toasts({ toasts, onDismiss }) {
  return (
    <div
      className="fixed z-[60] right-4 left-4 sm:left-auto sm:w-96 flex flex-col gap-2 pointer-events-none bottom-[calc(5rem+env(safe-area-inset-bottom))] lg:bottom-6"
      aria-live="polite"
      role="status"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cx(
            'pointer-events-auto flex items-start gap-3 rounded-lg px-4 py-3 text-sm font-medium shadow-[0_10px_30px_rgb(12_8_26/0.25)]',
            t.type === 'error' ? 'bg-stop text-on-stop' : 'bg-ink text-paper'
          )}
        >
          {t.type === 'error' ? (
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
          ) : (
            <Check className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
          )}
          <span className="flex-1 min-w-0 break-words">{t.message}</span>
          {t.action && (
            <button
              type="button"
              onClick={() => {
                t.action.onClick();
                onDismiss(t.id);
              }}
              className="shrink-0 -my-0.5 rounded-md px-2 py-0.5 font-semibold underline underline-offset-2 hover:no-underline"
            >
              {t.action.label}
            </button>
          )}
          <button type="button" onClick={() => onDismiss(t.id)} aria-label="Tutup notifikasi" className="opacity-70 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
