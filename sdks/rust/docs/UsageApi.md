# \UsageApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_usage_breakdown_v1_usage_breakdown_get**](UsageApi.md#get_usage_breakdown_v1_usage_breakdown_get) | **GET** /v1/usage/breakdown | Get Usage Breakdown
[**get_usage_history_v1_usage_history_get**](UsageApi.md#get_usage_history_v1_usage_history_get) | **GET** /v1/usage/history | Get Usage History
[**get_usage_v1_usage_get**](UsageApi.md#get_usage_v1_usage_get) | **GET** /v1/usage | Get Usage



## get_usage_breakdown_v1_usage_breakdown_get

> std::collections::HashMap<String, serde_json::Value> get_usage_breakdown_v1_usage_breakdown_get(authorization)
Get Usage Breakdown

Get per-endpoint breakdown for current month.

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


## get_usage_history_v1_usage_history_get

> std::collections::HashMap<String, serde_json::Value> get_usage_history_v1_usage_history_get(months, authorization)
Get Usage History

Get usage history for the last N months.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**months** | Option<**i32**> |  |  |[default to 12]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_usage_v1_usage_get

> std::collections::HashMap<String, serde_json::Value> get_usage_v1_usage_get(authorization)
Get Usage

Get current month's API usage for the authenticated tenant.

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

