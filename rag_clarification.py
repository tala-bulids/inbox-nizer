"""Application-owned, bounded disambiguation metadata."""
import re
from sqlalchemy import select
from models import Email


def clarification(db, question, email_ids, selected_email_id=None):
    ids=list(dict.fromkeys(email_ids))[:64]
    rows=db.execute(select(Email.id,Email.subject,Email.email_date).where(Email.id.in_(ids))
                    .order_by(Email.id).limit(5)).all() if ids else []
    def plain(value,size):
        return re.sub(r'[\x00-\x1f<>\[\]]',' ',value or '').strip()[:size]
    options=[dict(email_id=row.id,subject=plain(row.subject,180),date=plain(row.email_date,100)) for row in rows]
    answer=('وجدت أكثر من إجابة محتملة. أي طلب أو حدث تقصد؟ حدّد البريد أو أضف اسم الجهة والموعد.'
            if re.search(r'[\u0600-\u06ff]',question) else
            'I found multiple possible answers. Which application or event do you mean? Select an email or specify its organization and date.')
    if selected_email_id is not None:
        # Selecting an email cannot distinguish two records inside that email.
        # Do not offer the same button again and trap the user in a click loop.
        options = []
        answer = ('ما زالت الإجابة غير محددة في البريد الذي اخترته. أضف الوجهة أو اسم الجهة أو التاريخ إلى سؤالك.'
                  if re.search(r'[\u0600-\u06ff]', question) else
                  'I still cannot identify one answer in the selected email. Add a destination, organization, or date to your question.')
    return dict(answer=answer,sources=[],citations=[],status='needs_clarification',clarification_options=options)
