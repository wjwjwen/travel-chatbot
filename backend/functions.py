import base64
import io

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from modules.vehicle_insurance_policy import VehicleInsurancePolicy
from openai import AzureOpenAI
from pdf2image import convert_from_bytes


def extract_data_with_gpt4o_vision(document_path: str):
    """
    Extract structured data from a document using Azure OpenAI GPT-4o with vision capabilities.

    :param document_path: Path to the document to be processed.
    :return: Extracted data.
    """
    credential = DefaultAzureCredential()
    openai_token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    openai_client = AzureOpenAI(
        azure_endpoint="YOUR_OPENAI_ENDPOINT",
        azure_ad_token_provider=openai_token_provider,
        api_version="2024-08-01-preview",
    )

    user_content = [
        {
            "type": "text",
            "text": "Extract the data from this insurance policy. If a value is not present, provide null. Some values must be inferred based on the rules defined in the policy. Dates should be in the format YYYY-MM-DD.",
        }
    ]

    document_bytes = open(document_path, "rb").read()
    page_images = convert_from_bytes(document_bytes)
    for page_image in page_images:
        byteIO = io.BytesIO()
        page_image.save(byteIO, format="PNG")
        base64_data = base64.b64encode(byteIO.getvalue()).decode("utf-8")
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_data}"},
            }
        )

    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that extracts data from documents.",
            },
            {"role": "user", "content": user_content},
        ],
        response_format=VehicleInsurancePolicy,
        max_tokens=4096,
        temperature=0.1,
        top_p=0.1,
        logprobs=True,
    )

    return completion.choices[0].message.parsed



from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, ContentFormat


def extract_data_comprehensive(document_path: str):
    """
    Extract structured data from a document using a comprehensive approach with Azure AI Document Intelligence and Azure OpenAI GPT-4o with vision.

    :param document_path: Path to the document to be processed.
    :return: Extracted data.
    """
    credential = DefaultAzureCredential()
    openai_token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    openai_client = AzureOpenAI(
        azure_endpoint="YOUR_OPENAI_ENDPOINT",
        azure_ad_token_provider=openai_token_provider,
        api_version="2024-08-01-preview",
    )
    document_intelligence_client = DocumentIntelligenceClient(
        endpoint="YOUR_DOCUMENT_INTELLIGENCE_ENDPOINT", credential=credential
    )

    with open(document_path, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-layout",
            analyze_request=f,
            output_content_format=ContentFormat.MARKDOWN,
            content_type="application/pdf",
        )
    result: AnalyzeResult = poller.result()
    markdown = result.content

    document_bytes = open(document_path, "rb").read()
    page_images = convert_from_bytes(document_bytes)
    user_content = [
        {
            "type": "text",
            "text": "Extract the data from this insurance policy. If a value is not present, provide null. Some values must be inferred based on the rules defined in the policy. Dates should be in the format YYYY-MM-DD.",
        }
    ]
    user_content.append({"type": "text", "text": markdown})

    for page_image in page_images:
        byteIO = io.BytesIO()
        page_image.save(byteIO, format="PNG")
        base64_data = base64.b64encode(byteIO.getvalue()).decode("utf-8")
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_data}"},
            }
        )

    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that extracts data from documents.",
            },
            {"role": "user", "content": user_content},
        ],
        response_format=VehicleInsurancePolicy,
        max_tokens=4096,
        temperature=0.1,
        top_p=0.1,
        logprobs=True,
    )

    return completion.choices[0].message.parsed


from marker.models import load_all_models
from modules.invoice import Invoice
from modules.marker_surya_extensions import convert_single_pdf


def extract_data_with_marker_surya(document_path: str):
    """
    Extract structured data from a document using Marker/Surya and Azure OpenAI GPT-4o.

    :param document_path: Path to the document to be processed.
    :return: Extracted data.
    """
    credential = DefaultAzureCredential()
    openai_token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    openai_client = AzureOpenAI(
        azure_endpoint="YOUR_OPENAI_ENDPOINT",
        azure_ad_token_provider=openai_token_provider,
        api_version="2024-08-01-preview",
    )

    marker_models = load_all_models()

    markdown, images, pages, out_meta = convert_single_pdf(
        document_path,
        marker_models,
        langs=["English"],
        batch_multiplier=2,
        start_page=None,
        ocr_all_pages=True,
    )

    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that extracts data from documents.",
            },
            {
                "role": "user",
                "content": "Extract the data from this invoice. If a value is not present, provide null. Dates should be in the format YYYY-MM-DD.",
            },
            {"role": "user", "content": markdown},
        ],
        response_format=Invoice,
        max_tokens=4096,
        temperature=0.1,
        top_p=0.1,
    )

    return completion.choices[0].message.parsed




