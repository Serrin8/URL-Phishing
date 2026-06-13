import pandas as pd
import numpy as np
import pickle

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


df = pd.read_csv("dataset_phishing.csv")


df = df.drop(columns=["url"])

df["status"] = df["status"].map({
    "legitimate": 0,
    "phishing": 1
})


X = df.drop(columns=["status"])
y = df["status"]


X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)


scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)


rf_model = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    random_state=42,
    n_jobs=-1
)

rf_model.fit(X_train, y_train)

rf_pred = rf_model.predict(X_test)
rf_acc = accuracy_score(y_test, rf_pred)

print("\nRandom Forest Accuracy:", rf_acc)
print(classification_report(y_test, rf_pred))


svm_model = SVC(
    kernel="rbf",
    probability=True,
    random_state=42
)

svm_model.fit(X_train, y_train)

svm_pred = svm_model.predict(X_test)
svm_acc = accuracy_score(y_test, svm_pred)

print("\nSVM Accuracy:", svm_acc)
print(classification_report(y_test, svm_pred))


pickle.dump(rf_model, open("rf_url_phishing.pkl", "wb"))
pickle.dump(svm_model, open("svm_url_phishing.pkl", "wb"))
pickle.dump(scaler, open("scaler.pkl", "wb"))

print("\nModels saved successfully.")
