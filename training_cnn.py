import os
import pandas as pd
import numpy as np
import pickle

os.environ["OMP_NUM_THREADS"] = "2"
os.environ["TF_NUM_INTRAOP_THREADS"] = "2"
os.environ["TF_NUM_INTEROP_THREADS"] = "2"

import tensorflow as tf
tf.config.threading.set_intra_op_parallelism_threads(2)
tf.config.threading.set_inter_op_parallelism_threads(2)

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
from tensorflow.keras.optimizers import Adam


df = pd.read_csv("dataset_phishing.csv")

df.drop(columns=["url"], inplace=True)

df["status"] = df["status"].map({
    "legitimate": 0,
    "phishing": 1
})

X = df.drop(columns=["status"])
y = df["status"]


X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test  = scaler.transform(X_test)


X_train_cnn = X_train.reshape(X_train.shape[0], X_train.shape[1], 1)
X_test_cnn  = X_test.reshape(X_test.shape[0], X_test.shape[1], 1)


cnn_model = Sequential([
    Conv1D(
        filters=32,
        kernel_size=3,
        activation="relu",
        input_shape=(X_train_cnn.shape[1], 1)
    ),
    MaxPooling1D(pool_size=2),

    Conv1D(
        filters=64,
        kernel_size=3,
        activation="relu"
    ),
    MaxPooling1D(pool_size=2),

    Flatten(),

    Dense(64, activation="relu"),
    Dropout(0.3),

    Dense(1, activation="sigmoid")
])

cnn_model.compile(
    optimizer=Adam(learning_rate=0.001),
    loss="binary_crossentropy",
    metrics=["accuracy"]
)

cnn_model.summary()


cnn_model.fit(
    X_train_cnn,
    y_train,
    epochs=50,            # DO NOT increase on CPU
    batch_size=16,       # small batch = no freeze
    validation_split=0.1,
    verbose=1
)


cnn_loss, cnn_acc = cnn_model.evaluate(X_test_cnn, y_test, verbose=0)
print("\n CNN Accuracy:", cnn_acc)


cnn_model.save("cnn_url_phishing_model.keras")
pickle.dump(scaler, open("scaler.pkl", "wb"))

print("\n CNN model saved successfully .")
