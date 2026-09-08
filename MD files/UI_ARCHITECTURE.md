# UI Architecture — Behvarzan Site (Phase 24)

## Design System
رنگ اصلی برند (`--color-primary: #14532d`) از تصمیم قبلی پروژه (main.css اولیه) استخراج شده،
نه حدسی. تمام Design Tokens در `static/css/tokens.css`.

## Template Hierarchy

templates/base/base.html ← اسکلت مشترک (html, head, static links)
templates/base/public.html ← Layout سایت عمومی (Navbar + Footer)
templates/base/auth.html ← Layout صفحات ورود (بدون Navbar/Sidebar)
templates/base/dashboard.html ← Layout پنل با Sidebar + Topbar

مسیرهای View موجود (`website/home.html`, `members/portal_dashboard.html`, ...) عمداً
دست‌نخورده مانده‌اند تا هیچ Viewی نیاز به تغییر نداشته باشد؛ فقط `{% extends %}`
داخل این فایل‌ها به Layout جدید اشاره می‌کند.

## Component Architecture
Componentها (`templates/components/*.html`) صرفاً نمایشی‌اند و با `{% include %}` استفاده
می‌شوند — هیچ Query یا منطق Authorization داخلشان نیست. `navbar.html` فقط بر اساس
`user.is_authenticated`/`user.is_staff` منو را عوض می‌کند (UX، نه Authorization —
Backend همچنان هر دسترسی را enforce می‌کند).

## Naming Conventions
کلاس‌های CSS با BEM-lite: `.block__element`, `.block--modifier` (مثلاً `.dashboard__sidebar`,
`.btn-primary`).

## CSS Architecture
static/css/tokens.css ← رنگ، فونت، فاصله، شعاع، سایه
static/css/base.css ← Reset + typography پایه
static/css/layout.css ← Public/Dashboard layout
static/css/components.css ← Card, Button, Alert, Badge, Empty State
static/css/forms.css ← Form group, validation styling
static/css/tables.css ← Data table
static/css/responsive.css ← Breakpoints (mobile <576, tablet <992)


## JavaScript Architecture
Vanilla JS تنها (`static/js/navigation.js`) برای toggle موبایل Navbar/Sidebar.
Authorization هرگز در JS انجام نمی‌شود.

## RTL Rules
`<html dir="rtl" lang="fa">` در `base/base.html`. تمام Flex/Grid با جهت طبیعی RTL
(بدون `direction: ltr` اجباری در جایی).

## Accessibility Rules
- `:focus-visible` سراسری برای ناوبری کیبورد
- `aria-label`/`aria-expanded` روی دکمه‌های toggle
- برچسب صریح (`<label>`) برای هر ورودی فرم
- پیام‌های خطای ۴۰۰/۴۰۳/۴۰۴ اطلاعات حساس افشا نمی‌کنند
