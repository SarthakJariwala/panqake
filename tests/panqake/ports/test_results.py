from panqake.ports.results import PRAttachment


def test_parse_path_only():
    assert PRAttachment.parse("./login.png") == PRAttachment(
        path="./login.png", alt_text=None
    )


def test_parse_path_with_alt_text():
    assert PRAttachment.parse("./login.png#The login error state") == PRAttachment(
        path="./login.png", alt_text="The login error state"
    )


def test_parse_rejects_empty_path():
    try:
        PRAttachment.parse("#alt")
    except ValueError as error:
        assert str(error) == "attachment path is empty"
    else:
        raise AssertionError("expected ValueError")


def test_to_gh_value_round_trips_alt_text():
    attachment = PRAttachment.parse("./login.png#The login error state")
    assert attachment.to_gh_value() == "./login.png#The login error state"
    assert PRAttachment.parse("./after.png").to_gh_value() == "./after.png"
