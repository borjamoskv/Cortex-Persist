# \SwarmAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**CreateWorktreeV1SwarmWorktreesPost**](SwarmAPI.md#CreateWorktreeV1SwarmWorktreesPost) | **Post** /v1/swarm/worktrees | Create Worktree
[**DeleteWorktreeV1SwarmWorktreesWorktreeIdDelete**](SwarmAPI.md#DeleteWorktreeV1SwarmWorktreesWorktreeIdDelete) | **Delete** /v1/swarm/worktrees/{worktree_id} | Delete Worktree
[**GetSwarmStatusV1SwarmStatusGet**](SwarmAPI.md#GetSwarmStatusV1SwarmStatusGet) | **Get** /v1/swarm/status | Get Swarm Status
[**GetWorktreeStatusV1SwarmWorktreesWorktreeIdGet**](SwarmAPI.md#GetWorktreeStatusV1SwarmWorktreesWorktreeIdGet) | **Get** /v1/swarm/worktrees/{worktree_id} | Get Worktree Status
[**RunPsychohistorySimulationV1SwarmPsychohistoryPost**](SwarmAPI.md#RunPsychohistorySimulationV1SwarmPsychohistoryPost) | **Post** /v1/swarm/psychohistory | Run Psychohistory Simulation



## CreateWorktreeV1SwarmWorktreesPost

> WorktreeResponse CreateWorktreeV1SwarmWorktreesPost(ctx).WorktreeCreateRequest(worktreeCreateRequest).Authorization(authorization).Execute()

Create Worktree



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
	worktreeCreateRequest := *openapiclient.NewWorktreeCreateRequest("BranchName_example") // WorktreeCreateRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SwarmAPI.CreateWorktreeV1SwarmWorktreesPost(context.Background()).WorktreeCreateRequest(worktreeCreateRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SwarmAPI.CreateWorktreeV1SwarmWorktreesPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CreateWorktreeV1SwarmWorktreesPost`: WorktreeResponse
	fmt.Fprintf(os.Stdout, "Response from `SwarmAPI.CreateWorktreeV1SwarmWorktreesPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiCreateWorktreeV1SwarmWorktreesPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **worktreeCreateRequest** | [**WorktreeCreateRequest**](WorktreeCreateRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**WorktreeResponse**](WorktreeResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## DeleteWorktreeV1SwarmWorktreesWorktreeIdDelete

> interface{} DeleteWorktreeV1SwarmWorktreesWorktreeIdDelete(ctx, worktreeId).Authorization(authorization).Execute()

Delete Worktree



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
	worktreeId := "worktreeId_example" // string | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SwarmAPI.DeleteWorktreeV1SwarmWorktreesWorktreeIdDelete(context.Background(), worktreeId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SwarmAPI.DeleteWorktreeV1SwarmWorktreesWorktreeIdDelete``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `DeleteWorktreeV1SwarmWorktreesWorktreeIdDelete`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `SwarmAPI.DeleteWorktreeV1SwarmWorktreesWorktreeIdDelete`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**worktreeId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiDeleteWorktreeV1SwarmWorktreesWorktreeIdDeleteRequest struct via the builder pattern


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


## GetSwarmStatusV1SwarmStatusGet

> SwarmStatusResponse GetSwarmStatusV1SwarmStatusGet(ctx).Authorization(authorization).Execute()

Get Swarm Status



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
	resp, r, err := apiClient.SwarmAPI.GetSwarmStatusV1SwarmStatusGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SwarmAPI.GetSwarmStatusV1SwarmStatusGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetSwarmStatusV1SwarmStatusGet`: SwarmStatusResponse
	fmt.Fprintf(os.Stdout, "Response from `SwarmAPI.GetSwarmStatusV1SwarmStatusGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetSwarmStatusV1SwarmStatusGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**SwarmStatusResponse**](SwarmStatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetWorktreeStatusV1SwarmWorktreesWorktreeIdGet

> WorktreeResponse GetWorktreeStatusV1SwarmWorktreesWorktreeIdGet(ctx, worktreeId).Authorization(authorization).Execute()

Get Worktree Status



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
	worktreeId := "worktreeId_example" // string | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SwarmAPI.GetWorktreeStatusV1SwarmWorktreesWorktreeIdGet(context.Background(), worktreeId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SwarmAPI.GetWorktreeStatusV1SwarmWorktreesWorktreeIdGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetWorktreeStatusV1SwarmWorktreesWorktreeIdGet`: WorktreeResponse
	fmt.Fprintf(os.Stdout, "Response from `SwarmAPI.GetWorktreeStatusV1SwarmWorktreesWorktreeIdGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**worktreeId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetWorktreeStatusV1SwarmWorktreesWorktreeIdGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**WorktreeResponse**](WorktreeResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## RunPsychohistorySimulationV1SwarmPsychohistoryPost

> interface{} RunPsychohistorySimulationV1SwarmPsychohistoryPost(ctx).PsychohistoryRequest(psychohistoryRequest).Authorization(authorization).Execute()

Run Psychohistory Simulation



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
	psychohistoryRequest := *openapiclient.NewPsychohistoryRequest("ScenarioName_example") // PsychohistoryRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SwarmAPI.RunPsychohistorySimulationV1SwarmPsychohistoryPost(context.Background()).PsychohistoryRequest(psychohistoryRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SwarmAPI.RunPsychohistorySimulationV1SwarmPsychohistoryPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `RunPsychohistorySimulationV1SwarmPsychohistoryPost`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `SwarmAPI.RunPsychohistorySimulationV1SwarmPsychohistoryPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiRunPsychohistorySimulationV1SwarmPsychohistoryPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **psychohistoryRequest** | [**PsychohistoryRequest**](PsychohistoryRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

**interface{}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

