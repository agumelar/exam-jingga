import React from 'react';

/**
 * M3Button - Google Material Design 3 Button Component
 * Variants: 'filled' | 'tonal' | 'outlined' | 'text' | 'elevated' | 'fab'
 * Sizes: 'sm' | 'md' | 'lg'
 */
const M3Button = ({
  children,
  variant = 'filled',
  size = 'md',
  icon: Icon = null,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  fullWidth = false,
  className = '',
  onClick,
  type = 'button',
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-bold tracking-wide transition-all duration-200 m3-state-layer disabled:opacity-50 disabled:pointer-events-none select-none cursor-pointer';

  const sizeStyles = {
    sm: 'h-9 px-4 text-xs rounded-full gap-2',
    md: 'h-11 px-6 text-sm rounded-full gap-2.5',
    lg: 'h-13 px-8 text-base rounded-full gap-3',
    fab: 'h-14 px-6 text-base rounded-2xl gap-3 shadow-lg'
  };

  const variantStyles = {
    filled: 'bg-orange-600 hover:bg-orange-500 active:bg-orange-700 text-white shadow-sm hover:shadow-md dark:bg-orange-600 dark:hover:bg-orange-500',
    tonal: 'bg-orange-100 hover:bg-orange-200 text-orange-950 dark:bg-orange-950/60 dark:hover:bg-orange-900/60 dark:text-orange-200',
    outlined: 'border border-stone-300 dark:border-stone-700 text-stone-800 dark:text-stone-200 hover:bg-stone-100 dark:hover:bg-stone-800/60',
    text: 'text-orange-600 hover:bg-orange-50 dark:text-orange-400 dark:hover:bg-orange-950/30',
    elevated: 'bg-stone-50 dark:bg-stone-800 text-stone-800 dark:text-stone-100 m3-elevation-1 hover:m3-elevation-2 border border-stone-200/50 dark:border-stone-700/50',
    fab: 'bg-orange-600 text-white hover:bg-orange-500 shadow-lg hover:shadow-orange-600/30 dark:bg-orange-500'
  };

  const currentSize = variant === 'fab' ? 'fab' : size;

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={`
        ${baseStyles}
        ${sizeStyles[currentSize] || sizeStyles.md}
        ${variantStyles[variant] || variantStyles.filled}
        ${fullWidth ? 'w-full' : ''}
        ${className}
      `}
      {...props}
    >
      {loading ? (
        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      ) : (
        Icon && iconPosition === 'left' && <Icon size={size === 'sm' ? 16 : size === 'lg' ? 22 : 18} />
      )}
      <span>{children}</span>
      {!loading && Icon && iconPosition === 'right' && (
        <Icon size={size === 'sm' ? 16 : size === 'lg' ? 22 : 18} />
      )}
    </button>
  );
};

export default M3Button;
