import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib
import numpy as np
from sklearn.model_selection import cross_val_score

# --- Load your dataset ---
# Make sure 'synthetic_phishing_dataset.csv' is in the same folder or give full path
df = pd.read_csv("synthetic_phishing_dataset.csv")

# --- Combine textual fields into a single input string ---
df['text'] = df['Subject'].fillna('') + ' ' + df['Sender'].fillna('') + ' ' + df['Body'].fillna('')
X = df['text']
y = df['Label']

# --- Vectorize text using TF-IDF ---
vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
X_vec = vectorizer.fit_transform(X)

# --- Train/test split ---
X_train, X_test, y_train, y_test = train_test_split(X_vec, y, test_size=0.2, random_state=42)

# --- Train model ---
model = RandomForestClassifier()
model.fit(X_train, y_train)

# --- Evaluate ---
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# --- Save model and vectorizer for future use (e.g. with OCR input) ---
joblib.dump(model, "phishing_model.pkl")
joblib.dump(vectorizer, "vectorizer.pkl")
print(df['Label'].value_counts())
print(df.shape)
print("Duplicates:", df.duplicated(subset='text').sum())

# Get feature importances
importances = model.feature_importances_
feature_names = vectorizer.get_feature_names_out()

# Top 20
indices = np.argsort(importances)[-20:][::-1]
for i in indices:
    print(f"{feature_names[i]}: {importances[i]:.4f}")

scores = cross_val_score(model, X_vec, y, cv=5)
print("CV Accuracy Scores:", scores)
print("Mean CV Accuracy:", scores.mean())