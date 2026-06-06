# \TranslateAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**TranslateTextsV1TranslatePost**](TranslateAPI.md#TranslateTextsV1TranslatePost) | **Post** /v1/translate | Translate Texts



## TranslateTextsV1TranslatePost

> TranslateResponse TranslateTextsV1TranslatePost(ctx).TranslateRequest(translateRequest).Authorization(authorization).Execute()

Translate Texts



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
	translateRequest := *openapiclient.NewTranslateRequest(map[string]string{"key": "Inner_example"}, []string{"TargetLanguages_example"}) // TranslateRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TranslateAPI.TranslateTextsV1TranslatePost(context.Background()).TranslateRequest(translateRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TranslateAPI.TranslateTextsV1TranslatePost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `TranslateTextsV1TranslatePost`: TranslateResponse
	fmt.Fprintf(os.Stdout, "Response from `TranslateAPI.TranslateTextsV1TranslatePost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiTranslateTextsV1TranslatePostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **translateRequest** | [**TranslateRequest**](TranslateRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**TranslateResponse**](TranslateResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

