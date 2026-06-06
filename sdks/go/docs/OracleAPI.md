# \OracleAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**AuditTargetV1OracleAuditPost**](OracleAPI.md#AuditTargetV1OracleAuditPost) | **Post** /v1/oracle/audit | Audit Target



## AuditTargetV1OracleAuditPost

> OracleResponse AuditTargetV1OracleAuditPost(ctx).OracleRequest(oracleRequest).Authorization(authorization).Execute()

Audit Target



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
	oracleRequest := *openapiclient.NewOracleRequest("TargetUrl_example") // OracleRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.OracleAPI.AuditTargetV1OracleAuditPost(context.Background()).OracleRequest(oracleRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `OracleAPI.AuditTargetV1OracleAuditPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `AuditTargetV1OracleAuditPost`: OracleResponse
	fmt.Fprintf(os.Stdout, "Response from `OracleAPI.AuditTargetV1OracleAuditPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiAuditTargetV1OracleAuditPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **oracleRequest** | [**OracleRequest**](OracleRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**OracleResponse**](OracleResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

