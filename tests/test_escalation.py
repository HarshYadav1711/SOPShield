from sopshield.escalation import (
    CONFIDENCE_THRESHOLD,
    EscalationReason,
    EscalationState,
    check_message,
    is_immediate_escalation,
)


def test_explicit_escalation():
    state = EscalationState()
    event = check_message(
        "I need to speak to a manager now",
        retrieval_confidence=0.9,
        answered_from_sop=True,
        state=state,
    )
    assert event is not None
    assert event.reason == EscalationReason.EXPLICIT_REQUEST
    assert is_immediate_escalation(event.reason)


def test_angry_sentiment():
    state = EscalationState()
    event = check_message(
        "This is ridiculous, I'm furious!",
        retrieval_confidence=0.9,
        answered_from_sop=True,
        state=state,
    )
    assert event is not None
    assert event.reason == EscalationReason.ANGRY_SENTIMENT


def test_frustrated_tone():
    state = EscalationState()
    event = check_message(
        "I'm so frustrated, this is a waste of my time",
        retrieval_confidence=0.9,
        answered_from_sop=True,
        state=state,
    )
    assert event is not None
    assert event.reason == EscalationReason.ANGRY_SENTIMENT


def test_complaint():
    state = EscalationState()
    event = check_message(
        "I want a refund, your service was terrible",
        retrieval_confidence=0.9,
        answered_from_sop=True,
        state=state,
    )
    assert event is not None
    assert event.reason == EscalationReason.COMPLAINT


def test_pricing_negotiation():
    state = EscalationState()
    event = check_message(
        "Can you match a competitor's price on Botox?",
        retrieval_confidence=0.9,
        answered_from_sop=True,
        state=state,
    )
    assert event is not None
    assert event.reason == EscalationReason.PRICING_NEGOTIATION


def test_sensitive_medical():
    state = EscalationState()
    event = check_message(
        "I'm pregnant — is Botox safe for me?",
        retrieval_confidence=0.9,
        answered_from_sop=True,
        state=state,
    )
    assert event is not None
    assert event.reason == EscalationReason.SENSITIVE_UNSUPPORTED


def test_out_of_scope():
    state = EscalationState()
    event = check_message(
        "I need help with a dental surgery referral",
        retrieval_confidence=0.9,
        answered_from_sop=True,
        state=state,
    )
    assert event is not None
    assert event.reason == EscalationReason.OUT_OF_SCOPE


def test_low_confidence_first_miss():
    state = EscalationState()
    event = check_message(
        "do you ship products internationally",
        retrieval_confidence=0.1,
        answered_from_sop=False,
        state=state,
    )
    assert event is not None
    assert event.reason == EscalationReason.LOW_CONFIDENCE
    assert event.detail.find(f"{CONFIDENCE_THRESHOLD}") >= 0


def test_sop_gap_when_confidence_ok():
    state = EscalationState()
    event = check_message(
        "do you ship skincare internationally",
        retrieval_confidence=0.5,
        answered_from_sop=False,
        state=state,
    )
    assert event is not None
    assert event.reason == EscalationReason.SOP_GAP


def test_repeated_unanswered():
    state = EscalationState()
    check_message(
        "do you ship products internationally",
        retrieval_confidence=0.5,
        answered_from_sop=False,
        state=state,
    )
    event = check_message(
        "what about international shipping",
        retrieval_confidence=0.5,
        answered_from_sop=False,
        state=state,
    )
    assert event is not None
    assert event.reason == EscalationReason.REPEATED_UNANSWERED


def test_answered_resets_streak():
    state = EscalationState()
    check_message(
        "unknown topic",
        retrieval_confidence=0.5,
        answered_from_sop=False,
        state=state,
    )
    assert state.unanswered_streak == 1
    check_message(
        "What are your hours?",
        retrieval_confidence=0.8,
        answered_from_sop=True,
        state=state,
    )
    assert state.unanswered_streak == 0
