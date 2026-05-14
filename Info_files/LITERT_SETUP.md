# Google AI Edge / LiteRT Setup Guide

## Overview

SmartFarming now supports **Google AI Edge / LiteRT** for running Gemma 2 locally without Ollama.

**Key Benefits:**
- ✅ No Ollama installation needed
- ✅ Fully local inference on CPU/GPU
- ✅ Quantized model (~3.5GB)
- ✅ Auto-downloads model on first run
- ✅ Falls back to Google API if available
- ✅ Fallback to placeholder if no backend available

---

## Quick Start

### Step 1: Install Dependencies

```bash
# Required for LiteRT (fully local)
pip install mediapipe numpy

# Optional: for cloud fallback
pip install google-generativeai
```

### Step 2: Start SmartFarming

```bash
flask run
```

**That's it!** The app will:
1. Try to use LiteRT local model (auto-downloads on first run)
2. Fall back to Google API if `GEMMA_API_KEY` is set
3. Use placeholder responses if neither is available

### Step 3: First Run

The first time you use the chatbot:
- Model downloads (~3.5GB to `~/.gemma_models/`)
- Takes 10-30 minutes depending on internet
- Subsequent runs are instant

---

## Configuration Options

### Option A: Local LiteRT (Default - No Internet After Setup)
```bash
# Just install and run
pip install mediapipe numpy
flask run
```

### Option B: Google Cloud API Fallback
```bash
# Set API key for fallback
set GEMMA_API_KEY=your-api-key-here
flask run
```

Get API key: https://ai.google.dev/

### Option C: Custom Model Path
```bash
# Use custom model location
set GEMMA_MODEL_PATH=C:\path\to\gemma-2-2b-it-gpu-int8.tflite
flask run
```

### Option D: Force API Only (No Model Download)
```bash
# Skip LiteRT, use API only
set USE_LITERT_MODEL=false
set GEMMA_API_KEY=your-api-key
flask run
```

---

## Model Information

### Gemma 2 2B (Quantized - Int8)

| Property | Value |
|----------|-------|
| Size | 3.5 GB |
| RAM Required | 4 GB minimum |
| Speed | Fast (~0.5-2 sec per response) |
| Quality | Good for farming advice |
| Quantization | INT8 (reduced precision) |
| Download | Auto-downloads on first use |

### Available Models

Other Gemma models (download manually if desired):
- `gemma-2-9b-it-gpu-int8.tflite` - 9B model, better quality, needs 8GB+ RAM
- `gemma-2-2b-it-cpu.tflite` - CPU-optimized version

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'mediapipe'"
**Solution:**
```bash
pip install mediapipe numpy
```

### "Model download failed"
**Solution:**
1. Check internet connection
2. Manual download from: https://github.com/google-generativeai/llm-inference-benchmarks/releases
3. Set `GEMMA_MODEL_PATH` to manual path

### "LiteRT model not available"
**Solution:**
```bash
# Ensure mediapipe is installed
pip install --upgrade mediapipe

# Try downloading model again
python -c "from app.services.ai_model_service.Gemma.gemma_provider import GemmaProvider; GemmaProvider()"
```

### Slow responses
**Causes & Solutions:**
- CPU inference - get GPU support: https://tensorflow.org/lite/guide/gpu
- Model too large - use 2B instead of 9B
- First request always slower (model initialization)

### Model path permission denied
**Solution:**
```bash
# Use custom location with write permission
set GEMMA_MODEL_PATH=C:\Users\YourUser\gemma_models\model.tflite
```

---

## Hardware Requirements

| Component | Requirement |
|-----------|-------------|
| RAM | 4 GB minimum, 8 GB recommended |
| Disk | 10 GB free (for model + cache) |
| CPU | Modern multi-core (ARM/x86) |
| GPU | Optional - for faster inference |

### GPU Support

For GPU acceleration, install TensorFlow GPU:
```bash
pip install tensorflow-gpu  # For NVIDIA CUDA
# or
pip install tensorflow-metal  # For Apple Metal
```

---

## How It Works

```
User Query
    ↓
Flask App
    ↓
GemmaProvider (smart fallback)
    ↓
    ├─→ LiteRT Available? → Load local model → Inference ✓
    │
    ├─→ Google API Key set? → Use google-generativeai ✓
    │
    └─→ No AI backend? → Placeholder responses
```

---

## Performance Comparison

| Backend | Latency | Quality | No Internet | Cost |
|---------|---------|---------|-------------|------|
| **LiteRT** | 0.5-2s | Good | ✅ Yes | Free |
| Google API | 1-3s | Excellent | ❌ No | $$ |
| Ollama | 0.3-1s | Good | ✅ Yes | Free |

---

## Fallback Behavior

The provider automatically falls back if:

1. **LiteRT fails to initialize** → Tries Google API
2. **Google API not available** → Uses placeholder responses
3. **Inference errors** → Returns helpful fallback message

Example response chain:
```
LiteRT model error 
  → Try Google API
  → No API key available
  → Use placeholder response
  → User still gets helpful advice
```

---

## Development Tips

### Test Model Locally
```python
from app.services.ai_model_service.Gemma.gemma_provider import GemmaProvider

provider = GemmaProvider()
print(f"Provider: {provider.name}")
response = provider.complete("What is soil pH?")
print(response)
```

### Monitor First Run
```bash
# Watch model download progress
flask run --debug
# Check ~/.gemma_models/ directory during download
```

### Use Placeholder for Testing
```bash
# Test app without downloading model
set USE_PLACEHOLDER_AI=true
flask run
```

---

## Cleanup

### Remove Cached Model
```bash
# Windows
rmdir /s %USERPROFILE%\.gemma_models

# Unix/Mac
rm -rf ~/.gemma_models
```

Model will re-download on next run if needed.

---

## Next Steps

1. **Install:** `pip install mediapipe numpy`
2. **Run:** `flask run`
3. **Use:** Click "Chat" → Start chatting with local Gemma!

---

## Additional Resources

- MediaPipe Text Generator: https://developers.google.com/mediapipe/solutions/text/text_generator
- Gemma Models: https://www.kaggle.com/models/google/gemma
- TFLite Optimization: https://www.tensorflow.org/lite/guide/optimize

