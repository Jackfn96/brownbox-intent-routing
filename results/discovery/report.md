# Discovery report

697 DEV conversations. Goals by `claude-opus-5-5`, embeddings `BAAI/bge-small-en-v1.5`, Ward clustering into 35 clusters, names by `claude-opus-5-5`.

## Clusters by size

Clusters are numbered 1 (largest) upwards. *Mixed* means the LLM naming the cluster saw two or more different requests in it: the first place to look for a split.

| # | Name | Size | Share | Act | Contents |
|---|---|---|---|---|---|
| 1 | Return or replace defective item | 62 | 8.9% | 100% | one kind of request |
| 2 | Track a late delivery | 50 | 7.2% | 28% | one kind of request |
| 3 | Resolve a failed delivery | 42 | 6.0% | 71% | mixed requests |
| 4 | Verify phone/email to log in | 37 | 5.3% | 73% | one kind of request |
| 5 | Return item for refund | 35 | 5.0% | 100% | one kind of request |
| 6 | Return or exchange wrong item | 30 | 4.3% | 100% | one kind of request |
| 7 | Understand return policy and fees | 30 | 4.3% | 23% | mixed requests |
| 8 | Claim warranty on faulty item | 29 | 4.2% | 90% | one kind of request |
| 9 | Get help installing an item | 27 | 3.9% | 4% | one kind of request |
| 10 | Check item warranty details | 27 | 3.9% | 0% | one kind of request |
| 11 | Check status of return refund | 25 | 3.6% | 40% | one kind of request |
| 12 | Check order status | 22 | 3.2% | 0% | one kind of request |
| 13 | Get faster delivery | 20 | 2.9% | 70% | one kind of request |
| 14 | Update order address details | 16 | 2.3% | 100% | one kind of request |
| 15 | Pay or get refund via COD | 16 | 2.3% | 62% | mixed requests |
| 16 | Understand delivery charges | 15 | 2.2% | 0% | one kind of request |
| 17 | Learn how to order and receive | 14 | 2.0% | 29% | mixed requests |
| 18 | Dispute an order overcharge | 14 | 2.0% | 57% | one kind of request |
| 19 | Reactivate an inactive account | 14 | 2.0% | 100% | mixed requests |
| 20 | Cancel an order | 14 | 2.0% | 100% | one kind of request |
| 21 | Explain inconsistent item pricing | 14 | 2.0% | 14% | one kind of request |
| 22 | Ship item to unavailable location | 13 | 1.9% | 62% | one kind of request |
| 23 | Register item for warranty | 12 | 1.7% | 50% | one kind of request |
| 24 | Get missing verification code | 12 | 1.7% | 100% | one kind of request |
| 25 | Get exchange offer discount | 12 | 1.7% | 58% | mixed requests |
| 26 | Unlock account after verification lockout | 12 | 1.7% | 100% | one kind of request |
| 27 | Clarify conflicting warranty terms | 11 | 1.6% | 18% | one kind of request |
| 28 | Change account email address | 11 | 1.6% | 100% | one kind of request |
| 29 | Replace item from tampered package | 11 | 1.6% | 100% | one kind of request |
| 30 | Check and redeem loyalty points | 11 | 1.6% | 18% | one kind of request |
| 31 | Get out-of-stock item | 9 | 1.3% | 33% | one kind of request |
| 32 | Get invoice for an order | 9 | 1.3% | 100% | one kind of request |
| 33 | Change or reset password | 8 | 1.1% | 100% | one kind of request |
| 34 | Check if account needed to buy | 7 | 1.0% | 14% | one kind of request |
| 35 | Sign up with corporate email | 6 | 0.9% | 100% | one kind of request |

## Each cluster

### 1. Return or replace defective item (62)

Customers want to return, exchange, or get a refund or replacement for an item that is defective, faulty, or malfunctioning, including one case past the return window.

- Replace a defective item that is not working `#14`
- Return a malfunctioning item `#72`
- Return a faulty item for a replacement `#239`
- Return a malfunctioning item `#254`
- Return a malfunctioning item for a refund `#569`
- Exchange a defective item for a new one `#732`

### 2. Track a late delivery (50)

Customers want to know where their delayed or unshipped order is, why it's late, when it will arrive, and in some cases want it expedited.

