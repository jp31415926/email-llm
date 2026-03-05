# config.py
# holds the configuration for the specific system it is deployed on

# TODO Add all these options in the config file for Ollama
"""
    'ollama_options': [
        {
            'temperature': temperature,
            'fallback_num_ctx': 65536, # used if we can't query what the real context window is
            'repeat_penalty': 1.1,
            'top_k': 40,
            'top_p': 0.4,
            'min_p': 0.0,
            'repeat_last_n': 64,
            'repeat_penalty': 1.1
        }
    ],
"""


config = {
    'source_folder': './emails/new',
    'processed_folder': './emails/cur',
    'polling_interval_seconds': 30,
    'bot_name': 'Support Bot',
    'bot_email': 'bot@example.com',

    # LLM backend: 'ollama' or 'llamacpp'
    'llm_backend': 'ollama',

    # Ollama settings
    'ollama_api_url': 'http://localhost:11434/api/generate',
    'ollama_model': 'llama3',
    'ollama_temperature': 0.7,
    'ollama_prefix_prompt': 'You are a helpful email assistant.',

    # llama.cpp server settings
    'llamacpp_api_url': 'http://localhost:8080/completion',
    'llamacpp_temperature': 0.7,
    'llamacpp_prefix_prompt': 'You are a helpful email assistant.',
    'llamacpp_n_predict': 1024,

    'allowed_attachment_extensions': ['.txt', '.md', '.eml'],
    'smtp_host': 'smtp.example.com',
    'smtp_port': 25,
    'smtp_use_tls': False,
    'smtp_use_ssl': False,
}
