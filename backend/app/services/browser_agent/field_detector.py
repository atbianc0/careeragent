from __future__ import annotations

import re
from typing import Any

SENSITIVE_FIELD_KEYS = {
    "race_ethnicity",
    "gender",
    "disability",
    "veteran_status",
    "ssn",
    "date_of_birth",
    "unknown_sensitive",
}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _combined_text(field: dict[str, Any]) -> str:
    pieces = [
        field.get("tag"),
        field.get("input_type"),
        field.get("name"),
        field.get("id"),
        field.get("placeholder"),
        field.get("aria_label"),
        field.get("label_text"),
        field.get("nearby_text"),
        field.get("choice_text"),
        " ".join(field.get("options") or []),
    ]
    return _normalize_text(" ".join(str(piece or "") for piece in pieces))


def _field_result(
    field_key: str,
    confidence: float,
    safe_to_fill: bool,
    reason: str,
) -> tuple[str, float, bool, str]:
    return field_key, confidence, safe_to_fill, reason


def _classify_detected_field(field: dict[str, Any]) -> tuple[str, float, bool, str]:
    tag = _normalize_text(field.get("tag"))
    input_type = _normalize_text(field.get("input_type"))
    text = _combined_text(field)
    options_text = _normalize_text(" ".join(field.get("options") or []))

    if input_type == "password":
        return _field_result("unknown_sensitive", 0.99, False, "Password fields are never autofilled.")
    if any(token in text for token in ("social security", "ssn")):
        return _field_result("ssn", 0.99, False, "Sensitive identity field detected.")
    if any(token in text for token in ("date of birth", "birth date", "dob")):
        return _field_result("date_of_birth", 0.99, False, "Sensitive date-of-birth field detected.")
    if any(token in text for token in ("race", "ethnicity", "hispanic", "latino")):
        return _field_result("race_ethnicity", 0.98, False, "Demographic field detected.")
    if any(token in text for token in ("gender", "pronoun", "sex identity")):
        return _field_result("gender", 0.98, False, "Demographic field detected.")
    if "disability" in text:
        return _field_result("disability", 0.98, False, "Sensitive disability field detected.")
    if "veteran" in text or "military status" in text:
        return _field_result("veteran_status", 0.98, False, "Sensitive veteran-status field detected.")

    if input_type == "file":
        if any(token in text for token in ("resume", "cv", "curriculum vitae")):
            return _field_result("resume_upload", 0.99, True, "Matched resume upload field.")
        if "cover letter" in text:
            return _field_result("cover_letter_upload", 0.99, True, "Matched cover letter upload field.")
        return _field_result("unknown_question", 0.35, False, "Unknown file upload field.")

    if input_type == "email" or "email" in text:
        return _field_result("email", 0.99, True, "Matched email field.")
    if input_type == "tel" or any(token in text for token in ("phone", "mobile", "cell")):
        return _field_result("phone", 0.98, True, "Matched phone field.")
    if any(token in text for token in ("linkedin", "linked in")):
        return _field_result("linkedin", 0.98, True, "Matched LinkedIn field.")
    if "github" in text:
        return _field_result("github", 0.98, True, "Matched GitHub field.")
    if any(token in text for token in ("portfolio", "personal site", "website", "homepage")):
        return _field_result("portfolio" if "portfolio" in text else "website", 0.9, True, "Matched public link field.")

    if any(token in text for token in ("first name", "given name", "firstname")):
        return _field_result("first_name", 0.98, True, "Matched first-name field.")
    if any(token in text for token in ("last name", "family name", "surname", "lastname")):
        return _field_result("last_name", 0.98, True, "Matched last-name field.")
    if any(token in text for token in ("full name", "legal name", "your name", "applicant name")):
        return _field_result("full_name", 0.95, True, "Matched full-name field.")

    if any(token in text for token in ("street", "address line", "mailing address", "home address")):
        return _field_result("address", 0.92, True, "Matched address field.")
    if re.search(r"\bcity\b", text):
        return _field_result("city", 0.95, True, "Matched city field.")
    if any(token in text for token in ("state", "province", "region")):
        return _field_result("state", 0.92, True, "Matched state or province field.")
    if any(token in text for token in ("zip", "postal code", "postcode")):
        return _field_result("zip", 0.95, True, "Matched ZIP or postal code field.")
    if "country" in text:
        return _field_result("country", 0.94, True, "Matched country field.")

    if any(token in text for token in ("school", "university", "college")):
        return _field_result("school", 0.92, True, "Matched school field.")
    if any(token in text for token in ("degree", "major", "program of study")):
        return _field_result("degree", 0.9, True, "Matched degree field.")
    if any(token in text for token in ("graduation", "graduated", "grad date", "expected grad")):
        return _field_result("graduation_date", 0.92, True, "Matched graduation field.")

    if any(token in text for token in ("authorized to work", "work authorization", "legally authorized")):
        return _field_result("work_authorized_us", 0.97, True, "Matched work-authorization field.")
    if any(token in text for token in ("future sponsorship", "sponsorship in the future", "future visa sponsorship")):
        return _field_result("need_sponsorship_future", 0.96, True, "Matched future-sponsorship field.")
    if any(token in text for token in ("need sponsorship", "require sponsorship", "visa sponsorship")):
        return _field_result("need_sponsorship_now", 0.95, True, "Matched sponsorship field.")
    if "relocate" in text or "relocation" in text:
        return _field_result("willing_to_relocate", 0.95, True, "Matched relocation field.")

    if tag == "textarea":
        if any(token in text for token in ("why are you interested", "why this company", "why do you want to work", "why company")):
            return _field_result("why_company", 0.9, True, "Matched company-interest prompt.")
        if any(token in text for token in ("tell us about yourself", "about yourself", "introduce yourself", "professional summary")):
            return _field_result("tell_us_about_yourself", 0.9, True, "Matched about-yourself prompt.")
        if any(token in text for token in ("salary", "compensation", "pay expectation", "desired pay")):
            return _field_result("salary_expectation", 0.88, True, "Matched salary prompt.")
        if "cover letter" in text or "message to hiring team" in text or "message to recruiter" in text:
            return _field_result("general_cover_letter", 0.88, True, "Matched free-form cover letter field.")
        return _field_result("unknown_question", 0.4, False, "Open-ended question could not be classified safely.")

    if tag == "select":
        if any(token in text for token in ("authorized to work", "work authorization")):
            return _field_result("work_authorized_us", 0.95, True, "Matched work-authorization select.")
        if any(token in text for token in ("sponsorship", "visa")) and "future" in text:
            return _field_result("need_sponsorship_future", 0.94, True, "Matched future-sponsorship select.")
        if any(token in text for token in ("sponsorship", "visa")):
            return _field_result("need_sponsorship_now", 0.94, True, "Matched sponsorship select.")
        if "relocat" in text:
            return _field_result("willing_to_relocate", 0.94, True, "Matched relocation select.")
        if "gender" in text:
            return _field_result("gender", 0.97, False, "Sensitive demographic select detected.")
        if "veteran" in text:
            return _field_result("veteran_status", 0.97, False, "Sensitive veteran-status select detected.")
        if "disability" in text:
            return _field_result("disability", 0.97, False, "Sensitive disability select detected.")
        if any(token in options_text for token in ("prefer not to answer", "decline to self identify")) and any(
            token in text for token in ("gender", "race", "ethnicity", "veteran", "disability")
        ):
            return _field_result("unknown_sensitive", 0.95, False, "Sensitive EEO select detected.")

    if input_type in {"radio", "checkbox"}:
        if any(token in text for token in ("authorized to work", "work authorization")):
            return _field_result("work_authorized_us", 0.92, True, "Matched work-authorization choice.")
        if any(token in text for token in ("sponsorship", "visa")) and "future" in text:
            return _field_result("need_sponsorship_future", 0.9, True, "Matched future-sponsorship choice.")
        if any(token in text for token in ("sponsorship", "visa")):
            return _field_result("need_sponsorship_now", 0.9, True, "Matched sponsorship choice.")
        if "relocat" in text:
            return _field_result("willing_to_relocate", 0.9, True, "Matched relocation choice.")
        if any(token in text for token in ("gender", "race", "ethnicity", "disability", "veteran")):
            return _field_result("unknown_sensitive", 0.95, False, "Sensitive choice field detected.")

    if input_type in {"search", "hidden"}:
        return _field_result("unknown_question", 0.2, False, "Skipped non-user input field.")

    return _field_result("unknown_question", 0.2, False, "No safe rule-based match for this field.")


