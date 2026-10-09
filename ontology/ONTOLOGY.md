# BrownBox intent ontology, v2

Generated from `ontology.yaml` by `make ontology`. Edit the YAML, not this file.

| Domain | Intents |
|---|---|
| Orders | Check order status, Cancel an order, Change delivery or pickup address |
| Delivery | Order not arrived, Arrange a redelivery, Get faster delivery, Understand delivery charges |
| Returns and refunds | Return, replace or report a faulty item, Return policy and process, Chase a refund |
| Payments, pricing and offers | Dispute a charge or fee, Get an invoice, Question about listed prices, Offers, exchange deals and discounts, Loyalty points |
| Product support and warranty | Warranty information, Claim a repair under warranty, Installation and setup help |
| Account and login | Can't log in or verify, Unlock a locked account, Reset or change password, Change account email, Reactivate an account, Close an account, Sign-up and account requirements |
| Shopping help before buying | How to order, pay and collect, Out-of-stock items, Shipping to an unavailable location |

## Orders

### Check order status (`order_status`)

The customer wants to confirm an order went through or see what stage it is at.

inform · identity check · AI handles it · agent `orders_agent`

- **Includes:** Confirming an order was placed or approved; What an order status shown on the website means; Emails or notifications about an order that the customer doesn't understand
- **Excludes:** The order is late, overdue or hasn't arrived (order_not_arrived); Being asked to ship an item back (return_policy)
- **vs `order_not_arrived`:** If the customer says it is late, overdue or missing, it's order_not_arrived.
- **vs `return_policy`:** An email asking them to ship an item back is return_policy.
- **Examples:** #60, #302, #952

### Cancel an order (`cancel_order`)

The customer wants to cancel an order that hasn't been delivered yet.

act · identity check · AI handles it · agent `orders_agent`

- **Includes:** Unshipped or processing orders; The website's cancel button isn't working
- **Excludes:** The item has already arrived (initiate_return)
- **vs `initiate_return`:** Before delivery it's a cancellation; after delivery it's a return.
- **vs `change_delivery_address`:** Changing where it goes keeps the order; cancelling ends it.
- **Needs sign-off:** Cancel an order that has already been dispatched; Refund to a payment method other than the original one
- **Fraud signals:** Asks for the refund to go to a different person or account
- **Examples:** #2, #246, #307

### Change delivery or pickup address (`change_delivery_address`)

The customer wants to change the delivery or pickup address on an order, or add an address to their account.

act · identity check · AI handles it · agent `orders_agent`

- **Includes:** Orders already in transit; Adding a new saved address
- **Excludes:** An order already delivered to the wrong address (redeliver_order)
- **vs `redeliver_order`:** Before a delivery attempt it's an address change; after a failed or wrong-address delivery it's redeliver_order.
- **Fraud signals:** Asks to redirect a high-value order to a new address straight after an account change
- **Examples:** #73, #398, #582

## Delivery

### Order not arrived (`order_not_arrived`)

The customer's order hasn't reached them, whether it's late, untracked, or marked delivered but missing. The procedure checks tracking and branches.

inform · identity check · AI handles it · agent `delivery_agent`

- **Includes:** Late, delayed or unshipped orders; Tracking that isn't updating, or how to contact the courier; Asking to speed up an order that is already late; Tracking says delivered but nothing arrived, including parcels stolen from a doorstep
- **Excludes:** A delivery attempt the customer knows was missed or went to the wrong address (redeliver_order); Someone else ordered on the customer's account (fraud guard)
- **vs `order_status`:** A routine status check is order_status; late or missing is order_not_arrived.
- **vs `redeliver_order`:** If the customer asks to rebook a missed or misdirected delivery, it's redeliver_order.
- **vs `faster_delivery`:** Upgrading shipping on an order that isn't late is faster_delivery.
- **Needs sign-off:** Send a replacement or refund for a parcel marked delivered but not received
- **Fraud signals:** Repeated "not received" claims on the account (backend check); Claim contradicts the carrier's proof of delivery (backend check)
- **Examples:** #98, #249, #354, #779

### Arrange a redelivery (`redeliver_order`)

