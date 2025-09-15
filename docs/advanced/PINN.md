# Physics-Informed Neural Network (PINN) for Heat Transfer

This document describes the Physics-Informed Neural Network (PINN) implementation in qlib that addresses heat transfer problems with radiative effects.

## Overview

The PINN implementation (`PytorchPINN`) is a PyTorch-based model that combines data-driven learning with physics-based constraints. It is specifically designed for heat transfer applications that include radiative heat transfer effects.

## Key Features

### 1. Neural Network Architecture
- **Activation Functions**: Uses `tanh` activation functions throughout the network for better gradient stability
- **Initialization**: Xavier normal initialization optimized for tanh activations
- **Architecture**: Configurable depth with dropout layers for regularization

### 2. Physics-Informed Loss
The model incorporates physics knowledge through a custom loss function that includes:
- **Data Loss**: Standard MSE between predictions and targets
- **Physics Loss**: Incorporates heat transfer equations with radiative effects

### 3. Radiative Heat Transfer
The model includes the radiative heat transfer term:
```
qrad = ε * σ * (T^4 - T0^4)
```
Where:
- `ε`: Emission coefficient (trainable parameter, constrained to [0,1])
- `σ`: Stefan-Boltzmann constant (5.67e-8 W/m²K⁴)
- `T`: Temperature from neural network output
- `T0`: Reference temperature (default: 298.15K)

### 4. Robust Gradient Handling
- Proper handling of `None` gradients in physics loss computation
- Gradient clipping to prevent exploding gradients
- Fallback mechanisms for numerical stability

## Usage

### Basic Usage
```python
from qlib.contrib.model.pytorch_pinn import PytorchPINN

# Initialize the model
model = PytorchPINN(
    input_dim=6,
    hidden_size=64,
    num_layers=3,
    dropout=0.1,
    n_epochs=200,
    lr=0.001,
    physics_loss_weight=1.0,
    emission_coeff_init=0.8,
)

# Train the model (standard qlib interface)
model.fit(dataset)

# Make predictions
predictions = model.predict(test_dataset)
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_dim` | int | 6 | Input feature dimension |
| `hidden_size` | int | 64 | Hidden layer size |
| `num_layers` | int | 3 | Number of layers |
| `dropout` | float | 0.1 | Dropout rate |
| `n_epochs` | int | 200 | Training epochs |
| `lr` | float | 0.001 | Learning rate |
| `batch_size` | int | 2000 | Batch size |
| `physics_loss_weight` | float | 1.0 | Weight for physics loss |
| `data_loss_weight` | float | 1.0 | Weight for data loss |
| `emission_coeff_init` | float | 0.8 | Initial emission coefficient |
| `stefan_boltzmann` | float | 5.67e-8 | Stefan-Boltzmann constant |
| `reference_temp` | float | 298.15 | Reference temperature (K) |

### qlib Configuration Example
```yaml
task:
  model:
    class: PytorchPINN
    module_path: qlib.contrib.model.pytorch_pinn
    kwargs:
      input_dim: 6
      hidden_size: 64
      num_layers: 3
      dropout: 0.1
      physics_loss_weight: 1.0
      emission_coeff_init: 0.8
      GPU: 0
```

## Implementation Details

### Model Classes
1. **`PINNModel`**: Core PyTorch neural network with physics capabilities
2. **`PytorchPINN`**: qlib-compatible wrapper that implements the Model interface

### Physics Loss Computation
The physics loss includes:
1. Temperature gradient computation using automatic differentiation
2. Radiative heat transfer term calculation
3. Physics residual based on heat transfer equations
4. Robust handling of gradient computation failures

### Constraints and Regularization
- Emission coefficient is constrained to the physical range [0,1] using `torch.clamp`
- Gradient clipping prevents training instabilities
- Dropout layers provide regularization

## Improvements Over Previous Issues

This implementation addresses several specific issues:

1. ✅ **Removed**: `tf.config.experimental.set_experimental_options` calls
2. ✅ **Added**: Radiative heat transfer term in physics loss
3. ✅ **Fixed**: Uses tanh activation instead of ReLU for better gradients
4. ✅ **Fixed**: Proper EPSILON parameter constraints with clamping
5. ✅ **Fixed**: Robust None gradient handling in physics calculations

## Performance Tips

1. **Loss Balancing**: Adjust `physics_loss_weight` and `data_loss_weight` to balance physics constraints and data fitting
2. **Learning Rate**: Start with 0.001 and adjust based on convergence behavior
3. **Architecture**: Increase `hidden_size` for more complex problems
4. **Regularization**: Use dropout to prevent overfitting on small datasets

## Limitations

- The current physics loss is simplified and should be extended for specific heat transfer applications
- Temperature units should be consistent (Kelvin recommended for radiative calculations)
- Requires sufficient physics training data or constraints for effective learning

## Future Extensions

Potential improvements for specific applications:
- More sophisticated heat transfer boundary conditions
- Multi-dimensional spatial derivatives
- Coupling with CFD simulations
- Adaptive physics loss weighting schemes