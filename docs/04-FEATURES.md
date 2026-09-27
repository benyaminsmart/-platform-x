# Platform-X — Features

> Complete feature list, organized by user type and phase.
> This document is the source of truth for what we're building.

---

## 1. Feature Overview

Features are organized by:

- **User Type:** Guest, Tenant Staff, Tenant Admin, Platform Admin
- **Phase:** 1 (First tenant live), 2 (Platform core), 3-8 (expansion)
- **Priority:** Critical, Important, Nice-to-have

---

## 2. Guest Features (End-User)

### Authentication
| Feature | Phase | Priority |
|---------|-------|----------|
| Register with email | 1 | Critical |
| Login / logout | 1 | Critical |
| Forgot password | 1 | Critical |
| Email verification | 1 | Important |
| Social login (Google, Apple) | 3 | Nice-to-have |
| Two-factor authentication | 4 | Nice-to-have |

### Profile
| Feature | Phase | Priority |
|---------|-------|----------|
| View profile | 1 | Critical |
| Edit profile | 1 | Critical |
| Change password | 1 | Critical |
| Profile picture | 2 | Important |
| Preferred language | 1 | Critical |
| Preferred currency | 2 | Important |

### Booking
| Feature | Phase | Priority |
|---------|-------|----------|
| Search rooms by date | 1 | Critical |
| Filter by room type | 1 | Critical |
| View room details | 1 | Critical |
| Book a room | 1 | Critical |
| Cancel booking | 1 | Critical |
| View booking history | 1 | Critical |
| Booking confirmation email | 1 | Critical |
| Digital booking pass | 1 | Important |

### Dining
| Feature | Phase | Priority |
|---------|-------|----------|
| Browse menu | 1 | Critical |
| Add to cart | 1 | Critical |
| Place order | 1 | Critical |
| Order tracking | 2 | Important |
| Order history | 1 | Critical |

### Services
| Feature | Phase | Priority |
|---------|-------|----------|
| Book spa treatments | 1 | Critical |
| Reserve pool (events) | 1 | Critical |
| Room service requests | 1 | Critical |
| Housekeeping requests | 1 | Critical |
| Request maintenance | 2 | Important |

### Rewards
| Feature | Phase | Priority |
|---------|-------|----------|
| View points balance | 1 | Critical |
| View tier level | 1 | Critical |
| Referral code | 1 | Critical |
| Track referrals | 1 | Critical |
| Redeem rewards | 2 | Important |

### Payments
| Feature | Phase | Priority |
|---------|-------|----------|
| Pay with credit card | 1 | Critical |
| Save payment method | 2 | Important |
| Multi-currency | 2 | Important |
| Payment history | 1 | Critical |

### Notifications
| Feature | Phase | Priority |
|---------|-------|----------|
| Email notifications | 1 | Critical |
| WhatsApp notifications | 1 | Critical |
| In-app notifications | 2 | Important |
| Push notifications (mobile) | 8 | Nice-to-have |

---

## 3. Tenant Staff Features

### Reception / Front Desk
| Feature | Phase | Priority |
|---------|-------|----------|
| View today's check-ins | 1 | Critical |
| View today's check-outs | 1 | Critical |
| Confirm booking | 1 | Critical |
| Check-in guest | 1 | Critical |
| Check-out guest | 1 | Critical |
| View guest profile | 1 | Important |
| Handle walk-ins | 2 | Important |

### Restaurant Staff
| Feature | Phase | Priority |
|---------|-------|----------|
| View incoming orders | 1 | Critical |
| Accept / reject order | 1 | Critical |
| Mark order ready | 1 | Critical |
| Mark order delivered | 1 | Critical |
| Order history | 1 | Important |

### Spa Staff
| Feature | Phase | Priority |
|---------|-------|----------|
| View today's appointments | 1 | Critical |
| Confirm appointment | 1 | Critical |
| Mark treatment done | 1 | Critical |
| View schedule | 1 | Important |

### Housekeeping
| Feature | Phase | Priority |
|---------|-------|----------|
| View room service requests | 1 | Critical |
| Assign task to staff | 2 | Important |
| Mark task complete | 1 | Critical |
| Priority handling | 1 | Important |

---

## 4. Tenant Admin Features

### Dashboard
| Feature | Phase | Priority |
|---------|-------|----------|
| Real-time stats | 1 | Critical |
| Occupancy rate | 2 | Important |
| Revenue reports | 2 | Critical |
| Booking trends | 2 | Important |
| Customer insights | 2 | Important |

### Configuration
| Feature | Phase | Priority |
|---------|-------|----------|
| Brand settings (logo, colors) | 2 | Critical |
| Domain settings | 2 | Critical |
| Room management | 1 | Critical |
| Pricing management | 1 | Critical |
| Service menu (dining/spa) | 1 | Critical |
| Staff accounts | 2 | Critical |
| Notification preferences | 2 | Important |

### Bookings Management
| Feature | Phase | Priority |
|---------|-------|----------|
| View all bookings | 1 | Critical |
| Filter/search | 1 | Critical |
| Export bookings | 2 | Important |
| Modify booking | 2 | Important |
| Cancel booking | 1 | Critical |

### Customers
| Feature | Phase | Priority |
|---------|-------|----------|
| Customer database | 1 | Critical |
| Customer history | 1 | Important |
| Customer segmentation | 3 | Nice-to-have |
| Marketing campaigns | 4 | Nice-to-have |

### Finance
| Feature | Phase | Priority |
|---------|-------|----------|
| Revenue dashboard | 2 | Critical |
| Transaction list | 2 | Critical |
| Commission tracking | 2 | Critical |
| Invoice generation | 3 | Important |
| Payout reports | 3 | Important |

