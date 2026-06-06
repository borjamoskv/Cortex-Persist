# \AskAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**AskCortexV1AskPost**](AskAPI.md#AskCortexV1AskPost) | **Post** /v1/ask | Ask Cortex
[**AskStreamV1AskStreamPost**](AskAPI.md#AskStreamV1AskStreamPost) | **Post** /v1/ask/stream | Ask Stream
[**LlmStatusV1LlmStatusGet**](AskAPI.md#LlmStatusV1LlmStatusGet) | **Get** /v1/llm/status | Llm Status



## AskCortexV1AskPost

> AskResponse AskCortexV1AskPost(ctx).AskRequest(askRequest).Authorization(authorization).Execute()

Ask Cortex



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
	askRequest := *openapiclient.NewAskRequest("Query_example") // AskRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AskAPI.AskCortexV1AskPost(context.Background()).AskRequest(askRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AskAPI.AskCortexV1AskPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `AskCortexV1AskPost`: AskResponse
	fmt.Fprintf(os.Stdout, "Response from `AskAPI.AskCortexV1AskPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiAskCortexV1AskPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **askRequest** | [**AskRequest**](AskRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**AskResponse**](AskResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## AskStreamV1AskStreamPost

> interface{} AskStreamV1AskStreamPost(ctx).AskRequest(askRequest).Authorization(authorization).Execute()

Ask Stream



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
	askRequest := *openapiclient.NewAskRequest("Query_example") // AskRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AskAPI.AskStreamV1AskStreamPost(context.Background()).AskRequest(askRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AskAPI.AskStreamV1AskStreamPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `AskStreamV1AskStreamPost`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `AskAPI.AskStreamV1AskStreamPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiAskStreamV1AskStreamPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **askRequest** | [**AskRequest**](AskRequest.md) |  | 
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


## LlmStatusV1LlmStatusGet

> LLMStatusResponse LlmStatusV1LlmStatusGet(ctx).Authorization(authorization).Execute()

Llm Status



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
	resp, r, err := apiClient.AskAPI.LlmStatusV1LlmStatusGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AskAPI.LlmStatusV1LlmStatusGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `LlmStatusV1LlmStatusGet`: LLMStatusResponse
	fmt.Fprintf(os.Stdout, "Response from `AskAPI.LlmStatusV1LlmStatusGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiLlmStatusV1LlmStatusGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**LLMStatusResponse**](LLMStatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

