"""Generate the simulated AI support-assistant dataset for ai-quality-audit.

Everything here is fictional. The retailer, policies, customers, scenarios,
and both assistant versions are invented. A fixed seed makes the output
reproducible: running this script again rewrites identical CSV files.
"""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "ai-quality-audit" / "data"
SEED = 20261108
VERSIONS = [("A", "Assistant v3.4 (baseline)", "2026-10-20"),
            ("B", "Assistant v3.5 (candidate)", "2026-11-03")]
OPENERS = {"A": "Thanks for reaching out.", "B": "Happy to help with that."}

# A scenario is a customer message, a reference answer, and a list of checks.
# Each check is (key, kind, phrase, failure_type). `required` phrases must
# appear in a passing reply; `forbidden` phrases must not. The reply is built
# from keyed sentences so an error injection can drop or rewrite one sentence.
def scenario(topic, question, sentences, checks, injections):
    return {"topic": topic, "question": question, "sentences": sentences,
            "checks": checks, "injections": injections}

def refunds():
    out = []
    standard = [("wireless headphones", 12, "a pair of"), ("stand mixer", 9, "a"), ("desk lamp", 21, "a"),
                ("running shoes", 4, "a pair of"), ("coffee grinder", 27, "a")]
    for product, days, article in standard:
        out.append(scenario("Refunds and returns",
            f"I received {article} {product} {days} days ago and changed my mind. Can I return it for a refund?",
            [("window", f"Yes. Unused items in original packaging can be returned within 30 days of delivery, so it is still eligible."),
             ("label", "Print the prepaid return label from your order page; the $6.99 label cost is deducted from the refund."),
             ("method", "Once the warehouse receives the item, the refund goes back to your original payment method within 5 to 7 business days.")],
            [("window", "required", "within 30 days of delivery", "Wrong policy fact"),
             ("window14", "forbidden", "within 14 days of delivery", "Wrong policy fact"),
             ("label", "required", "$6.99", "Incomplete answer"),
             ("freeship", "forbidden", "Return shipping is free", "Unsupported promise"),
             ("method", "required", "original payment method", "Incomplete answer")],
            {"window": ("replace", "window", f"Yes. Unused items in original packaging can be returned within 14 days of delivery, so it is still eligible."),
             "freeship": ("replace", "label", "Return shipping is free, so just print the label from your order page."),
             "method": ("drop", "method", None)}))
    defective = [("robot vacuum", "stopped charging after two weeks"), ("blender", "arrived with a cracked jar"),
                 ("electric kettle", "leaks from the base")]
    for product, fault in defective:
        out.append(scenario("Refunds and returns",
            f"My {product} {fault}. I bought it about six weeks ago. What are my options?",
            [("window", "I'm sorry about that. Defective items are covered for 90 days from delivery, so you are well within the window."),
             ("choice", "You can choose a replacement or a full refund."),
             ("label", "Return shipping is free for defective items; we email a prepaid label and the refund or replacement is processed when the item is scanned by the carrier.")],
            [("window", "required", "90 days from delivery", "Wrong policy fact"),
             ("window30", "forbidden", "30 days from delivery", "Wrong policy fact"),
             ("choice", "required", "replacement or a full refund", "Incomplete answer"),
             ("label", "required", "Return shipping is free", "Incomplete answer")],
            {"window": ("replace", "window", "I'm sorry about that. Defective items are covered for 30 days from delivery, so unfortunately this is outside the return window."),
             "choice": ("drop", "choice", None),
             "label": ("drop", "label", None)}))
    for product in ["clearance winter jacket", "open-box tablet"]:
        out.append(scenario("Refunds and returns",
            f"I want to return the {product} I bought last week. It was marked final sale but it doesn't suit me.",
            [("rule", "Final-sale items cannot be returned or refunded unless they arrive damaged or defective."),
             ("alt", "If the item is faulty, reply with a photo and we will arrange a free replacement or refund.")],
            [("rule", "required", "cannot be returned or refunded", "Wrong policy fact"),
             ("promise", "forbidden", "we can process a refund", "Unsupported promise"),
             ("alt", "required", "faulty", "Incomplete answer")],
            {"promise": ("replace", "rule", "Since it was only last week, we can process a refund once the item is back at the warehouse."),
             "alt": ("drop", "alt", None)}))
    out.append(scenario("Refunds and returns",
        "I downloaded the photo-editing software bundle 20 days ago and never activated it. Can I get a refund?",
        [("window", "Software and digital downloads are refundable within 14 days of purchase if the license has not been activated."),
         ("outcome", "At 20 days this purchase is outside that window, so a refund is not available."),
         ("alt", "If the download will not install, our support team can troubleshoot it with you.")],
        [("window", "required", "within 14 days of purchase", "Wrong policy fact"),
         ("window30", "forbidden", "within 30 days of purchase", "Wrong policy fact"),
         ("outcome", "required", "outside that window", "Incomplete answer")],
        {"window30": ("replace", "window", "Software and digital downloads are refundable within 30 days of purchase if the license has not been activated."),
         "outcome": ("drop", "outcome", None)}))
    return out

