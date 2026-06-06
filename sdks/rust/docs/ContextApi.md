# \ContextApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**context_history_v1_context_history_get**](ContextApi.md#context_history_v1_context_history_get) | **GET** /v1/context/history | Context History
[**infer_context_v1_context_infer_get**](ContextApi.md#infer_context_v1_context_infer_get) | **GET** /v1/context/infer | Infer Context
[**list_signals_v1_context_signals_get**](ContextApi.md#list_signals_v1_context_signals_get) | **GET** /v1/context/signals | List Signals



## context_history_v1_context_history_get

> Vec<std::collections::HashMap<String, serde_json::Value>> context_history_v1_context_history_get(limit, authorization)
Context History

Retrieve past context inference snapshots.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**limit** | Option<**i32**> |  |  |[default to 10]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<std::collections::HashMap<String, serde_json::Value>>**](std::collections::HashMap.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## infer_context_v1_context_infer_get

> models::ContextSnapshotResponse infer_context_v1_context_infer_get(persist, authorization)
Infer Context

Run ambient context inference and return the current context snapshot.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**persist** | Option<**bool**> | Persist snapshot to DB |  |[default to true]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::ContextSnapshotResponse**](ContextSnapshotResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## list_signals_v1_context_signals_get

> Vec<models::ContextSignalModel> list_signals_v1_context_signals_get(authorization)
List Signals

List raw ambient signals without running inference.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<models::ContextSignalModel>**](ContextSignalModel.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