- Find out the estimated delivery time for an order `#23`
- Find out why an order has not been delivered on time `#98`
- Find out when a delayed order will be delivered `#249`
- Find out why an approved order hasn't shipped yet `#266`
- Get a delayed order delivered faster `#281`
- Check the status of a delayed order stuck at the local hub `#756`

### 3. Resolve a failed delivery (42)

Customers want help with orders that didn't reach them properly — missed deliveries to reschedule, packages marked delivered but not received, wrong-address or split-order deliveries, tracking and courier contact details, and complaints about rude couriers.

**Mixed with:** A few unrelated item issues: a missing accessory and returning unwanted free items.

- Find tracking information for a shipped order `#30`
- Get a missed delivery of an order rescheduled urgently `#244`
- Complain about a rude courier who mishandled a delivery `#448`
- Get an order delivered to the wrong address redelivered to the correct address quickly `#455`
- Arrange another delivery attempt for a missed order `#545`
- Get contact details for the courier handling an order to track it `#935`

### 4. Verify phone/email to log in (37)

Customers need help verifying their mobile number or email (including getting OTPs) to log in, sign up, or complete a purchase, including issues with international numbers or lost access to an old number.

- Sign up for an account without a US phone number for verification `#39`
- Get help logging in to an account with a mobile number `#220`
- Find out why and how to verify mobile number and email to log in `#229`
- Get help logging in to the mobile app with a mobile number `#447`
- Sign up for an account using an international phone number `#489`
- Log in to an account using a mobile number `#537`

### 5. Return item for refund (35)

Customers want to return damaged, faulty, or unsatisfactory items, mostly for a refund and occasionally for a replacement or a refunded return shipping charge.

- Return a damaged item `#112`
- Return an item for a refund `#204`
- Return an item that wasn't as expected for a refund `#289`
- Return a damaged item for a refund `#514`
- Return a damaged item for a refund `#620`
- Return a damaged item for a refund `#982`

### 6. Return or exchange wrong item (30)

Customers want to return or exchange items that were the wrong model, color, or size, or that don't fit or aren't compatible, for a refund or the correct replacement.

- Exchange an item for a larger size `#37`
- Return an item that doesn't fit for a refund `#123`
- Exchange a wrong item received for the correct one `#227`
- Return an incorrect item received instead of the one ordered `#243`
- Resolve receiving the wrong item in an order `#578`
- Return an item that is the wrong size `#729`

### 7. Understand return policy and fees (30)

Customers ask about return policies, why they must ship items back, return shipping and pickup options, and fees or deductions from return refunds, including requests to waive fees or reimburse courier costs.

**Mixed with:** Requests to waive return fees or get reimbursed for return shipping, plus one request to remove an unwanted warranty charge from an invoice

- Find out a seller's return policy for an item before buying `#65`
- Find out why they were asked to ship an item back `#161`
- Find out why they were asked to ship back an item `#264`
- Find out why they were asked to ship an ordered item `#282`
- Return an unused item and get the return fee waived `#722`
- Find out why a return refund was less than the amount paid `#830`

### 8. Claim warranty on faulty item (29)

Customers want to file a warranty claim or get a repair for a faulty, broken, or defective item (including replacements), often without the warranty card or after a service center denied the repair.

- Claim warranty on an item after losing the warranty card `#11`
- Get a repair for an item after the service center denied the request `#155`
- Resolve a warranty terms mismatch and missing warranty card for an item `#349`
- Claim warranty for a malfunctioning item `#449`
- Claim the warranty for a faulty item `#776`
- Claim warranty on a defective replacement item `#872`

### 9. Get help installing an item (27)

Customers want guidance on installing, assembling, or setting up a purchased item, including who is responsible for installation, whether installation affects the warranty, and whether wall mount accessories are included or available.

- Get help setting up a newly received item `#8`
- Find out whether an ordered item includes a wall mount and how to get one `#83`
- Ask whether a wall mount accessory is available for purchase for an item `#164`
- Find out who is responsible for installing a purchased item `#169`
- Get help setting up an item `#645`
- Get help assembling an item delivered in parts from different sellers `#794`

### 10. Check item warranty details (27)

Customers want to find or access the warranty details for a purchased item, including coverage, warranty start date, and how changed warranty terms affect their item.

