# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from __future__ import division
from __future__ import print_function

import os
import gc
import numpy as np
import pandas as pd
from typing import Callable, Optional, Text, Union, Dict, Any
from sklearn.metrics import mean_squared_error

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

from ...model.base import Model
from ...data.dataset import DatasetH
from ...data.dataset.handler import DataHandlerLP
from ...utils import (
    auto_filter_kwargs,
    init_instance_by_config,
    get_or_create_path,
)
from ...log import get_module_logger


class ModifiedPINN(Model):
    """
    Modified Physics-Informed Neural Network (PINN) with trainable physical parameters.
    
    This model implements a physics-informed neural network that learns physical parameters
    K (thermal conductivity), RHO (density), C_P (specific heat capacity), and MU (dynamic viscosity)
    alongside the neural network weights during training.
    
    Parameters
    ----------
    input_dim : int
        Input dimension (number of features)
    hidden_layers : list of int
        Hidden layer sizes, default [64, 64, 64]
    output_dim : int
        Output dimension, default 1
    activation : str
        Activation function, default 'tanh'
    lr : float
        Learning rate, default 0.001
    epochs : int
        Number of training epochs, default 100
    batch_size : int
        Batch size for training, default 32
    early_stop : int
        Early stopping patience, default 20
    physics_loss_weight : float
        Weight for physics loss term, default 1.0
    param_reg_weight : float
        Weight for parameter regularization, default 0.01
    initial_K : float
        Initial value for thermal conductivity, default 0.5
    initial_RHO : float
        Initial value for density, default 1000.0
    initial_C_P : float
        Initial value for specific heat capacity, default 4180.0
    initial_MU : float
        Initial value for dynamic viscosity, default 0.001
    K_bounds : tuple
        Bounds for K parameter (min, max), default (0.01, 10.0)
    RHO_bounds : tuple
        Bounds for RHO parameter (min, max), default (100.0, 10000.0)
    C_P_bounds : tuple
        Bounds for C_P parameter (min, max), default (1000.0, 10000.0)
    MU_bounds : tuple
        Bounds for MU parameter (min, max), default (0.0001, 0.1)
    save_path : str
        Path to save model checkpoints
    device : str
        Device to use ('cpu' or 'gpu'), default 'cpu'
    """
    
    def __init__(
        self,
        input_dim: int = 10,
        hidden_layers: list = [64, 64, 64],
        output_dim: int = 1,
        activation: str = "tanh",
        lr: float = 0.001,
        epochs: int = 100,
        batch_size: int = 32,
        early_stop: int = 20,
        physics_loss_weight: float = 1.0,
        param_reg_weight: float = 0.01,
        initial_K: float = 0.5,
        initial_RHO: float = 1000.0,
        initial_C_P: float = 4180.0,
        initial_MU: float = 0.001,
        K_bounds: tuple = (0.01, 10.0),
        RHO_bounds: tuple = (100.0, 10000.0),
        C_P_bounds: tuple = (1000.0, 10000.0),
        MU_bounds: tuple = (0.0001, 0.1),
        save_path: str = None,
        device: str = "cpu",
        **kwargs
    ):
        # Set random seeds for reproducibility
        tf.random.set_seed(42)
        np.random.seed(42)
        
        # Model configuration
        self.input_dim = input_dim
        self.hidden_layers = hidden_layers
        self.output_dim = output_dim
        self.activation = activation
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.early_stop = early_stop
        self.physics_loss_weight = physics_loss_weight
        self.param_reg_weight = param_reg_weight
        self.save_path = save_path
        
        # Physical parameter initialization
        self.initial_K = initial_K
        self.initial_RHO = initial_RHO
        self.initial_C_P = initial_C_P
        self.initial_MU = initial_MU
        
        # Parameter bounds for regularization
        self.K_bounds = K_bounds
        self.RHO_bounds = RHO_bounds
        self.C_P_bounds = C_P_bounds
        self.MU_bounds = MU_bounds
        
        # Configure device
        if device == "gpu" and tf.config.list_physical_devices('GPU'):
            self.device = "/GPU:0"
        else:
            self.device = "/CPU:0"
            
        # Initialize logger
        self.logger = get_module_logger(self.__class__.__name__)
        
        # Model and parameters will be initialized in fit()
        self.model = None
        self.physical_params = None
        self.optimizer = None
        self.fitted = False
        
        # Training history
        self.history = {
            'total_loss': [],
            'data_loss': [],
            'physics_loss': [],
            'param_reg_loss': [],
            'K_values': [],
            'RHO_values': [],
            'C_P_values': [],
            'MU_values': []
        }
    
    def _build_model(self):
        """Build the neural network architecture."""
        with tf.device(self.device):
            inputs = keras.Input(shape=(self.input_dim,), name='input')
            x = inputs
            
            # Hidden layers
            for i, units in enumerate(self.hidden_layers):
                x = layers.Dense(
                    units, 
                    activation=self.activation,
                    name=f'hidden_{i+1}'
                )(x)
            
            # Output layer
            outputs = layers.Dense(self.output_dim, name='output')(x)
            
            model = keras.Model(inputs=inputs, outputs=outputs, name='ModifiedPINN')
            
            return model
    
    def _initialize_physical_parameters(self):
        """Initialize trainable physical parameters."""
        with tf.device(self.device):
            # Create trainable variables for physical parameters
            self.K = tf.Variable(
                self.initial_K, 
                trainable=True, 
                name='thermal_conductivity',
                dtype=tf.float32
            )
            self.RHO = tf.Variable(
                self.initial_RHO, 
                trainable=True, 
                name='density',
                dtype=tf.float32
            )
            self.C_P = tf.Variable(
                self.initial_C_P, 
                trainable=True, 
                name='specific_heat_capacity',
                dtype=tf.float32
            )
            self.MU = tf.Variable(
                self.initial_MU, 
                trainable=True, 
                name='dynamic_viscosity',
                dtype=tf.float32
            )
            
            # Store in dictionary for easy access
            self.physical_params = {
                'K': self.K,
                'RHO': self.RHO,
                'C_P': self.C_P,
                'MU': self.MU
            }
    
    def _physics_equations(self, inputs, outputs):
        """
        Implement physics equations using the trainable parameters.
        This is a placeholder implementation - should be replaced with actual physics equations.
        """
        # Example physics loss: heat equation constraint
        # In a real implementation, this would contain actual differential equations
        # using the trainable parameters K, RHO, C_P, MU
        
        # For demonstration, create a simple physics constraint
        # that penalizes deviations from expected physical relationships
        physics_loss = tf.reduce_mean(tf.square(outputs))
        
        # Add parameter-dependent physics constraints
        # Example: thermal diffusivity = K / (RHO * C_P)
        thermal_diffusivity = self.K / (self.RHO * self.C_P)
        
        # Add constraint that thermal diffusivity should be reasonable
        physics_loss += tf.square(thermal_diffusivity - 1e-7)
        
        return physics_loss
    
    def _parameter_regularization_loss(self):
        """Apply regularization to keep parameters within physical bounds."""
        reg_loss = 0.0
        
        # K bounds regularization
        reg_loss += tf.nn.relu(self.K_bounds[0] - self.K) + tf.nn.relu(self.K - self.K_bounds[1])
        
        # RHO bounds regularization  
        reg_loss += tf.nn.relu(self.RHO_bounds[0] - self.RHO) + tf.nn.relu(self.RHO - self.RHO_bounds[1])
        
        # C_P bounds regularization
        reg_loss += tf.nn.relu(self.C_P_bounds[0] - self.C_P) + tf.nn.relu(self.C_P - self.C_P_bounds[1])
        
        # MU bounds regularization
        reg_loss += tf.nn.relu(self.MU_bounds[0] - self.MU) + tf.nn.relu(self.MU - self.MU_bounds[1])
        
        return reg_loss
    
    @tf.function
    def _train_step(self, x_batch, y_batch):
        """Single training step."""
        with tf.GradientTape() as tape:
            # Forward pass
            predictions = self.model(x_batch, training=True)
            
            # Data loss (MSE)
            data_loss = tf.reduce_mean(tf.square(y_batch - predictions))
            
            # Physics loss
            physics_loss = self._physics_equations(x_batch, predictions)
            
            # Parameter regularization loss
            param_reg_loss = self._parameter_regularization_loss()
            
            # Total loss
            total_loss = (data_loss + 
                         self.physics_loss_weight * physics_loss + 
                         self.param_reg_weight * param_reg_loss)
        
        # Get all trainable variables (model weights + physical parameters)
        trainable_vars = (self.model.trainable_variables + 
                         list(self.physical_params.values()))
        
        # Compute gradients
        gradients = tape.gradient(total_loss, trainable_vars)
        
        # Apply gradients
        self.optimizer.apply_gradients(zip(gradients, trainable_vars))
        
        return total_loss, data_loss, physics_loss, param_reg_loss
    
    def fit(self, dataset: DatasetH, evals_result=dict(), save_path=None):
        """
        Train the ModifiedPINN model.
        
        Parameters
        ----------
        dataset : DatasetH
            The dataset for training
        evals_result : dict
            Dictionary to store evaluation results
        save_path : str
            Path to save the trained model
        """
        # Set save path
        if save_path is not None:
            self.save_path = save_path
        
        # Prepare data
        df_train, df_valid = dataset.prepare(
            ["train", "valid"], col_set=["feature", "label"], data_key=DataHandlerLP.DK_L
        )
        x_train, y_train = df_train["feature"], df_train["label"]
        x_valid, y_valid = df_valid["feature"], df_valid["label"]
        
        # Convert to numpy arrays
        x_train = x_train.values.astype(np.float32)
        y_train = y_train.values.astype(np.float32)
        x_valid = x_valid.values.astype(np.float32)
        y_valid = y_valid.values.astype(np.float32)
        
        # Update input dimension if needed
        self.input_dim = x_train.shape[1]
        
        with tf.device(self.device):
            # Build model and initialize parameters
            self.model = self._build_model()
            self._initialize_physical_parameters()
            
            # Initialize optimizer
            self.optimizer = keras.optimizers.Adam(learning_rate=self.lr)
            
            self.logger.info(f"Model built with input_dim={self.input_dim}")
            self.logger.info(f"Model summary: {self.model.summary()}")
            self.logger.info(f"Training on device: {self.device}")
            
            # Training loop
            best_valid_loss = float('inf')
            early_stop_counter = 0
            
            # Create TensorFlow datasets
            train_dataset = tf.data.Dataset.from_tensor_slices((x_train, y_train))
            train_dataset = train_dataset.batch(self.batch_size).shuffle(1000)
            
            for epoch in range(self.epochs):
                # Training
                epoch_total_loss = 0.0
                epoch_data_loss = 0.0
                epoch_physics_loss = 0.0
                epoch_param_reg_loss = 0.0
                num_batches = 0
                
                for x_batch, y_batch in train_dataset:
                    total_loss, data_loss, physics_loss, param_reg_loss = self._train_step(x_batch, y_batch)
                    
                    epoch_total_loss += total_loss
                    epoch_data_loss += data_loss
                    epoch_physics_loss += physics_loss
                    epoch_param_reg_loss += param_reg_loss
                    num_batches += 1
                
                # Average losses
                epoch_total_loss /= num_batches
                epoch_data_loss /= num_batches
                epoch_physics_loss /= num_batches
                epoch_param_reg_loss /= num_batches
                
                # Validation
                valid_predictions = self.model(x_valid, training=False)
                valid_loss = tf.reduce_mean(tf.square(y_valid - valid_predictions))
                
                # Store history
                self.history['total_loss'].append(float(epoch_total_loss))
                self.history['data_loss'].append(float(epoch_data_loss))
                self.history['physics_loss'].append(float(epoch_physics_loss))
                self.history['param_reg_loss'].append(float(epoch_param_reg_loss))
                self.history['K_values'].append(float(self.K))
                self.history['RHO_values'].append(float(self.RHO))
                self.history['C_P_values'].append(float(self.C_P))
                self.history['MU_values'].append(float(self.MU))
                
                # Logging
                if epoch % 10 == 0:
                    self.logger.info(
                        f"Epoch {epoch}: "
                        f"Total Loss={epoch_total_loss:.6f}, "
                        f"Data Loss={epoch_data_loss:.6f}, "
                        f"Physics Loss={epoch_physics_loss:.6f}, "
                        f"Param Reg Loss={epoch_param_reg_loss:.6f}, "
                        f"Valid Loss={valid_loss:.6f}"
                    )
                    self.logger.info(
                        f"Parameters - K={self.K.numpy():.6f}, "
                        f"RHO={self.RHO.numpy():.2f}, "
                        f"C_P={self.C_P.numpy():.2f}, "
                        f"MU={self.MU.numpy():.6f}"
                    )
                
                # Early stopping
                if valid_loss < best_valid_loss:
                    best_valid_loss = valid_loss
                    early_stop_counter = 0
                    # Save best model
                    if self.save_path is not None:
                        self.save_model()
                else:
                    early_stop_counter += 1
                    if early_stop_counter >= self.early_stop:
                        self.logger.info(f"Early stopping at epoch {epoch}")
                        break
        
        self.fitted = True
        
        # Final parameter values
        self.logger.info("Final learned parameters:")
        self.logger.info(f"K (thermal conductivity): {self.K.numpy():.6f}")
        self.logger.info(f"RHO (density): {self.RHO.numpy():.2f}")
        self.logger.info(f"C_P (specific heat capacity): {self.C_P.numpy():.2f}")
        self.logger.info(f"MU (dynamic viscosity): {self.MU.numpy():.6f}")
        
        # Store results
        evals_result["train"] = {"loss": float(epoch_data_loss)}
        evals_result["valid"] = {"loss": float(valid_loss)}
        evals_result["learned_params"] = {
            "K": float(self.K.numpy()),
            "RHO": float(self.RHO.numpy()),
            "C_P": float(self.C_P.numpy()),
            "MU": float(self.MU.numpy())
        }
    
    def predict(self, dataset: DatasetH, segment: Union[Text, slice] = "test") -> pd.Series:
        """
        Make predictions using the trained model.
        
        Parameters
        ----------
        dataset : DatasetH
            Dataset to make predictions on
        segment : Text or slice
            Data segment to use for prediction
            
        Returns
        -------
        pd.Series
            Predictions
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before making predictions")
        
        # Prepare data
        df_test = dataset.prepare(segment, col_set="feature", data_key=DataHandlerLP.DK_I)
        x_test = df_test.values.astype(np.float32)
        
        with tf.device(self.device):
            # Make predictions
            predictions = self.model(x_test, training=False)
            predictions = predictions.numpy().flatten()
        
        # Return as pandas Series with original index
        return pd.Series(predictions, index=df_test.index)
    
    def save_model(self, path: str = None):
        """
        Save the trained model and learned parameters.
        
        Parameters
        ----------
        path : str
            Path to save the model. If None, uses self.save_path
        """
        if path is None:
            path = self.save_path
        
        if path is None:
            raise ValueError("No save path specified")
        
        # Create directory if it doesn't exist
        save_dir = get_or_create_path(path)
        
        # Save the neural network model
        self.model.save(os.path.join(save_dir, "pinn_model.keras"))
        
        # Save learned parameters
        params_dict = {
            "K": float(self.K.numpy()),
            "RHO": float(self.RHO.numpy()),
            "C_P": float(self.C_P.numpy()),
            "MU": float(self.MU.numpy()),
            "training_history": self.history
        }
        
        import json
        with open(os.path.join(save_dir, "learned_parameters.json"), 'w') as f:
            json.dump(params_dict, f, indent=2)
        
        self.logger.info(f"Model and parameters saved to {save_dir}")
    
    def load_model(self, path: str):
        """
        Load a trained model and learned parameters.
        
        Parameters
        ----------
        path : str
            Path to load the model from
        """
        # Load the neural network model
        self.model = keras.models.load_model(os.path.join(path, "pinn_model.keras"))
        
        # Load learned parameters
        import json
        with open(os.path.join(path, "learned_parameters.json"), 'r') as f:
            params_dict = json.load(f)
        
        # Restore physical parameters
        with tf.device(self.device):
            self.K = tf.Variable(params_dict["K"], trainable=True, name='thermal_conductivity', dtype=tf.float32)
            self.RHO = tf.Variable(params_dict["RHO"], trainable=True, name='density', dtype=tf.float32)
            self.C_P = tf.Variable(params_dict["C_P"], trainable=True, name='specific_heat_capacity', dtype=tf.float32)
            self.MU = tf.Variable(params_dict["MU"], trainable=True, name='dynamic_viscosity', dtype=tf.float32)
            
            self.physical_params = {
                'K': self.K,
                'RHO': self.RHO,
                'C_P': self.C_P,
                'MU': self.MU
            }
        
        # Restore training history
        self.history = params_dict["training_history"]
        self.fitted = True
        
        self.logger.info(f"Model and parameters loaded from {path}")
        self.logger.info(f"Loaded parameters - K={self.K.numpy():.6f}, RHO={self.RHO.numpy():.2f}, C_P={self.C_P.numpy():.2f}, MU={self.MU.numpy():.6f}")
    
    def get_learned_parameters(self) -> Dict[str, float]:
        """
        Get the current values of learned physical parameters.
        
        Returns
        -------
        Dict[str, float]
            Dictionary containing the learned parameter values
        """
        if not self.fitted:
            return {
                "K": self.initial_K,
                "RHO": self.initial_RHO,
                "C_P": self.initial_C_P,
                "MU": self.initial_MU
            }
        
        return {
            "K": float(self.K.numpy()),
            "RHO": float(self.RHO.numpy()),
            "C_P": float(self.C_P.numpy()),
            "MU": float(self.MU.numpy())
        }
    
    def get_training_history(self) -> Dict:
        """
        Get the training history including parameter evolution.
        
        Returns
        -------
        Dict
            Dictionary containing training history
        """
        return self.history.copy()