from voice.hw.audio_devices import wait_for_device


def test_returns_immediately_when_found():
    assert (
        wait_for_device(lambda: "plughw:1,0", "mic", timeout=5, interval=0.01)
        == "plughw:1,0"
    )


def test_retries_until_found():
    calls = iter([None, None, "plughw:2,0"])
    assert (
        wait_for_device(lambda: next(calls), "mic", timeout=5, interval=0.01)
        == "plughw:2,0"
    )


def test_gives_up_after_timeout():
    assert wait_for_device(lambda: None, "mic", timeout=0.05, interval=0.01) is None
