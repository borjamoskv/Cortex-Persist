# \TimingApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_time_history_v1_time_history_get**](TimingApi.md#get_time_history_v1_time_history_get) | **GET** /v1/time/history | Get Time History
[**record_heartbeat_v1_heartbeat_post**](TimingApi.md#record_heartbeat_v1_heartbeat_post) | **POST** /v1/heartbeat | Record Heartbeat
[**time_report_v1_time_get**](TimingApi.md#time_report_v1_time_get) | **GET** /v1/time | Time Report
[**time_today_v1_time_today_get**](TimingApi.md#time_today_v1_time_today_get) | **GET** /v1/time/today | Time Today



## get_time_history_v1_time_history_get

> Vec<serde_json::Value> get_time_history_v1_time_history_get(days, authorization)
Get Time History

Get daily time history.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**days** | Option<**i32**> |  |  |[default to 7]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## record_heartbeat_v1_heartbeat_post

> std::collections::HashMap<String, serde_json::Value> record_heartbeat_v1_heartbeat_post(heartbeat_request, authorization)
Record Heartbeat

Record an activity heartbeat for automatic time tracking.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**heartbeat_request** | [**HeartbeatRequest**](HeartbeatRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## time_report_v1_time_get

> models::TimeSummaryResponse time_report_v1_time_get(project, days, authorization)
Time Report

Get time tracking report for the last N days.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**project** | Option<**String**> |  |  |
**days** | Option<**i32**> |  |  |[default to 7]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::TimeSummaryResponse**](TimeSummaryResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## time_today_v1_time_today_get

> models::TimeSummaryResponse time_today_v1_time_today_get(project, authorization)
Time Today

Get today's time tracking summary.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**project** | Option<**String**> |  |  |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::TimeSummaryResponse**](TimeSummaryResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

