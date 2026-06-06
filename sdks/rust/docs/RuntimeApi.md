# \RuntimeApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_boot_recovery_v1_runtime_boot_recovery_get**](RuntimeApi.md#get_boot_recovery_v1_runtime_boot_recovery_get) | **GET** /v1/runtime/boot_recovery | Get Boot Recovery
[**get_health_v1_runtime_health_get**](RuntimeApi.md#get_health_v1_runtime_health_get) | **GET** /v1/runtime/health | Get Health



## get_boot_recovery_v1_runtime_boot_recovery_get

> models::RecoveryReport get_boot_recovery_v1_runtime_boot_recovery_get()
Get Boot Recovery

Get the memory recovery report generated during boot.

### Parameters

This endpoint does not need any parameter.

### Return type

[**models::RecoveryReport**](RecoveryReport.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_health_v1_runtime_health_get

> std::collections::HashMap<String, serde_json::Value> get_health_v1_runtime_health_get()
Get Health

Retrieve runtime health report.

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

