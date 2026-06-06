# \DaemonAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**DaemonStatusV1DaemonStatusGet**](DaemonAPI.md#DaemonStatusV1DaemonStatusGet) | **Get** /v1/daemon/status | Daemon Status



## DaemonStatusV1DaemonStatusGet

> map[string]interface{} DaemonStatusV1DaemonStatusGet(ctx).Authorization(authorization).Execute()

Daemon Status



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
	resp, r, err := apiClient.DaemonAPI.DaemonStatusV1DaemonStatusGet(context.Background()).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `DaemonAPI.DaemonStatusV1DaemonStatusGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `DaemonStatusV1DaemonStatusGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `DaemonAPI.DaemonStatusV1DaemonStatusGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiDaemonStatusV1DaemonStatusGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
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

