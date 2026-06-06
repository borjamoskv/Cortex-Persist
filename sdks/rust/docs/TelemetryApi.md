# \TelemetryApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**add_mafia_node_api_v1_telemetry_nodes_post**](TelemetryApi.md#add_mafia_node_api_v1_telemetry_nodes_post) | **POST** /api/v1/telemetry/nodes | Add Mafia Node
[**add_mafia_node_telemetry_nodes_post**](TelemetryApi.md#add_mafia_node_telemetry_nodes_post) | **POST** /telemetry/nodes | Add Mafia Node
[**add_mafia_node_v1_telemetry_nodes_post**](TelemetryApi.md#add_mafia_node_v1_telemetry_nodes_post) | **POST** /v1/telemetry/nodes | Add Mafia Node
[**get_mafia_nodes_api_v1_telemetry_nodes_get**](TelemetryApi.md#get_mafia_nodes_api_v1_telemetry_nodes_get) | **GET** /api/v1/telemetry/nodes | Get Mafia Nodes
[**get_mafia_nodes_telemetry_nodes_get**](TelemetryApi.md#get_mafia_nodes_telemetry_nodes_get) | **GET** /telemetry/nodes | Get Mafia Nodes
[**get_mafia_nodes_v1_telemetry_nodes_get**](TelemetryApi.md#get_mafia_nodes_v1_telemetry_nodes_get) | **GET** /v1/telemetry/nodes | Get Mafia Nodes
[**ingest_telemetry_api_v1_telemetry_ingest_post**](TelemetryApi.md#ingest_telemetry_api_v1_telemetry_ingest_post) | **POST** /api/v1/telemetry/ingest | Ingest Telemetry
[**ingest_telemetry_telemetry_ingest_post**](TelemetryApi.md#ingest_telemetry_telemetry_ingest_post) | **POST** /telemetry/ingest | Ingest Telemetry
[**ingest_telemetry_v1_telemetry_ingest_post**](TelemetryApi.md#ingest_telemetry_v1_telemetry_ingest_post) | **POST** /v1/telemetry/ingest | Ingest Telemetry



## add_mafia_node_api_v1_telemetry_nodes_post

> serde_json::Value add_mafia_node_api_v1_telemetry_nodes_post(mafia_node_proposal)
Add Mafia Node

Add a new mafia node fact and push to all active extensions.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**mafia_node_proposal** | [**MafiaNodeProposal**](MafiaNodeProposal.md) |  | [required] |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## add_mafia_node_telemetry_nodes_post

> serde_json::Value add_mafia_node_telemetry_nodes_post(mafia_node_proposal)
Add Mafia Node

Add a new mafia node fact and push to all active extensions.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**mafia_node_proposal** | [**MafiaNodeProposal**](MafiaNodeProposal.md) |  | [required] |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## add_mafia_node_v1_telemetry_nodes_post

> serde_json::Value add_mafia_node_v1_telemetry_nodes_post(mafia_node_proposal)
Add Mafia Node

Add a new mafia node fact and push to all active extensions.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**mafia_node_proposal** | [**MafiaNodeProposal**](MafiaNodeProposal.md) |  | [required] |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_mafia_nodes_api_v1_telemetry_nodes_get

> serde_json::Value get_mafia_nodes_api_v1_telemetry_nodes_get()
Get Mafia Nodes

Retrieve all active mafia nodes (base + dynamic).

### Parameters

This endpoint does not need any parameter.

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_mafia_nodes_telemetry_nodes_get

> serde_json::Value get_mafia_nodes_telemetry_nodes_get()
Get Mafia Nodes

Retrieve all active mafia nodes (base + dynamic).

### Parameters

This endpoint does not need any parameter.

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_mafia_nodes_v1_telemetry_nodes_get

> serde_json::Value get_mafia_nodes_v1_telemetry_nodes_get()
Get Mafia Nodes

Retrieve all active mafia nodes (base + dynamic).

### Parameters

This endpoint does not need any parameter.

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## ingest_telemetry_api_v1_telemetry_ingest_post

> serde_json::Value ingest_telemetry_api_v1_telemetry_ingest_post(telemetry_ingest_request)
Ingest Telemetry

Ingest sovereign telemetry facts (C5-REAL) from external edge sensors.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**telemetry_ingest_request** | [**TelemetryIngestRequest**](TelemetryIngestRequest.md) |  | [required] |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## ingest_telemetry_telemetry_ingest_post

> serde_json::Value ingest_telemetry_telemetry_ingest_post(telemetry_ingest_request)
Ingest Telemetry

Ingest sovereign telemetry facts (C5-REAL) from external edge sensors.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**telemetry_ingest_request** | [**TelemetryIngestRequest**](TelemetryIngestRequest.md) |  | [required] |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## ingest_telemetry_v1_telemetry_ingest_post

> serde_json::Value ingest_telemetry_v1_telemetry_ingest_post(telemetry_ingest_request)
Ingest Telemetry

Ingest sovereign telemetry facts (C5-REAL) from external edge sensors.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**telemetry_ingest_request** | [**TelemetryIngestRequest**](TelemetryIngestRequest.md) |  | [required] |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