A delivery attempt failed, was missed or went to the wrong address, and the customer wants it delivered again. The procedure confirms the failed attempt with the carrier first.

act · identity check · AI handles it · agent `delivery_agent`

- **Includes:** Rescheduling a missed delivery; Redelivering an order sent to the wrong address; The missing second package of a split order
- **Excludes:** The carrier shows a successful delivery (order_not_arrived)
- **vs `order_not_arrived`:** A known missed or misdirected attempt is redeliver_order; anything the customer can't explain is order_not_arrived.
- **vs `change_delivery_address`:** Before any attempt it's an address change.
- **Fraud signals:** Carrier shows a successful delivery the customer disputes (backend check)
- **Examples:** #244, #545, #860

### Get faster delivery (`faster_delivery`)

The customer wants a quicker shipping option for an item or an order that is not late.

act · no identity check · AI handles it · agent `delivery_agent`

- **Includes:** Expedited shipping before or after buying; Store pickup as a faster alternative
- **Excludes:** The order is already late (order_not_arrived)
- **vs `order_not_arrived`:** Speeding up a late order is order_not_arrived.
- **vs `delivery_charges`:** Asking what each option costs is delivery_charges.
- **Examples:** #77, #162, #379

### Understand delivery charges (`delivery_charges`)

The customer wants to know what delivery costs or why an order didn't get free delivery.

inform · no identity check · AI handles it · agent `knowledge_agent`

- **Includes:** Shipping prices and speeds for an item; Why an order didn't qualify for free delivery
- **Excludes:** Wanting a delivery charge refunded (charge_dispute); A charge on their own order they don't recognise (charge_dispute)
- **vs `charge_dispute`:** How delivery is priced is delivery_charges; a charge on their own order that they don't recognise or want back is charge_dispute, whose procedure looks it up.
- **Examples:** #110, #208, #710

## Returns and refunds

### Return, replace or report a faulty item (`initiate_return`)

The customer has an item that isn't right and wants it refunded, exchanged, replaced or completed, or reports a fault without saying what they want. For a fault, the procedure troubleshoots first; if that fails, it offers a return or replacement within the return window, and hands over to the warranty agent for a repair or outside the window. It checks eligibility (return window, condition, category) before booking anything.

act · identity check · AI handles it · agent `returns_agent`

- **Includes:** Defective, damaged, wrong, ill-fitting or unwanted items; A fault reported without naming a remedy ("it's not working"); Items delivered in a tampered or opened package; Missing parts or accessories (the procedure can send the part instead of a full return); Items paid for by cash on delivery; Cancelling or changing a return already started
- **Excludes:** Asking for a repair, or invoking the warranty (warranty_claim); Questions about the return policy with no return started (return_policy)
- **vs `warranty_claim`:** A fault with no remedy named, or a return or replacement, is initiate_return; asking for a repair or invoking the warranty is warranty_claim.
- **vs `return_policy`:** Asking how returns work is return_policy; asking to start one is initiate_return.
- **vs `refund_status`:** Once the item is back and the customer is chasing the money, it's refund_status.
- **vs `cancel_order`:** Before delivery it's a cancellation.
- **Needs sign-off:** Refund to a payment method other than the original one (e.g. bank details for a cash-on-delivery order); Refund or replace outside the return policy (past the window, non-returnable item); Waive a return fee
- **Fraud signals:** Asks for the refund to go to a different person or account; Refuses to provide photos of damage when asked; Repeated damaged or wrong-item claims on the account (backend check)
- **Can hand over to:** `warranty_agent`
- **Examples:** #239, #204, #227, #330

### Return policy and process (`return_policy`)

The customer wants to know how returns work for an item, without asking for money back.

inform · no identity check · AI handles it · agent `returns_agent`

- **Includes:** A seller's return policy, before or after buying; Return fees, return pickups and return shipping options; Why they were asked to ship an item back
- **Excludes:** Asking for a fee to be waived or refunded (charge_dispute)
- **vs `charge_dispute`:** Explaining a fee is return_policy; reversing it is charge_dispute.
- **vs `initiate_return`:** Starting a return is initiate_return.
- **Examples:** #187, #245, #581

