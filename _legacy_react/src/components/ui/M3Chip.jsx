import React from 'react';
import { Check, X } from 'lucide-react';

/**
 * M3Chip - Google Material Design 3 Chip Component
 * Variants: 'filter' | 'assist' | 'status'
 */
const M3Chip = ({
  label,
  selected = false,
  onClick,
  onRemove,
  icon: Icon = null,
  variant = 'filter',
  colorScheme = 'default', // 'default' | 'orange' | 'green' | 'red' | 'blue'
  className = '',
  disabled = false,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center gap-2 h-8 px-3.5 rounded-lg text-xs font-bold tracking-wide transition-all duration-150 select-none cursor-pointer';

  const colorVariants = {
    default: selected
      ? 'bg-orange-100 dark:bg-orange-950/60 text-orange-900 dark:text-orange-200 border border-orange-500/40'
      : 'bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 border border-stone-200 dark:border-stone-700 hover:bg-stone-200 dark:hover:bg-stone-700/60',
    orange: 'bg-orange-100 dark:bg-orange-950/60 text-orange-800 dark:text-orange-300 border border-orange-300 dark:border-orange-800',
    green: 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800',
    red: 'bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800',
    blue: 'bg-sky-100 dark:bg-sky-950/60 text-sky-800 dark:text-sky-300 border border-sky-300 dark:border-sky-800'
  };

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      onClick={disabled ? undefined : onClick}
      className={`
        ${baseStyles}
        ${colorVariants[colorScheme] || colorVariants.default}
        ${disabled ? 'opacity-50 pointer-events-none' : 'm3-state-layer'}
        ${className}
      `}
      {...props}
    >
      {selected ? (
        <Check size={14} strokeWidth={3} className="text-current" />
      ) : (
        Icon && <Icon size={14} />
      )}

      <span>{label}</span>

      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="hover:opacity-70 p-0.5 rounded-full"
        >
          <X size={12} strokeWidth={3} />
        </button>
      )}
    </div>
  );
};

export default M3Chip;