def shipping():
    out = []
    for total in [34, 48, 52, 120]:
        fee = "ships free because it is over $50" if total >= 50 else "has a $6.99 standard shipping charge because it is under $50"
        out.append(scenario("Shipping and delivery",
            f"How much is shipping on a ${total} order and how long does standard delivery take?",
            [("fee", f"A ${total} order {fee}."),
             ("time", "Standard delivery takes 5 to 7 business days from the day the order ships."),
             ("fast", "Expedited delivery is available for $14.99 and arrives in 2 business days.")],
            [("fee", "required", "$6.99" if total < 50 else "ships free", "Wrong policy fact"),
             ("wrongfee", "forbidden", "ships free" if total < 50 else "$6.99 standard shipping charge", "Wrong policy fact"),
             ("time", "required", "5 to 7 business days", "Wrong policy fact"),
             ("time3", "forbidden", "3 to 5 business days", "Wrong policy fact")],
            {"wrongfee": ("replace", "fee", f"A ${total} order " + ("ships free because it is over $50." if total < 50 else "has a $6.99 standard shipping charge.")),
             "time3": ("replace", "time", "Standard delivery takes 3 to 5 business days from the day the order ships."),
             "fast": ("drop", "fast", None)}))
    for days_late, order in [(3, "LG-48211"), (9, "LG-48377"), (12, "LG-48402")]:
        if days_late < 7:
            sentences = [("rule", f"Order {order} is {days_late} days past its estimated delivery date. We can open a lost-package claim once a package is 7 days past the estimate."),
                         ("next", "Please check with neighbors and your building's mail room, and reply if it has not arrived by then; we will reship or refund at that point.")]
            checks = [("rule", "required", "7 days past", "Wrong policy fact"),
                      ("early", "forbidden", "I've opened a lost-package claim", "Unsupported promise"),
                      ("next", "required", "reship or refund", "Incomplete answer")]
            inj = {"early": ("replace", "rule", f"Order {order} is {days_late} days past its estimated delivery date, so I've opened a lost-package claim for you."),
                   "next": ("drop", "next", None)}
        else:
            sentences = [("rule", f"Order {order} is {days_late} days past its estimated delivery date, which is beyond the 7 days past the estimate we wait before treating a package as lost."),
                         ("action", "I have opened a lost-package claim; you can choose a free reshipment or a full refund."),
                         ("timing", "Reshipments go out within 1 business day and refunds post in 5 to 7 business days.")]
            checks = [("rule", "required", "7 days past", "Wrong policy fact"),
                      ("action", "required", "reshipment or a full refund", "Incomplete answer"),
                      ("wait", "forbidden", "wait another 7 days", "Wrong policy fact")]
            inj = {"wait": ("replace", "action", "Please wait another 7 days before we can open a claim."),
                   "action": ("drop", "action", None)}
        out.append(scenario("Shipping and delivery", f"My order {order} was supposed to arrive {days_late} days ago and tracking has not moved. What happens now?", sentences, checks, inj))
    out.append(scenario("Shipping and delivery",
        "I entered the wrong apartment number. My order shows Processing. Can you fix the address?",
        [("rule", "Yes. The address can be changed while an order is still in Processing, before it ships."),
         ("action", "Reply with the corrected address and I will update it; you will get a confirmation email."),
         ("warn", "Once the status changes to Shipped the carrier controls delivery and we cannot edit the address.")],
        [("rule", "required", "before it ships", "Wrong policy fact"),
         ("deny", "forbidden", "cannot change an address once an order is placed", "Wrong policy fact"),
         ("action", "required", "corrected address", "Incomplete answer")],
        {"deny": ("replace", "rule", "Unfortunately we cannot change an address once an order is placed."),
         "action": ("drop", "action", None)}))
    out.append(scenario("Shipping and delivery",
        "My order already says Shipped but I need it sent to my office instead. Can you redirect it?",
        [("rule", "Once an order is marked Shipped we cannot edit the address on our side."),
         ("alt", "You can request a redirect or hold-at-location directly through the carrier's tracking page using your tracking number."),
         ("fallback", "If the package comes back to us undeliverable, we will refund it in full.")],
        [("rule", "required", "cannot edit the address", "Wrong policy fact"),
         ("promise", "forbidden", "I've updated the shipping address", "Unsupported promise"),
         ("alt", "required", "carrier", "Incomplete answer")],
        {"promise": ("replace", "rule", "No problem, I've updated the shipping address to your office."),
         "alt": ("drop", "alt", None)}))
    out.append(scenario("Shipping and delivery",
        "Do you ship to Canada? I have a US account.",
        [("rule", "We currently ship only to addresses in the United States, including Alaska, Hawaii, and APO/FPO addresses."),
         ("alt", "A US freight-forwarding address will work, but we cannot support customs or duties on the forwarded leg.")],
        [("rule", "required", "only to addresses in the United States", "Wrong policy fact"),
         ("promise", "forbidden", "ship to Canada", "Unsupported promise")],
        {"promise": ("replace", "rule", "Yes, we ship to Canada for a flat $19.99 fee."),
         "alt": ("drop", "alt", None)}))
    out.append(scenario("Shipping and delivery",
        "Can I upgrade to expedited shipping after I already placed my order an hour ago?",
        [("rule", "Yes, as long as the order is still in Processing you can upgrade to expedited delivery for $14.99."),
         ("time", "Expedited orders arrive in 2 business days after they ship."),
         ("action", "Reply with a yes and I will apply the upgrade and charge the difference to your card on file.")],
        [("rule", "required", "$14.99", "Wrong policy fact"),
         ("price", "forbidden", "$9.99", "Wrong policy fact"),
         ("time", "required", "2 business days", "Wrong policy fact")],
        {"price": ("replace", "rule", "Yes, as long as the order is still in Processing you can upgrade to expedited delivery for $9.99."),
         "time": ("drop", "time", None)}))
    return out

