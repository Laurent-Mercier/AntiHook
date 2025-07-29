# tests/test_url_processing.py

import pytest
from urllib.parse import urlparse

from api.preprocessing.url_processing import URLFeatureExtractor

@pytest.fixture
def extractor():
    return URLFeatureExtractor()

def test_transform_basic_urls(extractor):
    urls = [
        "https://example.com/path123",
        "http://sub.domain.co.uk/another/path?query=1",
        ""  # empty URL edge-case
    ]
    feats = extractor.transform(urls)
    assert isinstance(feats, list)
    assert len(feats) == 3

    for url, feat in zip(urls, feats):
        # parse with same logic
        parsed = urlparse(url or "")
        expected = {
            "url_length": len(url),
            "domain_length": len(parsed.netloc),
            "path_length": len(parsed.path),
            "num_digits": sum(c.isdigit() for c in url),
            "num_special": sum(not c.isalnum() for c in url),
            "is_https": int(parsed.scheme.lower() == "https")
        }
        assert feat == expected

def test_transform_https_flag(extractor):
    https_url = "HTTPS://UPPERCASE.com"
    http_url  = "http://lowercase.com"
    feats = extractor.transform([https_url, http_url])
    assert feats[0]["is_https"] == 1
    assert feats[1]["is_https"] == 0

def test_transform_counts_digits_and_specials(extractor):
    url = "https://123-abc!@#"
    feat = extractor.transform([url])[0]
    # digits: '1','2','3' → 3
    assert feat["num_digits"] == 3
    # specials: ':/','-','!','@','#' → count of non-alnum
    expected_specials = sum(not c.isalnum() for c in url)
    assert feat["num_special"] == expected_specials

def test_fit_returns_self(extractor):
    # fit should be a no-op returning the same instance
    result = extractor.fit(["any"], y=None)
    assert result is extractor

@pytest.mark.parametrize("bad_url", [None, 123, object()])
def test_transform_handles_non_string_by_treating_as_empty(extractor, bad_url):
    # non-string inputs should be treated like ""
    # (urlparse(url or "") uses "" if url is falsy)
    feat = extractor.transform([bad_url])[0]
    assert feat == {
        "url_length": 0,
        "domain_length": 0,
        "path_length": 0,
        "num_digits": 0,
        "num_special": 0,
        "is_https": 0
    }
