# \GraphAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**GetGraphAllV1GraphGet**](GraphAPI.md#GetGraphAllV1GraphGet) | **Get** /v1/graph | Get Graph All
[**GetGraphV1GraphProjectGet**](GraphAPI.md#GetGraphV1GraphProjectGet) | **Get** /v1/graph/{project} | Get Graph



## GetGraphAllV1GraphGet

> map[string]interface{} GetGraphAllV1GraphGet(ctx).Limit(limit).Authorization(authorization).Execute()

Get Graph All



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
	resp, r, err := apiClient.GraphAPI.GetGraphAllV1GraphGet(context.Background()).Limit(limit).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GraphAPI.GetGraphAllV1GraphGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetGraphAllV1GraphGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `GraphAPI.GetGraphAllV1GraphGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetGraphAllV1GraphGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **limit** | **int32** |  | [default to 50]
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


## GetGraphV1GraphProjectGet

> map[string]interface{} GetGraphV1GraphProjectGet(ctx, project).Limit(limit).Authorization(authorization).Execute()

Get Graph



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
	project := "project_example" // string | 
	limit := int32(56) // int32 |  (optional) (default to 50)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.GraphAPI.GetGraphV1GraphProjectGet(context.Background(), project).Limit(limit).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `GraphAPI.GetGraphV1GraphProjectGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetGraphV1GraphProjectGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `GraphAPI.GetGraphV1GraphProjectGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**project** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetGraphV1GraphProjectGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **limit** | **int32** |  | [default to 50]
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

