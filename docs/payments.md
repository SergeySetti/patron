# Payments

## Overview

Patron uses [Telegram Stars](https://core.telegram.org/bots/payments-stars) as payment provider and backend. Payments happen entirely within Telegram — no external checkout flow or payment gateway needed.

## Subscription Plan

| Plan    | Price            | Duration |
|---------|------------------|----------|
| Monthly | 2 Telegram Stars | 30 days  |

Only one plan exists for now. More plans can be added later.

## How It Works

1. User sends `/subscribe` — bot sends a Telegram Stars invoice.
2. Telegram handles the payment flow (pre-checkout query, charge).
3. On successful payment, the bot:
   - Records the transaction in `patron_users.transactions`.
   - Extends `subscription_expires_at` on the user document by 30 days.
   - If the user already has active time remaining, the new 30 days **stack** on top of the existing expiry (no time is lost).
   - If the subscription has expired, the new 30 days start from now.
4. On every user message, the bot checks `subscription_expires_at`:
   - Active (expiry in the future) — message is processed normally.
   - Expired / no subscription — user gets a reminder to `/subscribe`.
5. Task scheduler (`check_due_tasks`) is **not** gated by subscription — due tasks always fire regardless.

## Storage

### `patron_users.users` (existing collection)

Added field:
- `subscription_expires_at` (datetime, UTC) — when the current subscription period ends.

### `patron_users.transactions` (new collection)

Each successful payment creates a transaction document:

| Field                        | Type     | Description                         |
|------------------------------|----------|-------------------------------------|
| `user_id`                    | string   | Telegram user ID                    |
| `telegram_payment_charge_id` | string   | Unique charge ID from Telegram      |
| `provider_payment_charge_id` | string   | Provider-side charge ID             |
| `total_amount`               | int      | Amount in Stars                     |
| `currency`                   | string   | Always `"XTR"` for Stars            |
| `is_recurring`               | bool     | Whether this was a recurring charge |
| `created_at`                 | datetime | UTC timestamp of the payment        |

Indexes: `user_id`, `telegram_payment_charge_id` (unique).
