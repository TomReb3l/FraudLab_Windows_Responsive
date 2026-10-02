# Station 4 v0.4.4 — Research-Derived Fallback Corpus

This release moves the visitor-facing fallback layer into a separate authored
corpus. It is designed for public-exhibition reliability.

## Research basis

The patterns were derived from:
- Hellenic Police public advisories on accident/emergency telephone scams,
- Hellenic Police case reports involving fake doctors and injured relatives,
- FTC family-emergency scam guidance,
- Greek community reports used only as supplementary qualitative context.

The corpus does **not** reproduce real scam scripts verbatim. It captures
high-level conversational patterns while deliberately excluding:
- real institutions or brands,
- real payment destinations,
- IBANs,
- URLs,
- card data,
- OTP/PIN/CVV,
- real phone numbers.

## Locked scenario facts

- accident is claimed,
- relative is not seriously injured,
- own phone is unavailable,
- exact location remains unknown,
- demo amount is 480 EUR,
- payment destination is never specified,
- second speaker is a fictional generic case handler.

## Role handoff

Stages `establish` and `urgency` use the fictional relative role.

From `payment` onward, the corpus changes to a generic fictional
`case_handler`. The first response in that role includes an explicit handoff
sentence. The API returns `speaker_role`, `speaker_label`, and `role_handoff`
metadata so a future Windows/RTX voice provider can use a second synthetic
voice without redesigning the conversation engine.

## Reliability

All visitor-facing responses come from the approved corpus. The local LLM is
still allowed to classify ambiguous visitor language into a semantic topic,
but it does not generate the final response.
