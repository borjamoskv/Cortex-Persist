# \GovernanceApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_api_key_v1_admin_keys_post**](GovernanceApi.md#create_api_key_v1_admin_keys_post) | **POST** /v1/admin/keys | Create Api Key
[**deep_health_check_v1_health_deep_get**](GovernanceApi.md#deep_health_check_v1_health_deep_get) | **GET** /v1/health/deep | Deep Health Check
[**execute_credibility_strike_v1_admin_credibility_strike_post**](GovernanceApi.md#execute_credibility_strike_v1_admin_credibility_strike_post) | **POST** /v1/admin/credibility-strike | Execute Credibility Strike
[**export_project_v1_projects_project_export_get**](GovernanceApi.md#export_project_v1_projects_project_export_get) | **GET** /v1/projects/{project}/export | Export Project
[**generate_handoff_context_v1_handoff_post**](GovernanceApi.md#generate_handoff_context_v1_handoff_post) | **POST** /v1/handoff | Generate Handoff Context
[**get_system_status_v1_status_get**](GovernanceApi.md#get_system_status_v1_status_get) | **GET** /v1/status | Get System Status
[**list_api_keys_v1_admin_keys_get**](GovernanceApi.md#list_api_keys_v1_admin_keys_get) | **GET** /v1/admin/keys | List Api Keys



## create_api_key_v1_admin_keys_post

> models::ApiKeyResponse create_api_key_v1_admin_keys_post(name, tenant_id, authorization)
Create Api Key

Sovereign Key Provisioning.  First key is self-provisioned (bootstrap). Subsequent keys require 'admin' permission.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**name** | **String** |  | [required] |
**tenant_id** | Option<**String**> |  |  |[default to default]
**authorization** | Option<**String**> |  |  |

### Return type

[**models::ApiKeyResponse**](ApiKeyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## deep_health_check_v1_health_deep_get

> models::DeepHealthResponse deep_health_check_v1_health_deep_get(authorization)
Deep Health Check

Deep Health Check - probes all CORTEX subsystems.  Returns 200 if all checks pass, 503 if any subsystem is degraded. Designed for Kubernetes liveness/readiness probes.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::DeepHealthResponse**](DeepHealthResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## execute_credibility_strike_v1_admin_credibility_strike_post

> std::collections::HashMap<String, serde_json::Value> execute_credibility_strike_v1_admin_credibility_strike_post(project, ultrathink, authorization)
Execute Credibility Strike

Execute a JIT credibility strike for a project.  Computes exergy, constructs Merkle roots, signs the root, performs replay validation, and takes database snapshots.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**project** | **String** |  | [required] |
**ultrathink** | Option<**bool**> |  |  |[default to true]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## export_project_v1_projects_project_export_get

> models::ExportResponse export_project_v1_projects_project_export_get(project, path, format, authorization)
Export Project

Sovereign Export - dumps project memory to a secure JSON artifact.  Enforces path incarceration to prevent directory traversal.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**project** | **String** |  | [required] |
**path** | Option<**String**> |  |  |
**format** | Option<**String**> |  |  |[default to json]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::ExportResponse**](ExportResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## generate_handoff_context_v1_handoff_post

> std::collections::HashMap<String, serde_json::Value> generate_handoff_context_v1_handoff_post(authorization)
Generate Handoff Context

Manifest a session handoff artifact with hot context and recent episodes.  Used for transferring agentic state between platforms (macOS -> Web).

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


## get_system_status_v1_status_get

> models::StatusResponse get_system_status_v1_status_get(authorization)
Get System Status

Expose engine diagnostics and memory health metrics.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::StatusResponse**](StatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## list_api_keys_v1_admin_keys_get

> Vec<models::ApiKeyListItem> list_api_keys_v1_admin_keys_get(authorization)
List Api Keys

Expose non-sensitive metadata for all provisioned keys.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<models::ApiKeyListItem>**](ApiKeyListItem.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

