# Ontology v1: proposals to decide

The draft `ontology/ontology.yaml` applies every proposal below so it can be validated, but none is decided until you mark it. Test for each: **does resolving it need a different procedure** (steps, tools, policy or risk)? Cluster numbers (1 = largest) refer to `results/discovery/all-clusters.md`, which lists every conversation in each.

Mark each: **accept**, **reject**, or write what you'd do instead.

| # | Proposal | Why | Alternative | Your decision |
|---|---|---|---|---|
| P1 | **Merge** returns clusters 1 (defective, 62), 5 (refund, 35), 6 (wrong item, 30), 29 (tampered, 11) into one `initiate_return` | Same procedure: verify the order, check eligibility, book the return, then refund or replace. The reason for the return doesn't change the steps. The brief's own example intent. | Keep "wrong item" separate (the seller made the mistake, so maybe no return fee), or split refund from exchange | |
| P2 | **Split** cluster 7: policy questions → `return_policy`; fee waivers and reimbursements (#97, 328, 722, 758, 966) → `charge_dispute`, with cluster 18 | Questions are answered from policy (inform). Waiving or refunding a fee moves money, so it needs sign-off. | Keep fee waivers inside `return_policy` | |
| P3 | **Split** cluster 3 three ways: missed or misdirected delivery → `redeliver_order`; marked delivered but not received → `missing_delivery`; tracking and courier-contact questions → `delivery_delay` | Rescheduling is routine. A lost-parcel claim moves money and sits next to the fraud guard (the stolen-parcel trap). Tracking questions are the same as late deliveries. | Keep one "delivery problem" intent | |
| P4 | **Merge** warranty clusters 10 (details, 27), 27 (conflicting terms, 11), 23 (registration, 12) into `warranty_info` | All answered from warranty policy and brand information; no action on BrownBox's side | Keep registration separate (half of it is "act") | |
| P5 | **Split** cluster 15 (cash on delivery) by what's asked: paying → `payment_options`; COD returns → `initiate_return`; COD refund timing → `refund_status`; cashback → `offers_and_discounts` | The cluster grouped on the words "cash on delivery", not on the request. Classic over-clustering. | Keep one COD intent | |
| P6 | `offers_and_discounts` as **one intent at sign-off level** | Applying a missed discount moves money | Split "how offers work" (ai) from "apply my discount" (sign-off) | |
| P7 | **Merge** clusters 4 (verify phone/email, 37) and 24 (missing code, 12) into `login_verification`; keep 26 (lockout, 12) as `account_lockout` | Code and login help is routine. Unlocking an account is an account-takeover route, so it needs sign-off. | Merge all three into one login intent | |
| P8 | `cancel_order` at **ai** level | An unshipped order cancels cleanly and the refund follows automatically | `ai_with_signoff`, since a refund is triggered | |
| P9 | **Split** cluster 19: `reactivate_account` (10) and `close_account` (4) | Opposite procedures. Closing is hard to undo. | `close_account` is under 1% (4 conversations): merge into one `account_status` intent, or route it to a human as "other" | |
| P10 | **Merge** cluster 35 (corporate email sign-up), 34 (is an account needed) and the sign-up goals in cluster 4 into `signup_help` | All "help me get an account", answered from policy | Keep "is an account needed to buy" under `ordering_help` | |

Also check:
- **Participation levels**: 23 intents at `ai`, 7 at `ai_with_signoff` (marked with a reason in the YAML). Does any feel wrong?
- **Guards**: fraud or takeover (never), wants a human, complaint, unsupported language (all hand-off). Add or remove any?
- **Intents you'd add or rename**, compared with your reading notes.

## Decisions

| # | Decision | Applied as |
|---|---|---|
| P1 | Accept | `initiate_return`; eligibility is a procedure step; missing parts included |
| P2 | Accept | `return_policy` + `charge_dispute` |
| P3 | Changed | `delivery_delay` + `missing_delivery` merged into `order_not_arrived` (the router can't tell them apart without tracking data); `redeliver_order` kept, and its procedure confirms the failed attempt with the carrier |
| P4 | Accept | `warranty_info` |
| P5 | Changed | Split as proposed, but `payment_options` (5) folded into `ordering_help` ("how to order, pay and collect"); cash-on-delivery refunds need sign-off (refund to a different method) |
| P6 | Rejected | My principle: sign-off belongs on money-moving **actions**, not whole intents. Schema now has `signoff_actions`; participation is ai / handoff / never |
| P7 | Accept + | Lockout unlock needs sign-off; changing the verification phone or email needs sign-off too |
| P8 | Changed | Policy-based money rule: the AI cancels unshipped orders with a refund to the original card; dispatched orders or other refund methods need sign-off |
| P9 | Changed | `reactivate_account` with sign-off on reactivation (not a guard: guards are suspicion signals); `close_account` is a hand-off (data protection) |
| P10 | Accept | `signup_help`, scope written into the ontology |

Rules adopted: **policy-based money rule**; **split only where the customer's words tell the cases apart**; **AI intents need at least 1% of DEV (7 or more), risk routes exempt**. Fraud signals are now listed per intent, with the guard's examples broadened.