### Loyalty & Rewards
| Feature | Phase | Priority |
|---------|-------|----------|
| Configure loyalty tiers | 2 | Critical |
| Set points rules | 2 | Critical |
| Set discount levels | 2 | Critical |
| Manage referrals | 2 | Critical |

### Notifications
| Feature | Phase | Priority |
|---------|-------|----------|
| WhatsApp templates | 2 | Critical |
| Email templates | 2 | Critical |
| Auto-notifications | 2 | Critical |
| Notification history | 2 | Important |

---

## 5. Platform Admin Features

### Tenant Management
| Feature | Phase | Priority |
|---------|-------|----------|
| View all tenants | 2 | Critical |
| Create tenant | 2 | Critical |
| Suspend tenant | 2 | Critical |
| Delete tenant | 2 | Critical |
| Impersonate tenant admin | 2 | Important |

### Billing
| Feature | Phase | Priority |
|---------|-------|----------|
| Subscription management | 2 | Critical |
| Commission tracking | 2 | Critical |
| Invoice generation | 2 | Critical |
| Payment collection | 2 | Critical |
| Revenue reports | 2 | Critical |

### Platform Analytics
| Feature | Phase | Priority |
|---------|-------|----------|
| Total tenants | 2 | Critical |
| Active users | 2 | Critical |
| Total bookings | 2 | Critical |
| Platform revenue | 2 | Critical |
| Growth metrics | 2 | Critical |

### System
| Feature | Phase | Priority |
|---------|-------|----------|
| System health | 2 | Critical |
| Error logs | 2 | Critical |
| Backup status | 2 | Critical |
| API usage per tenant | 2 | Important |
| Performance metrics | 3 | Important |

---

## 6. Cross-Surface Features

### Web Platform
| Feature | Phase | Priority |
|---------|-------|----------|
| Responsive design | 1 | Critical |
| Multi-language (EN/AR/FIL/HI) | 1 | Critical |
| RTL support (Arabic) | 1 | Critical |
| SEO optimization | 1 | Important |
| Accessibility (WCAG 2.1 AA) | 3 | Important |

### Mobile App (Phase 8)
| Feature | Phase | Priority |
|---------|-------|----------|
| Native iOS + Android | 8 | Critical |
| Push notifications | 8 | Critical |
| Offline browsing | 8 | Important |
| Biometric login | 8 | Nice-to-have |
| In-app payments | 8 | Important |

### Telegram Bot (Phase 8)
| Feature | Phase | Priority |
|---------|-------|----------|
| Link account via phone | 8 | Critical |
| View bookings | 8 | Critical |
| Order food | 8 | Important |
| Room service requests | 8 | Critical |
| Rewards balance | 8 | Important |
| Notifications | 8 | Critical |

### API (for integrations)
| Feature | Phase | Priority |
|---------|-------|----------|
| REST endpoints | 2 | Critical |
| API keys per tenant | 2 | Critical |
| Rate limiting | 2 | Critical |
| API documentation (OpenAPI) | 2 | Critical |
| Webhooks | 3 | Important |

---

## 7. AI Features (Phase 7)

| Feature | Phase | Priority |
|---------|-------|----------|
| Concierge AI (guest chat) | 7 | Important |
| Multi-language AI | 7 | Important |
| Smart pricing (tenant) | 7 | Important |
| Demand forecasting | 7 | Nice-to-have |
| Review analysis | 7 | Nice-to-have |
| Personalized recommendations | 7 | Important |

---

## 8. Analytics & Reporting

### Guest-Side
| Feature | Phase | Priority |
|---------|-------|----------|
| Personal booking history | 1 | Critical |
| Personal spending summary | 2 | Important |
| Loyalty progress | 1 | Critical |

### Tenant-Side
| Feature | Phase | Priority |
|---------|-------|----------|
| Occupancy analytics | 2 | Critical |
| Revenue analytics | 2 | Critical |
| Customer analytics | 2 | Important |
| Service performance | 2 | Important |

### Platform-Side
| Feature | Phase | Priority |
|---------|-------|----------|
| Tenant performance | 2 | Critical |
| Platform revenue | 2 | Critical |
| Growth metrics | 2 | Critical |
| Category analysis | 4 | Important |

---

## 9. Feature Prioritization Summary

### Phase 1 (Critical only)
Focus: Get First tenant live with core features.

**Must-have:**
- Auth (register, login)
- Room booking
- Dining orders
- Spa/Pool/Room service
- Rewards basic
- Payments
- Notifications (email + WhatsApp)
- Tenant admin dashboard (basic)
- Front desk operations

### Phase 2-3
**Add:** Platform core, multi-tenancy, analytics, advanced tenant config.

### Phase 4-6
**Add:** New categories, advanced features.

### Phase 7-8
**Add:** AI, mobile, Telegram.

---

## 10. Features NOT Included (Out of Scope)

The following are explicitly NOT part of Platform-X:

- Hotel Property Management System (PMS) — that's a different product category
- Accounting software — integration only
- HR/payroll software
- Physical POS systems
- Room key management (hardware)

If tenants need these, we integrate with existing solutions.

---

## 11. Feature Development Process

1. **Spec** — write the feature spec (input, output, edge cases)
2. **Design** — design API + UI
3. **Implement** — code with tests
4. **Test** — unit + integration + E2E
5. **Document** — update docs
6. **Deploy** — staged rollout
7. **Monitor** — check metrics

No feature is "done" until all 7 steps complete.

---

Last updated: September 2026
Status: Living document — updated as features are added/removed.
