# api/preprocessing/url_processing.py

from sklearn.base import BaseEstimator, TransformerMixin
from urllib.parse import urlparse
from typing import Iterable, Dict


class URLFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extracts basic numeric features from a URL for downstream modeling.

    Features produced:
    - url_length: total number of characters in the URL
    - domain_length: length of the parsed netloc
    - path_length: length of the parsed path
    - num_digits: count of digit characters in the entire URL
    - num_special: count of non-alphanumeric characters
    - is_https: 1 if scheme == 'https', else 0

    transform(X) expects X to be an iterable of strings (or None/other),
    and returns a list of dicts suitable for feeding into a DictVectorizer.
    """

    def fit(self, X: Iterable, y=None):
        # No fitting necessary; this transformer is stateless.
        return self

    def transform(self, X: Iterable) -> list[Dict[str, int]]:
        features = []
        for url in X:
            # coerce non‐string to empty
            url_str = url if isinstance(url, str) else ""
            parsed = urlparse(url_str)
            domain = parsed.netloc or ""
            path = parsed.path or ""
            features.append({
                "url_length": len(url_str),
                "domain_length": len(domain),
                "path_length": len(path),
                "num_digits": sum(c.isdigit() for c in url_str),
                "num_special": sum(not c.isalnum() for c in url_str),
                "is_https": int(parsed.scheme.lower() == "https"),
            })
        return features
