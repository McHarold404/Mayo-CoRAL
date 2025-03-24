import os
import concurrent.futures
import threading
import sys
from openai import OpenAI

def ask_chatgpt(temperature=0.1, model_name="gpt-4o", api_key=None):
    """
    Calls the OpenAI API (via the OpenAI library) with a fixed prompt to test the candidate API key.
    """
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {'role': "system", "content": "Yo"},
            {'role': "user", "content": "Whats up?"}
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content

def generate_permutations(s: str) -> list:
    """
    Given a string s, generate all possible permutations where every occurrence
    of an ambiguous character ('l' or 'I', and 'O' or '0') can be replaced with either possibility.
    
    For example, if a character is 'l' or 'I', it can be replaced with either 'l' or 'I'.
    Similarly, if a character is 'O' or '0', it can be replaced with either 'O' or '0'.
    
    Returns:
        list: All possible permutations of the input string based on the ambiguous characters.
    """
    ambiguous_mapping = {
        'l': ('l', 'I'),
        'I': ('l', 'I'),
        'O': ('O', '0'),
        '0': ('O', '0')
    }
    
    # Identify all ambiguous indices along with their corresponding replacement tuple.
    ambiguous_indices = []
    for i, char in enumerate(s):
        if char in ambiguous_mapping:
            ambiguous_indices.append((i, ambiguous_mapping[char]))
    
    n = len(ambiguous_indices)
    if n == 0:
        return [s]
    
    results = []
    # There are 2^n possible combinations.
    for mask in range(2 ** n):
        chars = list(s)
        for j, (idx, possibilities) in enumerate(ambiguous_indices):
            # If the j-th bit is set, choose the first possibility; otherwise, the second.
            if mask & (1 << j):
                chars[idx] = possibilities[0]
            else:
                chars[idx] = possibilities[1]
        results.append("".join(chars))
    return results


# Global event to signal that a correct key has been found.
found_event = threading.Event()

def try_api_key(api_key):
    """
    Try using a candidate API key with ask_chatgpt. If a valid response is returned,
    set the global event and return the key and the response.
    """
    if found_event.is_set():
        return None
    try:
        result = ask_chatgpt(temperature=0.1, model_name="gpt-4o", api_key=api_key)
        # Check if result is a valid non-empty string.
        if isinstance(result, str) and result.strip() != "":
            found_event.set()
            return (api_key, result)
    except Exception as e:
        return None
    return None

def main():
    # Candidate API key string with ambiguous characters.
    test_string = "sk-svcacct-HG5bV7hSjiylByndgwcBcRrvsdgxj2dyN8sWUzlC5R7WPIMIuDNKFn3sa778y8oITSMrIST8BpT3BIbkFJJ-lluhPsmgOWyy5-S7ofR_egabhYNdeiMzMkTFa5ZpoWYe-yUOkEcnMOsp9pwDKehJR5J5belA"
    candidate_keys = generate_permutations(test_string)
    print(f"Total keys to try: {len(candidate_keys)}")
    
    # Use a ThreadPoolExecutor to test keys concurrently.
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        future_to_key = {executor.submit(try_api_key, key): key for key in candidate_keys}
        for future in concurrent.futures.as_completed(future_to_key):
            result = future.result()
            if result is not None:
                correct_key, response_text = result
                print("Correct API key found:", correct_key)
                print("Response:", response_text)
                # Cancel any remaining futures.
                for fut in future_to_key:
                    fut.cancel()
                sys.exit(0)
    
    print("No valid API key found.")

if __name__ == "__main__":
    main()
