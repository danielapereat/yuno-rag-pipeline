"""
Metadata extraction utilities for Jira and Confluence documents.
"""

import re
from typing import Dict, Optional
from openai import OpenAI
from config import OPENAI_API_KEY, GENERATION_MODEL, TEAM_PATTERNS


def extract_metadata_from_filename(filename: str) -> Dict[str, Optional[str]]:
    """
    Extract basic metadata from filename.

    Args:
        filename: Name of the file (e.g., 'AP-541.pdf', '3702794_3702794.pdf')

    Returns:
        Dictionary with document_type, source_id, and source_file
    """
    metadata = {
        "source_file": filename,
        "document_type": None,
        "source_id": None,
        "team": None
    }

    # Jira ticket pattern: PREFIX-NUMBER (e.g., AP-541, CORECM-13628, TST12-1599)
    # Prefix can contain letters AND numbers (e.g., TST12)
    jira_match = re.match(r'^([A-Z0-9]+)-(\d+)', filename)
    if jira_match:
        prefix = jira_match.group(1)
        ticket_number = jira_match.group(2)
        metadata["document_type"] = "jira"
        metadata["source_id"] = f"{prefix}-{ticket_number}"
        metadata["team"] = classify_team(prefix)
        return metadata

    # Confluence pattern: PAGE_ID_PAGE_ID (e.g., 3702794_3702794.pdf)
    confluence_match = re.match(r'^(\d+)_\d+', filename)
    if confluence_match:
        page_id = confluence_match.group(1)
        metadata["document_type"] = "confluence"
        metadata["source_id"] = page_id
        return metadata

    return metadata


def classify_team(prefix: str) -> Optional[str]:
    """
    Classify team based on Jira ticket prefix.

    Args:
        prefix: Jira ticket prefix (e.g., 'AP', 'CORECM', 'TST')

    Returns:
        Team name or None if not found
    """
    for pattern, team in TEAM_PATTERNS.items():
        if prefix.startswith(pattern):
            return team
    return None


def extract_provider_name(content: str, filename: str) -> Optional[str]:
    """
    Extract provider name from document content using OpenAI.

    Args:
        content: Full text content of the document
        filename: Name of the file for context

    Returns:
        Provider name or None if not found
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Truncate content if too long (first 3000 chars should be enough)
    truncated_content = content[:3000] if len(content) > 3000 else content

    prompt = f"""Analyze this document and extract the payment provider name if present.

Document filename: {filename}
Document content (beginning):
{truncated_content}

Common payment providers include: SafetyPay, Stripe, Adyen, MercadoPago, PayPal, Nequi, PIX, SPEI, PSE, etc.

Return ONLY the provider name if found, or "NONE" if no provider is mentioned.
Examples of good responses: "SafetyPay", "MercadoPago", "NONE"

Provider name:"""

    try:
        # Use gpt-4o-mini for faster and cheaper provider extraction
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )

        provider = response.choices[0].message.content.strip()

        # Return None if no provider found
        if provider.upper() == "NONE" or not provider:
            return None

        return provider

    except Exception as e:
        print(f"Error extracting provider name: {e}")
        return None


def extract_jira_metadata(content: str) -> Dict[str, Optional[str]]:
    """
    Extract Jira-specific metadata from content.

    Args:
        content: Full text content of Jira ticket

    Returns:
        Dictionary with Jira-specific fields
    """
    metadata = {
        "status": None,
        "priority": None,
        "assignee": None,
        "reporter": None,
        "created_date": None,
        "updated_date": None
    }

    # Extract Status
    status_match = re.search(r'Status:\s*([^\n]+)', content)
    if status_match:
        metadata["status"] = status_match.group(1).strip()

    # Extract Priority
    priority_match = re.search(r'Priority:\s*([^\n]+)', content)
    if priority_match:
        metadata["priority"] = priority_match.group(1).strip()

    # Extract Assignee
    assignee_match = re.search(r'Assignee:\s*([^\n]+)', content)
    if assignee_match:
        metadata["assignee"] = assignee_match.group(1).strip()

    # Extract Reporter
    reporter_match = re.search(r'Reporter:\s*([^\n]+)', content)
    if reporter_match:
        metadata["reporter"] = reporter_match.group(1).strip()

    # Extract Created Date
    created_match = re.search(r'Created:\s*([^\n]+)', content)
    if created_match:
        metadata["created_date"] = created_match.group(1).strip()

    # Extract Updated Date
    updated_match = re.search(r'Updated:\s*([^\n]+)', content)
    if updated_match:
        metadata["updated_date"] = updated_match.group(1).strip()

    return metadata


def extract_confluence_metadata(content: str) -> Dict[str, Optional[str]]:
    """
    Extract Confluence-specific metadata from content.

    Args:
        content: Full text content of Confluence page

    Returns:
        Dictionary with Confluence-specific fields
    """
    metadata = {
        "space": None,
        "version": None,
        "created_by": None,
        "created_date": None
    }

    # Extract Space
    space_match = re.search(r'Space:\s*([^\n]+)', content)
    if space_match:
        metadata["space"] = space_match.group(1).strip()

    # Extract Version
    version_match = re.search(r'Version:\s*([^\n]+)', content)
    if version_match:
        metadata["version"] = version_match.group(1).strip()

    # Extract Created By
    created_by_match = re.search(r'Created By:\s*([^\n]+)', content)
    if created_by_match:
        metadata["created_by"] = created_by_match.group(1).strip()

    # Extract Created Date
    created_date_match = re.search(r'Created Date:\s*([^\n]+)', content)
    if created_date_match:
        metadata["created_date"] = created_date_match.group(1).strip()

    return metadata
