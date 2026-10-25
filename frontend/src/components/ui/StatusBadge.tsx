import React from "react";

export type PriorityLevel =
  "high" | "medium" | "low" | "عالي" | "متوسط" | "عادي";

export interface PriorityBadgeProps {
  priority: PriorityLevel | string | undefined | null;
  language?: "ar" | "en";
  className?: string;
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({
  priority,
  language = "ar",
  className = "",
}) => {
  const norm = (priority || "").toLowerCase();
  const isHigh = norm === "high" || norm === "عالي";
  const isMedium = norm === "medium" || norm === "متوسط";

  const config = isHigh
    ? {
        bg: "bg-[#FBE8E4]",
        text: "text-[#B8422A]",
        border: "border-[#B8422A]",
        symbol: "!",
        enLabel: "High",
        arLabel: "عالية",
      }
    : isMedium
      ? {
          bg: "bg-[#FDF3DE]",
          text: "text-[#8A6318]",
          border: "border-[#C29D38]",
          symbol: "▲",
          enLabel: "Medium",
          arLabel: "متوسطة",
        }
      : {
          bg: "bg-[#EBF2EE]",
          text: "text-[#2D5A43]",
          border: "border-[#588157]",
          symbol: "•",
          enLabel: "Normal",
          arLabel: "منخفضة",
        };

  const label = language === "en" ? config.enLabel : config.arLabel;

  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 border text-[11px] font-mono-code font-semibold rounded-[2px] ${config.bg} ${config.text} ${config.border} ${className}`}
    >
      <span className="text-[10px]">{config.symbol}</span>
      <span>{label}</span>
    </span>
  );
};