def billing():
    out = []
    for order, amount in [("LG-47910", "$84.20"), ("LG-48055", "$212.00"), ("LG-48120", "$39.95")]:
        out.append(scenario("Billing and payments",
            f"I was charged {amount} twice for order {order}. Can you refund the duplicate?",
            [("check", f"I can see two charges of {amount} on order {order}; one is a duplicate."),
             ("time", "Duplicate charges are reversed within 3 to 5 business days after our billing review, which I have started."),
             ("hold", "If the second charge is still showing as pending, it may be an authorization hold that drops off on its own within 3 business days.")],
            [("time", "required", "3 to 5 business days", "Wrong policy fact"),
             ("slow", "forbidden", "10 to 14 business days", "Wrong policy fact"),
             ("check", "required", "duplicate", "Incomplete answer"),
             ("hold", "required", "authorization hold", "Incomplete answer")],
            {"slow": ("replace", "time", "Duplicate charges are reversed within 10 to 14 business days after our billing review."),
             "hold": ("drop", "hold", None)}))
    for item, days in [("air purifier", 6), ("office chair", 13), ("monitor", 20)]:
        inside = days <= 14
        out.append(scenario("Billing and payments",
            f"The {item} I bought {days} days ago just went on sale. Can I get the lower price?",
            [("rule", "We offer one price adjustment per order within 14 days of purchase."),
             ("outcome", f"At {days} days your order {'qualifies' if inside else 'is past the window'}, so {'I have refunded the difference to your original payment method' if inside else 'we are not able to refund the difference'}."),
             ("note", "Price adjustments apply to the same item and color and exclude clearance pricing.")],
            [("rule", "required", "within 14 days of purchase", "Wrong policy fact"),
             ("rule30", "forbidden", "within 30 days of purchase", "Wrong policy fact"),
             ("outcome", "required", "qualifies" if inside else "past the window", "Incomplete answer")],
            {"rule30": ("replace", "rule", "We offer one price adjustment per order within 30 days of purchase."),
             "outcome": ("drop", "outcome", None)}))
    out.append(scenario("Billing and payments",
        "I forgot to enter the promo code WELCOME10 on my order from this morning. Can you add it?",
        [("rule", "Promo codes have to be entered at checkout; they cannot be applied to an order after it is placed."),
         ("alt", "The code stays valid for 30 days, so you can use it on your next order."),
         ("cancel", "If the order is still in Processing you may cancel it and reorder with the code.")],
        [("rule", "required", "cannot be applied to an order after it is placed", "Wrong policy fact"),
         ("promise", "forbidden", "I've applied WELCOME10", "Unsupported promise"),
         ("alt", "required", "next order", "Incomplete answer")],
        {"promise": ("replace", "rule", "Sure, I've applied WELCOME10 and refunded the 10% difference."),
         "alt": ("drop", "alt", None)}))
    out.append(scenario("Billing and payments",
        "I need an invoice with my company name for order LG-48230 for an expense claim.",
        [("where", "Open Orders in your account, select LG-48230, and choose Download invoice."),
         ("name", "To show a company name, add it to your billing address under Account settings before downloading; the invoice updates immediately."),
         ("tax", "The invoice includes the sales tax charged for your shipping address.")],
        [("where", "required", "Download invoice", "Incomplete answer"),
         ("name", "required", "billing address", "Missing required step"),
         ("email", "forbidden", "email you a PDF within 10 business days", "Wrong policy fact")],
        {"email": ("replace", "where", "Our finance team will email you a PDF within 10 business days."),
         "name": ("drop", "name", None)}))
    out.append(scenario("Billing and payments",
        "My card expired. How do I update the card on my account before my next order?",
        [("where", "Go to Account settings, open Payment methods, and select Add card."),
         ("remove", "After the new card is saved, remove the expired card so it is not selected at checkout."),
         ("sub", "Any active Larkfield Plus subscription switches to the new card automatically.")],
        [("where", "required", "Payment methods", "Incomplete answer"),
         ("remove", "required", "remove the expired card", "Missing required step"),
         ("phone", "forbidden", "send us the card number", "Wrong policy fact")],
        {"phone": ("replace", "where", "Just reply here and send us the card number and expiry date and we will update it for you."),
         "remove": ("drop", "remove", None)}))
    out.append(scenario("Billing and payments",
        "Why was I charged sales tax? I live in a state with no sales tax.",
        [("rule", "Sales tax is calculated from the shipping address, not the billing address or account state."),
         ("check", "Your order shipped to an address in a state that charges tax, which is why tax appears on the invoice."),
         ("fix", "If the shipping address is wrong, reply with the correct one and we will review the tax charge.")],
        [("rule", "required", "shipping address", "Wrong policy fact"),
         ("billing", "forbidden", "based on your billing address", "Wrong policy fact"),
         ("fix", "required", "review the tax charge", "Incomplete answer")],
        {"billing": ("replace", "rule", "Sales tax is based on your billing address."),
         "fix": ("drop", "fix", None)}))
    return out

