# \SearchAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**SearchFactsGetV1SearchGet**](SearchAPI.md#SearchFactsGetV1SearchGet) | **Get** /v1/search | Search Facts Get
[**SearchFactsV1SearchPost**](SearchAPI.md#SearchFactsV1SearchPost) | **Post** /v1/search | Search Facts



## SearchFactsGetV1SearchGet

> []SearchResult SearchFactsGetV1SearchGet(ctx).Query(query).K(k).AsOf(asOf).GraphDepth(graphDepth).IncludeGraph(includeGraph).Authorization(authorization).Execute()

Search Facts Get



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
	query := "query_example" // string | 
	k := int32(56) // int32 |  (optional) (default to 5)
	asOf := "asOf_example" // string |  (optional)
	graphDepth := int32(56) // int32 |  (optional) (default to 0)
	includeGraph := true // bool |  (optional) (default to false)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SearchAPI.SearchFactsGetV1SearchGet(context.Background()).Query(query).K(k).AsOf(asOf).GraphDepth(graphDepth).IncludeGraph(includeGraph).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SearchAPI.SearchFactsGetV1SearchGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `SearchFactsGetV1SearchGet`: []SearchResult
	fmt.Fprintf(os.Stdout, "Response from `SearchAPI.SearchFactsGetV1SearchGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiSearchFactsGetV1SearchGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **query** | **string** |  | 
 **k** | **int32** |  | [default to 5]
 **asOf** | **string** |  | 
 **graphDepth** | **int32** |  | [default to 0]
 **includeGraph** | **bool** |  | [default to false]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]SearchResult**](SearchResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## SearchFactsV1SearchPost

> []SearchResult SearchFactsV1SearchPost(ctx).SearchRequest(searchRequest).Authorization(authorization).Execute()

Search Facts



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
	searchRequest := *openapiclient.NewSearchRequest("Query_example") // SearchRequest | 
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.SearchAPI.SearchFactsV1SearchPost(context.Background()).SearchRequest(searchRequest).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `SearchAPI.SearchFactsV1SearchPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `SearchFactsV1SearchPost`: []SearchResult
	fmt.Fprintf(os.Stdout, "Response from `SearchAPI.SearchFactsV1SearchPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiSearchFactsV1SearchPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **searchRequest** | [**SearchRequest**](SearchRequest.md) |  | 
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**[]SearchResult**](SearchResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

