# \SovereignGateApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**approve_action_v1_gate_action_id_approve_post**](SovereignGateApi.md#approve_action_v1_gate_action_id_approve_post) | **POST** /v1/gate/{action_id}/approve | Approve Action
[**deny_action_v1_gate_action_id_deny_post**](SovereignGateApi.md#deny_action_v1_gate_action_id_deny_post) | **POST** /v1/gate/{action_id}/deny | Deny Action
[**gate_status_v1_gate_status_get**](SovereignGateApi.md#gate_status_v1_gate_status_get) | **GET** /v1/gate/status | Gate Status
[**get_audit_log_v1_gate_audit_get**](SovereignGateApi.md#get_audit_log_v1_gate_audit_get) | **GET** /v1/gate/audit | Get Audit Log
[**list_pending_v1_gate_pending_get**](SovereignGateApi.md#list_pending_v1_gate_pending_get) | **GET** /v1/gate/pending | List Pending



## approve_action_v1_gate_action_id_approve_post

> models::GateActionResponse approve_action_v1_gate_action_id_approve_post(action_id, gate_approval_request, authorization)
Approve Action

Approve a pending L3 action with HMAC signature.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**action_id** | **String** |  | [required] |
**gate_approval_request** | [**GateApprovalRequest**](GateApprovalRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::GateActionResponse**](GateActionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## deny_action_v1_gate_action_id_deny_post

> serde_json::Value deny_action_v1_gate_action_id_deny_post(action_id, authorization)
Deny Action

Deny a pending L3 action.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**action_id** | **String** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## gate_status_v1_gate_status_get

> models::GateStatusResponse gate_status_v1_gate_status_get(authorization)
Gate Status

Get the current SovereignGate status.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::GateStatusResponse**](GateStatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_audit_log_v1_gate_audit_get

> serde_json::Value get_audit_log_v1_gate_audit_get(limit, authorization)
Get Audit Log

View the SovereignGate audit log.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**limit** | Option<**i32**> |  |  |[default to 50]
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**serde_json::Value**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## list_pending_v1_gate_pending_get

> Vec<models::GateActionResponse> list_pending_v1_gate_pending_get(authorization)
List Pending

List all pending L3 actions awaiting approval.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**Vec<models::GateActionResponse>**](GateActionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

