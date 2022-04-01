"""
Implement the simplest possible model.
Model itself based on Ma's.
Data just picking a single pressure and type.
Contact parameters handled by just concatenating to the sequence data.
No additional hand-engineered features (like Ma's chi).
Do rescale input data.
"""
from tensorflow import keras
from tensorflow.keras import layers, Sequential
import numpy as np
from matplotlib import pyplot as plt
import os

from preprocessing import prepare_datasets

pressure = 'All'  # '0.2e6'
experiment_type = 'All'  # 'drained'

split_data, train_stats = prepare_datasets(
        pressure=pressure,
        experiment_type=experiment_type,
        )

def sliding_windows(data, window_size: int, window_step: int):
    """
    Take a dataset of sequences of shape N, S, L and output another dataset
    of shorter sequences of size `window_size`, taken at intervals `window_step`
    so of shape M, window_size, L, with M >> N.
    Also shuffle the data.
    """
    inputs, outputs = data
    num_samples, sequence_length, num_labels = outputs.shape
    Xs, ys = [], []
    start, end = 0, window_size
    while end < sequence_length:
        Xs.append(inputs[:, start:end])
        ys.append(outputs[:, end + 1])
        start += window_step
        end += window_step

    Xs = np.array(Xs)
    ys = np.array(ys)
    # now we have the first dimension for samples and the second for windows,
    # we want to merge those to treat them as independent samples
    num_indep_samples = Xs.shape[0] * Xs.shape[1]
    Xs = np.reshape(Xs, (num_indep_samples,) + Xs.shape[2:])
    ys = np.reshape(ys, (num_indep_samples,) + ys.shape[2:])

    return shuffle(Xs, ys)

def shuffle(Xs, ys):
    inds = np.random.permutation(len(Xs))
    return Xs[inds], ys[inds]

window_size, window_step = 20, 5
windows = {split: sliding_windows(split_data[split], window_size, window_step)
            for split in ['train', 'val', 'test']}

_, sequence_length, num_features = split_data['train'][0].shape
num_labels = windows['train'][1].shape[-1]

# this is close to Ma's model (apart from the LSTM modification) 
model = Sequential([
        layers.Input(shape=(None, num_features)),
        layers.LSTM(50),
        layers.Dense(20, activation='relu'),
        layers.Dense(num_labels),
        ])
optimizer = keras.optimizers.Adam(lr=1e-3)
model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])

epochs = 4  # Ma: 2_000
batch_size = 256
history = model.fit(
        *windows['train'],
        epochs=epochs,
        validation_data=windows['val'],
        batch_size=batch_size,
        )

model_directory = f'trained_models/simple_rnn_{pressure}_{experiment_type}'
model.save(model_directory)
np.save(model_directory + '/train_stats.npy', train_stats)

loss = {
        'train': history.history['loss'],
        'val': history.history['val_loss']
        }
fig, ax = plt.subplots()
for split in ['train', 'val']:
    ax.plot(list(range(epochs)), loss[split], label=split + 'loss')
fig.legend()

if not os.path.exists('plots'):
    os.makedirs('plots')
fig.savefig('plots/' + f'loss_{pressure}_{experiment_type}.png')

def predict(inputs, model, window_size):
    """
    Take a batch of sequences, iterate over windows making predictions.
    """
    predictions = []

    start, end = 0, window_size
    while end < sequence_length:
        predictions.append(model(inputs[:, start:end]))
        start += 1
        end += 1

    predictions = np.array(predictions)
    predictions = np.transpose(predictions, (1, 0, 2))

    return predictions

test_inputs = split_data['test'][0][:32]
test_outputs = split_data['test'][1][:32]
test_predictions = predict(test_inputs, model, window_size)

steps = np.array(list(range(sequence_length)))
steps_predicted = np.array(list(range(window_size, sequence_length)))

# just to get the plot labels
import h5py
datafile = h5py.File('data/rnn_data.hdf5', 'r')

fig, ax = plt.subplots(3, 3)
for feature_idx in range(test_outputs.shape[2]):
    i = feature_idx % 3
    j = feature_idx // 3
    ax[i, j].plot(steps, test_outputs[0, :, feature_idx], label='truth')
    ax[i, j].plot(steps_predicted, test_predictions[0, :, feature_idx], label='predictions')
    ax[i, j].set_title(datafile.attrs['outputs'][feature_idx])
fig.suptitle(f'pressure {pressure}, type {experiment_type}')
fig.savefig('plots/' + f'test_predictions_{pressure}_{experiment_type}.png')

