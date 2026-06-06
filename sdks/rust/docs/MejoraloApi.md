# \MejoraloApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_history_v1_mejoralo_history_get**](MejoraloApi.md#get_history_v1_mejoralo_history_get) | **GET** /v1/mejoralo/history | Get History
[**record_session_v1_mejoralo_record_post**](MejoraloApi.md#record_session_v1_mejoralo_record_post) | **POST** /v1/mejoralo/record | Record Session
[**scan_project_v1_mejoralo_scan_post**](MejoraloApi.md#scan_project_v1_mejoralo_scan_post) | **POST** /v1/mejoralo/scan | Scan Project
[**ship_gate_v1_mejoralo_ship_post**](MejoraloApi.md#ship_gate_v1_mejoralo_ship_post) | **POST** /v1/mejoralo/ship | Ship Gate



## get_history_v1_mejoralo_history_get

> Vec<std::collections::HashMap<String, serde_json::Value>> get_history_v1_mejoralo_history_get(project, limit, authorization)
Get History

Retrieve MEJORAlo session history for a project.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**project** | **String** |  | [required] |
**limit** | Option<**i32**> |  |  |[default to 20]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<std::collections::HashMap<String, serde_json::Value>>**](std::collections::HashMap.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## record_session_v1_mejoralo_record_post

> models::MejoraloSessionResponse record_session_v1_mejoralo_record_post(mejoralo_session_request, authorization)
Record Session

Record a MEJORAlo audit session in the ledger.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**mejoralo_session_request** | [**MejoraloSessionRequest**](MejoraloSessionRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::MejoraloSessionResponse**](MejoraloSessionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## scan_project_v1_mejoralo_scan_post

> models::MejoraloScanResponse scan_project_v1_mejoralo_scan_post(mejoralo_scan_request, authorization)
Scan Project

Execute X-Ray 13D scan on a project.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**mejoralo_scan_request** | [**MejoraloScanRequest**](MejoraloScanRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::MejoraloScanResponse**](MejoraloScanResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## ship_gate_v1_mejoralo_ship_post

> models::MejoraloShipResponse ship_gate_v1_mejoralo_ship_post(mejoralo_ship_request, authorization)
Ship Gate

Validate the 7 Seals for production readiness.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**mejoralo_ship_request** | [**MejoraloShipRequest**](MejoraloShipRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::MejoraloShipResponse**](MejoraloShipResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

