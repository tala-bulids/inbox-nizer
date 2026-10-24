import type { ReactNode } from "react";
import { useLocale } from "../../app/locale";
export interface RetroWindowProps {
  title: string;
  icon?: ReactNode;
  subtitle?: string;
  toolbar?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  onClose?: () => void;
  onMaximize?: () => void;
  onMinimize?: () => void;
  titleBarColor?: string;
}
export function RetroWindow({
  title,
  icon,
  subtitle,
  toolbar,
  footer,
  children,
  className = "",
  bodyClassName = "",
  onClose,
  onMaximize,
  onMinimize,
  titleBarColor = "",
}: RetroWindowProps) {
  const { t } = useLocale();
  const controls = [
    { action: onClose, label: t("إغلاق النافذة", "Close window"), symbol: "×" },
    {
      action: onMinimize,
      label: t("تصغير النافذة", "Minimize window"),
      symbol: "−",
    },
    {
      action: onMaximize,
      label: t("تكبير النافذة", "Maximize window"),
      symbol: "□",
    },
  ];
  return (
    <div className={"retro-window " + className}>
      <div className={"retro-titlebar " + titleBarColor}>
        <span className="window-mark" aria-hidden="true" />
        <div className="window-title">
          {icon && <span aria-hidden="true">{icon}</span>}
          <span>{title}</span>
        </div>
        {subtitle && (
          <span className="window-subtitle" dir="auto">
            {subtitle}
          </span>
        )}
        {controls
          .filter((c) => c.action)
          .map((c) => (
            <button
              key={c.label}
              type="button"
              onClick={c.action}
              aria-label={c.label}
            >
              {c.symbol}
            </button>
          ))}
      </div>
      {toolbar && <div className="retro-toolbar">{toolbar}</div>}
      <div className={"retro-window-body " + bodyClassName}>{children}</div>
      {footer && <div className="retro-footer">{footer}</div>}
    </div>
  );
}
