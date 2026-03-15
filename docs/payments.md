# Payments

We want to use https://core.telegram.org/bots/payments-stars as payment provider and backend. This allows us to accept payments directly within Telegram, without needing to build a separate checkout flow or integrate with external payment gateways.

Our persistant storage (MongoDB) should be simple as hell for that. So to patron_users db add transactions and to users themselves add a field with subscription status (active, inactive, trialing, etc). When user sends /subscribe command, we starts the subscription flow: as described in https://core.telegram.org/bots/payments-stars

For the first version it is only one subscription plan and product: (monthly, ⭐️500 stars/month). We can add more plans later if needed.

When user successfully subscribes, we update their subscription status in the database. For every message we process from the user, we check their subscription status. If they are inactive, we can send them a message reminding them to subscribe to continue using the assistant.
