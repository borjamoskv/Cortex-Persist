# \OracleApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**audit_target_v1_oracle_audit_post**](OracleApi.md#audit_target_v1_oracle_audit_post) | **POST** /v1/oracle/audit | Audit Target



## audit_target_v1_oracle_audit_post

> models::OracleResponse audit_target_v1_oracle_audit_post(oracle_request, authorization)
Audit Target

The Oracle: Run a Sovereign Agent audit. Requires a valid CORTEX API Key (provisioned via Stripe subscription).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**oracle_request** | [**OracleRequest**](OracleRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::OracleResponse**](OracleResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

