const arabicLabels: Record<string, string> = {
  Business: "أعمال",
  "Customer Support": "دعم العملاء",
  "Events & Invitations": "فعاليات ودعوات",
  "Finance & Bills": "مالية وفواتير",
  "Job Application": "طلبات التوظيف",
  Newsletters: "نشرات بريدية",
  Personal: "شخصي",
  Promotions: "عروض",
  Reminders: "تذكيرات",
  "Travel & Bookings": "سفر وحجوزات",
};

export function categoryLabel(category: string, language: string): string {
  return language === "ar" ? arabicLabels[category] || category : category;
}
