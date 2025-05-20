# Pre-trained Models

RetroTrade includes several pre-trained models for demonstration and further development. These models can be used as-is or retrained with your own data.

## Included Models

### PPO (Proximal Policy Optimization)
- Location: `Agents/PPO_Trader/checkpoints/best_ppo_model.pt`
- Usage: Used for RL-based trading strategies. See `Agents/PPO_Trader/README.md` for training and evaluation.
- Input: Market state features
- Output: Trading actions (buy/sell/hold)

### Risk Management Models
- Location: `risk_management/saved_models/`
- Usage: Used for portfolio risk assessment, position sizing, and stop-loss logic.
- Input: Portfolio and market statistics
- Output: Risk-adjusted trade signals

### Sentiment Analysis Models
- Location: `sentiment_analysis/trained_models/`
- Usage: Used to extract sentiment signals from news, social media, or other text sources.
- Input: Text data (news headlines, tweets, etc.)
- Output: Sentiment scores or signals

## Model Loading & Integration
- Models are loaded via the `retrotrade/models/` and `retrotrade/models/rl_agent_handler.py` modules.
- You can swap, retrain, or extend models by updating the relevant folders and configuration files.

## Model Training Workflow Diagram

```
+-------------------+
|   Raw Data        |
+--------+----------+
         |
         v
+-------------------+
| Data Processing   |
+--------+----------+
         |
         v
+-------------------+
| Model Training    |
+--------+----------+
         |
         v
+-------------------+
| Pre-trained Model |
+-------------------+
```

## Customization
- To retrain models, use the provided training scripts in each module folder.
- For advanced users, modify model architectures or training parameters as needed.

## Troubleshooting
- Ensure model paths are correct in configuration files.
- Check dependencies in `requirements.txt` and module-specific requirements.
- For GPU acceleration, ensure CUDA is properly installed.
