#!/usr/bin/env python3
"""
hello_gemini_vertex.py

Prereqs:
  pip install google-genai
  (and Vertex AI credentials via ADC, e.g. running on GCP / workload identity / gcloud ADC)

Uses:
  GOOGLE_CLOUD_PROJECT
  GOOGLE_CLOUD_LOCATION
  GOOGLE_GENAI_USE_VERTEXAI=True
"""

import os
import sys

def main():
    # --- Set/override env vars exactly as requested ---
    os.environ["GOOGLE_CLOUD_PROJECT"] = "symmetric-hash-483302-v6"
    os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"  # Vertex AI mode

    # Optional: allow prompt override from CLI
    prompt = "Hello Gemini! Please reply with a short greeting and today's date."
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])

    try:
        from google import genai
        from google.genai import types as genai_types
    except Exception as e:
        raise SystemExit(
            "Missing dependency. Install with:\n  pip install google-genai\n\n"
            f"Import error: {e}"
        )

    client = genai.Client()

    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=256,
        ),
    )

    print(resp.text or "")

if __name__ == "__main__":
    main()
