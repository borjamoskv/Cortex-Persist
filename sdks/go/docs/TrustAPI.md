# \TrustAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**DryRunGuardV1TrustGuardPost**](TrustAPI.md#DryRunGuardV1TrustGuardPost) | **Post** /v1/trust/guard | Dry Run Guard
[**GetAgentTrustV1TrustProfilesAgentIdGet**](TrustAPI.md#GetAgentTrustV1TrustProfilesAgentIdGet) | **Get** /v1/trust/profiles/{agent_id} | Get Agent Trust
[**GetComplianceStatusV1TrustComplianceGet**](TrustAPI.md#GetComplianceStatusV1TrustComplianceGet) | **Get** /v1/trust/compliance | Get Compliance Status



## DryRunGuardV1TrustGuardPost

> map[string]interface{} DryRunGuardV1TrustGuardPost(ctx).StoreRequest(storeRequest).Authorization(authorization).Execute()

Dry Run Guard



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
	storeRequest := *openapiclient.NewStoreRequest("Project_example", "Content_example") // StoreRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TrustAPI.DryRunGuardV1TrustGuardPost(context.Background()).StoreRequest(storeRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TrustAPI.DryRunGuardV1TrustGuardPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `DryRunGuardV1TrustGuardPost`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `TrustAPI.DryRunGuardV1TrustGuardPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiDryRunGuardV1TrustGuardPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **storeRequest** | [**StoreRequest**](StoreRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

**map[string]interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetAgentTrustV1TrustProfilesAgentIdGet

> TrustProfileResponse GetAgentTrustV1TrustProfilesAgentIdGet(ctx, agentId).Authorization(authorization).Execute()

Get Agent Trust



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
	agentId := "agentId_example" // string | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TrustAPI.GetAgentTrustV1TrustProfilesAgentIdGet(context.Background(), agentId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TrustAPI.GetAgentTrustV1TrustProfilesAgentIdGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetAgentTrustV1TrustProfilesAgentIdGet`: TrustProfileResponse
	fmt.Fprintf(os.Stdout, "Response from `TrustAPI.GetAgentTrustV1TrustProfilesAgentIdGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**agentId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetAgentTrustV1TrustProfilesAgentIdGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**TrustProfileResponse**](TrustProfileResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetComplianceStatusV1TrustComplianceGet

> ComplianceReport GetComplianceStatusV1TrustComplianceGet(ctx).Authorization(authorization).Execute()

Get Compliance Status



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
	resp, r, err := apiClient.TrustAPI.GetComplianceStatusV1TrustComplianceGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TrustAPI.GetComplianceStatusV1TrustComplianceGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetComplianceStatusV1TrustComplianceGet`: ComplianceReport
	fmt.Fprintf(os.Stdout, "Response from `TrustAPI.GetComplianceStatusV1TrustComplianceGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetComplianceStatusV1TrustComplianceGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**ComplianceReport**](ComplianceReport.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

