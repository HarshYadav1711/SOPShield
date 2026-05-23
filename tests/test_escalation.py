from sopshield.escalation import EscalationState, check_message


def test_explicit_escalation():
    state = EscalationState()
    event = check_message(
        "I need to speak to a manager now",
        retrieval_confidence=0.9,
        answered_from_sop=True,
        state=state,
    )
    assert event is not None
    assert event.reason.value == "explicit_escalation"


def test_angry_sentiment():
    state = EscalationState()
    event = check_message(
        "This is ridiculous, I'm furious!",
        retrieval_confidence=0.9,
        answered_from_sop=True,
        state=state,
    )
    assert event is not None
    assert event.reason.value == "angry_sentiment"


def test_repeated_unanswered():
    state = EscalationState()
    check_message(
        "do you ship products internationally",
        retrieval_confidence=0.1,
        answered_from_sop=False,
        state=state,
    )
    event = check_message(
        "what about international shipping",
        retrieval_confidence=0.1,
        answered_from_sop=False,
        state=state,
    )
    assert event is not None
    assert event.reason.value == "repeated_unanswered"
