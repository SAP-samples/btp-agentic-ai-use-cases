"""Owned indirection layer for MCP tool loading.

Import get_mcp_tools from here — never directly from mcp_providers.agw or
from sap_cloud_sdk.agentgateway. This module is the single target that:

  1. The platform scans to identify which MCP servers this agent depends on,
     scoping the Agent Gateway client to only those declared in asset.yaml.
  2. The test fixture (conftest.py / IBD_TESTING=1) patches to inject mock
     tools from mcp-mock.json without touching any application code.
"""
from mcp_providers.agw import get_mcp_tools

__all__ = ["get_mcp_tools"]
