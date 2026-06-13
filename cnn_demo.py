import tensorflow as tf
import numpy as np
import pandas as pd

df = pd.read_csv("data.csv")

X = df[['feature1','feature2']].values.astype(np.float32)
y = df['label'].values.astype(np.float32)

X = X.reshape(-1, 2, 1, 1)

init_w = tf.keras.initializers.Constant(5.0)
init_b = tf.keras.initializers.Constant(3.0)

model = tf.keras.Sequential([
    tf.keras.layers.Conv2D(
        filters=4,
        kernel_size=(2,1),
        activation='sigmoid',          # Hidden → Sigmoid
        kernel_initializer=init_w,
        bias_initializer=init_b,
        input_shape=(2,1,1)
    ),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(
        4,
        activation='sigmoid',          # Hidden → Sigmoid
        kernel_initializer=init_w,
        bias_initializer=init_b
    ),
    tf.keras.layers.Dense(
        1,
        activation='relu',             # Output → ReLU
        kernel_initializer=init_w,
        bias_initializer=init_b
    )
])

model.compile(
    optimizer=tf.keras.optimizers.SGD(learning_rate=0.01),
    loss='mean_squared_error'
)

model.fit(X, y, epochs=100, verbose=1)

print("\n===== LAYER-BY-LAYER OUTPUTS =====")
x = X
for i, layer in enumerate(model.layers):
    x = layer(x)
    print(f"\nLayer {i+1}: {layer.__class__.__name__}")
    print(x.numpy())

print("\n===== FINAL PREDICTIONS =====")
pred = model.predict(X)

for i in range(len(X)):
    print(f"{df.iloc[i,0:2].values} → Prediction: {pred[i,0]:.4f}, Label: {int(y[i])}")
