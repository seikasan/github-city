import copy
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import github_city as city
from city_renderer import render_city

SVG = "{http://www.w3.org/2000/svg}"


def sample(**changes):
    data = {"username": "example", "commits": 400, "pull_requests": 20, "reviews": 10, "issues": 8,
            "recent_activity": 60, "active_days": 120, "public_repositories": 12, "stars": 15,
            "languages": [{"name": "C#", "color": "#178600", "repositories": 7}], "source": "synthetic-example"}
    data.update(changes)
    return data


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.config = city.load_config(None)

    def test_same_inputs_produce_identical_bytes(self):
        stats = sample()
        params = city.parameters(stats, self.config)
        self.assertEqual(render_city(stats, params), render_city(stats, params))
        self.assertNotEqual(render_city(stats, params), render_city(sample(username="other"), city.parameters(sample(username="other"), self.config)))

    def test_recent_activity_lights_existing_windows_without_reshuffling(self):
        quiet = sample(recent_activity=0)
        busy = sample(recent_activity=200)
        def lights(stats):
            root = ET.fromstring(render_city(stats, city.parameters(stats, self.config)))
            return {el.attrib["data-window"] for el in root.iter() if el.attrib.get("data-lit") == "true"}
        quiet_lights, busy_lights = lights(quiet), lights(busy)
        self.assertTrue(quiet_lights < busy_lights)

    def test_svg_is_self_contained_and_metadata_is_escaped(self):
        stats = sample(username='A<&"city')
        root = ET.fromstring(render_city(stats, city.parameters(stats, self.config)))
        self.assertEqual(root.find(SVG + "title").text, stats["username"] + " GitHub City")
        meta = json.loads(root.find(SVG + "metadata").text)
        self.assertEqual(meta["statistics"]["commits"], 400)
        for el in root.iter():
            self.assertNotIn(el.tag, [SVG + "script", SVG + "image", SVG + "foreignObject"])
            for key, value in el.attrib.items():
                self.assertFalse(key.lower().startswith("on"))
                self.assertNotIn("http://", value)
                self.assertNotIn("https://", value)

    def test_zero_and_extreme_inputs_keep_geometry_bounded(self):
        for value in [0, 10**15]:
            stats = sample(**{key: min(value, 365) if key == "active_days" else value for key in city.COUNTS})
            params = city.parameters(stats, self.config)
            root = ET.fromstring(render_city(stats, params))
            self.assertTrue(1 <= params["building_count"] <= 9)
            self.assertTrue(0 <= params["window_light_rate"] <= 1)
            self.assertTrue(32 <= params["skyline_height"] <= 350)
            buildings = [el for el in root.iter() if el.attrib.get("data-kind") == "building"]
            self.assertEqual(len(buildings), params["building_count"])
            self.assertTrue(all(32 <= float(el.attrib["data-height"]) <= 350 for el in buildings))

    def test_override_and_invalid_color(self):
        config = copy.deepcopy(self.config)
        config["overrides"] = {"building_count": 9, "window_light_rate": 1}
        params = city.parameters(sample(), config)
        self.assertEqual(params["building_count"], 9)
        self.assertEqual(params["window_light_rate"], 1)
        with self.assertRaises(ValueError):
            city.validate_stats(sample(languages=[{"name": "bad", "color": 'url(http://evil)', "repositories": 1}]))
        with self.assertRaises(ValueError):
            city.parameters(sample(commits=-1), config)

    def test_failure_preserves_last_generated_svg(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "city.svg"
            path.write_text("last known good")
            with patch.dict("os.environ", {"GH_CITY_TOKEN": ""}):
                result = city.main(["--config", str(Path(city.__file__).with_name("city.config.json")), "--output", str(path)])
            self.assertEqual(result, 1)
            self.assertEqual(path.read_text(), "last known good")


class FetchTests(unittest.TestCase):
    def make_response(self, end):
        start = end - timedelta(days=365)
        days = [{"date": (start + timedelta(days=i)).isoformat(), "contributionCount": 2} for i in range(365)]
        # Boundary dates returned by a week-level calendar must be excluded.
        days += [{"date": end.isoformat(), "contributionCount": 999}, {"date": (start - timedelta(days=1)).isoformat(), "contributionCount": 999}]
        return {"user": {"login": "example", "contributionsCollection": {
            "totalCommitContributions": 1000, "totalPullRequestContributions": 7,
            "totalPullRequestReviewContributions": 11, "totalIssueContributions": 3,
            "contributionCalendar": {"weeks": [{"contributionDays": days}]}}}}

    def test_pagination_and_complete_utc_period(self):
        end = date(2026, 10, 3)
        variables = []
        pages = [
            {"nodes": [{"stargazerCount": 4, "primaryLanguage": {"name": "C#", "color": "#178600"}}], "pageInfo": {"hasNextPage": True, "endCursor": "page-2"}},
            {"nodes": [{"stargazerCount": 6, "primaryLanguage": {"name": "Python", "color": "#3572A5"}}], "pageInfo": {"hasNextPage": False, "endCursor": "done"}},
        ]
        def request(query, args, token):
            variables.append(args)
            if query == city.STATS_QUERY:
                return self.make_response(end)
            return {"user": {"repositories": pages.pop(0)}}
        stats = city.fetch_stats("example", "fake-test-token", end, request)
        self.assertEqual(stats["recent_activity"], 60)
        self.assertEqual(stats["active_days"], 365)
        self.assertEqual(stats["public_repositories"], 2)
        self.assertEqual(stats["stars"], 10)
        self.assertEqual(variables[-1]["after"], "page-2")
        self.assertEqual(stats["period"]["to"], "2026-10-02")
        self.assertEqual(variables[0]["from"], "2025-10-03T00:00:00+00:00")

    def test_partial_calendar_is_not_treated_as_zero_activity(self):
        end = date(2026, 10, 3)
        response = self.make_response(end)
        response["user"]["contributionsCollection"]["contributionCalendar"]["weeks"][0]["contributionDays"].pop(0)
        with self.assertRaisesRegex(RuntimeError, "365 contribution dates"):
            city.fetch_stats("example", "fake", end, lambda *args: response)

    def test_graphql_errors_abort_even_if_partial_data_exists(self):
        class Response:
            def __enter__(self):
                from io import BytesIO
                return BytesIO(json.dumps({"data": {"user": {"login": "example"}}, "errors": [{"message": "rate limit exceeded"}]}).encode())
            def __exit__(self, *args):
                pass
        with patch("urllib.request.urlopen", return_value=Response()):
            with self.assertRaisesRegex(RuntimeError, "rate limit"):
                city.graphql(city.STATS_QUERY, {"login": "example"}, "fake")


if __name__ == "__main__":
    unittest.main()
