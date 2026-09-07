# Privacy and Vision AI Tests

**Version:** 1.0.0
**Owner:** Member 2 - Local Privacy + Vision AI

---

## 1. Purpose

This document defines the testing strategy for the Local Privacy + Vision AI module.

The Privacy module is responsible for:

* Detecting sensitive information.
* Detecting PII.
* Detecting passwords.
* Detecting faces.
* Redacting sensitive information from screenshots.
* Sanitizing sensitive information from DOM.
* Extracting safe visual elements.
* Verifying that sanitized data contains no exposed sensitive information.
* Blocking transmission when privacy verification fails.

---

# 2. Core Privacy Principle

The most important rule is:

> **RAW PRIVATE DATA MUST NEVER BE SENT TO THE SERVER.**

The Privacy module must process data locally before any server communication.

Correct flow:

```text
Raw Screenshot + DOM
        |
        v
Sensitive Data Detection
        |
        v
Redaction / Sanitization
        |
        v
Privacy Verification
        |
        v
Sanitized Screenshot + DOM
        |
        v
Server
```

Incorrect flow:

```text
Raw Screenshot + DOM
        |
        v
Server
```

---

# 3. Privacy Test Categories

The following areas must be tested:

```text
1. PII Detection
2. Password Detection
3. Face Detection
4. Screenshot Redaction
5. DOM Sanitization
6. Visual Element Detection
7. Privacy Verification
8. Privacy Boundary
9. False Positive / False Negative Testing
10. Performance Testing
```

---

# 4. Test Data

Use only synthetic test data.

Example:

```text
Name:
Fake Person

Email:
test@example.com

Phone:
9000000000

Password:
FakePassword123

Government ID:
TEST-ID-123456

Card:
4111111111111111
```

These values are for testing only.

Do not use:

* Real passwords
* Real credit/debit cards
* Real government IDs
* Real personal documents
* Real private photographs
* Real user credentials

---

# 5. PII Detection Tests

## PRIV-PII-001

**Test:** Detect a personal name.

### Input

```text
Name: Fake Person
```

### Expected Result

```text
Detected:
PERSON
```

**Status:**

```text
NOT TESTED
```

---

## PRIV-PII-002

**Test:** Detect an email address.

### Input

```text
Email: test@example.com
```

### Expected Result

```text
Detected:
EMAIL
```

**Status:**

```text
NOT TESTED
```

---

## PRIV-PII-003

**Test:** Detect a phone number.

### Input

```text
Phone: 9000000000
```

### Expected Result

```text
Detected:
PHONE
```

**Status:**

```text
NOT TESTED
```

---

## PRIV-PII-004

**Test:** Detect government ID pattern.

### Input

```text
Government ID: TEST-ID-123456
```

### Expected Result

```text
Detected:
GOVERNMENT_ID
```

**Status:**

```text
NOT TESTED
```

---

## PRIV-PII-005

**Test:** Detect payment-card pattern.

### Input

```text
Card: 4111111111111111
```

### Expected Result

```text
Detected:
CREDIT_CARD
```

**Status:**

```text
NOT TESTED
```

---

# 6. Password Detection Tests

## PRIV-PASS-001

**Test:** Detect password field in DOM.

### Input

```html
<input
  type="password"
  value="FakePassword123"
/>
```

### Expected Result

```text
Detected:
PASSWORD
```

The actual password value must not appear in sanitized output.

**Status:**

```text
NOT TESTED
```

---

## PRIV-PASS-002

**Test:** Detect password visually in screenshot.

### Expected Result

Password region is detected and redacted.

**Status:**

```text
NOT TESTED
```

---

# 7. Face Detection Tests

## PRIV-FACE-001

**Test:** Detect a face in a webpage screenshot.

### Expected Result

```text
Face region detected.
```

The detected region should be marked for redaction according to the configured privacy policy.

**Status:**

```text
NOT TESTED
```

---

## PRIV-FACE-002

**Test:** Verify face redaction.

### Expected Result

```text
Original face
      ↓
Detection
      ↓
Redaction
      ↓
Face is no longer identifiable
```

**Status:**

```text
NOT TESTED
```

---

# 8. Screenshot Redaction Tests

## PRIV-RED-001

**Test:** Redact email shown in screenshot.

### Before

```text
Email: test@example.com
```

### After

```text
Email: [EMAIL]
```

**Expected Result:**

Original email cannot be read from the sanitized screenshot.

**Status:**

```text
NOT TESTED
```

---

## PRIV-RED-002

**Test:** Redact password shown in screenshot.

