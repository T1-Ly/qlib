# ModifiedPINN: Physics-Informed Neural Network with Trainable Parameters

## Overview

The ModifiedPINN (Physics-Informed Neural Network) class implements a neural network that learns physical parameters alongside standard neural network weights. This approach allows the model to discover optimal physical parameters (K, RHO, C_P, MU) directly from data while respecting physics constraints.

## Key Features

### 1. Trainable Physical Parameters
- **K (Thermal Conductivity)**: Controls heat transfer in materials
- **RHO (Density)**: Mass per unit volume of the material
- **C_P (Specific Heat Capacity)**: Amount of heat required to raise temperature
- **MU (Dynamic Viscosity)**: Resistance to flow in fluids

### 2. Physics-Informed Training
- Combines data-driven loss with physics-based constraints
- Enforces physical relationships between parameters
- Maintains parameter bounds to ensure realistic values

### 3. Comprehensive Training Features
- Parameter regularization to prevent extreme values
- Early stopping for optimal convergence
- Training history tracking for all parameters
- Configurable physics loss weighting

### 4. Model Persistence
- Save/load trained models with learned parameters
- JSON export of parameter values and training history
- Compatible with TensorFlow's native save format

## Usage Example

```python
from qlib.contrib.model.tensorflow_pinn import ModifiedPINN

# Create model with initial parameter guesses
model = ModifiedPINN(
    input_dim=10,
    hidden_layers=[64, 32, 16],
    initial_K=0.5,          # Initial thermal conductivity
    initial_RHO=1000.0,     # Initial density
    initial_C_P=4000.0,     # Initial specific heat capacity
    initial_MU=0.001,       # Initial dynamic viscosity
    physics_loss_weight=1.0, # Weight for physics constraints
    param_reg_weight=0.01   # Weight for parameter regularization
)

# Train the model
evals_result = {}
model.fit(dataset, evals_result=evals_result, save_path="./pinn_model")

# Get learned parameters
learned_params = model.get_learned_parameters()
print(f"Learned K: {learned_params['K']:.6f}")
print(f"Learned RHO: {learned_params['RHO']:.2f}")
print(f"Learned C_P: {learned_params['C_P']:.2f}")
print(f"Learned MU: {learned_params['MU']:.6f}")

# Make predictions
predictions = model.predict(dataset, segment="test")

# Access training history
history = model.get_training_history()
```

## Configuration Parameters

### Neural Network Architecture
- `input_dim`: Number of input features
- `hidden_layers`: List of hidden layer sizes (default: [64, 64, 64])
- `output_dim`: Number of outputs (default: 1)
- `activation`: Activation function (default: 'tanh')

### Training Configuration
- `lr`: Learning rate (default: 0.001)
- `epochs`: Maximum training epochs (default: 100)
- `batch_size`: Training batch size (default: 32)
- `early_stop`: Early stopping patience (default: 20)

### Physics Parameters
- `physics_loss_weight`: Weight for physics loss term (default: 1.0)
- `param_reg_weight`: Weight for parameter regularization (default: 0.01)

### Initial Parameter Values
- `initial_K`: Initial thermal conductivity (default: 0.5)
- `initial_RHO`: Initial density (default: 1000.0)
- `initial_C_P`: Initial specific heat capacity (default: 4180.0)
- `initial_MU`: Initial dynamic viscosity (default: 0.001)

### Parameter Bounds
- `K_bounds`: Thermal conductivity bounds (default: (0.01, 10.0))
- `RHO_bounds`: Density bounds (default: (100.0, 10000.0))
- `C_P_bounds`: Specific heat capacity bounds (default: (1000.0, 10000.0))
- `MU_bounds`: Dynamic viscosity bounds (default: (0.0001, 0.1))

## Physics Implementation

The model implements physics constraints through:

1. **Parameter Regularization**: Soft constraints that penalize parameters outside physical bounds
2. **Physics Loss**: Custom loss function encoding physical relationships between parameters
3. **Combined Optimization**: Joint optimization of neural network weights and physical parameters

### Example Physics Constraint

```python
def physics_constraint(self, inputs, outputs):
    # Thermal diffusivity relationship
    thermal_diffusivity = self.K / (self.RHO * self.C_P)
    
    # Constraint: thermal diffusivity should be in reasonable range
    target_diffusivity = 1e-7  # Typical value for many materials
    constraint_loss = tf.square(thermal_diffusivity - target_diffusivity)
    
    return constraint_loss
```

## Training Process

The training process optimizes three loss components:

1. **Data Loss**: Standard MSE between predictions and targets
2. **Physics Loss**: Custom physics constraints
3. **Parameter Regularization**: Soft bounds on parameter values

Total loss = Data Loss + λ₁ × Physics Loss + λ₂ × Parameter Regularization

Where λ₁ and λ₂ are configurable weights.

## Output and Monitoring

### Training History
The model tracks comprehensive training metrics:
- Total, data, physics, and regularization losses
- Evolution of all physical parameters over training
- Validation performance

### Parameter Learning
Access learned parameters at any time:
```python
params = model.get_learned_parameters()
# Returns: {'K': value, 'RHO': value, 'C_P': value, 'MU': value}
```

### Training Visualization
Plot parameter evolution and loss curves:
```python
history = model.get_training_history()
# Contains: 'total_loss', 'data_loss', 'physics_loss', 'param_reg_loss',
#           'K_values', 'RHO_values', 'C_P_values', 'MU_values'
```

## Model Persistence

### Saving
```python
model.save_model(path="./my_pinn_model")
# Saves: pinn_model.keras (neural network) + learned_parameters.json
```

### Loading
```python
new_model = ModifiedPINN(input_dim=input_dim)
new_model.load_model(path="./my_pinn_model")
```

## Dependencies

- TensorFlow >= 2.0
- NumPy
- Pandas
- Standard qlib dependencies

## Example Applications

The ModifiedPINN is suitable for problems where:
- Physical parameters are unknown but follow known physics laws
- Data is available but parameter identification is needed
- Physics constraints should guide the learning process
- Interpretable parameter values are required

Common use cases include:
- Heat transfer parameter identification
- Fluid dynamics parameter estimation
- Material property discovery
- System identification in engineering applications

## Notes

- The physics equations in the current implementation are simplified examples
- Real applications should implement domain-specific physics constraints
- Parameter bounds should be set based on physical knowledge
- The model works best when physics constraints are well-defined
- Training may require tuning of loss weights for optimal performance