# TODO: Replace Ollama model with qwen2.5-coder:7b

- [x] Step 1: Edit config/settings.py (change default ollama_model)
- [x] Step 2: Edit agents/ollama_client.py (update fallbacks)
- [x] Step 3: Edit api/routes.py (update status message)
- [x] Step 4: Edit agents/crew.py (update fallback messages)
- [x] Step 5: Pull model `ollama pull qwen2.5-coder:7b`
- [x] Step 6: Test changes (run app, check /ollama-status, test estimation)


