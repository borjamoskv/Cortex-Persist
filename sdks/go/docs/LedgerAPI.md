# \LedgerAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**CreateCheckpointV1LedgerCheckpointPost**](LedgerAPI.md#CreateCheckpointV1LedgerCheckpointPost) | **Post** /v1/ledger/checkpoint | Create Checkpoint
[**GetLedgerStatusV1LedgerStatusGet**](LedgerAPI.md#GetLedgerStatusV1LedgerStatusGet) | **Get** /v1/ledger/status | Get Ledger Status
[**VerifyLedgerV1LedgerVerifyGet**](LedgerAPI.md#VerifyLedgerV1LedgerVerifyGet) | **Get** /v1/ledger/verify | Verify Ledger



## CreateCheckpointV1LedgerCheckpointPost

> CheckpointResponse CreateCheckpointV1LedgerCheckpointPost(ctx).Authorization(authorization).Execute()

Create Checkpoint



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
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.LedgerAPI.CreateCheckpointV1LedgerCheckpointPost(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `LedgerAPI.CreateCheckpointV1LedgerCheckpointPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CreateCheckpointV1LedgerCheckpointPost`: CheckpointResponse
	fmt.Fprintf(os.Stdout, "Response from `LedgerAPI.CreateCheckpointV1LedgerCheckpointPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiCreateCheckpointV1LedgerCheckpointPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**CheckpointResponse**](CheckpointResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetLedgerStatusV1LedgerStatusGet

> LedgerReportResponse GetLedgerStatusV1LedgerStatusGet(ctx).Authorization(authorization).Execute()

Get Ledger Status



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
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.LedgerAPI.GetLedgerStatusV1LedgerStatusGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `LedgerAPI.GetLedgerStatusV1LedgerStatusGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetLedgerStatusV1LedgerStatusGet`: LedgerReportResponse
	fmt.Fprintf(os.Stdout, "Response from `LedgerAPI.GetLedgerStatusV1LedgerStatusGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetLedgerStatusV1LedgerStatusGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**LedgerReportResponse**](LedgerReportResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## VerifyLedgerV1LedgerVerifyGet

> LedgerReportResponse VerifyLedgerV1LedgerVerifyGet(ctx).Authorization(authorization).Execute()

Verify Ledger



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
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.LedgerAPI.VerifyLedgerV1LedgerVerifyGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `LedgerAPI.VerifyLedgerV1LedgerVerifyGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `VerifyLedgerV1LedgerVerifyGet`: LedgerReportResponse
	fmt.Fprintf(os.Stdout, "Response from `LedgerAPI.VerifyLedgerV1LedgerVerifyGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiVerifyLedgerV1LedgerVerifyGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**LedgerReportResponse**](LedgerReportResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

