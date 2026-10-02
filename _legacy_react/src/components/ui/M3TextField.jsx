import React, { useState } from 'react';

/**
 * M3TextField - Google Material Design 3 Outlined Input Field
 */
const M3TextField = ({
  label,
  value,
  onChange,
  type = 'text',
  placeholder = '',
  icon: Icon = null,
  suffixIcon: SuffixIcon = null,
  error = '',
  helperText = '',
  disabled = false,
  required = false,
  className = '',
  id,
  ...props
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const inputId = id || `m3-input-${Math.random().toString(36).substr(2, 9)}`;

  const hasValue = value !== undefined && value !== null && String(value).length > 0;

  return (
    <div className={`flex flex-col gap-1.5 text-left w-full ${className}`}>
      <div 
        className={`
          relative flex items-center rounded-2xl border transition-all duration-200 bg-white dark:bg-stone-900
          ${disabled ? 'opacity-50 pointer-events-none bg-stone-100 dark:bg-stone-950' : ''}
          ${error 
            ? 'border-red-500 focus-within:ring-2 focus-within:ring-red-500/20' 
            : isFocused 
              ? 'border-orange-600 ring-2 ring-orange-500/20 dark:border-orange-500' 
              : 'border-stone-300 dark:border-stone-700 hover:border-stone-400 dark:hover:border-stone-600'}
        `}
      >
        {Icon && (
          <div className="pl-4 pr-1 text-stone-400 dark:text-stone-500 flex items-center">
            <Icon size={20} />
          </div>
        )}

        <div className="relative flex-1 py-3 px-4">
          {label && (
            <label
              htmlFor={inputId}
              className={`
                block text-[11px] font-black uppercase tracking-widest transition-all duration-150 select-none
                ${error 
                  ? 'text-red-500' 
                  : isFocused 
                    ? 'text-orange-600 dark:text-orange-400' 
                    : 'text-stone-500 dark:text-stone-400'}
              `}
            >
              {label} {required && <span className="text-red-500">*</span>}
            </label>
          )}

          <input
            id={inputId}
            type={type}
            value={value}
            onChange={onChange}
            disabled={disabled}
            placeholder={placeholder}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            className="w-full bg-transparent text-stone-900 dark:text-stone-100 text-sm font-semibold focus:outline-none placeholder:text-stone-400 dark:placeholder:text-stone-600"
            {...props}
          />
        </div>

        {SuffixIcon && (
          <div className="pr-4 pl-1 text-stone-400 dark:text-stone-500 flex items-center">
            <SuffixIcon size={20} />
          </div>
        )}
      </div>

      {(error || helperText) && (
        <p className={`text-xs font-medium px-2 ${error ? 'text-red-500 font-semibold' : 'text-stone-500 dark:text-stone-400'}`}>
          {error || helperText}
        </p>
      )}
    </div>
  );
};

export default M3TextField;