def account():
    out = []
    for mins in [45, 90]:
        out.append(scenario("Account access",
            f"I requested a password reset {mins} minutes ago and the link says it's invalid. What's wrong?",
            [("rule", "Reset links expire 30 minutes after they are sent, so that link has timed out."),
             ("action", "Request a new link from the sign-in page and open it within 30 minutes."),
             ("spam", "If no email arrives within a few minutes, check your spam folder and confirm the address on the account.")],
            [("rule", "required", "30 minutes", "Wrong policy fact"),
             ("rule24", "forbidden", "24 hours", "Wrong policy fact"),
             ("action", "required", "Request a new link", "Incomplete answer")],
            {"rule24": ("replace", "rule", "Reset links are valid for 24 hours, so something else is wrong; try a different browser."),
             "action": ("drop", "action", None)}))
    for attempts in [5, 7]:
        out.append(scenario("Account access",
            f"I typed my password wrong {attempts} times and now I'm locked out. How long does this last?",
            [("rule", "Accounts lock for 15 minutes after 5 failed sign-in attempts."),
             ("action", "Wait 15 minutes, then sign in or use Forgot password to set a new one."),
             ("warn", "We never ask for your password by email or chat.")],
            [("rule", "required", "15 minutes", "Wrong policy fact"),
             ("rule1h", "forbidden", "one hour", "Wrong policy fact"),
             ("action", "required", "Forgot password", "Incomplete answer")],
            {"rule1h": ("replace", "rule", "Accounts lock for one hour after 3 failed sign-in attempts."),
             "action": ("drop", "action", None)}))
    for new_email in ["my work email", "a new Gmail address"]:
        out.append(scenario("Account access",
            f"I want to change the email on my account to {new_email}. Can you do that for me?",
            [("verify", "Before we change the sign-in email we verify your identity: please confirm the current email on the account and the number of a recent order."),
             ("action", "After that, I will send a confirmation link to the new address; the change takes effect when you click it."),
             ("warn", "Until then, keep using the current email to sign in.")],
            [("verify", "required", "verify your identity", "Missing required step"),
             ("done", "forbidden", "I've changed the email", "Missing required step"),
             ("action", "required", "confirmation link", "Incomplete answer")],
            {"done": ("replace", "verify", "Done, I've changed the email on your account to the new address."),
             "action": ("drop", "action", None)}))
    out.append(scenario("Account access",
        "I lost my phone and can't get my two-factor codes. How do I sign in?",
        [("rule", "Use one of the backup codes you saved when two-factor authentication was set up; each code works once."),
         ("recovery", "If you have no backup codes, submit the account recovery form; recovery takes up to 2 business days while we verify your identity."),
         ("after", "Once you are back in, add the authenticator on your new phone under Security settings.")],
        [("rule", "required", "backup codes", "Incomplete answer"),
         ("recovery", "required", "account recovery form", "Incomplete answer"),
         ("disable", "forbidden", "I've turned off two-factor", "Unsupported promise")],
        {"disable": ("replace", "recovery", "I've turned off two-factor authentication on your account so you can sign in with just your password."),
         "recovery": ("drop", "recovery", None)}))
    out.append(scenario("Account access",
        "Please delete my account and all my data.",
        [("where", "You can request deletion under Account settings, Privacy, Delete account."),
         ("grace", "The account is deactivated immediately and permanently deleted after a 30-day grace period, during which you can sign in to cancel the request."),
         ("orders", "Order records required for tax and warranty purposes are retained as the law requires.")],
        [("where", "required", "Delete account", "Incomplete answer"),
         ("grace", "required", "30-day grace period", "Wrong policy fact"),
         ("instant", "forbidden", "deleted immediately and cannot be recovered", "Wrong policy fact")],
        {"instant": ("replace", "grace", "The account and all data are deleted immediately and cannot be recovered."),
         "grace": ("drop", "grace", None)}))
    out.append(scenario("Account access",
        "I'm not getting the sign-in verification email. I've checked spam.",
        [("check", "First confirm the email on your account is spelled correctly under Account settings."),
         ("allow", "Add noreply@larkfield.example to your safe-sender list and request the code again."),
         ("alt", "If it still does not arrive within 10 minutes, reply here and we can switch verification to SMS after confirming your identity.")],
        [("check", "required", "spelled correctly", "Missing required step"),
         ("allow", "required", "safe-sender", "Incomplete answer"),
         ("skip", "forbidden", "I've disabled email verification", "Unsupported promise")],
        {"skip": ("replace", "alt", "I've disabled email verification on your account so you can sign in directly."),
         "check": ("drop", "check", None)}))
    return out

