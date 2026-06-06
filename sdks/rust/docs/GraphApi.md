# \GraphApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_graph_all_v1_graph_get**](GraphApi.md#get_graph_all_v1_graph_get) | **GET** /v1/graph | Get Graph All
[**get_graph_v1_graph_project_get**](GraphApi.md#get_graph_v1_graph_project_get) | **GET** /v1/graph/{project} | Get Graph



## get_graph_all_v1_graph_get

> std::collections::HashMap<String, serde_json::Value> get_graph_all_v1_graph_get(limit, authorization)
Get Graph All

Get entity graph across all projects.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**limit** | Option<**i32**> |  |  |[default to 50]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_graph_v1_graph_project_get

> std::collections::HashMap<String, serde_json::Value> get_graph_v1_graph_project_get(project, limit, authorization)
Get Graph

Get entity graph for a specific project.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**project** | **String** |  | [required] |
**limit** | Option<**i32**> |  |  |[default to 50]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

