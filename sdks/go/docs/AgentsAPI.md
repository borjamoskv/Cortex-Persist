# \AgentsAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**GetAgentV1AgentsAgentIdGet**](AgentsAPI.md#GetAgentV1AgentsAgentIdGet) | **Get** /v1/agents/{agent_id} | Get Agent
[**ListAgentsV1AgentsGet**](AgentsAPI.md#ListAgentsV1AgentsGet) | **Get** /v1/agents | List Agents
[**RegisterAgentV1AgentsPost**](AgentsAPI.md#RegisterAgentV1AgentsPost) | **Post** /v1/agents | Register Agent



## GetAgentV1AgentsAgentIdGet

> AgentResponse GetAgentV1AgentsAgentIdGet(ctx, agentId).Authorization(authorization).Execute()

Get Agent



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
	resp, r, err := apiClient.AgentsAPI.GetAgentV1AgentsAgentIdGet(context.Background(), agentId).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AgentsAPI.GetAgentV1AgentsAgentIdGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetAgentV1AgentsAgentIdGet`: AgentResponse
	fmt.Fprintf(os.Stdout, "Response from `AgentsAPI.GetAgentV1AgentsAgentIdGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**agentId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetAgentV1AgentsAgentIdGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**AgentResponse**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListAgentsV1AgentsGet

> []AgentResponse ListAgentsV1AgentsGet(ctx).Authorization(authorization).Execute()

List Agents



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
	resp, r, err := apiClient.AgentsAPI.ListAgentsV1AgentsGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AgentsAPI.ListAgentsV1AgentsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListAgentsV1AgentsGet`: []AgentResponse
	fmt.Fprintf(os.Stdout, "Response from `AgentsAPI.ListAgentsV1AgentsGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiListAgentsV1AgentsGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]AgentResponse**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## RegisterAgentV1AgentsPost

> AgentResponse RegisterAgentV1AgentsPost(ctx).AgentRegisterRequest(agentRegisterRequest).Authorization(authorization).Execute()

Register Agent



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
	agentRegisterRequest := *openapiclient.NewAgentRegisterRequest("Name_example") // AgentRegisterRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AgentsAPI.RegisterAgentV1AgentsPost(context.Background()).AgentRegisterRequest(agentRegisterRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AgentsAPI.RegisterAgentV1AgentsPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `RegisterAgentV1AgentsPost`: AgentResponse
	fmt.Fprintf(os.Stdout, "Response from `AgentsAPI.RegisterAgentV1AgentsPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiRegisterAgentV1AgentsPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agentRegisterRequest** | [**AgentRegisterRequest**](AgentRegisterRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**AgentResponse**](AgentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