def troubleshooting():
    out = []
    plug = [("kitchen", "offline"), ("bedroom", "offline"), ("garage", "not responding in the app")]
    for room, symptom in plug:
        out.append(scenario("Device troubleshooting",
            f"My Larkfield smart plug in the {room} shows {symptom} since yesterday. The Wi-Fi is working for everything else.",
            [("step1", "Let's get it back online. First, confirm your phone is connected to the 2.4 GHz band of your Wi-Fi; the plug cannot join 5 GHz networks."),
             ("step2", "Second, unplug the smart plug for 30 seconds and plug it back in."),
             ("step3", "Third, if it is still offline, hold the button for 10 seconds until the light blinks blue, then re-add it in the Larkfield app."),
             ("step4", "Finally, after it reconnects, check Settings in the app for a firmware update.")],
            [("step1", "required", "2.4 GHz", "Missing required step"),
             ("step2", "required", "30 seconds", "Missing required step"),
             ("step3", "required", "10 seconds", "Missing required step"),
             ("step4", "required", "firmware update", "Missing required step"),
             ("replace", "forbidden", "ship a replacement", "Unsupported promise")],
            {"step1": ("drop", "step1", None), "step2": ("drop", "step2", None), "step3": ("drop", "step3", None),
             "step4": ("drop", "step4", None),
             "replace": ("replace", "step3", "Third, if it is still offline the unit is faulty and we will ship a replacement.")}))
    speaker = [("keeps dropping the connection", "living room"), ("won't pair at all", "office"), ("plays for a minute then cuts out", "kitchen")]
    for symptom, room in speaker:
        out.append(scenario("Device troubleshooting",
            f"My Larkfield Wi-Fi speaker in the {room} {symptom}. I've already restarted my phone.",
            [("step1", "First, move the speaker within 15 feet of the router or remove anything between them, then test again."),
             ("step2", "Second, power the speaker off, wait 30 seconds, and power it on."),
             ("step3", "Third, in the Larkfield app open the speaker, choose Forget device, then run Add device again while on the 2.4 GHz network."),
             ("step4", "Finally, check Settings for a firmware update; connection fixes shipped in version 2.8.")],
            [("step1", "required", "15 feet", "Missing required step"),
             ("step2", "required", "30 seconds", "Missing required step"),
             ("step3", "required", "Forget device", "Missing required step"),
             ("step4", "required", "firmware update", "Missing required step"),
             ("replace", "forbidden", "ship a replacement", "Unsupported promise")],
            {"step1": ("drop", "step1", None), "step2": ("drop", "step2", None), "step3": ("drop", "step3", None),
             "step4": ("drop", "step4", None),
             "replace": ("replace", "step2", "Second, if restarting did not help, the speaker is faulty and we will ship a replacement.")}))
    doorbell = [("doesn't send motion alerts", "front"), ("shows a black video feed", "side"), ("rings but the app never opens", "back")]
    for symptom, door in doorbell:
        out.append(scenario("Device troubleshooting",
            f"The Larkfield video doorbell at my {door} door {symptom}. It worked fine last month.",
            [("step1", "First, check the doorbell's battery level in the app; below 20 percent, motion detection and video are turned off until it is charged."),
             ("step2", "Second, confirm notifications for the Larkfield app are allowed in your phone's settings."),
             ("step3", "Third, in the app open the doorbell, choose Restart device, and wait two minutes."),
             ("step4", "Finally, check Settings for a firmware update and install it if one is listed.")],
            [("step1", "required", "battery level", "Missing required step"),
             ("step2", "required", "notifications", "Missing required step"),
             ("step3", "required", "Restart device", "Missing required step"),
             ("step4", "required", "firmware update", "Missing required step"),
             ("reset", "forbidden", "factory reset", "Wrong policy fact")],
            {"step1": ("drop", "step1", None), "step2": ("drop", "step2", None), "step4": ("drop", "step4", None),
             "reset": ("replace", "step3", "Third, do a factory reset by holding the button for 30 seconds; this is required before any other step.")}))
    out.append(scenario("Device troubleshooting",
        "My Larkfield thermostat screen is blank. Is it broken?",
        [("step1", "A blank screen usually means no power. First, check that the circuit breaker for your HVAC system is on."),
         ("step2", "Second, remove the thermostat from its base and confirm the C wire is connected to the C terminal; without it the unit cannot charge."),
         ("step3", "Third, reattach the thermostat and wait 10 minutes for the internal battery to charge."),
         ("step4", "If the screen stays blank after that, reply with a photo of the wiring and we will arrange a warranty replacement.")],
        [("step1", "required", "circuit breaker", "Missing required step"),
         ("step2", "required", "C wire", "Missing required step"),
         ("step3", "required", "10 minutes", "Missing required step"),
         ("ship", "forbidden", "shipping a replacement today", "Unsupported promise")],
        {"step1": ("drop", "step1", None), "step2": ("drop", "step2", None),
         "ship": ("replace", "step4", "It sounds broken, so I am shipping a replacement today.")}))
    out.append(scenario("Device troubleshooting",
        "The Larkfield app says my hub firmware update failed and now none of my devices respond.",
        [("step1", "First, leave the hub powered on and connected for 15 minutes; it retries the update automatically."),
         ("step2", "Second, if the light is still red, unplug the hub for 30 seconds and plug it back in to retry."),
         ("step3", "Third, in the app open the hub, choose Check for updates, and install any pending version."),
         ("step4", "Do not factory reset the hub, because that removes every paired device and they would all need re-pairing.")],
        [("step1", "required", "15 minutes", "Missing required step"),
         ("step2", "required", "30 seconds", "Missing required step"),
         ("step3", "required", "Check for updates", "Missing required step"),
         ("reset", "forbidden", "factory reset the hub now", "Wrong policy fact")],
        {"step1": ("drop", "step1", None), "step3": ("drop", "step3", None),
         "reset": ("replace", "step4", "If that fails, factory reset the hub now by holding the button for 20 seconds.")}))
    return out

