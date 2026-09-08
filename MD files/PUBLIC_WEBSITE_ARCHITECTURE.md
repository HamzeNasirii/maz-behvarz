# Public Website Architecture — Phase 25

## Sitemap
/ خانه
/about/, /about/history/, /about/mission/, /about/objectives/
/about/organizational-structure/ (از apps.organization واقعی)
/news/, /news/<slug>/
/announcements/, /announcements/<slug>/
/events/, /events/<slug>/
/board/ (از apps.board.BoardMembership، فیلتر is_public_visible)
/committees/ (از apps.committees.Committee، فیلتر is_public_visible)
/documents/ (PublicDocument — مستقل از apps.documents.Document)
/regulations/, /regulations/<slug>/
/faq/
/contact/ (apps.website — فرم قدیمی موجود)
/contact-us/ (apps.public_content — فرم جدید طبق این فاز)
/search/
/privacy/, /terms/
/sitemap.xml, /robots.txt

## Content Models
اپ `apps.public_content`: HeroSlide, Announcement, NewsArticle/NewsCategory, Event,
PublicDocument/DocumentCategory, Regulation, FAQ/FAQCategory, ContactMessage.

## Publishing Workflow
`ContentStatus`: DRAFT → REVIEW → PUBLISHED → ARCHIVED (+ SCHEDULED برای انتشار آینده‌نگر).
انتشار آینده‌نگرانه: `published_at > now` یعنی هنوز عمومی نیست، حتی اگر status=PUBLISHED باشد.
این قاعده در Selectors (`published()` در `managers.py`) اجرا می‌شود، نه در Template یا View.

## Public Visibility Rules
- `PublicDocument`: نیاز به `is_public=True AND is_published=True` هر دو با هم.
- `BoardMembership`/`Committee`/`CommitteeMembership`: `is_public_visible=True` (پیش‌فرض False).
- `Announcement`: `is_published=True` و `publish_at <= now`.

## SEO
- `sitemap.xml` از طریق `django.contrib.sitemaps` — فقط محتوای منتشرشده + صفحات ایستای عمومی.
- `robots.txt` مسیرهای `/admin/`, `/portal/`, `/login/`, `/api/` را Disallow می‌کند.
- هر صفحه‌ی Detail (News/Event/Announcement/Regulation) بلاک‌های `title`,
  `meta_description`, `og_title`, `og_description` را Override می‌کند.

## Search
پیاده‌سازی فعلی: `icontains` ساده روی News/Announcement/Event/Document/FAQ.
طراحی برای ارتقا به PostgreSQL Full Text Search: چون همه‌ی جستجوها از طریق
`selectors.py` عبور می‌کنند، جایگزینی `icontains` با `SearchVector` در آینده فقط
همان‌جا لازم است، نه در Viewها.

## Media Handling
تصاویر (`HeroSlide.image`, `NewsArticle.featured_image`, `Event.image`) از `ImageField`
با اعتبارسنجی خودکار جنگو/Pillow استفاده می‌کنند. اندازه‌ی فایل حداکثر توسط
`DATA_UPLOAD_MAX_MEMORY_SIZE` (۵ مگابایت، از گام ۲۰) محدود شده است.

## Security
- CSRF روی تمام فرم‌ها (Contact) فعال.
- محتوای متنی (news/announcement/regulation) با `|linebreaks` رندر می‌شود، نه `|safe` —
  از تزریق HTML خام جلوگیری می‌کند. اگر بعداً Rich Text Editor اضافه شود، باید یک
  کتابخانه‌ی Sanitize (مثل bleach) قبل از هر `|safe` اضافه شود.
- اسناد Private (`is_public=False`) هرگز در Selector عمومی برنمی‌گردند، نه فقط با
  مخفی‌کردن لینک.

## Caching Strategy (آماده برای آینده)
Home/News List کاندیدای Cache هستند؛ چون تمام قواعد نمایش در Selector متمرکز است،
اضافه‌کردن `@cache_page` روی این Viewها در آینده امن است — فقط باید مطمئن شد Cache
Invalidation بعد از هر Publish/Unpublish هم اجرا می‌شود (در این فاز هنوز Cache واقعی
فعال نشده).
