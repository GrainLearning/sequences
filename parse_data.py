"""
Preprocess data so that it can be used as input in an RNN.
Data consists of:
- contact_params (samples, 5)
- input_params (samples, sequence_length, x)
- output_params (samples, sequence_length, y)
"""
import numpy as np
import os
import h5py

contact_keys = [
        'E', # young's modulus  = 10^E
        'v', # poisson's ratio
        'kr', # rolling stiffness
        'eta', # rolling friction
        'mu', # sliding friction
        ]

input_keys = [
        'e_v',  # strains in 3 directions
        'e_y',
        'e_z',  # the axial direction
]

output_keys = [
        'e',  # void ratio
        'p',  # mean stress
        'q',  # deviatoric stress
        'f0',  # average contact normal force
        'a_c', # fabric anisotropy
        'a_n',  # mechanical anisotropy
        'a_t',  # mechanical anisotropy due to tangiential forces
]

unused_keys_sequence = [
        'dt',  # size of timestep taken at this iteration
        'numIter',  # iteration number in the simulation at which equilibrium is 
                    # reached at the current loading
        'K',  # mysterious
        'A',  # also mysterious
]

unused_keys_constant = [
        'conf',  # confining pressure (stored as group name already)
        'mode',  # drained/undrained (also stored as group name)
        'num',  # number of particles (always 10_000)
]
SEQUENCE_LENGTH = 200
TARGET_DIR = 'data/'
DATA_DIR = '/Users/aronjansen/Documents/grainsData/TriaxialCompression/'


def main(pressure, experiment_type):
    data_dir = DATA_DIR + f'{pressure}/{experiment_type}/'
    if not os.listdir(data_dir):
        print(f"Directory {data_dir} is empty.")
        return

    file_names = [fn for fn in os.listdir(data_dir) if fn.endswith('.npy')]

    contact_tensor = []
    inputs_tensor = []
    outputs_tensor = []
    for f in file_names:
        try:
            sim_params, sim_features = np.load(data_dir + f, allow_pickle=True)
        except IOError:
            print('IOError', f, pressure)
            continue
        # test if sequence is of full length
        test_features = sim_features[output_keys[0]]
        if len(test_features) == SEQUENCE_LENGTH:
            contact_tensor.append([sim_params[key] for key in contact_keys])
            inputs_tensor.append([sim_features[key] for key in input_keys])
            outputs_tensor.append([sim_features[key] for key in output_keys])

    contact_tensor = np.array(contact_tensor)
    inputs_tensor = np.array(inputs_tensor)
    outputs_tensor = np.array(outputs_tensor)

    # keras requires (batch, sequence_length, features) shape, so transpose axes
    inputs_tensor = np.transpose(inputs_tensor, (0, 2, 1))
    outputs_tensor = np.transpose(outputs_tensor, (0, 2, 1))

    print(f'Created tensor of {outputs_tensor.shape[0]} samples,')

    with h5py.File(TARGET_DIR + 'rnn_data.h5py', 'a') as f:
        grp = f.create_group(f'{pressure}/{experiment_type}')
        grp['contact_params'] = contact_tensor
        grp['inputs'] = inputs_tensor
        grp['outputs'] = outputs_tensor
    print(f"Added data to {TARGET_DIR + 'rnn_data.h5py'}")

if __name__ == '__main__':
    for pressure in ['0.2e6', '0.5e6', '1.0e6']:
        for experiment_type in ['drained', 'undrained']:  # there is a problem with undrained
            main(pressure, experiment_type)

