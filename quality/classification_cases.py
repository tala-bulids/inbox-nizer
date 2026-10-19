"""Generic bilingual intent pairs. No real senders or private mailbox text."""
from .dataset import LABELS
# Dev examples are eligible for training. Test examples are never used for selection.
DEV = [
 ('Your colleague sent you a professional connection request. Connect with your network.', 'لديك طلب تواصل مهني من زميل. تابع أخبار شبكتك المهنية.'),
 ('Support ticket update: we are investigating the login failure you reported.', 'تحديث طلب الدعم الفني: نحقق في مشكلة تسجيل الدخول التي أبلغتنا عنها.'),
 ('You are invited to a community workshop next Saturday at the library.', 'ندعوك لحضور لقاء مجتمعي يوم السبت في المكتبة.'),
 ('Your electricity invoice is available. Amount due: 120. Please pay by the due date.', 'فاتورة الكهرباء متاحة. المبلغ المستحق 120. يرجى سداد الفاتورة.'),
 ('We have received your job application and will contact you after reviewing it.', 'استلمنا طلبك الوظيفي وسنتواصل معك بعد مراجعته.'),
 ('Weekly research digest: read this week’s selected science articles and commentary.', 'النشرة الأسبوعية: مقالات مختارة وتحليلات حول العلوم والتقنية.'),
 ('Hi cousin, how are you? We would love to see you at home this weekend.', 'مرحبا يا صديقي كيف حالك؟ اشتقنا لك ونود زيارتك هذا الأسبوع.'),
 ('Limited sale: save 40 percent on your next purchase. Shop our latest offers.', 'تخفيضات محدودة: وفر 40 بالمئة على مشترياتك القادمة وتسوق أحدث العروض.'),
 ('Reminder: your document submission is still pending. The deadline is tomorrow.', 'تذكير: لم ترسل المستند المطلوب بعد. آخر موعد غدا.'),
 ('Your flight reservation is confirmed. Departure and arrival information is attached.', 'تم تأكيد حجز رحلتك الجوية. تفاصيل المغادرة والوصول مرفقة.'),
]
FINAL = [
 ('A colleague endorsed your professional skills and sent you a networking invitation.', 'أضاف زميل توصية لمهاراتك المهنية وأرسل لك دعوة للتواصل.'),
 ('Your technical support case has been resolved. The reported software error is fixed.', 'تم حل بلاغ الدعم الفني الخاص بك وإصلاح العطل الذي أبلغت عنه.'),
 ('Invitation: join our public art exhibition opening on Tuesday evening.', 'دعوة: يسرنا حضوركم افتتاح معرض الفنون مساء الثلاثاء.'),
 ('Receipt: we received your rent payment of 900. Your outstanding balance is zero.', 'إيصال: استلمنا سداد الإيجار بمبلغ 900. لا يوجد رصيد مستحق.'),
 ('Thank you for interviewing for the analyst position. Unfortunately we selected another candidate.', 'شكرا لحضور مقابلة وظيفة المحلل. نعتذر فقد تم اختيار مرشح آخر.'),
 ('Monthly editorial bulletin: essays about technology policy and summaries of new research.', 'نشرة شهرية تحريرية: مقالات عن سياسات التقنية وملخصات الأبحاث الجديدة.'),
 ('Hey brother, I miss our chats. How is your family doing? Write back when you can.', 'يا أخي اشتقت لأحاديثنا. كيف حال العائلة؟ طمئني عليكم عندما تتفرغ.'),
 ('Buy a new laptop today and pay in installments. This discount expires soon.', 'اشتر حاسوبا جديدا اليوم وادفع بالتقسيط. ينتهي الخصم قريبا.'),
 ('Final reminder: the form you promised is overdue. Please send it before the cutoff.', 'تذكير أخير: تأخرت الاستمارة المطلوبة. أرسلها قبل انتهاء المهلة.'),
 ('Hotel booking confirmed: your room is reserved for three nights starting next Monday.', 'تم تأكيد حجز الفندق: غرفتك محجوزة لثلاث ليال بدءا من الاثنين القادم.'),
]
def examples(pairs):
    return [dict(text=text,labels=[LABELS[i]],language=language,id=f'{i}-{language}') for i,pair in enumerate(pairs) for language,text in zip(('en','ar'),pair)]
