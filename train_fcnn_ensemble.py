import pandas as pd
import numpy as np
import pickle
import math

from sklearn.model_selection import train_test_split, RandomizedSearchCV, StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, classification_report
from sklearn.ensemble import VotingClassifier
from sklearn.preprocessing import StandardScaler

from xgboost import XGBClassifier
import lightgbm as lgb
from catboost import CatBoostClassifier

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset


print("=" * 65)
print("  INPUT LAYER — Feature Ingestion & Normalization")
print("=" * 65)

df = pd.read_csv("dataset_phishing.csv")
df.drop(columns=["url"], inplace=True)
df["status"] = df["status"].map({"legitimate": 0, "phishing": 1})

X = df.drop(columns=["status"])
y = df["status"]

scaler = StandardScaler()
X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=X.columns)

print(f"\n  Input Features      : {X_scaled.shape[1]}")
print(f"  Total Samples       : {X_scaled.shape[0]}")
print(f"  Class Distribution  :\n{y.value_counts().rename({0:'Legitimate', 1:'Phishing'}).to_string()}")

X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print(f"\n  Training Samples    : {X_train.shape[0]}")
print(f"  Test Samples        : {X_test.shape[0]}")


print("\n" + "=" * 65)
print("  HIDDEN LAYER 1 — Parallel Boosting Nodes")
print("=" * 65)

print("\n  [Node A] XGBoost — Tuning via RandomizedSearchCV\n")

xgb_params = {
    "n_estimators"     : [1000, 1500, 2000],
    "max_depth"        : [6, 8, 10, 12],
    "learning_rate"    : [0.01, 0.02, 0.03],
    "subsample"        : [0.7, 0.8, 0.9, 1.0],
    "colsample_bytree" : [0.7, 0.8, 0.9, 1.0],
    "gamma"            : [0, 0.1, 0.2],
    "min_child_weight" : [1, 3, 5]
}

xgb_base = XGBClassifier(eval_metric="logloss", tree_method="hist", random_state=42)

xgb_search = RandomizedSearchCV(
    xgb_base, xgb_params,
    n_iter=20, scoring="accuracy",
    cv=5, verbose=1, n_jobs=-1
)
xgb_search.fit(X_train, y_train)
best_xgb = xgb_search.best_estimator_

pred_xgb = best_xgb.predict(X_test)
xgb_acc  = accuracy_score(y_test, pred_xgb)
print(f"\n  [Node A] XGBoost Accuracy  : {xgb_acc*100:.2f}%")
print(classification_report(y_test, pred_xgb))


print("  [Node B] LightGBM\n")

lgb_model = lgb.LGBMClassifier(
    n_estimators=2500, learning_rate=0.01,
    num_leaves=64, subsample=0.9,
    colsample_bytree=0.9, random_state=42,
    verbose=-1
)
lgb_model.fit(X_train, y_train)
pred_lgb = lgb_model.predict(X_test)
lgb_acc  = accuracy_score(y_test, pred_lgb)
print(f"  [Node B] LightGBM Accuracy : {lgb_acc*100:.2f}%")
print(classification_report(y_test, pred_lgb))


print("  [Node C] CatBoost\n")

cat_model = CatBoostClassifier(
    iterations=2000, learning_rate=0.03,
    depth=10, verbose=0
)
cat_model.fit(X_train, y_train)
pred_cat = cat_model.predict(X_test)
cat_acc  = accuracy_score(y_test, pred_cat)
print(f"  [Node C] CatBoost Accuracy : {cat_acc*100:.2f}%")
print(classification_report(y_test, pred_cat))

print("  " + "-" * 45)
print("  Hidden Layer 1 — Node Summary:")
print(f"    Node A  XGBoost   ->  {xgb_acc*100:.2f}%")
print(f"    Node B  LightGBM  ->  {lgb_acc*100:.2f}%")
print(f"    Node C  CatBoost  ->  {cat_acc*100:.2f}%")
print("  " + "-" * 45)


print("\n  Building Meta-Features from Node probability outputs...")

def get_meta_features(models, X):
    probs = [m.predict_proba(X) for m in models]
    return np.hstack(probs)

models_list = [best_xgb, lgb_model, cat_model]

meta_train = get_meta_features(models_list, X_train)
meta_test  = get_meta_features(models_list, X_test)

print(f"  Meta-feature shape (train) : {meta_train.shape}")
print(f"  Meta-feature shape (test)  : {meta_test.shape}")
print(f"  Features per node          : 2  [P(Legitimate), P(Phishing)]")
print(f"  Total meta-features        : 6  (3 nodes x 2)")


print("\n" + "=" * 65)
print("  HIDDEN LAYER 2 — Neural Network Meta-Learner (PyTorch)")
print("=" * 65)
print()
print("  Layer        Neurons    Activation")
print("  " + "-" * 38)
print("  Input             6    meta-features")
print("  Hidden 2a        64    ReLU + Dropout(0.3)")
print("  Hidden 2b        32    ReLU + Dropout(0.2)")
print("  Hidden 2c        16    ReLU")
print("  Output            1    Sigmoid")
print()


