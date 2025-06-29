import fitz  # PyMuPDF
import pdfplumber
import os
import json
import base64
import spacy
import pandas as pd
import re
from PIL import Image
from io import BytesIO
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from speculativeRetrieval import speculative_rag_pipeline
from table_population import generate_dynamic_query
from model_inference.gemini import *
from model_inference.gpt import *
# from utils import extract_caption
from k_chunking import *
import json
from document_chunker import process_document
from definitions import load_definitions
from table_population import populate_table_row
from token_tracker import get_total_cost
import argparse
from dotenv import load_dotenv
import os

load_dotenv()

# model_keys = {
#     0: os.getenv("OPENAI_API_KEY"),
#     1: os.getenv("GEMINI_KEY"),
# }


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config


def get_context(config):
    config["document_name"] = args.document_name
    config["model"]["key"] = args.key

    document_name = config["document_name"]
    context = generate_context(
        pdf_path=os.path.join("training_studies", f"{document_name}.pdf"),
        prompt_path=config["prompts"]["context_prompt"],
        config=config
    )

    print("CONTEXT GENERATED FOR DOCUMENT:")
    print("--------------------------")
    print(context)
    print("--------------------------")


    return context

chunks = [
    ### chunk 1 contains the gold answer.
    {
        "type": "text",
        "content": "[13]. Only biochemical progression-free\nsurvival (bPFS) and radiographic progression-free survival\n(rPFS) were improved in the D plus ADT arm. The results of the CHAARTED trial that had the same\ndesign as ours were presented in 2014 [14] and published in\n2015 [15]. Median OS was significantly improved in the ADT\nplus D arm (57.6 vs 44.0 mo; HR: 0.61; p < 0.001). There was\na 17.0-mo difference between arms in patients with high-\nvolume disease (HVD; 49.2 vs 32.2 mo; HR: 0.60; p < 0.001). We retrospectively retrieved data on metastatic volume\nfrom medical files of all patients included in the GETUG-\nAFU15 study, applying the CHAARTED definition of HVD\nand low-volume\ndisease (LVD) and\nupdated survival\nanalyses. We present long-term outcomes in the overall\npopulation and in the HVD and LVD subgroups. 2.\nPatients and methods\nThe GETUG-AFU15 trial is a French multicenter open-label randomized\nstudy [13]. From October 2004 to December 2008, 385 patients were\nenrolled including 193 in the ADT arm and 192 in the ADT plus D arm.",
        "page": 1,
        "length": 2989
    },
    ### chunk 2
    {
        "type": "text",
        "content": "Other patients were considered to have LVD. Following the Prostate Speciﬁc Antigen (PSA) Working Group\ndeﬁnition, biochemical progression was deﬁned as a previous conﬁrmed\nPSA decrease of at least 50% and an increase of at least 50% above the nadir,\nwith a minimum increase of 5 ng/ml. For patients without a previous PSA\ndecrease of 50%, progression was deﬁned as a PSA increase at least 25%\nabove the nadir and at least 5 ng/ml [17]. In patients with measurable\nlesions, radiographic progression was deﬁned using Response Evaluation\nCriteria in Solid Tumors (RECIST) v.1.0 criteria [18]. In patients with bone\nlesions only, radiographic progression was deﬁned as one or more new\nbonelesionsonbonescan. Radiographicprogressionwastheoccurrenceof\nnew bone lesions or RECIST progression, whichever happened ﬁrst. Death\nwas considered as an event. 2.1. Statistics\nThe primary end point was OS. Secondary end points included bPFS and\nrPFS. Survival end points were deﬁned as the time between randomiza-\ntion and death from any cause (OS), radiographic progression or death\n(rPFS), PSA progression or radiographic progression or death (bPFS).",
        "page": 1,
        "length": 1886
    },
    ### chunk 3
    {
        "type": "table",
        "content": "Patients with LVD had no\nsurvival improvement with early D.\nPatient summary: In this study, docetaxel added to castration did not improve survival\nin patients with metastatic hormone-sensitive prostate cancer, partly due to methodo-\nlogical issues. However, early chemotherapy should be discussed with all patients, given\nthe data of three randomized trials including GETUG-AFU15.\n# 2015 European Association of Urology. Published by Elsevier B.V. All rights reserved. E U R O P E A N U R O L O G Y 7 0 ( 2 0 1 6 ) 2 5 6 – 2 6 2\n257",
        "page": 1,
        "length": 239,
        "source": "pdfplumber",
        "table_content": "No table found"
    },
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the extraction pipeline.")
    parser.add_argument("--document_name", type=str, required=True, help="The name of the document to process.")
    parser.add_argument("--key", type=int, required=True, help="The model key to use.")
    parser.add_argument("--config", type=str, default="config.json", help="Path to the config file.")


    args = parser.parse_args()
    config = load_config(args.config)

    document_name = "training_studies/" + args.document_name
    json_path = os.path.join(f"db/{document_name}/hybrid_chunks.json")

    # Replace the placeholders with command-line arguments
    config["document_name"] = args.document_name
    config["model"]["key"] = args.key

    context = get_context(config=config)
    columns_info = [{"Column" : "Total Participants - N", "Definition": "The total number of participants included in the clinical trial."},
                    {"Column" : "Treatment Arm - N", "Definition": "The total number of participants included in the experimental arm of the clinical trial"},
                    {"Column" : "Control Arm - N", "Definition": "The total number of participants included in the control arm of the clinical trial"}
                    ]
    group_label = ""
    query = generate_dynamic_query(group_label, columns_info, config)
    sampled_chunks,responses, best_answer = speculative_rag_pipeline(chunks=chunks,config=config,context=context,pdf_path=os.path.join("training_studies", f"{document_name}.pdf"), retreival_query="What is the median overall survival of patients with high volume metastatic hormone-sensitive prostate cancer treated with chemohormonal therapy?", columns_info= columns_info, top_n=3)
    print(sampled_chunks,responses, best_answer) 

