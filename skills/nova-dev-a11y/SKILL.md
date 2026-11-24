---
name: nova-dev-a11y
description: Accessibility check for UI changes: labels, keyboard use, focus, contrast, alt text, and screen reader names. Use for "nova dev a11y" or any change to a page, form or component.
---

# Nova Dev A11y

For each changed UI element, check:

1. **Name:** every control has a visible label or `aria-label`. Icons-only buttons have a name.
2. **Keyboard:** reachable with Tab, activated with Enter/Space, no keyboard trap. Custom widgets have the right role.
3. **Focus:** a visible focus style. Not removed with `outline: none` without a replacement.
4. **Contrast:** text against background at least 4.5:1 (3:1 for large text). Check any new colors.
5. **Images:** meaningful alt text; decorative images use empty alt.
6. **Forms:** each input has a label; errors are announced and tied to the field.
7. **Motion and size:** no required motion; touch targets at least 44px.

Report each failing item with file:line, the user impact, and the smallest fix. If nothing fails in the changed elements, say which ones you checked. End with Skipped / Risk.
