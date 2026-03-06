"""
LSTM-based time-series forecaster for GridOS.

Uses PyTorch to build, train, and run inference with a stacked LSTM
network for load and solar generation forecasting.  Falls back to a
simple persistence model if PyTorch is not installed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ── Numpy-only helpers ───────────────────────────────────────────────────────


def _create_sequences(
    data: np.ndarray, lookback: int, horizon: int
) -> tuple[np.ndarray, np.ndarray]:
    """Slide a window over ``data`` to create (X, y) pairs.

    Parameters
    ----------
    data:
        1-D array of time-series values.
    lookback:
        Number of past steps used as input features.
    horizon:
        Number of future steps to predict.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        X of shape ``(N, lookback, 1)`` and y of shape ``(N, horizon)``.
    """
    xs, ys = [], []
    for i in range(len(data) - lookback - horizon + 1):
        xs.append(data[i : i + lookback])
        ys.append(data[i + lookback : i + lookback + horizon])
    x_arr = np.array(xs, dtype=np.float32).reshape(-1, lookback, 1)
    y = np.array(ys, dtype=np.float32)
    return x_arr, y


# ── LSTM Forecaster ──────────────────────────────────────────────────────────


class LSTMForecaster:
    """LSTM-based time-series forecaster.

    Parameters
    ----------
    lookback:
        Number of historical time steps used as input.
    horizon:
        Number of future time steps to predict.
    hidden_size:
        Number of LSTM hidden units.
    num_layers:
        Number of stacked LSTM layers.
    learning_rate:
        Optimiser learning rate.
    model_dir:
        Directory for saving / loading trained model weights.
    """

    def __init__(
        self,
        lookback: int = 96,
        horizon: int = 96,
        hidden_size: int = 64,
        num_layers: int = 2,
        learning_rate: float = 1e-3,
        model_dir: str = "./models_cache",
    ) -> None:
        self.lookback = lookback
        self.horizon = horizon
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.learning_rate = learning_rate
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self._model: Any = None
        self._scaler_min: float = 0.0
        self._scaler_max: float = 1.0
        self._torch_available: bool = False

        try:
            import importlib.util

            self._torch_available = importlib.util.find_spec("torch") is not None
        except (ImportError, ModuleNotFoundError):
            logger.warning(
                "PyTorch not installed — LSTMForecaster will use persistence fallback."
            )

    # ── Data Preparation ─────────────────────────────────────────────

    def prepare_data(
        self, values: np.ndarray, train_ratio: float = 0.8
    ) -> dict[str, np.ndarray]:
        """Normalise data and split into train / validation sets.

        Parameters
        ----------
        values:
            1-D numpy array of time-series values.
        train_ratio:
            Fraction of data used for training.

        Returns
        -------
        dict
            Keys: ``X_train``, ``y_train``, ``X_val``, ``y_val``.
        """
        self._scaler_min = float(np.min(values))
        self._scaler_max = float(np.max(values))
        rng = self._scaler_max - self._scaler_min
        if rng == 0:
            rng = 1.0
        normalised = (values - self._scaler_min) / rng

        x_seq, y_seq = _create_sequences(normalised, self.lookback, self.horizon)
        split = int(len(x_seq) * train_ratio)
        return {
            "X_train": x_seq[:split],
            "y_train": y_seq[:split],
            "X_val": x_seq[split:],
            "y_val": y_seq[split:],
        }

    # ── Model Building ───────────────────────────────────────────────

    def build_model(self) -> Any:
        """Build the LSTM model (requires PyTorch)."""
        if not self._torch_available:
            logger.warning("Cannot build LSTM model — PyTorch not installed")
            return None

        import torch
        import torch.nn as nn

        class _LSTMNet(nn.Module):
            def __init__(self, hidden_size: int, num_layers: int, horizon: int):
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=1,
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    batch_first=True,
                    dropout=0.1 if num_layers > 1 else 0.0,
                )
                self.fc = nn.Linear(hidden_size, horizon)

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                out, _ = self.lstm(x)
                prediction: torch.Tensor = self.fc(out[:, -1, :])
                return prediction

        self._model = _LSTMNet(self.hidden_size, self.num_layers, self.horizon)
        logger.info(
            "LSTM model built: hidden=%d, layers=%d", self.hidden_size, self.num_layers
        )
        return self._model

    # ── Training ─────────────────────────────────────────────────────

    def fit(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        x_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        epochs: int = 50,
        batch_size: int = 32,
    ) -> dict[str, list[float]]:
        """Train the LSTM model.

        Returns
        -------
        dict
            Training history with ``train_loss`` and ``val_loss`` per epoch.
        """
        if not self._torch_available or self._model is None:
            logger.warning(
                "Skipping training — PyTorch not available or model not built"
            )
            return {"train_loss": [], "val_loss": []}

        import torch
        from torch.utils.data import DataLoader, TensorDataset

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(device)

        optimizer = torch.optim.Adam(self._model.parameters(), lr=self.learning_rate)
        criterion = torch.nn.MSELoss()

        train_ds = TensorDataset(
            torch.tensor(x_train, dtype=torch.float32),
            torch.tensor(y_train, dtype=torch.float32),
        )
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

        history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}

        for epoch in range(1, epochs + 1):
            self._model.train()
            epoch_loss = 0.0
            for xb, yb in train_loader:
                xb, yb = xb.to(device), yb.to(device)
                optimizer.zero_grad()
                pred = self._model(xb)
                loss = criterion(pred, yb)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * xb.size(0)
            epoch_loss /= len(train_ds)
            history["train_loss"].append(epoch_loss)

            # Validation
            val_loss = 0.0
            if x_val is not None and y_val is not None:
                self._model.eval()
                with torch.no_grad():
                    xv = torch.tensor(x_val, dtype=torch.float32).to(device)
                    yv = torch.tensor(y_val, dtype=torch.float32).to(device)
                    val_pred = self._model(xv)
                    val_loss = criterion(val_pred, yv).item()
            history["val_loss"].append(val_loss)

            if epoch % 10 == 0 or epoch == 1:
                logger.info(
                    "Epoch %d/%d — train_loss=%.6f, val_loss=%.6f",
                    epoch,
                    epochs,
                    epoch_loss,
                    val_loss,
                )

        return history

    # ── Prediction ───────────────────────────────────────────────────

    def predict(self, recent_values: np.ndarray) -> np.ndarray:
        """Generate a forecast from the most recent observations.

        Parameters
        ----------
        recent_values:
            1-D array of length ``lookback`` with the most recent values
            in original scale.

        Returns
        -------
        np.ndarray
            1-D array of length ``horizon`` with forecasted values in
            original scale.
        """
        if not self._torch_available or self._model is None:
            # Persistence fallback — repeat last value
            logger.debug("Using persistence fallback for forecast")
            return np.full(self.horizon, recent_values[-1], dtype=np.float32)

        import torch

        rng = self._scaler_max - self._scaler_min
        if rng == 0:
            rng = 1.0
        normalised = (recent_values - self._scaler_min) / rng
        x = torch.tensor(normalised.reshape(1, self.lookback, 1), dtype=torch.float32)

        self._model.eval()
        with torch.no_grad():
            pred = self._model(x).cpu().numpy().flatten()

        # Inverse scale
        result: np.ndarray = pred * rng + self._scaler_min
        return result

    # ── Persistence ──────────────────────────────────────────────────

    def save(self, filename: str = "lstm_forecaster.pt") -> Path:
        """Save model weights to disk."""
        path = self.model_dir / filename
        if self._torch_available and self._model is not None:
            import torch

            torch.save(
                {
                    "model_state": self._model.state_dict(),
                    "scaler_min": self._scaler_min,
                    "scaler_max": self._scaler_max,
                    "lookback": self.lookback,
                    "horizon": self.horizon,
                    "hidden_size": self.hidden_size,
                    "num_layers": self.num_layers,
                },
                path,
            )
            logger.info("Model saved to %s", path)
        return path

    def load(self, filename: str = "lstm_forecaster.pt") -> None:
        """Load model weights from disk."""
        path = self.model_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        if not self._torch_available:
            raise ImportError("PyTorch is required to load the model")

        import torch

        checkpoint = torch.load(path, map_location="cpu", weights_only=True)  # noqa: B614
        self._scaler_min = checkpoint["scaler_min"]
        self._scaler_max = checkpoint["scaler_max"]
        self.lookback = checkpoint["lookback"]
        self.horizon = checkpoint["horizon"]
        self.hidden_size = checkpoint["hidden_size"]
        self.num_layers = checkpoint["num_layers"]
        self.build_model()
        self._model.load_state_dict(checkpoint["model_state"])
        self._model.eval()
        logger.info("Model loaded from %s", path)