- Find out when the warranty on an item starts `#19`
- Find out the warranty details for a purchased item `#89`
- Access the warranty details for a purchased item `#151`
- Find out how changes to warranty terms affect an item's warranty `#165`
- Get the warranty details for an item `#692`
- Find out if the warranty covers a faulty item bought online `#959`

### 11. Check status of return refund (25)

Customers who returned an item want to know the status of their refund, why it hasn't arrived, or how long it will take, and want delayed or missing refunds processed.

- Check the status of a refund for a returned item `#44`
- Get help with a missing refund for a returned item `#183`
- Get a delayed refund for a returned item `#337`
- Find out how long a refund takes when returning an incompatible item `#386`
- Get a delayed refund for a returned item processed `#882`
- Check the status of a refund for a returned item `#998`

### 12. Check order status (22)

Customers want to confirm an order was placed or processed and find out its current or shipping status, including understanding what displayed order statuses mean.

- Check the status of an order `#60`
- Check the shipping status of an order `#190`
- Check the confirmation and status of an order `#302`
- Check the status of an order `#454`
- Check the confirmation and status of an order `#906`
- Check the status of an order `#952`

### 13. Get faster delivery (20)

Customers want to learn about or obtain expedited or faster shipping for an item or order, either before purchase or as an upgrade to an existing order.

- Get a faster delivery option for an order `#77`
- Get an item that can't ship to their location delivered faster `#122`
- Get faster delivery for an order to their location `#162`
- Get faster delivery for an item to their location `#314`
- Get faster delivery for an order `#379`
- Get faster delivery for an ordered item `#783`

### 14. Update order address details (16)

Customers want to change the pickup or delivery address for an order, or add a new delivery address to their account.

- Change the pick-up address for an order `#73`
- Change the pick-up address for an order `#350`
- Add a new delivery address to an account `#398`
- Change the pickup/delivery address for an order in transit `#582`
- Change the pickup address for an order `#651`
- Change the pickup address for an order `#971`

### 15. Pay or get refund via COD (16)

