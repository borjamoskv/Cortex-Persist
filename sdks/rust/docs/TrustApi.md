# \TrustApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**dry_run_guard_v1_trust_guard_post**](TrustApi.md#dry_run_guard_v1_trust_guard_post) | **POST** /v1/trust/guard | Dry Run Guard
[**get_agent_trust_v1_trust_profiles_agent_id_get**](TrustApi.md#get_agent_trust_v1_trust_profiles_agent_id_get) | **GET** /v1/trust/profiles/{agent_id} | Get Agent Trust
[**get_compliance_status_v1_trust_compliance_get**](TrustApi.md#get_compliance_status_v1_trust_compliance_get) | **GET** /v1/trust/compliance | Get Compliance Status



## dry_run_guard_v1_trust_guard_post

> std::collections::HashMap<String, serde_json::Value> dry_run_guard_v1_trust_guard_post(store_request, authorization)
Dry Run Guard

Dry-run a store proposal against StorageGuard (Ω₃).  Returns 200 {valid: true} or 400 with specific violation details.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**store_request** | [**StoreRequest**](StoreRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_agent_trust_v1_trust_profiles_agent_id_get

> models::TrustProfileResponse get_agent_trust_v1_trust_profiles_agent_id_get(agent_id, authorization)
Get Agent Trust

Retrieve the Bayesian trust profile for a specific agent.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**agent_id** | **String** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::TrustProfileResponse**](TrustProfileResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_compliance_status_v1_trust_compliance_get

> models::ComplianceReport get_compliance_status_v1_trust_compliance_get(authorization)
Get Compliance Status

Generate aggregate compliance report (EU AI Act Art 12).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::ComplianceReport**](ComplianceReport.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

