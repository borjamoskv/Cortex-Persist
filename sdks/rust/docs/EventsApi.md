# \EventsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**stream_events_v1_events_stream_get**](EventsApi.md#stream_events_v1_events_stream_get) | **GET** /v1/events/stream | Stream Events
[**stream_events_v1_public_events_stream_get**](EventsApi.md#stream_events_v1_public_events_stream_get) | **GET** /v1/public/events/stream | Stream Events



## stream_events_v1_events_stream_get

> serde_json::Value stream_events_v1_events_stream_get(types, authorization)
Stream Events

Subscribe to CORTEX coordination events via SSE.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**types** | Option<**String**> | Comma-separated list of event types |  |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## stream_events_v1_public_events_stream_get

> serde_json::Value stream_events_v1_public_events_stream_get()
Stream Events

Server-Sent Events endpoint for real-time CORTEX telemetry.

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

