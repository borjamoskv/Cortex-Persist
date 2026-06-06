# \TipsAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**GetTipsByCategoryTipsCategoryCategoryGet**](TipsAPI.md#GetTipsByCategoryTipsCategoryCategoryGet) | **Get** /tips/category/{category} | Get Tips By Category
[**GetTipsByProjectTipsProjectProjectGet**](TipsAPI.md#GetTipsByProjectTipsProjectProjectGet) | **Get** /tips/project/{project} | Get Tips By Project
[**GetTipsTipsGet**](TipsAPI.md#GetTipsTipsGet) | **Get** /tips | Get Tips
[**ListCategoriesTipsCategoriesGet**](TipsAPI.md#ListCategoriesTipsCategoriesGet) | **Get** /tips/categories | List Categories



## GetTipsByCategoryTipsCategoryCategoryGet

> TipsListResponse GetTipsByCategoryTipsCategoryCategoryGet(ctx, category).Lang(lang).Limit(limit).Authorization(authorization).Execute()

Get Tips By Category



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
	category := "category_example" // string | 
	lang := "lang_example" // string | Language code (en, es, eu) (optional) (default to "en")
	limit := int32(56) // int32 |  (optional) (default to 5)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TipsAPI.GetTipsByCategoryTipsCategoryCategoryGet(context.Background(), category).Lang(lang).Limit(limit).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TipsAPI.GetTipsByCategoryTipsCategoryCategoryGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetTipsByCategoryTipsCategoryCategoryGet`: TipsListResponse
	fmt.Fprintf(os.Stdout, "Response from `TipsAPI.GetTipsByCategoryTipsCategoryCategoryGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**category** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetTipsByCategoryTipsCategoryCategoryGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **lang** | **string** | Language code (en, es, eu) | [default to &quot;en&quot;]
 **limit** | **int32** |  | [default to 5]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**TipsListResponse**](TipsListResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetTipsByProjectTipsProjectProjectGet

> TipsListResponse GetTipsByProjectTipsProjectProjectGet(ctx, project).Lang(lang).Limit(limit).Authorization(authorization).Execute()

Get Tips By Project



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
	lang := "lang_example" // string | Language code (en, es, eu) (optional) (default to "en")
	limit := int32(56) // int32 |  (optional) (default to 3)
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TipsAPI.GetTipsByProjectTipsProjectProjectGet(context.Background(), project).Lang(lang).Limit(limit).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TipsAPI.GetTipsByProjectTipsProjectProjectGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetTipsByProjectTipsProjectProjectGet`: TipsListResponse
	fmt.Fprintf(os.Stdout, "Response from `TipsAPI.GetTipsByProjectTipsProjectProjectGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**project** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetTipsByProjectTipsProjectProjectGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **lang** | **string** | Language code (en, es, eu) | [default to &quot;en&quot;]
 **limit** | **int32** |  | [default to 3]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**TipsListResponse**](TipsListResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetTipsTipsGet

> TipsListResponse GetTipsTipsGet(ctx).Count(count).Lang(lang).Authorization(authorization).Execute()

Get Tips



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
	count := int32(56) // int32 | Number of tips to return (optional) (default to 1)
	lang := "lang_example" // string | Language code (en, es, eu) (optional) (default to "en")
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TipsAPI.GetTipsTipsGet(context.Background()).Count(count).Lang(lang).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TipsAPI.GetTipsTipsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetTipsTipsGet`: TipsListResponse
	fmt.Fprintf(os.Stdout, "Response from `TipsAPI.GetTipsTipsGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiGetTipsTipsGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **count** | **int32** | Number of tips to return | [default to 1]
 **lang** | **string** | Language code (en, es, eu) | [default to &quot;en&quot;]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**TipsListResponse**](TipsListResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListCategoriesTipsCategoriesGet

> CategoriesResponse ListCategoriesTipsCategoriesGet(ctx).Lang(lang).Authorization(authorization).Execute()

List Categories



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
	lang := "lang_example" // string | Language code (en, es, eu) (optional) (default to "en")
	authorization := "authorization_example" // string | Bearer <api-key> (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.TipsAPI.ListCategoriesTipsCategoriesGet(context.Background()).Lang(lang).Authorization(authorization).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `TipsAPI.ListCategoriesTipsCategoriesGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListCategoriesTipsCategoriesGet`: CategoriesResponse
	fmt.Fprintf(os.Stdout, "Response from `TipsAPI.ListCategoriesTipsCategoriesGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiListCategoriesTipsCategoriesGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **lang** | **string** | Language code (en, es, eu) | [default to &quot;en&quot;]
 **authorization** | **string** | Bearer &lt;api-key&gt; | 

### Return type

[**CategoriesResponse**](CategoriesResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

