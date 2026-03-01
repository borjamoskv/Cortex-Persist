"""Unit tests for the SAP OData Client and its components.

Tests the Vault, Transport, Schema parser, and Client facade without network I/O.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from cortex.sap.client import SAPClient
from cortex.sap.models import SAPAuthError, SAPConfig, SAPEntityError
from cortex.sap.schema import parse_metadata_xml
from cortex.sap.transport import SAPTransport
from cortex.sap.vault import SAPVault

# ─── Schema Parsing Tests ────────────────────────────────────────────


def test_schema_parsing():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <edmx:Edmx Version="1.0" xmlns:edmx="http://schemas.microsoft.com/ado/2007/06/edmx">
      <edmx:DataServices m:DataServiceVersion="2.0">
        <Schema Namespace="API_BUSINESS_PARTNER" xmlns="http://schemas.microsoft.com/ado/2008/09/edm">
          <EntityType Name="A_BusinessPartnerType">
            <Key>
              <PropertyRef Name="BusinessPartner" />
            </Key>
            <Property Name="BusinessPartner" Type="Edm.String" />
            <Property Name="BusinessPartnerCategory" Type="Edm.String" />
          </EntityType>
        </Schema>
      </edmx:DataServices>
    </edmx:Edmx>"""
    entity_map = parse_metadata_xml(xml)
    assert "A_BusinessPartnerType" in entity_map
    assert set(entity_map["A_BusinessPartnerType"]) == {"BusinessPartner", "BusinessPartnerCategory"}

def test_schema_parsing_invalid():
    entity_map = parse_metadata_xml("Not XML")
    assert entity_map == {}

# ─── Vault Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_vault_basic_auth():
    config = SAPConfig(base_url="http://test", username="alice", password="bob")
    vault = SAPVault(config)
    
    async with httpx.AsyncClient() as client:
        headers = await vault.get_auth_headers(client)
    
    # "alice:bob" base64 encoded is "YWxpY2U6Ym9i"
    assert headers["Authorization"] == "Basic YWxpY2U6Ym9i"


@pytest.mark.asyncio
@respx.mock
async def test_vault_oauth2():
    config = SAPConfig(
        base_url="http://test",
        auth_type="oauth2",
        oauth_token_url="http://auth/token",
        oauth_client_id="id",
        oauth_client_secret="sec",
    )
    vault = SAPVault(config)

    respx.post("http://auth/token").mock(
        return_value=httpx.Response(200, json={"access_token": "mocked_jwt"})
    )

    async with httpx.AsyncClient() as client:
        headers = await vault.get_auth_headers(client)

    assert headers["Authorization"] == "Bearer mocked_jwt"


@pytest.mark.asyncio
@respx.mock
async def test_vault_oauth2_failure():
    config = SAPConfig(
        base_url="http://test", auth_type="oauth2", oauth_token_url="http://auth/token"
    )
    vault = SAPVault(config)
    respx.post("http://auth/token").mock(return_value=httpx.Response(401))

    async with httpx.AsyncClient() as client:
        with pytest.raises(SAPAuthError, match="request failed: 401"):
            await vault.get_auth_headers(client)


def test_vault_csrf_management():
    config = SAPConfig(base_url="http://test")
    vault = SAPVault(config)
    
    assert vault.has_csrf is False
    vault.set_csrf_token("abc-123")
    assert vault.has_csrf is True
    
    headers = vault.build_request_headers("POST", {}, True)
    assert headers["x-csrf-token"] == "abc-123"
    assert headers["Content-Type"] == "application/json"
    
    vault.clear()
    assert vault.has_csrf is False


# ─── Transport Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_transport_connect_success():
    config = SAPConfig(base_url="http://sap.local")
    transport = SAPTransport(config, SAPVault(config))

    respx.head("http://sap.local").mock(
        return_value=httpx.Response(200, headers={"x-csrf-token": "valid-token"})
    )

    await transport.connect()
    assert transport.vault.has_csrf
    assert transport.is_connected
    await transport.close()
    assert not transport.is_connected


@pytest.mark.asyncio
@respx.mock
async def test_transport_connect_auth_failure():
    config = SAPConfig(base_url="http://sap.local")
    transport = SAPTransport(config, SAPVault(config))

    respx.head("http://sap.local").mock(return_value=httpx.Response(401))

    with pytest.raises(SAPAuthError, match="check credentials"):
        await transport.connect()
    assert not transport.is_connected


@pytest.mark.asyncio
@respx.mock
async def test_transport_retry_loop_success(caplog):
    config = SAPConfig(base_url="http://sap.local", max_retries=3)
    transport = SAPTransport(config, SAPVault(config))
    await transport.connect()

    # Fail twice, succeed on third
    route = respx.get("http://sap.local/Entity")
    route.side_effect = [
        httpx.ConnectError("Network drop"),
        httpx.ConnectError("Network drop"),
        httpx.Response(200, json={"d": {"results": []}}),
    ]

    data = await transport.request("GET", "http://sap.local/Entity")
    assert data == {"d": {"results": []}}
    assert route.call_count == 3
    assert "Retrying 2/3" in caplog.text


@pytest.mark.asyncio
@respx.mock
async def test_transport_status_code_mapping():
    config = SAPConfig(base_url="http://sap.local", max_retries=1)
    transport = SAPTransport(config, SAPVault(config))
    await transport.connect()

    respx.get("http://sap.local/Err").mock(return_value=httpx.Response(403))
    with pytest.raises(SAPAuthError, match="Forbidden"):
        await transport.request("GET", "http://sap.local/Err")

    respx.get("http://sap.local/Err2").mock(return_value=httpx.Response(404, text="Oops"))
    with pytest.raises(SAPEntityError, match="SAP error 404: Oops"):
        await transport.request("GET", "http://sap.local/Err2")


# ─── Facade Client Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_client_crud_operations():
    client = SAPClient(SAPConfig(base_url="http://sap.local"))

    # Mock connect
    respx.head("http://sap.local").mock(
        return_value=httpx.Response(200, headers={"x-csrf-token": "tkn"})
    )
    await client.connect()

    # Mock read_entity_set
    respx.get("http://sap.local/EntitySet?$format=json&$top=10&$skip=0&$filter=Id%20eq%201&$select=Id,Name").mock(
        return_value=httpx.Response(200, json={"d": {"results": [{"Id": 1, "Name": "Test"}]}})
    )
    result = await client.read_entity_set(
        "EntitySet", top=10, filters="Id eq 1", select=["Id", "Name"]
    )
    assert len(result) == 1
    assert result[0]["Name"] == "Test"

    # Mock read_entity
    respx.get("http://sap.local/EntitySet('123')?$format=json").mock(
        return_value=httpx.Response(200, json={"d": {"Id": "123"}})
    )
    ent = await client.read_entity("EntitySet", "'123'")
    assert ent["Id"] == "123"

    # Mock create
    respx.post("http://sap.local/EntitySet").mock(
        return_value=httpx.Response(201, json={"d": {"Created": True}})
    )
    created = await client.create_entity("EntitySet", {"val": 1})
    assert created["Created"] is True

    # Mock update
    respx.patch("http://sap.local/EntitySet('123')").mock(
        return_value=httpx.Response(204)
    )
    success = await client.update_entity("EntitySet", "'123'", {"val": 2}, merge=True)
    assert success is True

    await client.close()
