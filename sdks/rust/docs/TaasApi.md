# \TaasApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**execute_job_v1_taas_jobs_job_id_execute_post**](TaasApi.md#execute_job_v1_taas_jobs_job_id_execute_post) | **POST** /v1/taas/jobs/{job_id}/execute | Execute Job
[**request_job_quote_v1_taas_jobs_quote_post**](TaasApi.md#request_job_quote_v1_taas_jobs_quote_post) | **POST** /v1/taas/jobs/quote | Request Job Quote
[**verify_job_proof_v1_taas_jobs_job_id_verify_get**](TaasApi.md#verify_job_proof_v1_taas_jobs_job_id_verify_get) | **GET** /v1/taas/jobs/{job_id}/verify | Verify Job Proof



## execute_job_v1_taas_jobs_job_id_execute_post

> models::JobExecutionResult execute_job_v1_taas_jobs_job_id_execute_post(job_id, authorization)
Execute Job

Execute a previously quoted job and receive proof of execution.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**job_id** | **String** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::JobExecutionResult**](JobExecutionResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## request_job_quote_v1_taas_jobs_quote_post

> models::JobQuote request_job_quote_v1_taas_jobs_quote_post(job_request, authorization)
Request Job Quote

Request a quote and SLA for an agent execution job.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**job_request** | [**JobRequest**](JobRequest.md) |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::JobQuote**](JobQuote.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## verify_job_proof_v1_taas_jobs_job_id_verify_get

> std::collections::HashMap<String, serde_json::Value> verify_job_proof_v1_taas_jobs_job_id_verify_get(job_id, proof, authorization)
Verify Job Proof

Verify cryptographic proof of execution for a job.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**job_id** | **String** |  | [required] |
**proof** | **String** |  | [required] |
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**std::collections::HashMap<String, serde_json::Value>**](serde_json::Value.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