### Chase a refund (`refund_status`)

The customer returned or cancelled something and wants to know where their refund is or how it will be paid.

inform · identity check · AI handles it · agent `returns_agent`

- **Includes:** Delayed or missing refunds; Refund timelines and refund methods, including cash on delivery
- **Excludes:** A refund smaller than expected that they want corrected (charge_dispute)
- **vs `initiate_return`:** Before the item is sent back it's initiate_return.
- **vs `charge_dispute`:** Disputing the refund amount is charge_dispute.
- **Examples:** #44, #337, #612

## Payments, pricing and offers

### Dispute a charge or fee (`charge_dispute`)

The customer thinks they were charged too much, or charged a fee they shouldn't pay, and wants it explained and refunded or waived.

act · identity check · AI handles it · agent `billing_agent`

- **Includes:** Overcharges and unexpected charges on an order; A charge on their order they don't recognise (the procedure looks up what it was for); Return fees, courier costs or unwanted add-on charges they want back
- **Excludes:** Different prices on the website with no order affected (pricing_question); Charges the customer says they never made (fraud guard)
- **vs `pricing_question`:** If they were charged more on an order, it's charge_dispute; just asking about listed prices is pricing_question.
- **vs `delivery_charges`:** Asking why a delivery fee applies is delivery_charges.
- **Needs sign-off:** Refund an overcharge or waive a fee
- **Fraud signals:** Asks for the money to go to a different person or account
- **Examples:** #80, #126, #722, #758

### Get an invoice (`invoice_request`)

The customer wants an invoice for one or more past orders.

act · identity check · AI handles it · agent `billing_agent`

- **Includes:** Missing invoices, or invoices to be resent
- **Examples:** #47, #81, #750

### Question about listed prices (`pricing_question`)

The customer wants to know why the same item shows different prices on the website.

inform · no identity check · AI handles it · agent `knowledge_agent`

- **Includes:** Different prices across listings, pages or checkout
- **Excludes:** Being charged more than the listed price on an order (charge_dispute)
- **vs `charge_dispute`:** An affected order makes it charge_dispute.
- **Examples:** #86, #209, #687

### Offers, exchange deals and discounts (`offers_and_discounts`)

The customer asks about an exchange (trade-in) offer, cashback or discount, or wants one applied to an order.

act · identity check · AI handles it · agent `billing_agent`

- **Includes:** How exchange offers and cashback work; Applying a missed or promised discount to an order
- **Excludes:** Loyalty points (loyalty_points)
- **vs `loyalty_points`:** Points balances and redemption are loyalty_points.
- **Needs sign-off:** Apply a discount, price-drop adjustment or exchange value to an order
- **Fraud signals:** Claims a promised discount that has no record (backend check)
- **Examples:** #146, #215, #573

### Loyalty points (`loyalty_points`)

The customer wants to know how many loyalty points they earned or how to redeem them.

inform · identity check · AI handles it · agent `billing_agent`

- **Includes:** A redemption that fails on the website
- **vs `offers_and_discounts`:** Exchange offers and cashback are offers_and_discounts.
- **Examples:** #75, #487, #964

## Product support and warranty

### Warranty information (`warranty_info`)

The customer wants to know what a warranty covers, when it starts, which terms apply, or how to register or extend it.

inform · no identity check · AI handles it · agent `warranty_agent`

- **Includes:** Conflicting warranty terms between the website, card and brand; Registering an item or buying an extended warranty; Whether cover still applies without the warranty card
- **Excludes:** Getting a faulty item repaired or replaced (warranty_claim)
- **vs `warranty_claim`:** Asking about cover, even without the card, is warranty_info; using it for a fault is warranty_claim.
- **Examples:** #19, #299, #114, #247

### Claim a repair under warranty (`warranty_claim`)

The customer asks for a faulty item to be repaired or replaced under warranty, or invokes the warranty for a fault.

act · identity check · AI handles it · agent `warranty_agent`

