# Reading notes: 25 DEV conversations (my own view, before any LLM output)

Read from `notes/reading-sample.md` (conversations 1–25). Written 2026-10-05, before discovery.

Bear in mind sometimes the agent starts conversation and sometimes the customer.

1. Intent is to understand shipping given they paid for expedited shipping haven't received it yet.
- Intent given on first customer turn
- Customer still not happy on turn 2
- Quite clean conversation, one intent only

2. Intent is in turn 1 - issue with dishwasher but not sure exactly what issue is
- After order number the full granularity of the issue is shown on turn 3 (wrong item received)
- Again very clean conversation one intent

3. First intent clear from turn 1 and domain (product issue - OTP code)
- Switches on turn 7 for customer to new intent but same product.

4. Domain is product issues - intent to understand product warranty online purchases
- Takes action to ask customer if they attempted to troubleshoot, they did, so agent moves to requesting technician visit.

5. Domain and intent on turn 1 to change address of an order (delivery issue)
- Then gets escalated to another agent on turn 5/6
- Shipping agent has to re-ask for order number (would be nice if this memory carried over during handoff)

6. Domain is order issues, intent to understand why they haven't received order yet
- Agent is a junior agent so can't expedite deliveries so hands off to a human

7. Domain is shipping, intent is shipping cost queries
- Agent offers to provide discount code without insisting they sign up to newsletter first (when they should)

8. Domain is product queries, intent to discover product warranty on turn 1

9. Domain is returns, intent to return item turn 1
- Agent assumes worn so can't be returned, corrected by customer they only tried them on
- Agent can't help initiate returns process itself.

10. Domain is exchanges. Intent to understand discount code on website for exchanges.
- Customer put on hold (for agent to check or human to check - not clear?)
- Agent puts discount code on after that

11. Domain is reward points / intent is to redeem them for certain product
- Customer not satisfied with agent outcome, agent escalated to senior team members (humans?)

12. Domain is invoices - intent is invoices for previous orders turn 1.
- Agent resolves it then passes feedback on

13. Domain order queries intent to understand where order is at in delivery process
- Agent recognises customer is unhappy so offers next order discount as resolution.

14. Intent turn 1 returns customer wants to return item
- Product not working so agent offers refund but customer unhappy they have to pay for refund
- Defective so agent waives refund fee

15. Intent turn 1 customer waiting for delivery not arrived and unhappy

16. Intent to purchase microwave needs agent help throughout.
- Agent helps customer fill out order form

17. Intent and domain turn 1 order status query in my orders section
- Another question same intent and domain half way through conversation

18. Domain product issue intent verification code on product
- Agent escalated to verification team for help (verification agent receives conversation now)
- Resolved by verification agent

19. Domain and intent first turn return it and get a refund. It was a Cash on Delivery order, so I'm not sure how to proceed.
- Resolved

20. Domain is purchasing requiring account first, intent is to buy product
- Sub question within conversation can I still make a purchase without creating an account

21. Domain loyalty points intent understand if they got loyalty points for washing machine purchase.
- Also asks Can you please guide me on how to redeem these points - agent helps

22. Domain is account issues - intent to reset password (fraud risk?)
- Agent asks for security answer from customer
- Agent puts customer on hold and changes password a placeholder password - this could be deemed risky. Would sending a password reset link for them to verify via email also be safer?

23. Domain product queries - intent to understand product warranty
- Agent helps provide contact details for support of manufacturer

24. Password reset request domain / intent to change
- provide me with your date of birth and the last four digits of your social security number? - agent asks this
- Agent suggests to change your password, please log in to your account, click on the "Settings" option, and then select "Change Password."
- Agent confirms technical issue customer facing when attempting to change password (escalates to technical team)

25. Domain is deliveries - intent to understand faster delivery options
- Resolved by offering in store pickup.
