# Labelling edge cases

Conversations where the label needed a judgement call, collected while labelling the practice
set. Each one is either a rule we applied (so later labels stay consistent) or a question for
the ontology review after labelling. New ones come from the `note` field in
`data/gold/practice.jsonl` (the label tool asks "Edge case?" before saving).

## Rules applied while labelling

- **Is it a switch?** Ask: would the agent routed to at the first clear message still be the
  right one? Follow-up questions on the same request (timing, fees, steps) are never a switch.
  A switch means the customer drops the first request for one needing a different procedure.
- **Is it a secondary?** Only if the customer makes a second, separate request that needs its
  own procedure. A question about the same item or order is part of the primary.
- **Second request or switch?** Did the customer get, or still want, what they first asked
  for? Yes → second request (raised alongside the first, or after it's settled: #588 discount
  after the price question, #352 pickup after the refund). No, they gave it up unfinished →
  switch (#626).
- **Backend findings don't change the intent.** The router only sees the customer's words. If
  the agent discovers something in their system (the account is actually locked), that's a
  branch inside the procedure, not a different label.
- **Label the words, not whether they make sense.** The data is synthetic and sometimes
  mismatches products and requests.

## Cases

| Conversation | Labelled | Why it's interesting | For the ontology review? |
|---|---|---|---|
| 383 | password_reset (21), C1, no guard | "Lost my phone and forgot my password"; the agent finds the account locked; the customer later says "it says my account is locked". The customer's words say password reset, the backend says lockout. Agent hands to senior support on their own: not `wants_human`. | Yes: should account_lockout and password_reset merge into one intent whose procedure branches on account state? Same routing principle as order_not_arrived. |
| 546 | login_verification (19) | Customer already bought a TV and asks *why* an email wants them to verify their mobile and email. Not blocked, so it doesn't fit 19's definition ("can't log in or complete a purchase"). | Yes: widen 19 to "questions or problems with mobile or email verification". Also: a customer worried the email is phishing isn't covered by any intent or by the fraud guard. |
| 351 | initiate_return (8), C1, no switch, no guard | C5 "How long will it take?" looks like a return-policy question but is a follow-up on the return already requested. C6–C7 frustration over the restocking fee isn't a complaint. | No: teaching example for the switch and complaint rules (useful for the Loom). |
| 394 | order_not_arrived (4), C1, no switch | Marked delivered but missing; at C6 the customer picks a replacement. The replacement is an outcome inside the procedure, not a switch, and it's one of 4's sign-off actions. | No: example of action-level sign-off for the Loom. |
| 233 | order_not_arrived (4), C1, no guard (borderline) | C8 "I'm not happy with the service. I expected better from BrownBox", after the request is done; no formal complaint, compensation or escalation. The agent's discovery of a missed delivery attempt doesn't make it redeliver_order. | Yes: tighten the complaint guard to "wants the complaint acted on" and add general dissatisfaction to its "doesn't fire" list. |
| 212 | warranty_claim (17), C1, no switch | "Lost the warranty card, can I still get warranty?" then a fault at C4. Looks like warranty_info then a switch, but warranty_claim includes "missing warranty cards". | No: rule: when a first question is about something the customer then does, check whether the action intent already covers it. |
| 924 | charge_dispute (11), C1, `w5` only | Overcharge; C5 "still not satisfied… can I speak to your supervisor?" `w` catches it; "unacceptable" and "make sure it doesn't happen again" left as frustration, not a complaint. | Same complaint-guard question as 233. |
| 584 | order_status (1), C1, no switch. **Probably wrong: return_policy (9)** | "I got an email asking me to ship my baby food order, why?" then "when will I receive it?" Claude advised order_status, but return_policy includes "Why they were asked to ship an item back"; both pre-label models said return_policy. | Yes: correct at adjudication (keep the blind label for the anchoring measure). The includes line already covers it, so no ontology change needed. |
| 626 | initiate_return (8), C1, switch at C6 to warranty_claim (17), no guard | Return refused (installed fridge); C5 still demands a refund; at C6 accepts the warranty route the agent offered. Agent check says switch: after C6 the work is a warranty claim. C3 "ridiculous", C8 "frustrating": no complaint. | Yes: should an agent-proposed switch be a planned hand-over in initiate_return's procedure ("not eligible → offer warranty claim → hand to warranty_agent") rather than something the router has to spot? |
| 232 | invoice_request (12), C1, no guard | Labeller's note: "customer is frustrated". Frustration while pursuing the request: no complaint. | Same complaint-guard question as 233. |
| 185 | charge_dispute (11), clear C3, second request (8 or 17) | Overcharge settled, then at C8 "not functioning correctly"; agent troubleshoots and replaces "under warranty". Delivered yesterday, so inside the return window → 8 by the boundary rule; she never says what remedy she wants. | **Yes: my "faulty item" proposal** (troubleshoot → hand over to returns or warranty). |
| 631 | no suggestion (models split: cancel_order / other) | Cancel a return already under way ("changed my mind, I'll keep it"). Not covered by any intent. | Yes: add "cancelling or changing a return already started" to 8. |
| 492 | warranty_claim (17), C1 | Lost warranty card, no fault mentioned; C6 "guide me through claiming". "Transfer me to the support center" (C5) follows the agent's instruction: not `w`. | Yes: tighten to "missing card when making a claim". |
| 425 | installation_help (18), C1, no secondary | "Can your team install my jeans, and will it affect the warranty?" Two questions, one intent: installation_help includes "whether installation affects the warranty". C3 restates the warranty half: not a switch. | Discussion: shows intents are defined by procedure, not by topic words (a warranty question routed to the installation agent). Also data noise: installing jeans. |