- **Includes:** A missing warranty card when making a claim; A service centre that refused the repair
- **Excludes:** A fault reported without naming a remedy (initiate_return, which troubleshoots first); A return or replacement within the return window (initiate_return)
- **vs `initiate_return`:** Asking for a repair or invoking the warranty is warranty_claim; a fault with no remedy named, or a return, is initiate_return.
- **vs `warranty_info`:** Questions about cover alone, even with a lost card, are warranty_info.
- **Needs sign-off:** Replace or repair outside the warranty terms
- **Examples:** #11, #449, #776

### Installation and setup help (`installation_help`)

The customer wants help installing, assembling or setting up an item, or asks who does the installation.

inform · no identity check · AI handles it · agent `knowledge_agent`

- **Includes:** Whether installation affects the warranty; Wall mounts and installation accessories
- **Examples:** #8, #169, #794

## Account and login

### Can't log in or verify (`login_verification`)

The customer can't log in or complete a mobile or email verification, including when they don't know why. The procedure checks the account's state and branches. A locked account follows the unlock steps, a forgotten password gets a reset link to the registered email, and a code problem gets the code resent.

act · identity check · AI handles it · agent `account_agent`

- **Includes:** Can't log in and doesn't know why; Codes that never arrive; Logging in with a mobile number; Questions about why they're being asked to verify their mobile or email
- **Excludes:** Signing up for a new account (signup_help)
- **vs `account_lockout`:** If the customer says the account is locked after too many attempts, it's account_lockout; if they can't say why they can't log in, it's login_verification.
- **vs `password_reset`:** If the customer says they forgot their password or want to change it, it's password_reset.
- **vs `signup_help`:** Creating a new account is signup_help.
- **Needs sign-off:** Change the phone number or email that codes are sent to; Unlock the account
- **Fraud signals:** Asks for a code to be sent to a new number or address; Asks the agent to read out or bypass a one-time code
- **Examples:** #220, #229, #131, #690

### Unlock a locked account (`account_lockout`)

The account is locked after too many failed verification attempts and the customer wants access back.

act · identity check · AI handles it · agent `account_agent`

- **Includes:** Accounts blocked by too many verification code attempts
- **vs `login_verification`:** If the customer can't log in but doesn't say the account is locked, it's login_verification, which checks.
- **Needs sign-off:** Unlock the account
- **Fraud signals:** The customer says they didn't try to log in; The email or phone changed recently (backend check)
- **Examples:** #3, #321, #944

### Reset or change password (`password_reset`)

The customer wants to change their password or reset a forgotten one. The procedure sends a reset link to the registered email only; it never sets, reads or asks for a password, and never asks for government ID numbers.

act · identity check · AI handles it · agent `account_agent`

- **Includes:** Forgotten passwords
- **Excludes:** Someone else changed the password (fraud guard)
- **vs `login_verification`:** Code or number verification problems are login_verification.
- **Fraud signals:** Asks for the reset link to go to a different email address
- **Examples:** #116, #749, #757

### Change account email (`change_email`)

The customer wants to change or add the email address on their account.

act · identity check · AI handles it · agent `account_agent`

- **Includes:** Regaining access after an email change
- **Excludes:** Someone else changed the email (fraud guard)
- **Needs sign-off:** Change the account email
- **Fraud signals:** Can't access the current email and can't verify another way
- **Examples:** #255, #755, #953

### Reactivate an account (`reactivate_account`)

The customer's account was deactivated or went inactive and they want it back.

act · identity check · AI handles it · agent `account_agent`

- **Includes:** Accounts deactivated for inactivity
- **vs `close_account`:** Reactivating restores access; closing removes it.
- **Needs sign-off:** Reactivate the account
- **Fraud signals:** Asks to change the email or phone in the same conversation as reactivating
- **Examples:** #32, #434, #733

### Close an account (`close_account`)

The customer wants to deactivate or delete their account. Deletion carries data-protection obligations, so a person handles it.

act · identity check · Hand off to a person · agent `human_support`

- **Includes:** Deactivating an account; Deleting account data
- **vs `reactivate_account`:** Closing removes access; reactivating restores it.
- **Examples:** #111, #391, #777

### Sign-up and account requirements (`signup_help`)

The customer wants to create a new account, or asks whether they need one to buy. No identity check is needed because there is no account yet.