class MetaLearnerNN(nn.Module):

    def __init__(self, input_dim=6):
        super(MetaLearnerNN, self).__init__()

        self.hidden1 = nn.Linear(input_dim, 64)
        self.bn1     = nn.BatchNorm1d(64)
        self.drop1   = nn.Dropout(0.3)

        self.hidden2 = nn.Linear(64, 32)
        self.bn2     = nn.BatchNorm1d(32)
        self.drop2   = nn.Dropout(0.2)

        self.hidden3 = nn.Linear(32, 16)
        self.output  = nn.Linear(16, 1)

        self.relu    = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):

        x = self.relu(self.bn1(self.hidden1(x)))
        x = self.drop1(x)

        x = self.relu(self.bn2(self.hidden2(x)))
        x = self.drop2(x)

        x = self.relu(self.hidden3(x))
        x = self.sigmoid(self.output(x))

        return x


X_meta_train = torch.tensor(meta_train, dtype=torch.float32)
y_meta_train = torch.tensor(y_train.values, dtype=torch.float32).unsqueeze(1)
X_meta_test  = torch.tensor(meta_test,  dtype=torch.float32)
y_meta_test  = torch.tensor(y_test.values,  dtype=torch.float32).unsqueeze(1)

train_dataset = TensorDataset(X_meta_train, y_meta_train)
train_loader  = DataLoader(train_dataset, batch_size=64, shuffle=True)

nn_model  = MetaLearnerNN(input_dim=6)
criterion = nn.BCELoss()
optimizer = optim.Adam(nn_model.parameters(), lr=0.001, weight_decay=1e-4)
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.5)

EPOCHS = 80

print(f"  Training Neural Meta-Learner for {EPOCHS} epochs...\n")
print(f"  {'Epoch':<10} {'Train Loss':<18} {'Val Loss':<16} {'Val Accuracy'}")
print("  " + "-" * 56)

best_val_loss = float("inf")
best_weights  = None

for epoch in range(1, EPOCHS + 1):

    nn_model.train()
    epoch_loss = 0.0

    for X_batch, y_batch in train_loader:
        optimizer.zero_grad()
        preds = nn_model(X_batch)
        loss  = criterion(preds, y_batch)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()

    scheduler.step()

    nn_model.eval()
    with torch.no_grad():
        val_preds = nn_model(X_meta_test)
        val_loss  = criterion(val_preds, y_meta_test).item()
        val_bin   = (val_preds >= 0.5).float()
        val_acc   = (val_bin == y_meta_test).float().mean().item()

    if val_loss < best_val_loss:
        best_val_loss = val_loss
        best_weights  = {k: v.clone() for k, v in nn_model.state_dict().items()}

    print(f"  Epoch {epoch:<5}  Train Loss: {epoch_loss/len(train_loader):.4f}    Val Loss: {val_loss:.4f}    Val Acc: {val_acc*100:.2f}%")

nn_model.load_state_dict(best_weights)


print("\n" + "=" * 65)
print("  OUTPUT LAYER — Sigmoid -> Binary Classification")
print("=" * 65)

nn_model.eval()
with torch.no_grad():
    final_probs = nn_model(X_meta_test)
    final_preds = (final_probs >= 0.5).int().numpy().flatten()

nn_acc = accuracy_score(y_test, final_preds)

print(f"\n  Neural Ensemble Stack Accuracy : {nn_acc*100:.2f}%")
print("\n  Final Classification Report:\n")
print(classification_report(y_test, final_preds, target_names=["Legitimate", "Phishing"]))


print("\n" + "=" * 65)
print("  COMPARISON — Original Soft Voting Ensemble")
print("=" * 65)

ensemble = VotingClassifier(
    estimators=[("xgb", best_xgb), ("lgb", lgb_model), ("cat", cat_model)],
    voting="soft"
)
ensemble.fit(X_train, y_train)
pred_ens = ensemble.predict(X_test)
ens_acc  = accuracy_score(y_test, pred_ens)

print(f"\n  Soft-Vote Ensemble Accuracy    : {ens_acc*100:.2f}%")
print(f"  Neural Stack Accuracy          : {nn_acc*100:.2f}%")


print("\n" + "=" * 65)
print("  CROSS VALIDATION — 10-Fold Stratified K-Fold")
print("=" * 65)

skf    = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
scores = cross_val_score(best_xgb, X_scaled, y, cv=skf, scoring="accuracy")

print(f"\n  Fold Accuracies : {[round(s*100, 2) for s in scores]}")
print(f"  Mean Accuracy   : {scores.mean()*100:.2f}%")
print(f"  Std Deviation   : +/-{scores.std()*100:.2f}%")

acc = scores.mean()
print("\nFinal Accuracy of the model :", math.ceil(acc*100), "%")


print("\n" + "=" * 65)
print("  SAVING ALL MODELS")
print("=" * 65)

pickle.dump(ensemble,  open("ensemble_model.pkl",  "wb"))
pickle.dump(best_xgb,  open("xgboost_model.pkl",   "wb"))
pickle.dump(lgb_model, open("lightgbm_model.pkl",  "wb"))
pickle.dump(cat_model, open("catboost_model.pkl",  "wb"))
pickle.dump(scaler,    open("scaler.pkl",           "wb"))
torch.save(nn_model.state_dict(), "meta_learner_nn.pt")

print("\n Model Created  ensemble_model.pkl")
