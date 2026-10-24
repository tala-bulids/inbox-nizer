import { LogOut, Globe } from "lucide-react";
export interface DesktopTopBarProps {
  language: "ar" | "en";
  onToggleLanguage: () => void;
  onLogout?: () => void;
  userEmail?: string;
}
export function DesktopTopBar({
  language,
  onToggleLanguage,
  onLogout,
  userEmail,
}: DesktopTopBarProps) {
  const en = language === "en";
  return (
    <header className="desktop-bar">
      <span className="desktop-brand" dir="ltr">
        <span aria-hidden="true">✉</span> inbox-nizer
      </span>
      <div className="desktop-actions">
        {userEmail && <bdi className="desktop-account">{userEmail}</bdi>}
        <button
          type="button"
          onClick={onToggleLanguage}
          aria-label={en ? "التبديل للعربية" : "Switch to English"}
        >
          <Globe size={16} aria-hidden="true" />
          <span lang={en ? "ar" : "en"}>{en ? "العربية" : "English"}</span>
        </button>
        {onLogout && (
          <button type="button" onClick={onLogout}>
            <LogOut size={16} aria-hidden="true" />
            <span>{en ? "Sign out" : "خروج"}</span>
          </button>
        )}
      </div>
    </header>
  );
}
