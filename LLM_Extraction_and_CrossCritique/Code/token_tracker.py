# token_tracker.py
total_output_tokens = 0
total_input_tokens = 0
total_token_cost = 0  # renamed for clarity
input_token_cost_per_million = 0.1
output_token_cost_per_million = 0.4

def add_tokens(input_tokens: int, output_tokens: int):
    global total_input_tokens, total_output_tokens
    total_input_tokens += input_tokens
    total_output_tokens += output_tokens

def get_total_cost() -> float:
    global total_token_cost
    total_token_cost = (total_input_tokens * input_token_cost_per_million + 
                        total_output_tokens * output_token_cost_per_million) / 1_000_000
    return total_token_cost