def detect_form_fields(page: Any) -> list[dict[str, Any]]:
    raw_fields = page.evaluate(
        """
        () => {
          const elements = Array.from(document.querySelectorAll("input, textarea, select"));
          return elements.map((el, index) => {
            const attr = (name) => (el.getAttribute(name) || "").trim();
            const elementId = attr("id");
            const labelForId = elementId
              ? Array.from(document.querySelectorAll("label")).find((label) => (label.getAttribute("for") || "").trim() === elementId)
              : null;
            const closestLabel = el.closest("label");
            const ariaLabelledBy = attr("aria-labelledby")
              .split(/\\s+/)
              .map((id) => document.getElementById(id))
              .filter(Boolean)
              .map((node) => (node.textContent || "").trim())
              .join(" ");
            const choiceText = closestLabel
              ? (closestLabel.textContent || "").trim()
              : ((el.parentElement && el.parentElement.textContent) || "").trim();
            const nearbyText = ((el.parentElement && el.parentElement.innerText) || "").trim();
            const detectorId = attr("data-careeragent-autofill-id") || `careeragent-autofill-${index + 1}`;
            el.setAttribute("data-careeragent-autofill-id", detectorId);

            return {
              selector: `[data-careeragent-autofill-id="${detectorId}"]`,
              tag: (el.tagName || "").toLowerCase(),
              input_type: attr("type").toLowerCase(),
              name: attr("name"),
              id: elementId,
              placeholder: attr("placeholder"),
              aria_label: attr("aria-label"),
              label_text: [
                labelForId ? (labelForId.textContent || "").trim() : "",
                closestLabel ? (closestLabel.textContent || "").trim() : "",
                ariaLabelledBy,
              ]
                .filter(Boolean)
                .join(" ")
                .trim(),
              nearby_text: nearbyText.slice(0, 280),
              choice_text: choiceText.slice(0, 160),
              value_attr: attr("value"),
              disabled: Boolean(el.disabled),
              required: Boolean(el.required),
              options: el.tagName.toLowerCase() === "select"
                ? Array.from(el.options).slice(0, 25).map((option) => ((option.textContent || "").trim())).filter(Boolean)
                : [],
            };
          });
        }
        """
    )

    detected_fields: list[dict[str, Any]] = []
    for raw_field in raw_fields:
        field = dict(raw_field)
        field_key, confidence, safe_to_fill, reason = _classify_detected_field(field)
        field["field_key"] = field_key
        field["confidence"] = round(confidence, 2)
        field["safe_to_fill"] = safe_to_fill and not field.get("disabled", False)
        if field_key in SENSITIVE_FIELD_KEYS:
            field["safe_to_fill"] = False
        field["reason"] = reason if not field.get("disabled") else "Field is disabled."
        detected_fields.append(field)

    return detected_fields
