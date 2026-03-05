# DO NOT MODIFY THIS FILE
# Only inject env vars at runtime

"""
Eventually, we need all these options in the config file.

    'options': [
        {
            'temperature': temperature,
            'num_ctx': 65536,
            'repeat_penalty': 1.1,
            'top_k': 40,
            'top_p': 0.9,
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
    'ollama_api_url': 'http://localhost:11434/api/generate',
    'ollama_model': 'llama3',
    'ollama_temperature': 0.7,
    'ollama_prefix_prompt': 'You are a helpful email assistant.',
    'allowed_attachment_extensions': ['.txt', '.md', '.eml'],
    'smtp_host': 'smtp.example.com',
    'smtp_port': 25,
    'smtp_use_tls': False,
    'smtp_use_ssl': False,
}
