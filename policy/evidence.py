"""Transparent check for whether a caller has supplied decision-grade evidence.

The transcript classifier estimates scam risk.  This module answers a separate
question: has the caller described a concrete purpose or request yet?  A risk
score alone must not end screening when the call is still vague.
"""
from __future__ import annotations

import re


CONCRETE_REQUESTS = (
    r'\b(?:read|tell|share|repeat|confirm|give|dictate)\b.{0,45}\b(?:code|digits|passcode|password|phrase|temporary number|card number|security digits|details)\b',
    r'\bverify\b.{0,35}\b(?:identity code|code|digits|passcode|temporary number)\b',
    r'\b(?:buy|purchase|settle)\b.{0,45}\b(?:gift cards?|prepaid cards?|vouchers?|balance)\b',
    r'\b(?:send|move|transfer|wire|pay)\b.{0,45}\b(?:money|funds|balance|savings|payment|account|cryptocurrency|currency|fine|fee|redemption codes?)\b',
    r'\b(?:open|install|approve|accept|give|connect)\b.{0,45}\b(?:quick assist|remote access|support (?:app|utility)|control|connection|screen|device remotely)\b',
    r'\b(?:recovery words?|recovery phrase|redemption (?:code|information)|activation details)\b',
    r'\b(?:arrest|enforcement|penalty|service shutoff|turned off)\b',
)


CLEAR_PURPOSES = (
    r'\bappointment\b',
    r'\b(?:delivery|package|parcel|shipment|pickup desk)\b',
    r'\b(?:school|after-school|parent portal|library program)\b',
    r'\b(?:scheduled visit|service window|technician|utility visit|utility company|home repair team|internet installer|payment request)\b',
    r'\b(?:event|community center|neighborhood association|volunteer group|local library|library session)\b',
    r'\b(?:clinic|dental office|diagnostic center|pharmacy|optometrist|physiotherapy office|medical result|result is ready|reschedule)\b',
    r'\b(?:fraud-awareness|security reminder|public safety message|fraud warning|fraud alert)\b',
    r'\b(?:insurance office|membership desk|property manager)\b',
    r'\b(?:official app|number (?:printed|published|on your statement)|usual (?:(?:office|support) )?(?:number|line)|no action is needed|never provide)\b',
)


def assess(text: str) -> dict:
    """Return a visible policy feature; labels never enter this decision."""
    normalized = ' '.join(text.lower().split())
    for pattern in CONCRETE_REQUESTS:
        match = re.search(pattern, normalized)
        if match:
            return {'sufficient': True, 'kind': 'concrete request', 'cue': match.group(0)}
    for pattern in CLEAR_PURPOSES:
        match = re.search(pattern, normalized)
        if match:
            return {'sufficient': True, 'kind': 'clear purpose', 'cue': match.group(0)}
    return {'sufficient': False, 'kind': 'missing purpose or request', 'cue': ''}
