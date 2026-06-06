# \RuntimeAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**GetBootRecoveryV1RuntimeBootRecoveryGet**](RuntimeAPI.md#GetBootRecoveryV1RuntimeBootRecoveryGet) | **Get** /v1/runtime/boot_recovery | Get Boot Recovery
[**GetHealthV1RuntimeHealthGet**](RuntimeAPI.md#GetHealthV1RuntimeHealthGet) | **Get** /v1/runtime/health | Get Health



## GetBootRecoveryV1RuntimeBootRecoveryGet

> RecoveryReport GetBootRecoveryV1RuntimeBootRecoveryGet(ctx).Execute()

Get Boot Recovery



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
	resp, r, err := apiClient.RuntimeAPI.GetBootRecoveryV1RuntimeBootRecoveryGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `RuntimeAPI.GetBootRecoveryV1RuntimeBootRecoveryGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetBootRecoveryV1RuntimeBootRecoveryGet`: RecoveryReport
	fmt.Fprintf(os.Stdout, "Response from `RuntimeAPI.GetBootRecoveryV1RuntimeBootRecoveryGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiGetBootRecoveryV1RuntimeBootRecoveryGetRequest struct via the builder pattern


### Return type

[**RecoveryReport**](RecoveryReport.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetHealthV1RuntimeHealthGet

> map[string]interface{} GetHealthV1RuntimeHealthGet(ctx).Execute()

Get Health



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
	resp, r, err := apiClient.RuntimeAPI.GetHealthV1RuntimeHealthGet(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `RuntimeAPI.GetHealthV1RuntimeHealthGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetHealthV1RuntimeHealthGet`: map[string]interface{}
	fmt.Fprintf(os.Stdout, "Response from `RuntimeAPI.GetHealthV1RuntimeHealthGet`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiGetHealthV1RuntimeHealthGetRequest struct via the builder pattern


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

