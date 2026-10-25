import React from "react";
import { Link } from "react-router-dom";
import { Mail, ArrowLeft, ArrowRight, Calendar, User } from "lucide-react";

export interface SourceCardProps {
  emailId: string | number;
  subject: string;
  sender?: string;
  date?: string;
  excerpt?: string;
  language?: "ar" | "en";
  className?: string;
}

export const SourceCard: React.FC<SourceCardProps> = ({
  emailId,
  subject,
  sender,
  date,
  excerpt,
  language = "ar",
  className = "",
}) => {
  const isEn = language === "en";

  return (
    <div
      className={`border-[1.5px] border-[#241E18] bg-[#FAF6EE] p-3 rounded-[4px] shadow-[2px_2px_0px_#241E18] flex flex-col gap-2 ${className}`}
    >
      <div className="flex items-start justify-between gap-3 border-b border-[#241E18]/15 pb-2">
        <div className="flex items-center gap-2 text-xs font-mono-code text-[#241E18]/80 min-w-0 flex-1">
          <Mail className="w-3.5 h-3.5 text-[#E07A5F] shrink-0" />
          <span className="font-semibold text-[#241E18] truncate" dir="auto">
            {subject}
          </span>
        </div>
        <Link className="button" to={`/email/${emailId}`}>
          <span>{isEn ? "View Email" : "عرض الرسالة"}</span>
          {isEn ? (
            <ArrowRight className="w-3 h-3" />
          ) : (
            <ArrowLeft className="w-3 h-3" />
          )}
        </Link>
      </div>

      {excerpt && (
        <div
          className={`text-xs text-[#241E18]/90 leading-relaxed bg-[#FFFDF9] border border-[#241E18]/15 p-2.5 rounded-[3px] ${isEn ? "font-mono-code" : "font-arabic"}`}
          dir="auto"
        >
          "{excerpt}"
        </div>
      )}

      <div className="flex items-center justify-between text-[11px] font-mono-code text-[#241E18]/65 pt-0.5">
        {sender && (
          <div className="flex items-center gap-1.5 truncate">
            <User className="w-3 h-3 text-[#241E18]/50 shrink-0" />
            <span className="truncate" dir="auto">
              {sender}
            </span>
          </div>
        )}
        {date && (
          <div className="flex items-center gap-1.5 shrink-0">
            <Calendar className="w-3 h-3 text-[#241E18]/50 shrink-0" />
            <span dir="ltr">{date}</span>
          </div>
        )}
      </div>
    </div>
  );
};
