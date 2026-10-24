import React from "react";

export interface RetroButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
    | "primary"
    | "secondary"
    | "mustard"
    | "sage"
    | "danger"
    | "ghost"
    | "active";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
  children: React.ReactNode;
}

export const RetroButton: React.FC<RetroButtonProps> = ({
  variant = "secondary",
  size = "md",
  icon,
  children,
  className = "",
  disabled,
  ...props
}) => {
  const baseClasses =
    "inline-flex items-center justify-center font-mono-code font-medium tracking-tight select-none transition-all duration-75 text-center whitespace-nowrap shrink-0 disabled:opacity-50 disabled:pointer-events-none cursor-pointer";

  const sizeClasses = {
    sm: "text-xs px-2.5 py-1 gap-1.5 rounded-[3px]",
    md: "text-xs md:text-sm px-3.5 py-1.5 gap-2 rounded-[4px]",
    lg: "text-sm md:text-base px-5 py-2.5 gap-2.5 rounded-[5px]",
  }[size];

  const variantClasses = {
    primary:
      "bg-[#E07A5F] text-[#241E18] border-[1.5px] border-[#241E18] shadow-[2px_2px_0px_#241E18] hover:bg-[#D46B50] active:translate-x-[1.5px] active:translate-y-[1.5px] active:shadow-none",
    secondary:
      "bg-[#FAF6EE] text-[#241E18] border-[1.5px] border-[#241E18] shadow-[2px_2px_0px_#241E18] hover:bg-[#F2ECE0] active:translate-x-[1.5px] active:translate-y-[1.5px] active:shadow-none",
    mustard:
      "bg-[#E9C46A] text-[#241E18] border-[1.5px] border-[#241E18] shadow-[2px_2px_0px_#241E18] hover:bg-[#DEC25D] active:translate-x-[1.5px] active:translate-y-[1.5px] active:shadow-none",
    sage: "bg-[#81B29A] text-[#193225] border-[1.5px] border-[#241E18] shadow-[2px_2px_0px_#241E18] hover:bg-[#74A58D] active:translate-x-[1.5px] active:translate-y-[1.5px] active:shadow-none",
    danger:
      "bg-[#E76F51] text-[#241E18] border-[1.5px] border-[#241E18] shadow-[2px_2px_0px_#241E18] hover:bg-[#D85D3E] active:translate-x-[1.5px] active:translate-y-[1.5px] active:shadow-none",
    ghost:
      "bg-transparent text-[#241E18] border border-transparent hover:bg-[#EDE6D6]/70 active:bg-[#E2D8C3]",
    active:
      "bg-[#241E18] text-[#FFFDF9] border-[1.5px] border-[#241E18] shadow-none translate-x-[1px] translate-y-[1px]",
  }[variant];

  return (
    <button
      className={`${baseClasses} ${sizeClasses} ${variantClasses} ${className}`}
      disabled={disabled}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </button>
  );
};
