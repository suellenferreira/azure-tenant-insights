"""
Core Azure Resource Graph query engine.

Handles:
  - Paginated queries (1000 records/page, skip_token based)
  - Throttle-aware retry (reads x-ms-user-quota-remaining)
  - Graceful degradation on 403 / authorization errors
  - Dynamic resource type discovery

API Reference:
  https://learn.microsoft.com/en-us/azure/governance/resource-graph/
"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Resource Graph maximum page size
PAGE_SIZE = 1000

# Transient AzureCliCredential subprocess failure handling
CLI_MAX_RETRIES = 3
CLI_BACKOFF_BASE = 2.0  # seconds; exponential: 2s, 4s, 8s


def query_resource_graph(
    credential,
    query: str,
    subscription_ids: List[str],
    throttle_delay: float = 1.0,
    management_groups: Optional[List[str]] = None,
    caller: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Executes a paginated Resource Graph KQL query and returns all results.

    Automatically follows skip_token pages until all results are retrieved.
    Respects throttle_delay between pages and handles 429 rate-limiting.

    Args:
        caller: Optional collector name (e.g. "defender"). When provided,
            warnings/errors are logged under ``collectors.<caller>`` so the
            report's "Data collection notes" attribute the issue to the
            originating collector instead of the generic resource_graph engine.

    Returns: flat list of result row dicts.
    """
    from azure.mgmt.resourcegraph import ResourceGraphClient
    from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions

    # Route warnings/errors to the caller's logger so reports attribute them
    # to the right collector (e.g. defender) rather than the generic engine.
    log = logging.getLogger(f"collectors.{caller}") if caller else logger

    client = ResourceGraphClient(credential)
    all_results: List[Dict[str, Any]] = []

    # Resource Graph accepts at most 1000 subscriptions per request — chunk larger
    # sets so nothing is silently dropped. Management-group scope needs no chunking.
    if management_groups:
        sub_chunks: List[Optional[List[str]]] = [None]
    else:
        sub_chunks = [
            subscription_ids[i:i + 1000]
            for i in range(0, len(subscription_ids), 1000)
        ] or [[]]
        if len(subscription_ids) > 1000:
            log.info(
                f"Querying {len(subscription_ids)} subscriptions in {len(sub_chunks)} "
                f"chunk(s) of up to 1000 (Resource Graph per-request limit)."
            )

    for chunk in sub_chunks:
        skip_token: Optional[str] = None
        page = 0
        cli_retries = 0  # transient AzureCliCredential subprocess failures

        while True:
            page += 1
            options = QueryRequestOptions(
                result_format="objectArray",
                top=PAGE_SIZE,
                skip_token=skip_token,
            )

            if management_groups:
                req = QueryRequest(
                    query=query,
                    management_groups=management_groups,
                    options=options,
                )
            else:
                req = QueryRequest(
                    query=query,
                    subscriptions=chunk,
                    options=options,
                )

            try:
                resp = client.resources(req)
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "TooManyRequests" in error_msg:
                    log.warning("Rate limited by Resource Graph. Waiting 30 seconds...")
                    time.sleep(30)
                    continue
                elif "403" in error_msg or "AuthorizationFailed" in error_msg:
                    log.warning(f"Authorization error — skipping query: {error_msg[:200]}")
                    break  # move on to the next subscription chunk
                elif (
                    "Failed to invoke the Azure CLI" in error_msg
                    or "AzureCliCredential" in error_msg
                ) and cli_retries < CLI_MAX_RETRIES:
                    # Transient: the `az` subprocess can fail under concurrency.
                    # Retry the same page with exponential backoff before giving up.
                    cli_retries += 1
                    backoff = CLI_BACKOFF_BASE * (2 ** (cli_retries - 1))
                    log.warning(
                        f"Azure CLI token fetch failed (transient, attempt "
                        f"{cli_retries}/{CLI_MAX_RETRIES}). Retrying in {backoff:.0f}s..."
                    )
                    time.sleep(backoff)
                    page -= 1  # do not advance the page counter on retry
                    continue
                else:
                    log.error(f"Resource Graph query failed (page {page}): {error_msg[:300]}")
                    break

            cli_retries = 0  # reset after a successful page
            data = resp.data or []
            all_results.extend(data)

            logger.debug(
                f"Resource Graph page {page}: {len(data)} rows (cumulative: {len(all_results)})"
            )

            skip_token = resp.skip_token
            if not skip_token:
                break

            time.sleep(throttle_delay)

    return all_results


def get_resource_types(
    credential,
    subscription_ids: List[str],
    throttle_delay: float = 1.0,
) -> List[str]:
    """
    Discovers all resource types present in the subscriptions.

    Returns lowercase type strings sorted by resource count descending.
    This is the core of the dynamic resource coverage approach —
    no types are hardcoded or pre-registered.
    """
    query = """
    Resources
    | summarize count() by type
    | order by count_ desc
    | project type
    """

    results = query_resource_graph(
        credential=credential,
        query=query,
        subscription_ids=subscription_ids,
        throttle_delay=throttle_delay,
    )

    return [r["type"].lower() for r in results if "type" in r]
