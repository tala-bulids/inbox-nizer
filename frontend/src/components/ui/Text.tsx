import type { ReactNode } from "react";
export function Identifier({ children }: { children: ReactNode }) {
  return <bdi dir="ltr">{children}</bdi>;
}
export function ContentText({ children }: { children: ReactNode }) {
  return (
    <div dir="auto" className="content-text">
      {children}
    </div>
  );
}
