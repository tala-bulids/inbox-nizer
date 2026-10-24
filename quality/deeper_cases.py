"""New generic training contrasts and a frozen, separate final challenge."""
# None of these examples contains a mailbox transcript or a real sender.
TRAIN={
'Business':[
'Your professional profile appeared in searches this week. See who viewed your skills.',
'زملاؤك اطلعوا على ملفك المهني هذا الأسبوع وأرسل أحدهم طلب إضافة إلى شبكة علاقاتك.',
'A former coworker wants to connect professionally. They work in financial services.',
'دعوة تواصل من زميل يعمل في المحاسبة. يمكنك الاطلاع على خبراته المهنية.',
'Your network shared a discussion about salary negotiations and career development.',
'نشر أحد معارفك نقاشا عن الرواتب والتطور الوظيفي. تابع الحوار المهني.',
'People you may know: meet professionals with similar experience and exchange ideas.',
'أشخاص قد تعرفهم في مجالك المهني. وسع شبكة معارفك وتبادل الخبرات معهم.',
'A contact recommended your project management skills to their colleagues.',
'قام زميل بتزكية مهاراتك في إدارة المشاريع على ملفك المهني.',
'Your weekly professional profile analytics: twelve people viewed your profile.',
'إحصاءات الملف المهني: زار صفحتك عدد من المهنيين الباحثين عن خبرات مشابهة.',
'Please review the project budget draft with the team. No payment is requested.',
'يرجى مراجعة مسودة ميزانية المشروع مع الفريق. هذه مناقشة عمل وليست فاتورة.',
],
'Finance & Bills':[
'Your subscription renewal was charged to your card. Receipt and transaction details attached.',
'تم خصم رسوم تجديد الاشتراك من بطاقتك. الإيصال وتفاصيل المعاملة مرفقة.',
'Invoice overdue: the remaining balance for delivered services must be paid.',
'فاتورة متأخرة: يرجى سداد الرصيد المتبقي مقابل الخدمات المقدمة.',
'Your refund has been processed and will appear in your bank account.',
'تمت معالجة الاسترداد وسيظهر المبلغ في حسابك البنكي.',
'Monthly bank statement available: transactions, opening balance and closing balance.',
'كشف الحساب البنكي الشهري جاهز ويتضمن العمليات والرصيد الافتتاحي والختامي.',
'Payment confirmation for your order. Amount paid and tax are listed on the receipt.',
'تأكيد الدفع لطلبك. يتضمن الإيصال المبلغ المدفوع والضريبة.',
],
'Promotions':[
'Unlock a discount on premium membership. Upgrade today and save on the annual price.',
'احصل على خصم للاشتراك المميز. قم بالترقية اليوم ووفر من السعر السنوي.',
'Get cashback when you buy selected products. Browse our weekend sale.',
'استرد جزءا من قيمة مشترياتك عند شراء منتجات مختارة. تصفح عروض نهاية الأسبوع.',
'Exclusive sale for members: buy a jacket and receive a second one free.',
'عرض حصري للأعضاء: اشتر سترة واحصل على الثانية مجانا.',
'Try our paid course with a special introductory price and a coupon.',
'جرب دورتنا المدفوعة بسعر افتتاحي خاص ورمز خصم.',
],
'Job Application':[
'Following your interview, we would like to offer you the engineering position.',
'بعد المقابلة نرغب في تقديم عرض وظيفي لك لوظيفة مهندس.',
'Your application for the internship was unsuccessful this time.',
'نعتذر عن عدم قبول طلبك للتدريب في هذه المرحلة.',
'Please complete the assessment for the position you applied for.',
'يرجى إكمال التقييم الخاص بالوظيفة التي تقدمت إليها.',
'We shortlisted your application. Please select an interview appointment.',
'تم إدراج طلبك ضمن القائمة المختصرة. يرجى اختيار موعد المقابلة.',
],
'Newsletters':[
'This edition examines banking regulation and summarizes economic research. Read the editorial.',
'يتناول هذا العدد تنظيم البنوك ويلخص أبحاث الاقتصاد. اقرأ المقال الافتتاحي.',
'A curated digest of professional advice, industry analysis and interviews. Weekly edition.',
'ملخص تحريري أسبوعي لنصائح مهنية وتحليلات القطاع ومقابلات مختارة.',
'Our monthly reading list covers personal finance and investment education, with no offers.',
'قائمة القراءة الشهرية عن التمويل الشخصي والتثقيف الاستثماري مع مقالات مختارة.',
],
'Personal':[
'Hi friend, thanks for paying for lunch yesterday! I will see you at home tonight.',
'يا صديقي شكرا على عزيمة الغداء أمس. أراك في المنزل الليلة.',
'Mom, I transferred the money for our family gift. Hope you like it.',
'يا أمي حولت مبلغ هدية العائلة. أتمنى أن تعجبك.',
],
'Reminders':[
'Reminder: you still need to finish the form before the deadline.',
'تذكير: لا تزال الاستمارة غير مكتملة ويرجى إنهاؤها قبل الموعد النهائي.',
'Don’t forget your appointment tomorrow. This is your scheduled reminder.',
'لا تنس موعدك غدا. هذا تذكير بالموعد المسجل مسبقا.',
],
'Events & Invitations':[
'You are invited to the annual industry forum. Venue and program are attached.',
'ندعوك لحضور الملتقى السنوي للقطاع. موقع اللقاء والبرنامج مرفقان.',
'Join our community discussion at the town hall next month. Attendance is open.',
'شارك في النقاش المجتمعي في قاعة المدينة الشهر القادم. الحضور متاح.',
],
'Customer Support':[
'We received your complaint about the damaged package. A support agent will investigate.',
'استلمنا شكواك بخصوص الطرد التالف وسيتولى موظف الدعم التحقيق.',
'Your password recovery support request has been resolved.',
'تم حل طلب الدعم المتعلق باستعادة كلمة المرور.',
],
'Travel & Bookings':[
'Your itinerary is updated. The connecting flight and reserved hotel remain confirmed.',
'تم تحديث خط سير سفرك. الرحلة المتصلة وحجز الفندق لا يزالان مؤكدين.',
'Boarding information for your reserved flight. Check in before departure.',
'معلومات الصعود لرحلتك المحجوزة. أكمل إجراءات السفر قبل المغادرة.',
]}
# New final texts: never used for training or candidate selection.
HOLDOUT={
'Business':[
'A banking analyst in your professional community wants to add you as a connection.',
'محلل مصرفي من مجتمعك المهني يرغب في إضافتك إلى قائمة معارفه.',
'Your professional profile got an endorsement for accounting expertise from a former manager.',
'تلقيت تزكية لخبراتك المحاسبية على صفحتك المهنية من مدير سابق.',
],
'Finance & Bills':[
'We charged the monthly hosting fee. Download the tax receipt for this transaction.',
'خصمنا رسوم الاستضافة الشهرية. إيصال الضريبة لهذه المعاملة متاح.',
'Your loan installment remains unpaid. The outstanding amount is shown on your statement.',
'لم تسدد قسط القرض بعد. يظهر المبلغ المستحق في كشف حسابك.',
],
'Promotions':[
'Celebrate with discounted phones. Split the purchase price into four easy payments.',
'احتفل معنا بخصومات الهواتف وقسم سعر الشراء على أربع دفعات ميسرة.',
'Become a premium subscriber for half the usual price during this seasonal offer.',
'اشترك في الباقة المميزة بنصف السعر المعتاد خلال العرض الموسمي.',
],
'Job Application':[
'We regret that your candidacy for the design vacancy will not progress after assessment.',
'نأسف لعدم متابعة ترشيحك لشاغر التصميم بعد التقييم.',
'The recruitment panel approved your candidacy. Your employment offer is attached.',
'وافقت لجنة التوظيف على ترشيحك. عرض العمل مرفق بهذه الرسالة.',
],
'Newsletters':[
'In this issue: a journalist explains consumer debt trends and reviews three recent books.',
'في هذا العدد يشرح الكاتب اتجاهات ديون المستهلكين ويراجع ثلاثة كتب صدرت حديثا.',
'Editor’s picks for this month: career essays and a long interview with a researcher.',
'اختيارات المحرر لهذا الشهر: مقالات مهنية وحوار مطول مع باحث.',
],
'Personal':[
'Hello uncle, I hope your journey home went well. The children send their love.',
'مرحبا يا عمي أتمنى أن تكون رحلتك للمنزل مريحة. الأطفال يرسلون محبتهم.',
'Thanks for lending me the cash last night, cousin. Let us catch up this evening.',
'شكرا على إقراضي المبلغ البارحة يا ابن عمي. لنجلس معا هذا المساء.',
],
'Reminders':[
'A quick reminder that your scheduled visit is tomorrow morning. Please don’t forget.',
'تذكير سريع بأن زيارتك المجدولة غدا صباحا. نرجو ألا تنساها.',
'You have not finished the required survey. This is a reminder before submissions close.',
'لم تكمل الاستبيان المطلوب. نذكرك به قبل إغلاق الاستجابات.',
],
'Events & Invitations':[
'The museum invites you to a free public lecture in the main auditorium next Thursday.',
'يدعوك المتحف إلى محاضرة عامة مجانية في المسرح الرئيسي يوم الخميس القادم.',
'Invitation to our local volunteers gathering: share ideas at the community center.',
'دعوة للقاء المتطوعين المحليين لتبادل الأفكار في المركز المجتمعي.',
],
'Customer Support':[
'An agent has reviewed the crash logs you provided. Here are steps to resolve your ticket.',
'راجع الموظف سجلات العطل التي أرسلتها. إليك خطوات معالجة بلاغ الدعم.',
'Your complaint about the missing item has been escalated to the service team.',
'تم تصعيد شكواك بشأن القطعة المفقودة إلى فريق خدمة العملاء.',
],
'Travel & Bookings':[
'Your train seats are reserved. Attached are the tickets and station departure details.',
'تم حجز مقاعد القطار. التذاكر وتفاصيل محطة المغادرة مرفقة.',
'The airline confirmed a change to your return journey. Please review the revised itinerary.',
'أكدت شركة الطيران تغييرا في رحلة عودتك. راجع خط السير المعدل.',
]}

def rows(data):
    return [dict(text=text,labels=[label],id=f'{label}-{i}') for label,texts in data.items() for i,text in enumerate(texts)]