def extract_data_with_openai(document_path: str):
    """
    Extract structured data from a document using Azure AI Document Intelligence and Azure OpenAI GPT-4o.

    :param document_path: Path to the document to be processed.
    :return: Extracted data.
    """
    credential = DefaultAzureCredential()
    openai_token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    openai_client = AzureOpenAI(
        azure_endpoint="YOUR_OPENAI_ENDPOINT",
        azure_ad_token_provider=openai_token_provider,
        api_version="2024-08-01-preview",
    )
    document_intelligence_client = DocumentIntelligenceClient(
        endpoint="YOUR_DOCUMENT_INTELLIGENCE_ENDPOINT", credential=credential
    )

    with open(document_path, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-layout",
            analyze_request=f,
            output_content_format=ContentFormat.MARKDOWN,
            content_type="application/pdf",
        )
    result: AnalyzeResult = poller.result()
    markdown = result.content

    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that extracts data from documents.",
            },
            {
                "role": "user",
                "content": "Extract the data from this invoice. If a value is not present, provide null. Dates should be in the format YYYY-MM-DD.",
            },
            {"role": "user", "content": markdown},
        ],
        response_format=Invoice,
        max_tokens=4096,
        temperature=0.1,
        top_p=0.1,
    )

    return completion.choices[0].message.parsed


import json

from modules.classification import Classification, Classifications


def classify_with_gpt4o_vision(document_path: str, classifications: list):
    """
    Classify a document using Azure OpenAI GPT-4o with vision capabilities.

    :param document_path: Path to the document to be classified.
    :param classifications: List of classifications with descriptions and keywords.
    :return: Classification results.
    """
    credential = DefaultAzureCredential()
    openai_token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    openai_client = AzureOpenAI(
        azure_endpoint="YOUR_OPENAI_ENDPOINT",
        azure_ad_token_provider=openai_token_provider,
        api_version="2024-08-01-preview",
    )

    user_content = [
        {"type": "text", "text": f"Classifications:\n\n{json.dumps(classifications)}"}
    ]

    document_bytes = open(document_path, "rb").read()
    pages = convert_from_bytes(document_bytes)
    for page in pages:
        byteIO = io.BytesIO()
        page.save(byteIO, format="PNG")
        base64_data = base64.b64encode(byteIO.getvalue()).decode("utf-8")
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_data}"},
            }
        )

    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "Using the classifications provided, classify each page of the following document into one of the classifications.",
            },
            {"role": "user", "content": user_content},
        ],
        response_format=Classifications,
        max_tokens=4096,
        temperature=0.1,
        top_p=0.1,
        logprobs=True,
    )

    return completion.choices[0].message.parsed


import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def classify_with_embeddings(
    document_path: str, classifications: list, threshold: float = 0.4
):
    """
    Classify a document using Azure AI Document Intelligence and embeddings.

    :param document_path: Path to the document to be classified.
    :param classifications: List of classifications with descriptions and keywords.
    :param threshold: Similarity threshold for classification.
    :return: Classification results.
    """
    credential = DefaultAzureCredential()
    openai_token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    openai_client = AzureOpenAI(
        azure_endpoint="YOUR_OPENAI_ENDPOINT",
        azure_ad_token_provider=openai_token_provider,
        api_version="2024-08-01-preview",
    )
    document_intelligence_client = DocumentIntelligenceClient(
        endpoint="YOUR_DOCUMENT_INTELLIGENCE_ENDPOINT", credential=credential
    )

    with open(document_path, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-layout",
            analyze_request=f,
            output_content_format=ContentFormat.MARKDOWN,
            content_type="application/pdf",
        )
    result: AnalyzeResult = poller.result()

    pages_content = [
        result.content[
            page.spans[0]["offset"] : page.spans[0]["offset"] + page.spans[0]["length"]
        ]
        for page in result.pages
    ]
    page_embeddings = [get_embedding(text, openai_client) for text in pages_content]

    classification_embeddings = [cls["embedding"] for cls in classifications]
    classification_matrix = np.array(classification_embeddings)
    document_classifications = Classifications(classifications=[])

    for idx, page_emb in enumerate(page_embeddings):
        page_vector = np.array(page_emb).reshape(1, -1)
        similarities = cosine_similarity(page_vector, classification_matrix)[0]
        best_match_idx = np.argmax(similarities)
        best_similarity = similarities[best_match_idx]
        classification = (
            classifications[best_match_idx]["classification"]
            if best_similarity >= threshold
            else "Unclassified"
        )

        document_classifications.classifications.append(
            Classification(
                page_number=idx,
                classification=classification,
                similarity=best_similarity,
                all_similarities=[
                    {"classification": cls["classification"], "similarity": str(sim)}
                    for cls, sim in zip(classifications, similarities)
                ],
            )
        )

    return document_classifications


def get_embedding(text: str, openai_client):
    response = openai_client.embeddings.create(
        input=text, model="text-embedding-3-large"
    )
    embedding = response.data[0].embedding
    return embedding
