import json
from urllib.error import URLError

import robot_api
from robot_api import RobotAPI


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_retry_reuses_payload_and_measure_updates_channel(monkeypatch):
    requests = []
    replies = [URLError("transient"), Response({
        "accepted": True, "virtual_time_s": 6,
        "measure_result": "no_signal",
    })]

    def fake_urlopen(request, timeout):
        requests.append(request)
        result = replies.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(robot_api, "urlopen", fake_urlopen)
    api = RobotAPI("team", retries=1)
    assert api.measure((0, 0), 2) == {"result": "no_signal"}
    assert requests[0].data == requests[1].data
    assert json.loads(requests[0].data)["request_id"] == "measure-1"
    assert api.current_channel == 2
    assert api.virtual_time_s == 6


def test_clear_does_not_change_receiver_channel(monkeypatch):
    def fake_urlopen(request, timeout):
        return Response({"accepted": True, "virtual_time_s": 14,
                         "clear_result": "no_target_in_range"})

    monkeypatch.setattr(robot_api, "urlopen", fake_urlopen)
    api = RobotAPI("team")
    api.current_channel = 7
    assert api.clear((10, 20), 3) == {"result": "no_target_in_range"}
    assert api.current_channel == 7
    assert api.failed_clears == 1
