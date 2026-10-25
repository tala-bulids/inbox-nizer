import React, { useId } from "react";

export interface RetroInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const RetroInput: React.FC<RetroInputProps> = ({
  label,
  helperText,
  error,
  icon,
  className = "",
  id,
  ...props
}) => {
  const generated = useId();
  const inputId = id || generated;
  const hintId = inputId + "-hint";
  return (
    <div className="flex flex-col gap-1 w-full text-start">
      {label && (
        <label
          htmlFor={inputId}
          className="text-xs font-mono-code font-semibold text-[#241E18]"
        >
          {label}
        </label>
      )}
      <div className="relative flex items-center w-full">
        {icon && (
          <div className="absolute right-3 rtl:right-3 ltr:right-auto ltr:left-3 text-[#241E18]/60 pointer-events-none shrink-0 flex items-center">
            {icon}
          </div>
        )}
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error || helperText ? hintId : undefined}
          className={`w-full bg-[#FAF6EE] text-[#241E18] border-[1.5px] border-[#241E18] rounded-[3px] py-1.5 text-xs md:text-sm font-arabic placeholder:text-[#241E18]/40 focus:outline-none focus:bg-[#FFFDF9] focus:ring-1 focus:ring-[#241E18] focus:border-[#241E18] shadow-[inset_1px_1px_2px_rgba(36,30,24,0.1)] transition-colors ${
            icon ? "pr-9 pl-3 rtl:pr-9 rtl:pl-3 ltr:pl-9 ltr:pr-3" : "px-3"
          } ${error ? "border-[#E07A5F] bg-[#FDF2EE]" : ""} ${className}`}
          {...props}
        />
      </div>
      {helperText && !error && (
        <span
          id={hintId}
          className="text-[11px] font-mono-code text-[#241E18]/60"
        >
          {helperText}
        </span>
      )}
      {error && (
        <span
          id={hintId}
          className="text-[11px] font-mono-code text-[#93432d] font-medium"
        >
          {error}
        </span>
      )}
    </div>
  );
};
