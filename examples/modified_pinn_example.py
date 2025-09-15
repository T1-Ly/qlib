#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Example usage of ModifiedPINN for physics-informed neural network with trainable parameters.

This example demonstrates:
1. Creating a ModifiedPINN with trainable physical parameters
2. Training the model on synthetic data
3. Monitoring parameter evolution during training
4. Saving and loading learned parameters
5. Making predictions with the trained model

Usage:
    python examples/modified_pinn_example.py
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tempfile

# Add the qlib directory to the path for standalone execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import tensorflow as tf
    tf_available = True
except ImportError:
    tf_available = False
    print("TensorFlow is required for this example. Please install it with: pip install tensorflow")
    sys.exit(1)


def generate_physics_data(n_samples=2000, n_features=8, noise_level=0.05):
    """
    Generate synthetic data that incorporates physics relationships.
    
    This function creates synthetic data that has underlying physics relationships
    involving thermal conductivity (K), density (RHO), specific heat capacity (C_P),
    and dynamic viscosity (MU).
    """
    print("Generating synthetic physics data...")
    
    np.random.seed(42)
    
    # True physical parameters (what we want the model to learn)
    true_K = 1.2      # thermal conductivity
    true_RHO = 1500.0 # density  
    true_C_P = 3800.0 # specific heat capacity
    true_MU = 0.005   # dynamic viscosity
    
    # Generate input features (temperature, pressure, velocity, etc.)
    features = np.random.randn(n_samples, n_features)
    
    # Create physics-based relationships
    # Example: heat transfer involves K, RHO, C_P
    thermal_diffusivity = true_K / (true_RHO * true_C_P)
    
    # Create a synthetic target that depends on the physical parameters
    # This is a simplified example - in real applications, this would be 
    # the solution to actual physics equations
    target = (
        features[:, 0] * true_K +
        features[:, 1] * true_RHO / 1000.0 +
        features[:, 2] * true_C_P / 1000.0 +
        features[:, 3] * true_MU * 1000.0 +
        np.sqrt(thermal_diffusivity) * (features[:, 4] + features[:, 5]) +
        0.1 * np.sum(features[:, 6:], axis=1)
    )
    
    # Add noise
    target += noise_level * np.random.randn(n_samples)
    
    print(f"Generated {n_samples} samples with {n_features} features")
    print(f"True parameters - K: {true_K}, RHO: {true_RHO}, C_P: {true_C_P}, MU: {true_MU}")
    
    return features, target, {
        'K': true_K, 'RHO': true_RHO, 'C_P': true_C_P, 'MU': true_MU
    }


def create_mock_dataset(features, target):
    """Create a mock dataset compatible with qlib's DatasetH interface."""
    
    # Create date index
    dates = pd.date_range('2020-01-01', periods=len(features), freq='D')
    instruments = ['physics_system'] * len(features)
    
    # Create DataFrame
    feature_cols = [f'feature_{i}' for i in range(features.shape[1])]
    data_dict = {}
    for i, col in enumerate(feature_cols):
        data_dict[col] = features[:, i]
    data_dict['label'] = target
    
    df = pd.DataFrame(data_dict)
    df.index = pd.MultiIndex.from_arrays([instruments, dates], names=['instrument', 'datetime'])
    
    return df, feature_cols


class MockDatasetH:
    """Mock dataset that implements the qlib DatasetH interface."""
    
    def __init__(self, df, feature_cols):
        self.df = df
        self.feature_cols = feature_cols
        
    def prepare(self, segments, col_set, data_key=None):
        if isinstance(segments, list) and len(segments) == 2:
            # Split data for train/validation
            split_idx = int(0.8 * len(self.df))
            train_df = self.df.iloc[:split_idx]
            valid_df = self.df.iloc[split_idx:]
            
            if col_set == ["feature", "label"]:
                train_features = train_df[self.feature_cols]
                train_labels = train_df[['label']]
                valid_features = valid_df[self.feature_cols]
                valid_labels = valid_df[['label']]
                
                return (
                    {"feature": train_features, "label": train_labels},
                    {"feature": valid_features, "label": valid_labels}
                )
        elif col_set == "feature":
            return self.df[self.feature_cols]
        
        return self.df


def plot_training_history(history, true_params):
    """Plot the training history and parameter evolution."""
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    # Plot losses
    epochs = range(len(history['total_loss']))
    
    axes[0, 0].plot(epochs, history['total_loss'], label='Total Loss')
    axes[0, 0].plot(epochs, history['data_loss'], label='Data Loss') 
    axes[0, 0].plot(epochs, history['physics_loss'], label='Physics Loss')
    axes[0, 0].set_xlabel('Epoch')
    axes[0, 0].set_ylabel('Loss')
    axes[0, 0].set_title('Training Losses')
    axes[0, 0].legend()
    axes[0, 0].set_yscale('log')
    
    # Plot parameter evolution
    param_names = ['K', 'RHO', 'C_P', 'MU']
    param_colors = ['red', 'blue', 'green', 'orange']
    
    for i, (param, color) in enumerate(zip(param_names, param_colors)):
        row = (i + 1) // 3
        col = (i + 1) % 3
        
        axes[row, col].plot(epochs, history[f'{param}_values'], 
                           color=color, label=f'Learned {param}', linewidth=2)
        axes[row, col].axhline(y=true_params[param], color=color, linestyle='--', 
                              label=f'True {param}', alpha=0.7)
        axes[row, col].set_xlabel('Epoch')
        axes[row, col].set_ylabel(f'{param} Value')
        axes[row, col].set_title(f'Parameter Evolution: {param}')
        axes[row, col].legend()
        axes[row, col].grid(True, alpha=0.3)
    
    # Remove empty subplot
    axes[1, 2].remove()
    
    plt.tight_layout()
    return fig


