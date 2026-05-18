import multiprocessing

# Worker timeout — must exceed the longest possible AI call.
# LLM calls can take 30-60 s; set to 120 s to give a safe buffer.
timeout = 120

# Keep-alive for SSE connections.
keepalive = 5

# 1 worker keeps the in-process LLM from competing with itself for RAM.
# Scale up only if you move the model to a separate inference service.
workers = 1

# gthread workers let multiple SSE streams and regular requests share one
# process without blocking each other during long AI calls.
worker_class = "gthread"
threads = 4

# Bind from environment so Render / local dev both work.
import os
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
