# \ExergyProxyAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**ProxyChatCompletionsLlmProxyV1ChatCompletionsPost**](ExergyProxyAPI.md#ProxyChatCompletionsLlmProxyV1ChatCompletionsPost) | **Post** /llm-proxy/v1/chat/completions | Proxy Chat Completions



## ProxyChatCompletionsLlmProxyV1ChatCompletionsPost

> interface{} ProxyChatCompletionsLlmProxyV1ChatCompletionsPost(ctx).Execute()

Proxy Chat Completions



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

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ExergyProxyAPI.ProxyChatCompletionsLlmProxyV1ChatCompletionsPost(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ExergyProxyAPI.ProxyChatCompletionsLlmProxyV1ChatCompletionsPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ProxyChatCompletionsLlmProxyV1ChatCompletionsPost`: interface{}
	fmt.Fprintf(os.Stdout, "Response from `ExergyProxyAPI.ProxyChatCompletionsLlmProxyV1ChatCompletionsPost`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiProxyChatCompletionsLlmProxyV1ChatCompletionsPostRequest struct via the builder pattern


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

