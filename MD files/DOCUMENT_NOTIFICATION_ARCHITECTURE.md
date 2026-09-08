# Document & Notification Architecture — Phase 32

## ADR: چرا Document Model موجود Extend شد، نه بازسازی؟
`apps.documents.Document` (فاز ۱۶) قبلاً برای پیوست سند به Member/EmploymentAssignment
طراحی شده بود. بازسازی کامل آن Regression گسترده در فاز‌های ۱۶ ایجاد می‌کرد. به‌جای
آن، فیلدهای جدید (visibility, status, scope, checksum, ...) بدون تغییر رفتار قدیمی
اضافه شدند. `apps.public_content.PublicDocument` (فاز ۲۵) دست‌نخورده ماند چون مفهوم
متفاوتی (سند رسمی سایت عمومی) را نمایندگی می‌کند.

## ADR: چرا Secure Storage جداگانه (S3/Private Bucket) پیاده نشد؟
معماری فعلی پروژه از Local FileSystem Storage استفاده می‌کند (بدون Cloud Storage).
امنیت از طریق **Controlled Download View** (`documents_mgmt:download`) تأمین شد —
نه با تغییر Storage Backend — چون هیچ URL مستقیم عمومی به `MEDIA_URL` برای این
اسناد در `config/urls.py` expose نشده است.

## ADR: چگونه Authorization روی Document اعمال شد؟
یک Resolver جدید (`document_health_houses`, `scope_document_queryset`) در Registry
مرکزی موجود (`apps.authorization.registry`) ثبت شد — دقیقاً با همان الگوی
Committee/RoleAssignment در فازهای قبل. **هیچ Authorization Engine دومی ساخته نشد.**

## Document Visibility vs Status
دو مفهوم کاملاً مستقل (طبق بخش ۵ سند):
- `visibility`: PRIVATE / INTERNAL / RESTRICTED / PUBLIC — **چه کسانی** مجازند ببینند.
- `status`: DRAFT / REVIEW / APPROVED / PUBLISHED / ARCHIVED — **در چه مرحله**‌ای از
  چرخه‌ی انتشار قرار دارد.
یک سند فقط وقتی واقعاً Public است که `status=PUBLISHED` **و** `visibility=PUBLIC`
هر دو با هم برقرار باشند.

## Security Threat Model (بخش ۸۷ سند)
| تهدید | کنترل |
|---|---|
| IDOR | `Authorization.can()` روی هر Document/Notification در View — تست‌شده |
| Path Traversal | Django Storage به‌صورت پیش‌فرض sanitize می‌کند — تست‌شده |
| Malicious Upload | `validate_document_file()`: extension + MIME + حجم |
| MIME Spoofing | بررسی content_type ارسالی؛ **محدودیت شناخته‌شده**: بدون کتابخانه‌ی Magic Bytes، جعل کامل ممکن است (Technical Debt) |
| Stored XSS | عنوان/توضیحات سند Plain Text؛ هیچ‌جا `\|safe` بدون Sanitization استفاده نشد |
| Information Disclosure | Public Selector فقط `PUBLISHED+PUBLIC` را برمی‌گرداند |
| Notification Enumeration | مالکیت مستقیماً از `request.user` چک می‌شود، نه از URL |

## Notification Targeting
`notify_users_in_scope()` به‌عنوان Extension Point آماده است، ولی **در هیچ نقطه‌ای
خودکار صدا زده نمی‌شود** — چون سند فاز ۳۲ به‌صراحت گفته «Audience را حدس نزن» و
هیچ Business Rule مشخصی برای «سند منتشرشده باید به چه کسانی اطلاع بدهد» وجود ندارد.

## Known Issues
هیچ‌کدام.

## Technical Debt
- تشخیص واقعی نوع فایل (Magic Bytes) پیاده نشد — نیاز به کتابخانه‌ی خارجی (`python-magic`)
  دارد که طبق اصل «dependency غیرضروری اضافه نکن» از این فاز خارج ماند.
- `scope_document_queryset` با Python-side iteration (نه Query دیتابیسی) پیاده شده —
  همان الگوی شناخته‌شده‌ی Committee/RoleAssignment.
- Document → Notification Integration خودکار پیاده نشد (طبق تصمیم آگاهانه‌ی بالا).
- Versioning سند (نسخه‌های متعدد یک سند) فقط با فیلد `version` (عدد صحیح) آماده
  شده؛ مکانیزم واقعی «نسخه‌ی جدید = رکورد جدید مرتبط با نسخه‌ی قبلی» در این فاز
  پیاده نشد چون Business Rule مشخصی برایش وجود نداشت.

## Technical Debt از فاز ۳۱ (طبق بخش ۸۵ سند، فقط گزارش، بدون اصلاح در این فاز)
- Constraintهای یکتایی سمت‌های هیئت‌مدیره هنوز مستقل از `Board` (دوره) هستند.
- صفحه‌ی عمومی هیئت‌مدیره هنوز بر اساس دوره فیلتر نمی‌کند.