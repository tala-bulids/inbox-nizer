import { useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Inbox,
  Search,
  Sparkles,
  ListChecks,
  Settings,
  Menu,
  X,
  LogOut,
  Languages,
} from "lucide-react";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
export function Shell() {
  const { logout } = useAuth();
  const { t, toggle, language } = useLocale();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const items = [
    { path: "/", ar: "البريد الوارد", en: "Inbox", icon: Inbox },
    { path: "/search", ar: "البحث", en: "Search", icon: Search },
    { path: "/ask", ar: "اسأل البريد", en: "Ask AI", icon: Sparkles },
    { path: "/tasks", ar: "المهام", en: "Tasks", icon: ListChecks },
    { path: "/settings", ar: "الإعدادات", en: "Settings", icon: Settings },
  ];
  const nav = (
    <nav aria-label={t("التنقل الرئيسي", "Main navigation")}>
      {items.map(({ path, ar, en, icon: Icon }) => (
        <NavLink
          end={path === "/"}
          to={path}
          key={path}
          onClick={() => setOpen(false)}
        >
          <Icon size={19} aria-hidden="true" />
          {t(ar, en)}
        </NavLink>
      ))}
    </nav>
  );
  const title = items.find((item) => item.path === location.pathname);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        {t("انتقل إلى المحتوى", "Skip to content")}
      </a>
      <aside className="sidebar">
        <Link className="brand" to="/">
          <span className="brand-mark">✦</span>
          <span>
            {t("البريد الذكي", "Smart Inbox")}
            <small>AI SMART INBOX</small>
          </span>
        </Link>
        {nav}
        <div className="sidebar-foot">
          <span className="status-dot" />
          {t("مساحة عمل خاصة", "Private workspace")}
          <p>
            {t(
              "بريدك أولًا. الذكاء الاصطناعي للمساعدة.",
              "Your email first. AI to assist.",
            )}
          </p>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="mobile-menu">
            <Dialog.Root open={open} onOpenChange={setOpen}>
              <Dialog.Trigger asChild>
                <button aria-label={t("فتح القائمة", "Open menu")}>
                  <Menu size={20} />
                </button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="dialog-overlay" />
                <Dialog.Content
                  className="drawer"
                  dir={language === "ar" ? "rtl" : "ltr"}
                >
                  <Dialog.Title>
                    {t("البريد الذكي", "Smart Inbox")}
                  </Dialog.Title>
                  <Dialog.Description>
                    {t("انتقل بين أدوات البريد", "Navigate your inbox tools")}
                  </Dialog.Description>
                  {nav}
                  <Dialog.Close asChild>
                    <button aria-label={t("إغلاق القائمة", "Close menu")}>
                      <X size={18} />
                    </button>
                  </Dialog.Close>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
          </div>
          <span className="breadcrumb">
            {t("مساحة العمل", "Workspace")}
            <span>/</span>
            {title ? t(title.ar, title.en) : t("تفاصيل البريد", "Email detail")}
          </span>
          <div className="topbar-actions">
            <button
              onClick={toggle}
              aria-label={t("Switch to English", "التبديل للعربية")}
            >
              <Languages size={17} />
              <span>{language === "ar" ? "English" : "العربية"}</span>
            </button>
            <button onClick={logout}>
              <LogOut size={17} />
              <span>{t("خروج", "Sign out")}</span>
            </button>
          </div>
        </header>
        <main id="main" className="main-content" tabIndex={-1}>
          <Outlet />
        </main>
        <footer className="workspace-footer">
          {t(
            "المحتوى الأصلي · المعلومات المستخرجة · النص المولّد — لكلٍّ سياقه",
            "Original content · extracted information · generated prose — clearly separated",
          )}
        </footer>
      </div>
    </div>
  );
}
