# Capability Matrix

Infer possible WeChat capabilities from the user's requirement and record them in `current-plan.md`. Persist them to `profile.yaml` only after the user confirms they are real project facts.

| Capability | Trigger Clues | Usually Requires |
|---|---|---|
| Login | user accounts, profiles, saved state, member area | AppID, privacy notes, auth flow decision |
| Phone number authorization | phone binding, contact, SMS-free registration | AppID, permission reason, privacy guide |
| Payment | checkout, order, recharge, membership purchase | merchant/payment config, backend or cloud function, review category fit |
| Subscribe messages | reminders, booking notifications, status updates | message templates, user opt-in, review copy |
| Image upload | avatar, album, proof image, product photos | media storage, size limits, security check |
| User-generated content | posts, comments, uploads, reviews | content security, moderation policy, collection permissions |
| Content security | public text, image, audio, video, UGC | WeChat security API or cloud checks |
| Location | nearby stores, map, delivery address, check-in | location permission reason, privacy guide |
| Share | invite, referral, sharing pages | share path design, poster or card metadata |
| Cloud functions | server-side logic, database writes, secrets, privileged operations | cloud environment, function naming, error contract |
| Privacy and review | personal data, permissions, payment, UGC, location | privacy protection guide, service category, review instructions |

When multiple capabilities are plausible, mark them as `inferred` in the plan and ask for confirmation only when implementation depends on the answer.

