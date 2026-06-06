# \SovereignGateAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**ApproveActionV1GateActionIdApprovePost**](SovereignGateAPI.md#ApproveActionV1GateActionIdApprovePost) | **Post** /v1/gate/{action_id}/approve | Approve Action
[**DenyActionV1GateActionIdDenyPost**](SovereignGateAPI.md#DenyActionV1GateActionIdDenyPost) | **Post** /v1/gate/{action_id}/deny | Deny Action
[**GateStatusV1GateStatusGet**](SovereignGateAPI.md#GateStatusV1GateStatusGet) | **Get** /v1/gate/status | Gate Status
[**GetAuditLogV1GateAuditGet**](SovereignGateAPI.md#GetAuditLogV1GateAuditGet) | **Get** /v1/gate/audit | Get Audit Log
[**ListPendingV1GatePendingGet**](SovereignGateAPI.md#ListPendingV1GatePendingGet) | **Get** /v1/gate/pending | List Pending



## ApproveActionV1GateActionIdApprovePost

> GateActionResponse ApproveActionV1GateActionIdApprovePost(ctx, actionId).GateApprovalRequest(gateApprovalRequest).Authorization(authorization).Execute()

Approve Action



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
	actionId := "actionId_example" // string | 
	gateApprovalRequest := *openapiclient.NewGateApprovalRequest("Signature_example") // GateApprovalRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SovereignGateAPI.ApproveActionV1GateActionIdApprovePost(context.Background(), actionId).GateApprovalRequest(gateApprovalRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SovereignGateAPI.ApproveActionV1GateActionIdApprovePost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ApproveActionV1GateActionIdApprovePost`: GateActionResponse
	fmt.Fprintf(os.Stdout, "Response from `SovereignGateAPI.ApproveActionV1GateActionIdApprovePost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**actionId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiApproveActionV1GateActionIdApprovePostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **gateApprovalRequest** | [**GateApprovalRequest**](GateApprovalRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**GateActionResponse**](GateActionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## DenyActionV1GateActionIdDenyPost

> interface{} DenyActionV1GateActionIdDenyPost(ctx, actionId).Authorization(authorization).Execute()

Deny Action



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
	actionId := "actionId_example" // string | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SovereignGateAPI.DenyActionV1GateActionIdDenyPost(context.Background(), actionId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SovereignGateAPI.DenyActionV1GateActionIdDenyPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `DenyActionV1GateActionIdDenyPost`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `SovereignGateAPI.DenyActionV1GateActionIdDenyPost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**actionId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiDenyActionV1GateActionIdDenyPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GateStatusV1GateStatusGet

> GateStatusResponse GateStatusV1GateStatusGet(ctx).Authorization(authorization).Execute()

Gate Status



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
	resp, r, err := apiClient.SovereignGateAPI.GateStatusV1GateStatusGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SovereignGateAPI.GateStatusV1GateStatusGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GateStatusV1GateStatusGet`: GateStatusResponse
	fmt.Fprintf(os.Stdout, "Response from `SovereignGateAPI.GateStatusV1GateStatusGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGateStatusV1GateStatusGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**GateStatusResponse**](GateStatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetAuditLogV1GateAuditGet

> interface{} GetAuditLogV1GateAuditGet(ctx).Limit(limit).Authorization(authorization).Execute()

Get Audit Log



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
	limit := int32(56) // int32 |  (optional) (default to 50)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SovereignGateAPI.GetAuditLogV1GateAuditGet(context.Background()).Limit(limit).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SovereignGateAPI.GetAuditLogV1GateAuditGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetAuditLogV1GateAuditGet`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `SovereignGateAPI.GetAuditLogV1GateAuditGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetAuditLogV1GateAuditGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | **int32** |  | [default to 50]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListPendingV1GatePendingGet

> []GateActionResponse ListPendingV1GatePendingGet(ctx).Authorization(authorization).Execute()

List Pending



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
	resp, r, err := apiClient.SovereignGateAPI.ListPendingV1GatePendingGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SovereignGateAPI.ListPendingV1GatePendingGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListPendingV1GatePendingGet`: []GateActionResponse
	fmt.Fprintf(os.Stdout, "Response from `SovereignGateAPI.ListPendingV1GatePendingGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiListPendingV1GatePendingGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]GateActionResponse**](GateActionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

