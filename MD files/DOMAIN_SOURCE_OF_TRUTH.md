# Domain Source of Truth Registry — Phase 35

این فایل مرجع رسمی «کدام کد، صاحب کدام مفهوم است» برای کل پروژه است.

## Membership
| مفهوم | صاحب رسمی | فایل |
|---|---|---|
| بررسی درخواست اولیه‌ی عضویت | `approval_status` | `apps/members/models.py::Member.approval_status` |
| چرخه‌ی جاری عضویت | `status` (State Machine) | `apps/members/services.py` (submit/review/approve/reject/activate/suspend/reinstate/expire/cancel_membership) |
| سابقه‌ی زمانی عضویت | `MembershipPeriod` | `apps/members/services.py` (start/end_membership_period, renew_membership) |
| تعهد مالی | `MembershipFee` | `apps/members/services.py::record_fee_payment` |

## RoleAssignment — ⚠️ بدون Source of Truth واحد (BLOCKED)
| مسیر | فایل | مصرف‌کننده‌ی فعال |
|---|---|---|
| مسیر ۱ (approval_status) | `apps/authorization/role_services.py` | `apps/authorization/pending_views.py::pending_roles_view` |
| مسیر ۲ (status State Machine) | `apps/authorization/role_lifecycle_services.py` | `apps/authorization/views.py` (roles:approve/reject/...) |

**تا تصمیم سازمانی، هر دو مسیر معتبر و فعال باقی می‌مانند.**

## Committee
| مفهوم | صاحب رسمی |
|---|---|
| Lifecycle کمیته | `apps/committees/services.py` (تنها Service موجود) |

## Board
| مفهوم | صاحب رسمی |
|---|---|
| Lifecycle دوره‌ی هیئت‌مدیره | `apps/board/services.py` (تنها Service موجود) |

## Employment
| مفهوم | صاحب رسمی |
|---|---|
| تخصیص/تأیید محل خدمت | `apps/employment/services.py` (تنها Service موجود) |

## Request
| مفهوم | صاحب رسمی |
|---|---|
| Lifecycle عمومی درخواست | `apps/requests/services.py` |
| Whitelist اهداف مجاز | `apps/requests/target_validation.py` |