### Before

```text
Password: FakePassword123
```

### After

```text
Password: [REDACTED]
```

**Expected Result:**

Password is not readable.

**Status:**

```text
NOT TESTED
```

---

## PRIV-RED-003

**Test:** Redact face region.

### Expected Result

The configured redaction method is applied to the detected face.

**Status:**

```text
NOT TESTED
```

---

# 9. DOM Sanitization Tests

## PRIV-DOM-001

**Test:** Sanitize email from DOM.

### Before

```html
<div>
  Email: test@example.com
</div>
```

### Expected

```html
<div>
  Email: [EMAIL]
</div>
```

**Status:**

```text
NOT TESTED
```

---

## PRIV-DOM-002

**Test:** Sanitize password from DOM.

### Before

```html
<input
  type="password"
  value="FakePassword123"
/>
```

### Expected

```text
Password value is removed or replaced with [REDACTED].
```

**Status:**

```text
NOT TESTED
```

---

## PRIV-DOM-003

**Test:** Sanitize phone number.

### Before

```text
Phone: 9000000000
```

### Expected

```text
Phone: [PHONE]
```

**Status:**

```text
NOT TESTED
```

---

## PRIV-DOM-004

**Test:** Sanitize personal name.

### Before

```text
Name: Fake Person
```

### Expected

```text
Name: [PERSON]
```

**Status:**

```text
NOT TESTED
```

---

# 10. Visual Element Detection Tests

The Privacy module should preserve useful webpage structure while removing sensitive information.

## PRIV-VISUAL-001

**Test:** Detect button.

### Input

```html
<button id="upload-btn">
  Upload Document
</button>
```

### Expected Output

```json
{
  "type": "button",
  "label": "Upload Document",
  "id": "upload-btn"
}
```

**Status:**

```text
NOT TESTED
```

---

## PRIV-VISUAL-002

**Test:** Detect input field.

### Expected Result

```text
Input field detected.
```

Sensitive values must not be included.

**Status:**

```text
NOT TESTED
```

---

## PRIV-VISUAL-003

**Test:** Detect links.

### Expected Result

Safe link information can be preserved.

Sensitive text contained in the link must be sanitized where required.

**Status:**

```text
NOT TESTED
```

---

# 11. Privacy Verification Tests

Privacy verification happens immediately before sending data to the Server.

## PRIV-VERIFY-001

**Test:** Verify sanitized DOM.

### Expected Result

No known sensitive values remain.

```text
PASS
```

**Status:**

```text
NOT TESTED
```

---

## PRIV-VERIFY-002

**Test:** Verify sanitized screenshot.

### Expected Result

Sensitive visual regions have been properly redacted.

**Status:**

```text
NOT TESTED
```

---

## PRIV-VERIFY-003

**Test:** Block transmission when sensitive data remains.

### Scenario

Privacy verification detects:

```text
test@example.com
```

still present in sanitized data.

### Expected Result

```text
Privacy Verification
        ↓
FAIL
        ↓
BLOCK SERVER REQUEST
```

**Status:**

```text
NOT TESTED
```

---

# 12. Critical Privacy Boundary Test

## PRIV-CRITICAL-001

This is one of the most important tests in the entire project.

### Input

```text
Name: Fake Person
Email: test@example.com
Password: FakePassword123
```

### Processing

```text
Raw Data
   ↓
Detection
   ↓
Redaction
   ↓
Verification
```

### Expected Output

```text
Name: [PERSON]
Email: [EMAIL]
Password: [REDACTED]
```

### Server Payload

The Server payload must NOT contain:

```text
Fake Person
test@example.com
FakePassword123
```

### Expected Result

```text
RAW PRIVATE DATA = NOT FOUND
```

If any raw sensitive value reaches the Server:

```text
TEST = FAIL
SEVERITY = CRITICAL
```

**Status:**

```text
NOT TESTED
```

---

# 13. False Positive Tests

The Privacy module should avoid unnecessarily redacting safe information.

Examples:

```text
Company Name
Public Website URL
Public Button Text
Public Documentation
Public Product Name
```

### Expected Result

Safe information remains available to the AI when it is not sensitive.

**Status:**

```text
NOT TESTED
```

---

# 14. False Negative Tests

A false negative occurs when sensitive information exists but is not detected.

Examples:

```text
Email not detected
Password not detected
Phone not detected
Face not detected
```

### Expected Result

Sensitive information should be detected according to the supported detection rules.

False negatives should be recorded and used to improve the detection system.

**Status:**

```text
NOT TESTED
```

---