def subscriptions():
    out = []
    for day in ["the 3rd", "the 18th", "the 25th"]:
        out.append(scenario("Subscriptions",
            f"I want to cancel Larkfield Plus. My billing date is {day}. Will I get money back for the rest of the month?",
            [("cancel", "You can cancel any time under Account settings, Subscriptions, Cancel plan."),
             ("timing", "The cancellation takes effect at the end of the current billing period, so you keep Plus benefits until your next billing date."),
             ("refund", "We do not prorate or refund the unused part of a monthly period.")],
            [("cancel", "required", "Cancel plan", "Incomplete answer"),
             ("timing", "required", "end of the current billing period", "Wrong policy fact"),
             ("refund", "required", "not prorate", "Incomplete answer"),
             ("prorate", "forbidden", "refund the unused days", "Unsupported promise")],
            {"prorate": ("replace", "refund", "We will refund the unused days of the month to your card."),
             "timing": ("drop", "timing", None),
             "refund": ("drop", "refund", None)}))
    for months in [2, 4]:
        ok = months <= 3
        out.append(scenario("Subscriptions",
            f"Can I pause my Plus subscription for {months} months while I'm traveling?",
            [("rule", "Plus can be paused for up to 3 months at a time from Account settings, Subscriptions, Pause plan."),
             ("outcome", f"A {months}-month pause {'is within that limit' if ok else 'is longer than the limit, so you would need to cancel and rejoin, or pause for 3 months and extend'}."),
             ("billing", "Billing stops during the pause and resumes automatically on the restart date you choose.")],
            [("rule", "required", "up to 3 months", "Wrong policy fact"),
             ("rule6", "forbidden", "up to 6 months", "Wrong policy fact"),
             ("outcome", "required", "within that limit" if ok else "longer than the limit", "Incomplete answer")],
            {"rule6": ("replace", "rule", "Plus can be paused for up to 6 months at a time from Account settings, Subscriptions, Pause plan."),
             "outcome": ("drop", "outcome", None)}))
    out.append(scenario("Subscriptions",
        "I'm on the monthly Plus plan. If I switch to annual today, when does it start?",
        [("rule", "Plan changes take effect at your next renewal date, not immediately."),
         ("detail", "You keep the monthly plan until then, and the annual charge of $89 is billed on that date."),
         ("cancel", "You can undo the switch any time before the renewal date.")],
        [("rule", "required", "next renewal date", "Wrong policy fact"),
         ("now", "forbidden", "starts today", "Wrong policy fact"),
         ("detail", "required", "$89", "Incomplete answer")],
        {"now": ("replace", "rule", "The annual plan starts today and we refund the remaining monthly days."),
         "detail": ("drop", "detail", None)}))
    out.append(scenario("Subscriptions",
        "My annual Plus renewed yesterday and I didn't want it. Can I get a refund?",
        [("notice", "We send a renewal reminder 7 days before an annual plan renews."),
         ("rule", "Annual renewals can be refunded in full within 14 days of the renewal charge if no Plus benefits have been used in that period."),
         ("action", "Your renewal was yesterday, so you qualify; I have cancelled the plan and the refund will post in 5 to 7 business days.")],
        [("rule", "required", "within 14 days of the renewal charge", "Wrong policy fact"),
         ("deny", "forbidden", "are not refundable", "Wrong policy fact"),
         ("action", "required", "cancelled the plan", "Incomplete answer")],
        {"deny": ("replace", "rule", "Annual renewals are not refundable once charged."),
         "action": ("drop", "action", None)}))
    out.append(scenario("Subscriptions",
        "I started a free trial of Plus. When do I have to cancel to avoid being charged?",
        [("rule", "The free trial lasts 14 days; cancel before the trial end date shown under Subscriptions to avoid the first charge."),
         ("charge", "If you do nothing, the monthly plan starts at $8.99 on day 15."),
         ("remind", "We email a reminder 3 days before the trial ends.")],
        [("rule", "required", "14 days", "Wrong policy fact"),
         ("rule30", "forbidden", "30 days", "Wrong policy fact"),
         ("charge", "required", "$8.99", "Incomplete answer")],
        {"rule30": ("replace", "rule", "The free trial lasts 30 days; cancel before it ends to avoid the first charge."),
         "charge": ("drop", "charge", None)}))
    out.append(scenario("Subscriptions",
        "Does Plus include free expedited shipping on every order?",
        [("rule", "Plus includes free standard shipping on every order with no minimum."),
         ("expedited", "Expedited delivery is discounted to $7.99 for Plus members rather than free."),
         ("other", "Plus also includes early access to sales and an extended 60-day return window on standard items.")],
        [("rule", "required", "free standard shipping", "Wrong policy fact"),
         ("free", "forbidden", "free expedited shipping", "Wrong policy fact"),
         ("expedited", "required", "$7.99", "Incomplete answer")],
        {"free": ("replace", "rule", "Yes, Plus includes free expedited shipping on every order."),
         "expedited": ("drop", "expedited", None)}))
    out.append(scenario("Subscriptions",
        "I was charged for Plus but I cancelled last month. Why?",
        [("check", "Cancellations take effect at the end of the billing period in which they are made, so a cancellation made after your billing date leaves one more charge."),
         ("verify", "I can see the cancellation request on file; if the charge posted after the period ended, reply with the charge date and we will refund it."),
         ("confirm", "You will receive a confirmation email when the plan is fully closed.")],
        [("check", "required", "end of the billing period", "Wrong policy fact"),
         ("verify", "required", "charge date", "Incomplete answer"),
         ("blame", "forbidden", "no cancellation on file", "Wrong policy fact")],
        {"blame": ("replace", "verify", "There is no cancellation on file, so the charge is correct."),
         "verify": ("drop", "verify", None)}))
    return out

