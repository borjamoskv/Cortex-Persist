# \DaemonApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**daemon_status_v1_daemon_status_get**](DaemonApi.md#daemon_status_v1_daemon_status_get) | **GET** /v1/daemon/status | Daemon Status



## daemon_status_v1_daemon_status_get

> std::collections::HashMap<String, serde_json::Value> daemon_status_v1_daemon_status_get(authorization)
Daemon Status

Get last daemon watchdog check results.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

