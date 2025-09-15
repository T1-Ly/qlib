# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from __future__ import division
from __future__ import print_function

import numpy as np
import pandas as pd
from typing import Union, Optional, Callable
import copy
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, TensorDataset

from .pytorch_utils import count_parameters
from ...model.base import Model
from ...data.dataset import DatasetH, TSDatasetH
from ...data.dataset.handler import DataHandlerLP
from ...data.dataset.weight import Reweighter
from ...utils import (
    init_instance_by_config,
    get_or_create_path,
)
from ...log import get_module_logger
from ...model.utils import ConcatDataset


class PINNModel(nn.Module):
    """
    Physics-Informed Neural Network for Heat Transfer with Radiative Terms
    
    This model includes:
    - Neural network with tanh activation functions
    - Radiative heat transfer term: qrad = ε*σ*(T^4 - T0^4)
    - Trainable emission coefficient (ε)
    - Stefan-Boltzmann constant (σ) for radiative heat transfer
    """
    
    def __init__(
        self,
        input_dim: int = 6,
        hidden_size: int = 64,
        num_layers: int = 3,
        dropout: float = 0.1,
        emission_coeff_init: float = 0.8,
        stefan_boltzmann: float = 5.67e-8,
        reference_temp: float = 298.15,  # Reference temperature T0 in Kelvin
    ):
        super(PINNModel, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.stefan_boltzmann = stefan_boltzmann
        self.reference_temp = reference_temp
        
        # Build the neural network with tanh activation functions
        layers = []
        
        # Input layer
        layers.append(nn.Linear(input_dim, hidden_size))
        layers.append(nn.Tanh())
        layers.append(nn.Dropout(dropout))
        
        # Hidden layers
        for _ in range(num_layers - 2):
            layers.append(nn.Linear(hidden_size, hidden_size))
            layers.append(nn.Tanh())
            layers.append(nn.Dropout(dropout))
        
        # Output layer
        layers.append(nn.Linear(hidden_size, 1))
        
        self.network = nn.Sequential(*layers)
        
        # Trainable emission coefficient (ε) with proper constraints
        self.emission_coeff = nn.Parameter(
            torch.tensor(emission_coeff_init, dtype=torch.float32)
        )
        
        # Initialize weights using Xavier initialization for tanh
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize network weights using Xavier initialization for tanh activation"""
        for module in self.network:
            if isinstance(module, nn.Linear):
                nn.init.xavier_normal_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
    
    def forward(self, x):
        """Forward pass through the network"""
        return self.network(x)
    
    def get_emission_coefficient(self):
        """Get the constrained emission coefficient (clamped between 0 and 1)"""
        return torch.clamp(self.emission_coeff, min=0.0, max=1.0)
    
    def compute_radiative_heat_transfer(self, temperature):
        """
        Compute radiative heat transfer: qrad = ε*σ*(T^4 - T0^4)
        
        Args:
            temperature: Temperature tensor (assumed to be in Kelvin or normalized)
        
        Returns:
            Radiative heat transfer tensor
        """
        epsilon = self.get_emission_coefficient()
        
        # Ensure temperature is positive for T^4 calculation
        temp_abs = torch.abs(temperature) + self.reference_temp
        temp_ref = torch.tensor(self.reference_temp, device=temperature.device, dtype=temperature.dtype)
        
        # Compute T^4 - T0^4
        temp_diff_4th = torch.pow(temp_abs, 4) - torch.pow(temp_ref, 4)
        
        # Radiative heat transfer
        qrad = epsilon * self.stefan_boltzmann * temp_diff_4th
        
        return qrad


class PytorchPINN(Model):
    """
    Physics-Informed Neural Network (PINN) Model for Heat Transfer
    
    This implementation addresses the following issues:
    1. Uses tanh activation functions instead of ReLU for better gradient stability
    2. Includes radiative heat transfer term in physics loss calculation
    3. Properly handles emission coefficient constraints
    4. Avoids None gradients through proper tensor handling
    5. Does not use problematic TensorFlow experimental configuration calls
    """
    
    def __init__(
        self,
        input_dim: int = 6,
        hidden_size: int = 64,
        num_layers: int = 3,
        dropout: float = 0.1,
        n_epochs: int = 200,
        lr: float = 0.001,
        batch_size: int = 2000,
        early_stop: int = 20,
        weight_decay: float = 0.0,
        optimizer: str = "adam",
        physics_loss_weight: float = 1.0,
        data_loss_weight: float = 1.0,
        emission_coeff_init: float = 0.8,
        stefan_boltzmann: float = 5.67e-8,
        reference_temp: float = 298.15,
        n_jobs: int = 10,
        GPU: int = 0,
        seed: Optional[int] = None,
        metric: str = "mse",
    ):
        # Set logger
        self.logger = get_module_logger("PytorchPINN")
        self.logger.info("Physics-Informed Neural Network (PINN) pytorch version...")
        
        # Set hyperparameters
        self.input_dim = input_dim
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.n_epochs = n_epochs
        self.lr = lr
        self.batch_size = batch_size
        self.early_stop = early_stop
        self.weight_decay = weight_decay
        self.optimizer_name = optimizer.lower()
        self.physics_loss_weight = physics_loss_weight
        self.data_loss_weight = data_loss_weight
        self.emission_coeff_init = emission_coeff_init
        self.stefan_boltzmann = stefan_boltzmann
        self.reference_temp = reference_temp
        self.n_jobs = n_jobs
        self.seed = seed
        self.metric = metric
        
        # Set device
        self.device = torch.device("cuda:%d" % (GPU) if torch.cuda.is_available() and GPU >= 0 else "cpu")
        
        # Set random seed
        if self.seed is not None:
            np.random.seed(self.seed)
            torch.manual_seed(self.seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(self.seed)
        
        # Initialize model
        self.model = PINNModel(
            input_dim=input_dim,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            emission_coeff_init=emission_coeff_init,
            stefan_boltzmann=stefan_boltzmann,
            reference_temp=reference_temp,
        ).to(self.device)
        
        # Initialize optimizer
        if self.optimizer_name == "adam":
            self.optimizer = optim.Adam(
                self.model.parameters(),
                lr=self.lr,
                weight_decay=self.weight_decay
            )
        elif self.optimizer_name == "sgd":
            self.optimizer = optim.SGD(
                self.model.parameters(),
                lr=self.lr,
                weight_decay=self.weight_decay
            )
        else:
            raise NotImplementedError(f"optimizer {optimizer} is not supported!")
        
        # Initialize scheduler
        self.scheduler = ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=10,
            verbose=True
        )
        
        self.logger.info(f"PINN model initialized with {count_parameters(self.model):.4f}M parameters")
        self.logger.info(f"Device: {self.device}")
        
        # Training history
        self.train_losses = []
        self.valid_losses = []
        self.physics_losses = []
        
    @property
    def use_gpu(self):
        return self.device != torch.device("cpu")
    
    def mse_loss(self, pred, label):
        """Mean Squared Error loss"""
        return torch.mean((pred - label) ** 2)
    
    def compute_physics_loss(self, inputs, outputs):
        """
        Compute physics-informed loss including radiative heat transfer
        
        This is a simplified physics loss for demonstration.
        In a real application, this would include:
        - Heat equation: ∂T/∂t = α∇²T + qrad
        - Boundary conditions
        - Initial conditions
        """
        # Enable gradient computation for physics loss
        inputs.requires_grad_(True)
        
        # Forward pass
        temperature = self.model(inputs)
        
        # Compute radiative heat transfer term
        qrad = self.model.compute_radiative_heat_transfer(temperature)
        
        # Compute gradients for physics equation (simplified)
        grad_outputs = torch.ones_like(temperature)
        gradients = torch.autograd.grad(
            outputs=temperature,
            inputs=inputs,
            grad_outputs=grad_outputs,
            create_graph=True,
            retain_graph=True,
            only_inputs=True
        )[0]
        
        # Handle None gradients
        if gradients is None:
            self.logger.warning("None gradients encountered in physics loss computation")
            return torch.tensor(0.0, device=self.device, requires_grad=True)
        
        # Simple physics loss: ensure gradients are reasonable and include radiative effects
        # This is a placeholder - actual physics equations would be more complex
        laplacian_approx = torch.sum(gradients ** 2, dim=1, keepdim=True)
        physics_residual = laplacian_approx - qrad / 1000.0  # Scale qrad appropriately
        
        physics_loss = torch.mean(physics_residual ** 2)
        
        return physics_loss
    
    def train_epoch(self, data_loader):
        """Train the model for one epoch"""
        self.model.train()
        total_loss = 0.0
        total_data_loss = 0.0
        total_physics_loss = 0.0
        n_batches = 0
        
        for batch_idx, (data, target, weight) in enumerate(data_loader):
            data, target, weight = data.to(self.device), target.to(self.device), weight.to(self.device)
            
            self.optimizer.zero_grad()
            
            # Forward pass
            output = self.model(data)
            
            # Data loss (supervised)
            data_loss = self.mse_loss(output, target)
            weighted_data_loss = torch.mean(data_loss * weight.squeeze())
            
            # Physics loss
            physics_loss = self.compute_physics_loss(data, output)
            
            # Combined loss
            total_batch_loss = (
                self.data_loss_weight * weighted_data_loss +
                self.physics_loss_weight * physics_loss
            )
            
            # Backward pass
            total_batch_loss.backward()
            
            # Gradient clipping to prevent exploding gradients
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            # Accumulate losses
            total_loss += total_batch_loss.item()
            total_data_loss += weighted_data_loss.item()
            total_physics_loss += physics_loss.item()
            n_batches += 1
        
        avg_loss = total_loss / n_batches
        avg_data_loss = total_data_loss / n_batches
        avg_physics_loss = total_physics_loss / n_batches
        
        return avg_loss, avg_data_loss, avg_physics_loss
    
    def test_epoch(self, data_loader):
        """Test the model for one epoch"""
        self.model.eval()
        total_loss = 0.0
        n_batches = 0
        
        with torch.no_grad():
            for data, target, weight in data_loader:
                data, target, weight = data.to(self.device), target.to(self.device), weight.to(self.device)
                
                output = self.model(data)
                loss = self.mse_loss(output, target)
                weighted_loss = torch.mean(loss * weight.squeeze())
                
                total_loss += weighted_loss.item()
                n_batches += 1
        
        return total_loss / n_batches
    
    def fit(
        self,
        dataset: Union[DatasetH, TSDatasetH],
        evals_result=dict(),
        save_path=None,
        reweighter=None,
    ):
        # Prepare datasets
        df_train, df_valid = dataset.prepare(
            ["train", "valid"], col_set=["feature", "label"], data_key=DataHandlerLP.DK_L
        )
        
        x_train, y_train = df_train["feature"], df_train["label"]
        x_valid, y_valid = df_valid["feature"], df_valid["label"]
        
        # Handle weights
        try:
            wdf_train, wdf_valid = dataset.prepare(
                ["train", "valid"], col_set=["weight"], data_key=DataHandlerLP.DK_L
            )
            w_train, w_valid = wdf_train["weight"], wdf_valid["weight"]
        except KeyError:
            w_train = pd.DataFrame(np.ones_like(y_train.values), index=y_train.index)
            w_valid = pd.DataFrame(np.ones_like(y_valid.values), index=y_valid.index)
        
        # Convert to tensors
        x_train_tensor = torch.tensor(x_train.values, dtype=torch.float32)
        y_train_tensor = torch.tensor(y_train.values, dtype=torch.float32)
        w_train_tensor = torch.tensor(w_train.values, dtype=torch.float32)
        
        x_valid_tensor = torch.tensor(x_valid.values, dtype=torch.float32)
        y_valid_tensor = torch.tensor(y_valid.values, dtype=torch.float32)
        w_valid_tensor = torch.tensor(w_valid.values, dtype=torch.float32)
        
        # Create data loaders
        train_dataset = TensorDataset(x_train_tensor, y_train_tensor, w_train_tensor)
        valid_dataset = TensorDataset(x_valid_tensor, y_valid_tensor, w_valid_tensor)
        
        train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)
        valid_loader = DataLoader(valid_dataset, batch_size=self.batch_size, shuffle=False)
        
        # Initialize tracking variables
        best_loss = float('inf')
        best_model_state = None
        patience_counter = 0
        
        # Initialize evals_result
        evals_result.setdefault("train", [])
        evals_result.setdefault("valid", [])
        
        self.logger.info("Starting PINN training...")
        
        # Training loop
        for epoch in range(self.n_epochs):
            # Train epoch
            train_loss, train_data_loss, train_physics_loss = self.train_epoch(train_loader)
            
            # Validation epoch
            valid_loss = self.test_epoch(valid_loader)
            
            # Update learning rate
            self.scheduler.step(valid_loss)
            
            # Track losses
            self.train_losses.append(train_loss)
            self.valid_losses.append(valid_loss)
            self.physics_losses.append(train_physics_loss)
            
            # Log progress
            if epoch % 10 == 0 or epoch == self.n_epochs - 1:
                emission_coeff = self.model.get_emission_coefficient().item()
                self.logger.info(
                    f"Epoch {epoch:3d}: "
                    f"train_loss={train_loss:.6f}, "
                    f"valid_loss={valid_loss:.6f}, "
                    f"data_loss={train_data_loss:.6f}, "
                    f"physics_loss={train_physics_loss:.6f}, "
                    f"emission_coeff={emission_coeff:.4f}"
                )
            
            # Early stopping
            if valid_loss < best_loss:
                best_loss = valid_loss
                best_model_state = copy.deepcopy(self.model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= self.early_stop:
                self.logger.info(f"Early stopping at epoch {epoch}")
                break
            
            # Store evaluation results
            evals_result["train"].append(train_loss)
            evals_result["valid"].append(valid_loss)
        
        # Restore best model
        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)
        
        # Save model if path provided
        if save_path is not None:
            self.save(save_path)
        
        final_emission_coeff = self.model.get_emission_coefficient().item()
        self.logger.info(f"Training completed. Final emission coefficient: {final_emission_coeff:.4f}")
    
    def predict(self, dataset: Union[DatasetH, TSDatasetH], segment: str = "test"):
        """Make predictions using the trained model"""
        if segment:
            df_test = dataset.prepare(segment, col_set="feature", data_key=DataHandlerLP.DK_I)
            x_test = df_test["feature"]
        else:
            x_test = dataset
        
        self.model.eval()
        
        # Convert to tensor
        x_test_tensor = torch.tensor(x_test.values, dtype=torch.float32).to(self.device)
        
        # Make predictions
        with torch.no_grad():
            predictions = self.model(x_test_tensor).cpu().numpy()
        
        # Return as pandas Series with original index
        return pd.Series(predictions.flatten(), index=x_test.index)
    
    def save(self, filepath):
        """Save the model"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': {
                'input_dim': self.input_dim,
                'hidden_size': self.hidden_size,
                'num_layers': self.num_layers,
                'dropout': self.dropout,
                'emission_coeff_init': self.emission_coeff_init,
                'stefan_boltzmann': self.stefan_boltzmann,
                'reference_temp': self.reference_temp,
            }
        }, filepath)
    
    def load(self, filepath):
        """Load the model"""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])