Customers want to use Cash on Delivery for purchases (often when it's unavailable) or return COD-paid items and learn how and when their refund arrives.

**Mixed with:** Questions about how instant cashback offers work and refund modes for canceled orders.

- Return a defective item for a refund of a Cash on Delivery payment `#41`
- Return an item from a Cash on Delivery order for a refund `#348`
- Pay for an item with cash on delivery, which isn't offered for it `#381`
- Get Cash on Delivery enabled for an item purchase `#781`
- Pay for an item with Cash on Delivery `#866`
- Find out how to pay cash on delivery for an item `#990`

### 16. Understand delivery charges (15)

Customers want to know the shipping cost and speed for an item, or why their order was charged a delivery fee instead of qualifying for free delivery.

- Find out the delivery charges for an item before purchasing `#110`
- Find out delivery charges and shipping speeds for an item `#139`
- Find out why an order was charged a delivery fee instead of qualifying for free delivery `#208`
- Find out why an item doesn't qualify for free delivery `#409`
- Find out why an order is not eligible for free delivery `#698`
- Find out the standard shipping charges for an item `#710`

### 17. Learn how to order and receive (14)

Customers want guidance on placing an order on the website and on how it will reach them, whether through delivery, scheduled or in-store pickup, or combining orders from different sellers into one shipment.

**Mixed with:** Placing an order and arranging pickup or delivery are both common; a smaller set asks to combine multi-seller orders to avoid double shipping charges.

- Learn how to schedule a pickup for an item `#62`
- Learn the in-store pickup process for an order `#105`
- Learn how to place an order for an item `#267`
- Schedule a pickup for an ordered item `#471`
- Learn how to place an order for an item on the website `#699`
- Get help placing an order for an item on the website `#741`

### 18. Dispute an order overcharge (14)

Customers want unexpected extra charges or overcharges on an order explained and, in many cases, refunded or waived.

- Get a refund for an overcharge on an order `#80`
- Find out why an order was charged more than the listed price `#90`
- Find out why an order had unexpected extra charges `#118`
- Get a refund for an overcharge on an order `#126`
- Find out why an order had an unexpected extra charge `#488`
- Get a refund for an overcharge on an order `#565`

### 19. Reactivate an inactive account (14)

Customers want to restore access to accounts that were deactivated or went inactive so they can log in or make purchases, while a few want to deactivate their account.

**Mixed with:** Requests to deactivate an account

- Reactivate an inactive account to make a purchase `#32`
- Deactivate an account `#111`
- Deactivate an account `#391`
- Reactivate an inactive account to regain login access `#434`
- Reactivate a deactivated account `#733`
- Deactivate an account `#777`

### 20. Cancel an order (14)

Customers want to cancel orders that are still processing or unshipped, often because they no longer need them, found a better deal, or the online cancel button isn't working.

- Cancel an order when the cancel button won't work `#2`
- Cancel an order that can't be cancelled online `#128`
- Cancel an order that has not shipped yet `#246`
- Cancel an order `#307`
- Cancel an order that has not shipped yet `#661`
- Get an approved but unshipped order shipped urgently `#663`

### 21. Explain inconsistent item pricing (14)

Customers want to know why the same item appears at different prices across listings, pages, checkout, over time, or compared with what others paid, and sometimes want the discrepancy resolved.

- Report inconsistent prices for the same item on the website `#86`
- Report inconsistent pricing for the same item and get it resolved `#99`
- Find out why an item shows different prices on the product and checkout pages `#209`
- Resolve a difference between the price paid and the advertised price for an item `#325`
- Find out why the same item is listed at different prices `#687`
- Find out why the same item has different prices `#689`

### 22. Ship item to unavailable location (13)

Customers want to know whether an item can be shipped to their country or location, often internationally, and to get it ordered or delivered despite it showing as unavailable there.

- Get an item shipped to a location where it is unavailable for delivery `#42`
- Get an item shipped to a location where it is listed as unavailable for shipping `#234`
- Order an item that shows as unavailable for shipping to their location `#323`
- Find out whether an item can be shipped internationally `#464`
- Find the international shipping option for an item `#694`
- Order an item that is unavailable for shipping to their location `#874`

### 23. Register item for warranty (12)

Customers want to register a purchased item with the brand for warranty benefits or sign up for an extended warranty on it.

- Learn how to register an item for warranty benefits `#100`
- Learn how to register an item for warranty `#114`
- Find out how to register an item with the brand for warranty `#132`
- Sign up for an extended warranty on a purchased item `#247`
- Register an item with the brand for warranty benefits `#878`
- Sign up for an extended warranty on a purchased item `#950`

### 24. Get missing verification code (12)

Customers are not receiving the verification code or link needed to complete a purchase or log into their account and want it resent or the issue fixed.

- Get a verification code to log into an account `#22`
- Fix not receiving the verification code needed to complete a purchase `#131`
- Get account verified to log in after not receiving a verification code `#270`
- Get a verification code that was not received for an order `#306`
- Get a verification code that isn't arriving so a purchase can be completed `#690`
- Get help receiving a verification code for an order `#704`

### 25. Get exchange offer discount (12)

Customers want to learn about or have exchange (trade-in) offer discounts applied to new or existing orders, including missed or promised discounts.

**Mixed with:** A couple of requests for other discounts, such as a price-drop adjustment or an additional discount on an item.

- Get the promised exchange-offer discount applied when exchanging an item `#102`
- Learn how to use an exchange offer when buying an item `#146`
- Apply a missed exchange offer discount to an existing order `#215`
- Get an additional discount on an item `#235`
- Get an exchange offer discount on a purchased item `#857`
- Get the promised exchange offer discount applied to an order `#862`

### 26. Unlock account after verification lockout (12)

Customers want to regain access to their BrownBox account after it was locked or blocked due to too many failed verification code attempts.

- Regain access to an account locked after too many verification code attempts `#3`
- Regain account access after exceeding verification code attempts `#101`
- Regain access to an account locked by too many verification code attempts `#321`
- Regain account access after exceeding verification code attempts `#490`
- Regain access to a locked account by resetting the verification code `#854`
- Fix an account login blocked by too many verification code attempts `#944`

### 27. Clarify conflicting warranty terms (11)

Customers want to know which warranty terms actually apply to an item when the retailer's website conflicts with the warranty card or the brand's website.

- Resolve a mismatch in warranty terms between the website and the warranty card `#141`
- Clarify conflicting warranty terms for an item `#299`
- Resolve a mismatch in warranty terms between the website and the warranty card `#468`
- Find out which of two conflicting warranty terms for an item is accurate `#865`
- Clarify conflicting warranty terms between the website and the warranty card `#967`
- Resolve a mismatch between the website's warranty terms and the brand's warranty terms for a purchased item `#997`

### 28. Change account email address (11)

Customers want to change, update, or add the email address linked to their account (or an order), often to regain login access after an email change.

- Add a new email address to an account `#218`
- Change the email address linked to an account `#255`
- Regain access to an account after changing email address `#589`
- Update the account email address to regain login access `#755`
- Change the email address linked to an account `#953`
- Change the email address used to log in to an account `#958`

### 29. Replace item from tampered package (11)

Customers received items in tampered or opened packages, sometimes damaged, used, or not working, and want to report it and get an exchange or replacement.

- Report an item delivered in a tampered package that appears used `#135`
- Report a tampered delivery package and get the possibly damaged item resolved `#181`
- Exchange an item that arrived in a tampered package for the same item `#330`
- Get a replacement for an item delivered in a tampered package `#539`
- Return or exchange an item delivered in a tampered package `#845`
- Exchange an item that arrived in a tampered, opened package for a new one `#977`

### 30. Check and redeem loyalty points (11)

Customers want to know how many loyalty points a purchase earned and how to redeem those points for discounts or items, including when a redemption fails on the website.

- Learn how to redeem loyalty points and what they can be used for `#75`
- Redeem reward points for an item `#87`
- Find out how many loyalty points a purchase earns `#487`
- Find out how many loyalty points were earned from a purchase `#748`
- Learn how to redeem loyalty points on a purchase `#964`
- Learn how to redeem loyalty points for a discount `#984`

### 31. Get out-of-stock item (9)

Customers want to know when an out-of-stock item will be restocked or want help ordering an item that is currently unavailable.

- Order an item that is out of stock `#7`
- Find out when an out-of-stock item will be available again `#78`
- Find out when an out-of-stock item will be available again `#205`
- Find out when an out-of-stock item will be available again `#317`
- Find out when an out-of-stock item will be available again `#594`
- Find out when an out-of-stock item will be available again `#885`

### 32. Get invoice for an order (9)

Customers want a missing or previously issued invoice for one or more past orders sent or resent to them.

- Get an invoice for a previous order `#47`
- Get invoices for previous orders sent `#70`
- Get a missing invoice for an order `#81`
- Obtain invoices for previous orders `#137`
- Get a missing invoice for an order `#217`
- Get invoices for previous orders resent `#750`

### 33. Change or reset password (8)

Customers want to change their account password or reset a forgotten password to regain access to their account.

- Change the password for an account `#106`
- Change the password for an account `#116`
- Change the password for an account `#647`
- Reset the password for an account they can't log into `#749`
- Reset a forgotten password to regain account access `#757`
- Change the password for an account `#835`

### 34. Check if account needed to buy (7)

Customers want to know whether they need an account to make a purchase, what the account requirements are, and how to create or verify one.

- Complete account verification to log in and make a purchase `#0`
- Find out whether an account is needed to make a purchase `#125`
- Find out whether an account is needed to shop and how to create one `#396`
- Learn the account requirements for making a purchase `#541`
- Find out whether an account is needed to make a purchase `#623`
- Find out whether an account is needed to buy an item and how to create one `#790`

### 35. Sign up with corporate email (6)

Customers want to create a BrownBox account using a corporate email address, including cases where the address is rejected during sign-up.

- Get help completing sign-up with a corporate email address `#74`
- Sign up for an account using a corporate email address `#276`
- Sign up for an account using a corporate email address `#358`
- Sign up for an account using a corporate email address that is being rejected `#436`
- Sign up for an account using a corporate email address `#586`
- Sign up for an account using a corporate email address `#925`

## Second requests

156 of 697 conversations (22%) have a second request.

- Order an item that is out of stock → **Find out when an out-of-stock item will be back in stock** `#7`
- Find out whether an account is needed to make a purchase → **Learn the return policy for an item** `#21`
- Find out the estimated delivery time for an order → **Expedite shipping for an order** `#23`
- Find tracking information for a shipped order → **Get expedited shipping or compensation for a delayed order** `#30`
- Find out when a delayed order will arrive → **Get compensation for a delayed delivery** `#36`
- Return a defective item for a refund of a Cash on Delivery payment → **Get return courier charges reimbursed** `#41`
- Check the delivery status of a delayed order → **Get a delayed order delivered faster** `#45`
- Get an invoice for a previous order → **Give feedback that invoices are hard to find on the website** `#47`
- Find out whether installation by BrownBox affects an item's warranty → **Get help installing an item** `#48`
- Return a defective item for a replacement → **Have the return fee waived for a defective item** `#54`
- Check the status of a refund for a returned item paid by cash on delivery → **Find out whether return shipping charges will be reimbursed** `#55`
- Resolve being unable to log in to the account with a mobile number → **Troubleshoot being unable to log in with the account password** `#71`
- Get a faster delivery option for an order → **Cancel the order for a refund** `#77`
- Find out when an out-of-stock item will be available again → **Place an order for an out-of-stock item** `#78`
- Find out whether an ordered item includes a wall mount and how to get one → **Check whether a wall mount accessory is compatible with an ordered item** `#83`

## Inform vs act

act 422 (61%), inform 275 (39%)

## Choosing the number of clusters

Silhouette (cosine) for each k. Higher means tighter, better-separated clusters. We over-cluster on purpose (k = 35) and merge by hand.

| k | silhouette |
|---|---|
| 15 | 0.227 |
| 20 | 0.249 |
| 25 | 0.278 |
| 30 | 0.291 |
| 35 | 0.315 |
| 40 | 0.335 |
| 45 | 0.344 |
| 50 | 0.360 |
| 55 | 0.376 |

## Spot-check: 10 random goals against the customer's own words

Check each goal says what the customer wanted, not how it ended.

**#42** goal: *Get an item shipped to a location where it is unavailable for delivery* (cluster 22)

> Hi Emily, I am trying to order a Wet Grinder from your website, but it's not available for shipping to my location. Can you help me with this?
> I live in a small town in Texas.

**#140** goal: *Return a defective item for a replacement* (cluster 1)

> Hi John, I received my food processor yesterday, but it's not working correctly. I want to return it and get a replacement.
> Sure, my order number is #987654321, and my email address is xyz@gmail.com.

**#155** goal: *Get a repair for an item after the service center denied the request* (cluster 8)

> Hi John, I have a problem with my refrigerator. It's not cooling, and I requested a repair, but the service center denied it. I'm really upset about it.
> Sure, my order number is #987654321, and my email address is xyz@gmail.com.

**#204** goal: *Return an item for a refund* (cluster 5)

> Hi, I recently received an electric kettle I ordered, but I'd like to return it and get a refund.
> Sure, it's BB123456789.

**#322** goal: *Get a verification code that isn't arriving for an order* (cluster 24)

> Hi Sarah, I'm having trouble receiving the OTP or verification code for my jeans order. This is really frustrating!
> Sure, my order number is BB789012, and my email address is john.doe@email.com.

**#354** goal: *Get a missing order that was marked delivered but never received* (cluster 3)

> Hi Sarah, I am calling to inquire about my order for a shirt. It was supposed to be delivered yesterday, but I haven't received it yet.
> The order number is #BB789034, and my name is Lily Smith.

**#404** goal: *Fix a problem logging into the app with a mobile number* (cluster 4)

> Hi John, I recently purchased a BP monitor from your website, and I'm having trouble logging in with my mobile number on the mobile app.
> It's the BP Monitor app.

**#804** goal: *Find out the status of a delayed refund for a returned damaged item* (cluster 11)

> Hello, I need assistance with my recent return and exchange request for a Kitchen Chimney.
> Yes, it's 123456789.

**#946** goal: *Get a refund for an overcharge on an order invoice* (cluster 18)

> Hi Rachel, I'm calling because I received an invoice for a ceiling fan that I purchased on your website, and I noticed that I was overcharged. I'm not happy about this.
> Yes, it's 123456.

**#993** goal: *Understand unexpected charges on an order bill* (cluster 18)

> Hi, I received my order for a shirt, but I noticed there are hidden charges on my bill. Can you help me understand what they are for?
> Sure, it's 123456.

