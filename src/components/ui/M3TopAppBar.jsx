import React from 'react';

/**
 * M3TopAppBar - Google Material Design 3 Top App Bar
 */
const M3TopAppBar = ({
  title,
  subtitle,
  leadingIcon: LeadingIcon = null,
  onLeadingClick,
  actions = null,
  className = '',
  sticky = false
}) => {
  return (
    <header 
      className={`
        w-full bg-white/95 dark:bg-stone-900/95 backdrop-blur-md border-b border-stone-200/80 dark:border-stone-800/80 px-4 lg:px-6 py-3 flex items-center justify-between z-30 transition-all text-left
        ${sticky ? 'sticky top-0 shadow-xs' : ''}
        ${className}
      `}
    >
      {/* Leading Icon / Title Area */}
      <div className="flex items-center gap-3 min-w-0">
        {LeadingIcon && (
          <button
            type="button"
            onClick={onLeadingClick}
            className="p-2 rounded-full text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 transition"
          >
            <LeadingIcon size={22} />
          </button>
        )}

        <div className="min-w-0">
          <h1 className="text-lg font-black text-stone-900 dark:text-white uppercase tracking-tight truncate">
            {title}
          </h1>
          {subtitle && (
            <p className="text-[11px] font-bold text-stone-500 dark:text-stone-400 tracking-wider uppercase truncate">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      {/* Trailing Actions */}
      {actions && (
        <div className="flex items-center gap-2 flex-shrink-0">
          {actions}
        </div>
      )}
    </header>
  );
};

export default M3TopAppBar;