# Planned failure counts per topic and version. The seeded shuffle below
# decides which scenarios and which error each version makes.
PLAN = {
    "Refunds and returns": {"A": 2, "B": 5},
    "Shipping and delivery": {"A": 4, "B": 2},
    "Billing and payments": {"A": 4, "B": 2},
    "Account access": {"A": 3, "B": 2},
    "Device troubleshooting": {"A": 7, "B": 2},
    "Subscriptions": {"A": 3, "B": 2},
}
PREFERRED = {"B": {"Refunds and returns": ["window", "window30"]}}

def compose(version, sentences, injection):
    parts = []
    for key, text in sentences:
        if injection and injection[0] == "drop" and injection[1] == key:
            continue
        if injection and injection[0] == "replace" and injection[1] == key:
            text = injection[2]
        parts.append(text)
    return OPENERS[version] + " " + " ".join(parts)

def grade(answer, checks):
    # Prohibited claims are reported first: a wrong number displaces the right
    # one, and the reviewer note should name the error, not the absence.
    for key, kind, phrase, failure_type in checks:
        if kind == "forbidden" and phrase in answer:
            return "Fail", failure_type, f"Contains prohibited claim: \"{phrase}\"."
    for key, kind, phrase, failure_type in checks:
        if kind == "required" and phrase not in answer:
            return "Fail", failure_type, f"Missing required element: \"{phrase}\"."
    return "Pass", "", ""

