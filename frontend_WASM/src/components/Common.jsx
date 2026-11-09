/** Shared card, badge, and alert primitives. */

import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';

export const Card = ({ as: Component = 'div', children, className = '', ...props }) => (
  <Component
    className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 ${className}`}
    {...props}
  >
    {children}
  </Component>
);

export const CardHeader = ({ children, className = '', ...props }) => (
  <div className={`-mx-5 -mt-5 mb-5 border-b border-slate-100 px-5 py-4 dark:border-slate-800 ${className}`} {...props}>
    {children}
  </div>
);

export const CardTitle = ({ as: Component = 'h2', children, className = '', ...props }) => (
  <Component className={`text-lg font-semibold text-slate-900 dark:text-white ${className}`} {...props}>
    {children}
  </Component>
);

export const CardDescription = ({ children, className = '', ...props }) => (
  <p className={`mt-1 text-sm text-slate-500 dark:text-slate-400 ${className}`} {...props}>
    {children}
  </p>
);

export const CardContent = ({ children, className = '', ...props }) => (
  <div className={className} {...props}>{children}</div>
);

export const CardFooter = ({ children, className = '', ...props }) => (
  <div className={`-mx-5 -mb-5 mt-5 border-t border-slate-100 px-5 py-4 dark:border-slate-800 ${className}`} {...props}>
    {children}
  </div>
);

const badgeVariants = {
  primary: 'bg-primary-50 text-primary-700 ring-primary-600/15 dark:bg-primary-950/60 dark:text-primary-300 dark:ring-primary-400/20',
  info: 'bg-sky-50 text-sky-700 ring-sky-600/15 dark:bg-sky-950/50 dark:text-sky-300 dark:ring-sky-400/20',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-600/15 dark:bg-emerald-950/50 dark:text-emerald-300 dark:ring-emerald-400/20',
  warning: 'bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-950/50 dark:text-amber-300 dark:ring-amber-400/20',
  danger: 'bg-rose-50 text-rose-700 ring-rose-600/15 dark:bg-rose-950/50 dark:text-rose-300 dark:ring-rose-400/20',
  neutral: 'bg-slate-100 text-slate-700 ring-slate-500/15 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-400/20',
};

export const Badge = ({ children, variant = 'primary', className = '', ...props }) => (
  <span
    className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${badgeVariants[variant] || badgeVariants.primary} ${className}`}
    {...props}
  >
    {children}
  </span>
);

const alertVariants = {
  info: {
    icon: Info,
    classes: 'border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900 dark:bg-sky-950/50 dark:text-sky-100',
    iconClasses: 'text-sky-600 dark:text-sky-300',
  },
  success: {
    icon: CheckCircle2,
    classes: 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-100',
    iconClasses: 'text-emerald-600 dark:text-emerald-300',
  },
  warning: {
    icon: AlertTriangle,
    classes: 'border-amber-200 bg-amber-50 text-amber-950 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-100',
    iconClasses: 'text-amber-600 dark:text-amber-300',
  },
  danger: {
    icon: AlertCircle,
    classes: 'border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-100',
    iconClasses: 'text-rose-600 dark:text-rose-300',
  },
  error: {
    icon: AlertCircle,
    classes: 'border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-100',
    iconClasses: 'text-rose-600 dark:text-rose-300',
  },
};

export const Alert = ({ type = 'info', title, children, onClose, className = '', ...props }) => {
  const variant = alertVariants[type] || alertVariants.info;
  const Icon = variant.icon;

  return (
    <div
      className={`flex items-start gap-3 rounded-xl border p-4 ${variant.classes} ${className}`}
      role={type === 'danger' || type === 'error' ? 'alert' : 'status'}
      {...props}
    >
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${variant.iconClasses}`} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title && <h3 className="mb-1 font-semibold">{title}</h3>}
        <div className="text-sm leading-relaxed">{children}</div>
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="-mr-1 -mt-1 rounded-lg p-1.5 opacity-70 transition hover:bg-black/5 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-current dark:hover:bg-white/10"
          aria-label="Dismiss message"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
};

