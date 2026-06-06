# TaasApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**executeJobV1TaasJobsJobIdExecutePost**](TaasApi.md#executejobv1taasjobsjobidexecutepost) | **POST** /v1/taas/jobs/{job_id}/execute | Execute Job |
| [**requestJobQuoteV1TaasJobsQuotePost**](TaasApi.md#requestjobquotev1taasjobsquotepost) | **POST** /v1/taas/jobs/quote | Request Job Quote |
| [**verifyJobProofV1TaasJobsJobIdVerifyGet**](TaasApi.md#verifyjobproofv1taasjobsjobidverifyget) | **GET** /v1/taas/jobs/{job_id}/verify | Verify Job Proof |



## executeJobV1TaasJobsJobIdExecutePost

> JobExecutionResult executeJobV1TaasJobsJobIdExecutePost(jobId, authorization)

Execute Job

Execute a previously quoted job and receive proof of execution.

### Example

```ts
import {
  Configuration,
  TaasApi,
} from '';
import type { ExecuteJobV1TaasJobsJobIdExecutePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TaasApi();

  const body = {
    // string
    jobId: jobId_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ExecuteJobV1TaasJobsJobIdExecutePostRequest;

  try {
    const data = await api.executeJobV1TaasJobsJobIdExecutePost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **jobId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**JobExecutionResult**](JobExecutionResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## requestJobQuoteV1TaasJobsQuotePost

> JobQuote requestJobQuoteV1TaasJobsQuotePost(jobRequest, authorization)

Request Job Quote

Request a quote and SLA for an agent execution job.

### Example

```ts
import {
  Configuration,
  TaasApi,
} from '';
import type { RequestJobQuoteV1TaasJobsQuotePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TaasApi();

  const body = {
    // JobRequest
    jobRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies RequestJobQuoteV1TaasJobsQuotePostRequest;

  try {
    const data = await api.requestJobQuoteV1TaasJobsQuotePost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **jobRequest** | [JobRequest](JobRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**JobQuote**](JobQuote.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## verifyJobProofV1TaasJobsJobIdVerifyGet

> { [key: string]: any; } verifyJobProofV1TaasJobsJobIdVerifyGet(jobId, proof, authorization)

Verify Job Proof

Verify cryptographic proof of execution for a job.

### Example

```ts
import {
  Configuration,
  TaasApi,
} from '';
import type { VerifyJobProofV1TaasJobsJobIdVerifyGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new TaasApi();

  const body = {
    // string
    jobId: jobId_example,
    // string
    proof: proof_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies VerifyJobProofV1TaasJobsJobIdVerifyGetRequest;

  try {
    const data = await api.verifyJobProofV1TaasJobsJobIdVerifyGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **jobId** | `string` |  | [Defaults to `undefined`] |
| **proof** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

