import { useState, useEffect, Suspense } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Inbox,
  Search,
  Sparkles,
  ListChecks,
  Settings,
  Menu,
  X,
} from "lucide-react";
import { useSignOut } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { Loading } from "../shared/States";
import { DesktopTopBar } from "../ui/DesktopTopBar";

export function Shell() {
  const logout = useSignOut();
  const { t, toggle, language } = useLocale();
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    document.getElementById("main")?.focus();
  }, [location.pathname]);

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
          <Icon size={18} aria-hidden="true" />
          <span>{t(ar, en)}</span>
        </NavLink>
      ))}
    </nav>
  );

  const title = items.find((item) => item.path === location.pathname);

  return (
    <div className="min-h-screen flex flex-col bg-[#F5F0E6] text-[#241E18]">
      <DesktopTopBar
        language={language === "en" ? "en" : "ar"}
        onToggleLanguage={toggle}
        onLogout={logout}
      />
      <div className="app-shell flex-1">
        <a className="skip-link" href="#main">
          {t("انتقل إلى المحتوى", "Skip to content")}
        </a>
        <aside className="sidebar">
          {nav}
          <div className="sidebar-foot">
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2 h-2 rounded-[1px] bg-[#81B29A] border border-[#241E18] block" />
              <span className="font-mono-code text-xs font-semibold">
                {t("مساحة عمل خاصة", "Private workspace")}
              </span>
            </div>
            <p className="text-xs text-[#241E18]/60 font-arabic">
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
                    className="drawer bg-[#EFE7D8] border-2 border-[#241E18] shadow-[4px_4px_0px_#241E18]"
                    dir={language === "ar" ? "rtl" : "ltr"}
                  >
                    <div className="flex items-center justify-between border-b border-[#241E18]/20 pb-3 mb-4">
                      <Dialog.Title className="font-bold text-base">
                        Inbox+nizer
                      </Dialog.Title>
                      <Dialog.Close asChild>
                        <button
                          aria-label={t("إغلاق القائمة", "Close menu")}
                          className="w-7 h-7 rounded-[2px] border border-[#241E18] bg-[#FAF6EE] flex items-center justify-center"
                        >
                          <X size={16} />
                        </button>
                      </Dialog.Close>
                    </div>
                    <Dialog.Description className="sr-only">
                      {t("انتقل بين أدوات البريد", "Navigate your inbox tools")}
                    </Dialog.Description>
                    {nav}
                  </Dialog.Content>
                </Dialog.Portal>
              </Dialog.Root>
            </div>
            <span className="breadcrumb">
              {t("مساحة العمل", "Workspace")}
              <span>/</span>
              {title
                ? t(title.ar, title.en)
                : location.pathname.startsWith("/email/")
                  ? t("تفاصيل البريد", "Email detail")
                  : t("صفحة غير موجودة", "Page not found")}
            </span>
          </header>
          <main id="main" className="main-content" tabIndex={-1}>
            <Suspense fallback={<Loading />}>
              <Outlet />
            </Suspense>
          </main>
          <footer className="workspace-footer">
            {t(
              "المحتوى الأصلي · المعلومات المستخرجة · النص المولّد — لكلٍّ سياقه",
              "Original content · extracted information · generated prose — clearly separated",
            )}
          </footer>
        </div>
      </div>
    </div>
  );
}