# 15. Detection Metrics

For the evaluation dataset, record:

### True Positive

Sensitive information correctly detected.

### False Positive

Safe information incorrectly detected as sensitive.

### False Negative

Sensitive information missed.

### True Negative

Safe information correctly left unchanged.

---

## Precision

```text
Precision =
True Positives /
(True Positives + False Positives)
```

---

## Recall

```text
Recall =
True Positives /
(True Positives + False Negatives)
```

Record these values for the final evaluation.

---

# 16. Redaction Quality Tests

Measure:

```text
Correctly redacted sensitive regions
Incorrectly redacted safe regions
Missed sensitive regions
```

The goal is:

```text
High sensitive-data protection
+
Low unnecessary redaction
```

---

# 17. Privacy Bypass Tests

Test whether sensitive information can accidentally bypass sanitization.

Try:

```text
DOM text
HTML attributes
Input values
Placeholder text
Accessibility labels
Screenshot text
Screenshot regions
Hidden form values
```

### Expected Result

Sensitive information that falls within the supported detection scope must be protected before transmission.

**Status:**

```text
NOT TESTED
```

---

# 18. Empty / Normal Page Test

## PRIV-NORMAL-001

**Test:** Process a webpage containing no obvious sensitive information.

### Expected Result

```text
No unnecessary redaction.
Normal webpage structure preserved.
```

**Status:**

```text
NOT TESTED
```

---

# 19. Large Page Test

## PRIV-PERF-001

**Test:** Process a large webpage.

Measure:

```text
Screenshot processing time
DOM sanitization time
Detection time
Redaction time
Memory usage
CPU/GPU usage
```

### Expected Result

Processing completes without browser crashes or excessive resource usage.

**Status:**

```text
NOT TESTED
```

---

# 20. Privacy Processing Failure

## PRIV-ERROR-001

**Test:** Simulate Privacy module failure.

### Expected Result

```text
Privacy Processing
       ↓
FAIL
       ↓
No Server Request
       ↓
Safe Error
```

Raw webpage data must not be transmitted as a fallback.

**Status:**

```text
NOT TESTED
```

---

# 21. Complete Privacy Test

## PRIV-E2E-001

### Webpage

```text
Name: Fake Person
Email: test@example.com
Phone: 9000000000
Password: FakePassword123

[Upload Document]
[Submit]
```

### User Instruction

```text
Find the upload button
```

### Expected Processing

```text
Screenshot + DOM
       ↓
PII Detection
       ↓
Password Detection
       ↓
Face Detection
       ↓
Redaction
       ↓
DOM Sanitization
       ↓
Privacy Verification
       ↓
Sanitized Context
```

### Expected Sanitized Data

```text
Name: [PERSON]
Email: [EMAIL]
Phone: [PHONE]
Password: [REDACTED]

[Upload Document]
[Submit]
```

### Expected Result

The useful webpage structure remains available while sensitive information is protected.

**Status:**

```text
NOT TESTED
```

---

# 22. Privacy Test Checklist

Before the Privacy module is considered complete:

* [ ] Name detection works.
* [ ] Email detection works.
* [ ] Phone detection works.
* [ ] Government ID detection works.
* [ ] Credit-card pattern detection works.
* [ ] Password detection works.
* [ ] Face detection works.
* [ ] Screenshot redaction works.
* [ ] DOM sanitization works.
* [ ] Visual elements are preserved.
* [ ] Privacy verification works.
* [ ] Privacy verification can block transmission.
* [ ] Raw PII cannot reach the Server.
* [ ] False positives are measured.
* [ ] False negatives are measured.
* [ ] Precision is measured.
* [ ] Recall is measured.
* [ ] Redaction quality is measured.
* [ ] Processing performance is measured.
* [ ] Privacy failures are handled safely.

---

# 23. Final Acceptance Criteria

The Privacy module is considered ready when:

```text
✓ Sensitive information is detected
✓ Sensitive information is redacted
✓ DOM is sanitized
✓ Useful webpage structure is preserved
✓ Privacy verification works
✓ Failed verification blocks transmission
✓ Raw PII cannot reach the Server
✓ Precision and recall are measured
✓ Redaction quality is measured
✓ Resource usage is measured
✓ Privacy failures are handled safely
```

---

# 24. Most Important Rule

The Privacy module must always follow:

```text
COLLECT
   ↓
DETECT
   ↓
REDACT
   ↓
SANITIZE
   ↓
VERIFY
   ↓
SEND ONLY SAFE DATA
```

> **If privacy verification fails, the Server request must be blocked.**
