# api/preprocessing/url_processing.py

from sklearn.base import BaseEstimator, TransformerMixin
from urllib.parse import urlparse


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
    
    transform(X) expects X to be an iterable of string URLs, and returns
    a list of dicts suitable for feeding into a DictVectorizer.
    """
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        features = []
        for url in X:
            parsed = urlparse(url or "")
            domain = parsed.netloc or ""
            path = parsed.path or ""
            features.append({
                "url_length": len(url),
                "domain_length": len(domain),
                "path_length":   len(path),
                "num_digits":    sum(c.isdigit() for c in url),
                "num_special":   sum(not c.isalnum() for c in url),
                "is_https":      int(parsed.scheme.lower() == "https"),
            })
        return features
