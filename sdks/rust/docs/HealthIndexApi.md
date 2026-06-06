# \HealthIndexApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**health_index_check_v1_health_check_get**](HealthIndexApi.md#health_index_check_v1_health_check_get) | **GET** /v1/health/check | Health Index Check
[**health_index_history_v1_health_history_get**](HealthIndexApi.md#health_index_history_v1_health_history_get) | **GET** /v1/health/history | Health Index History
[**health_index_metrics_v1_health_metrics_get**](HealthIndexApi.md#health_index_metrics_v1_health_metrics_get) | **GET** /v1/health/metrics | Health Index Metrics
[**health_index_prometheus_v1_health_prometheus_get**](HealthIndexApi.md#health_index_prometheus_v1_health_prometheus_get) | **GET** /v1/health/prometheus | Health Index Prometheus
[**health_index_report_v1_health_report_get**](HealthIndexApi.md#health_index_report_v1_health_report_get) | **GET** /v1/health/report | Health Index Report
[**health_index_score_v1_health_score_get**](HealthIndexApi.md#health_index_score_v1_health_score_get) | **GET** /v1/health/score | Health Index Score



## health_index_check_v1_health_check_get

> std::collections::HashMap<String, serde_json::Value> health_index_check_v1_health_check_get()
Health Index Check

Quick health check - score, grade, healthy boolean.

### Parameters

This endpoint does not need any parameter.

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## health_index_history_v1_health_history_get

> std::collections::HashMap<String, serde_json::Value> health_index_history_v1_health_history_get(limit)
Health Index History

Persisted health score history.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**limit** | Option<**i32**> |  |  |[default to 20]

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## health_index_metrics_v1_health_metrics_get

> std::collections::HashMap<String, serde_json::Value> health_index_metrics_v1_health_metrics_get()
Health Index Metrics

Raw metric snapshots for monitoring dashboards.

### Parameters

This endpoint does not need any parameter.

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## health_index_prometheus_v1_health_prometheus_get

> serde_json::Value health_index_prometheus_v1_health_prometheus_get()
Health Index Prometheus

Prometheus text exposition format.

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


## health_index_report_v1_health_report_get

> std::collections::HashMap<String, serde_json::Value> health_index_report_v1_health_report_get()
Health Index Report

Full health report with recommendations and warnings.

### Parameters

This endpoint does not need any parameter.

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## health_index_score_v1_health_score_get

> std::collections::HashMap<String, serde_json::Value> health_index_score_v1_health_score_get()
Health Index Score

Numeric score only (0-100).

### Parameters

This endpoint does not need any parameter.

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