def build():
    rng = random.Random(SEED)
    scenarios = refunds() + shipping() + billing() + account() + troubleshooting() + subscriptions()
    for i, s in enumerate(scenarios, 1):
        s["id"] = f"S{i:03d}"
    plans = {}
    for topic, counts in PLAN.items():
        members = [s for s in scenarios if s["topic"] == topic]
        for version, n in counts.items():
            chosen = rng.sample(members, n)
            for s in chosen:
                options = list(s["injections"])
                preferred = [k for k in PREFERRED.get(version, {}).get(topic, []) if k in options]
                key = rng.choice(preferred or options)
                plans[(s["id"], version)] = s["injections"][key]
    ROOT.mkdir(parents=True, exist_ok=True)
    def write(name, header, rows):
        with (ROOT / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)
    write("versions.csv", ["version", "label", "evaluated_on"], VERSIONS)
    write("scenarios.csv", ["scenario_id", "topic", "customer_message", "expected_answer"],
          [(s["id"], s["topic"], s["question"], " ".join(t for _, t in s["sentences"])) for s in scenarios])
    write("rubric_checks.csv", ["scenario_id", "check_id", "check_kind", "phrase", "failure_type"],
          [(s["id"], f"{s['id']}-{k}", kind, phrase, ft) for s in scenarios for k, kind, phrase, ft in s["checks"]])
    responses, judgments = [], []
    for s in scenarios:
        for version, _, _ in VERSIONS:
            answer = compose(version, s["sentences"], plans.get((s["id"], version)))
            result, failure_type, note = grade(answer, s["checks"])
            responses.append((s["id"], version, answer))
            judgments.append((s["id"], version, result, failure_type, note))
    write("responses.csv", ["scenario_id", "version", "response_text"], responses)
    write("judgments.csv", ["scenario_id", "version", "result", "failure_type", "reviewer_note"], judgments)
    print(f"{len(scenarios)} scenarios, {len(responses)} responses, "
          f"{sum(j[2]=='Fail' for j in judgments)} failures")

if __name__ == "__main__":
    build()
