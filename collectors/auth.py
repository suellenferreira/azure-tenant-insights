"""
Authentication module for Azure Tenant Insights.

Supports:
  1. Service Principal  (--client-id + --client-secret + --tenant-id)
  2. DefaultAzureCredential — covers: Azure CLI, Managed Identity,
     Environment Variables (AZURE_CLIENT_ID / SECRET / TENANT_ID),
     Visual Studio Code, and Interactive Browser.

Source: https://learn.microsoft.com/en-us/python/api/azure-identity/
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_credential(
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    cloud: str = "AzurePublicCloud",
):
    """
    Returns an authenticated Azure credential object.

    Priority:
      1. Service Principal (if client_id + client_secret are provided)
      2. DefaultAzureCredential (CLI / Managed Identity / Environment / etc.)
    """
    from azure.identity import ClientSecretCredential, DefaultAzureCredential

    # A partial Service Principal configuration must never silently fall back to
    # a cached CLI/VS Code/managed-identity credential for a different account.
    if client_id or client_secret:
        if not (tenant_id and client_id and client_secret):
            raise ValueError(
                "Service Principal authentication requires --tenant-id, --client-id, "
                "and --client-secret together. Remove the partial options to use "
                "DefaultAzureCredential instead."
            )
        logger.debug("Using Service Principal (ClientSecretCredential) authentication")
        return ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    logger.debug(
        "Using DefaultAzureCredential (CLI / Managed Identity / Environment Variables)"
    )

    # DefaultAzureCredential will automatically try available methods in order.
    # AzureDeveloperCliCredential (azd) is excluded to prevent silent fallback to a
    # different azd-authenticated account when az CLI is the intended credential.
    # See: https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential
    try:
        cred = DefaultAzureCredential(exclude_developer_cli_credential=True)
        # Validate credential works before returning
        token = cred.get_token("https://management.azure.com/.default")
        if token:
            logger.debug("Authentication successful via DefaultAzureCredential")
        return cred
    except Exception as e:
        raise RuntimeError(
            f"Authentication failed: {e}\n\n"
            "Resolution options:\n"
            "  1. Run 'az login' for interactive CLI authentication.\n"
            "  2. Set environment variables: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID\n"
            "  3. Use --client-id and --client-secret flags for Service Principal auth.\n"
            "  4. If running on Azure, ensure a Managed Identity is assigned.\n"
        ) from e