def main():
    """Main function demonstrating ModifiedPINN usage."""
    
    print("ModifiedPINN Example")
    print("=" * 50)
    
    if not tf_available:
        print("TensorFlow is not available. Please install it to run this example.")
        return
    
    # Step 1: Generate synthetic physics data
    features, target, true_params = generate_physics_data(n_samples=2000, n_features=8)
    
    # Step 2: Create mock dataset
    df, feature_cols = create_mock_dataset(features, target)
    dataset = MockDatasetH(df, feature_cols)
    
    print(f"Dataset shape: {df.shape}")
    print(f"Features: {feature_cols}")
    
    # Step 3: Create and configure ModifiedPINN
    print("\nCreating ModifiedPINN model...")
    
    # Import here to avoid dependency issues if running as standalone
    try:
        from qlib.contrib.model.tensorflow_pinn import ModifiedPINN
    except ImportError:
        print("Could not import ModifiedPINN. Make sure qlib is installed.")
        return
    
    pinn_model = ModifiedPINN(
        input_dim=len(feature_cols),
        hidden_layers=[64, 32, 16],
        output_dim=1,
        lr=0.001,
        epochs=50,
        batch_size=64,
        early_stop=10,
        physics_loss_weight=0.1,
        param_reg_weight=0.01,
        # Initial parameter guesses (intentionally different from true values)
        initial_K=0.5,
        initial_RHO=1000.0,
        initial_C_P=4000.0,
        initial_MU=0.001,
        # Parameter bounds
        K_bounds=(0.1, 5.0),
        RHO_bounds=(500.0, 3000.0),
        C_P_bounds=(2000.0, 6000.0),
        MU_bounds=(0.0001, 0.02),
        device="cpu"
    )
    
    print("Model configuration:")
    print(f"  Hidden layers: {pinn_model.hidden_layers}")
    print(f"  Learning rate: {pinn_model.lr}")
    print(f"  Physics loss weight: {pinn_model.physics_loss_weight}")
    print(f"  Parameter regularization weight: {pinn_model.param_reg_weight}")
    
    # Display initial parameters
    initial_params = pinn_model.get_learned_parameters()
    print(f"\nInitial parameters: {initial_params}")
    print(f"True parameters:    {true_params}")
    
    # Step 4: Train the model
    print("\nTraining ModifiedPINN...")
    print("-" * 30)
    
    evals_result = {}
    
    with tempfile.TemporaryDirectory() as temp_dir:
        save_path = os.path.join(temp_dir, "pinn_example_model")
        
        pinn_model.fit(dataset, evals_result=evals_result, save_path=save_path)
        
        # Step 5: Analyze results
        print("\nTraining completed!")
        print(f"Final training results: {evals_result}")
        
        # Get learned parameters
        learned_params = pinn_model.get_learned_parameters()
        print(f"\nLearned parameters: {learned_params}")
        print(f"True parameters:    {true_params}")
        
        # Calculate parameter errors
        print("\nParameter Learning Accuracy:")
        for param in ['K', 'RHO', 'C_P', 'MU']:
            error = abs(learned_params[param] - true_params[param]) / true_params[param] * 100
            print(f"  {param}: {learned_params[param]:.6f} (true: {true_params[param]:.6f}) - Error: {error:.2f}%")
        
        # Step 6: Test prediction
        print("\nTesting predictions...")
        predictions = pinn_model.predict(dataset, segment="test")
        print(f"Predictions shape: {predictions.shape}")
        print(f"Sample predictions: {predictions.head()}")
        
        # Step 7: Test save/load functionality
        print("\nTesting save/load functionality...")
        pinn_model.save_model()
        
        # Create new model and load
        new_model = ModifiedPINN(input_dim=len(feature_cols))
        new_model.load_model(save_path)
        
        # Verify parameters were loaded correctly
        loaded_params = new_model.get_learned_parameters()
        print(f"Loaded parameters: {loaded_params}")
        
        params_match = all(
            abs(learned_params[k] - loaded_params[k]) < 1e-6 
            for k in learned_params.keys()
        )
        print(f"Parameters loaded correctly: {params_match}")
        
        # Step 8: Plot results (if matplotlib is available)
        try:
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            
            history = pinn_model.get_training_history()
            fig = plot_training_history(history, true_params)
            
            plot_path = os.path.join(temp_dir, "training_history.png")
            fig.savefig(plot_path, dpi=150, bbox_inches='tight')
            print(f"\nTraining history plot saved to: {plot_path}")
            
        except ImportError:
            print("\nMatplotlib not available, skipping plot generation.")
    
    print("\n" + "=" * 50)
    print("ModifiedPINN example completed successfully!")
    print("\nKey features demonstrated:")
    print("✓ Physics-informed neural network with trainable parameters")
    print("✓ Parameter learning from data")
    print("✓ Physics loss and regularization")
    print("✓ Training history tracking")
    print("✓ Model save/load functionality")
    print("✓ Parameter bounds enforcement")


if __name__ == "__main__":
    main()