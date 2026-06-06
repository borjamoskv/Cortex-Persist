# \TaasAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**ExecuteJobV1TaasJobsJobIdExecutePost**](TaasAPI.md#ExecuteJobV1TaasJobsJobIdExecutePost) | **Post** /v1/taas/jobs/{job_id}/execute | Execute Job
[**RequestJobQuoteV1TaasJobsQuotePost**](TaasAPI.md#RequestJobQuoteV1TaasJobsQuotePost) | **Post** /v1/taas/jobs/quote | Request Job Quote
[**VerifyJobProofV1TaasJobsJobIdVerifyGet**](TaasAPI.md#VerifyJobProofV1TaasJobsJobIdVerifyGet) | **Get** /v1/taas/jobs/{job_id}/verify | Verify Job Proof



## ExecuteJobV1TaasJobsJobIdExecutePost

> JobExecutionResult ExecuteJobV1TaasJobsJobIdExecutePost(ctx, jobId).Authorization(authorization).Execute()

Execute Job



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID/cortex"
)

func main() {
	jobId := "jobId_example" // string | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TaasAPI.ExecuteJobV1TaasJobsJobIdExecutePost(context.Background(), jobId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TaasAPI.ExecuteJobV1TaasJobsJobIdExecutePost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ExecuteJobV1TaasJobsJobIdExecutePost`: JobExecutionResult
	fmt.Fprintf(os.Stdout, "Response from `TaasAPI.ExecuteJobV1TaasJobsJobIdExecutePost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**jobId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiExecuteJobV1TaasJobsJobIdExecutePostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**JobExecutionResult**](JobExecutionResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## RequestJobQuoteV1TaasJobsQuotePost

> JobQuote RequestJobQuoteV1TaasJobsQuotePost(ctx).JobRequest(jobRequest).Authorization(authorization).Execute()

Request Job Quote



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID/cortex"
)

func main() {
	jobRequest := *openapiclient.NewJobRequest("TaskType_example", map[string]interface{}{"key": interface{}(123)}, *openapiclient.NewJobSLA("ConfidenceLevel_example", int32(123), false)) // JobRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TaasAPI.RequestJobQuoteV1TaasJobsQuotePost(context.Background()).JobRequest(jobRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TaasAPI.RequestJobQuoteV1TaasJobsQuotePost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `RequestJobQuoteV1TaasJobsQuotePost`: JobQuote
	fmt.Fprintf(os.Stdout, "Response from `TaasAPI.RequestJobQuoteV1TaasJobsQuotePost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiRequestJobQuoteV1TaasJobsQuotePostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **jobRequest** | [**JobRequest**](JobRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**JobQuote**](JobQuote.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## VerifyJobProofV1TaasJobsJobIdVerifyGet

> map[string]interface{} VerifyJobProofV1TaasJobsJobIdVerifyGet(ctx, jobId).Proof(proof).Authorization(authorization).Execute()

Verify Job Proof



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID/cortex"
)

func main() {
	jobId := "jobId_example" // string | 
	proof := "proof_example" // string | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TaasAPI.VerifyJobProofV1TaasJobsJobIdVerifyGet(context.Background(), jobId).Proof(proof).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TaasAPI.VerifyJobProofV1TaasJobsJobIdVerifyGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `VerifyJobProofV1TaasJobsJobIdVerifyGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `TaasAPI.VerifyJobProofV1TaasJobsJobIdVerifyGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**jobId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiVerifyJobProofV1TaasJobsJobIdVerifyGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **proof** | **string** |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