inform · no identity check · AI handles it · agent `account_agent`

- **Includes:** Signing up with a corporate email or an international phone number; Whether an account is needed to make a purchase
- **vs `login_verification`:** An existing account that can't log in is login_verification.
- **Examples:** #276, #436, #125, #489

## Shopping help before buying

### How to order, pay and collect (`ordering_help`)

The customer wants help placing an order, paying for it, or understanding how it will reach them.

inform · no identity check · AI handles it · agent `knowledge_agent`

- **Includes:** Payment options, including cash on delivery and why it isn't offered; Scheduled or in-store pickup; Combining orders from different sellers into one delivery
- **Examples:** #267, #105, #499, #781

### Out-of-stock items (`item_availability`)

The customer wants an item that is out of stock, or asks when it will be back.

inform · no identity check · AI handles it · agent `knowledge_agent`

- **Includes:** Restock dates
- **Examples:** #7, #78, #205

### Shipping to an unavailable location (`shipping_availability`)

The customer wants an item sent to a location it shows as unavailable for, including abroad.

inform · no identity check · AI handles it · agent `knowledge_agent`

- **Includes:** International shipping
- **vs `faster_delivery`:** Speed of delivery to a supported location is faster_delivery.
- **Examples:** #42, #323, #464

## Guards

Checked on every customer message; a guard overrides any intent.

### Suspected fraud or account takeover (`fraud_or_takeover`): Never

Someone other than the customer may have used, or be trying to use, their account, card or identity. Checked on every message; backend risk checks live in each intent's procedure.

- **Fires on:** I never placed this order; There are charges on my card I didn't make; Someone changed my password or email; My account was hacked, or I got a code I didn't ask for; Asks the agent to read out, resend to a new number, or skip a one-time code; It's my husband's account, he asked me to sort it out; Send the refund to this other account instead; Send the reset link or code to this other email or number instead
- **Not on:** My parcel was stolen from my doorstep (order_not_arrived); The package arrived opened or tampered with (initiate_return); I forgot my password (password_reset); My account is locked after too many attempts (account_lockout); A family member ordered on the account by mistake ("my son placed an order by mistake"); A charge on my order I don't recognise, asking what it is for (charge_dispute)

### Asks for a human (`wants_human`): Hand off to a person

The customer asks to speak to a person, supervisor or manager.

- **Fires on:** I want to speak to your supervisor; Can I talk to a real person?
- **Not on:** The agent decides to escalate on its own; Can you check with your team?; "I need to talk to someone about my return", as a way of opening the conversation; Agreeing to a transfer the agent suggested

### Complaint (`complaint`): Hand off to a person

The customer wants a complaint acted on. That means a formal complaint, compensation, a complaint about how staff or a courier behaved, or a threat to escalate outside BrownBox.

- **Fires on:** I want to make a formal complaint; The courier was rude to me; I want compensation for this; I'll be reporting this
- **Not on:** Frustration while still pursuing their request ("this is so annoying", "that's ridiculous", "this is unacceptable"); Dissatisfaction with nothing asked for ("I'm not happy with the service", "I expected better")

### Unsupported language (`unsupported_language`): Hand off to a person

The customer writes in a language BrownBox support doesn't cover.

- **Fires on:** A message mostly in another language
- **Not on:** English with a product or place name in another language

## Agents

| Agent | Intents |
|---|---|
| `account_agent` | `login_verification`, `account_lockout`, `password_reset`, `change_email`, `reactivate_account`, `signup_help` |
| `billing_agent` | `charge_dispute`, `invoice_request`, `offers_and_discounts`, `loyalty_points` |
| `delivery_agent` | `order_not_arrived`, `redeliver_order`, `faster_delivery` |
| `human_support` | `close_account` |
| `knowledge_agent` | `delivery_charges`, `pricing_question`, `installation_help`, `ordering_help`, `item_availability`, `shipping_availability` |
| `orders_agent` | `order_status`, `cancel_order`, `change_delivery_address` |
| `returns_agent` | `initiate_return`, `return_policy`, `refund_status` |
| `warranty_agent` | `warranty_info`, `warranty_claim` |
